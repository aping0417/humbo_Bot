import discord
import discord.context_managers
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
from pytube import YouTube
import json
import asyncio
from cogs.playlist import Playlist
from core.classes import Cog_Extension
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
from discord import ui, Interaction, ButtonStyle
import logging

load_dotenv()

log = logging.getLogger("music")

ydl_opts = {
    "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",  # 格式
    "quiet": True,  # 抑制 youtube_dl 的大部分输出
    "extractaudio": True,  # 只抓聲音
    "outtmpl": "downloads/%(title)s.%(ext)s",  # 指定下载文件的输出模板
    "noplaylist": False,  # 禁用播放清單（之後會開放）
    # 'postprocessors': [{
    # 'key': 'FFmpegExtractAudio',
    # 'preferredcodec': 'm4a',  # 转换为 mp3
    # 'preferredquality': '192',  # 设置比特率为192k
    # }], （這些是限制版本）
}
ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# 建立 Spotify 客戶端（建議用環境變數儲存）
sp = Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    )
)


def extract_spotify_track_info(url):
    try:
        if "track" in url:
            track = sp.track(url)
            if track and track.get("name") and track.get("artists"):
                return [f"{track['name']} {track['artists'][0]['name']}"]
            else:
                return []

        elif "playlist" in url:
            playlist = sp.playlist_tracks(url)
            result = []
            for item in playlist["items"]:
                track = item.get("track")
                if track and track.get("name") and track.get("artists"):
                    result.append(f"{track['name']} {track['artists'][0]['name']}")
            return result

    except Exception as e:
        print(f"[Spotify] 錯誤: {e}")
        return []


# 設定 -reconnect 1 （斷線自動重連） -reconnect_streamed 1（處理Streaming Media會自動重連）
# -reconnect_delay_max 5(斷線5秒內會自動重連) "options": "-vn" （只處理聲音）


class MusicPlayer:
    def __init__(self, playlist_manager):
        self.play_queue = []  # 每首歌格式：("url", "title", playlist_name)
        self.playlist_manager = playlist_manager
        self.current_playlist_id = None  # ⬅️ 播放中的 playlist（由 guild_id 給）
        self._panel_updater = None  # ← 新增：外部註冊

    def set_panel_updater(self, updater_coro):
        """註冊一個協程函式：async def updater_coro(guild_id, vc): ..."""
        self._panel_updater = updater_coro

    async def _maybe_update_panel(self, voice_client):
        if not self._panel_updater:
            return
        try:
            guild_id = str(voice_client.guild.id)
            await self._panel_updater(guild_id, voice_client)
        except Exception as e:
            print(f"[panel_update] {e}")

    def play_next(self, voice_client):
        if not voice_client or not voice_client.is_connected():
            log.warning("⚠️ Voice client 不存在或未連線")
            return

        if self.play_queue:
            url, title, playlist_name = self.play_queue.pop(0)
            log.info(f"從佇列播放：{title} ({url}), 來源 playlist={playlist_name}")
        elif self.current_playlist_id:
            result = self.playlist_manager.pop_next_song(self.current_playlist_id)
            if result:
                title, url = result
                playlist_name = self.current_playlist_id
                log.info(f"從資料庫播放：{title} ({url})，guild={playlist_name}")
            else:
                log.info(f"guild={self.current_playlist_id} 歌單已空，停止播放")
                self.current_playlist_id = None
                # 播放結束 → 嘗試刷新面板（讓播放鍵恢復可按）
                vc = voice_client
                loop = vc.client.loop
                loop.create_task(self._maybe_update_panel(vc))
                return
        else:
            log.info("沒有可播放的歌曲")
            return

        try:
            source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
            voice_client.play(
                source,
                after=lambda e: self._after_song(e, voice_client, playlist_name, url),
            )
            log.info(f"▶️ 正在播放：{title}")

            # 開播 → 播放鍵應禁用、暫停鍵顯示「暫停」
            vc = voice_client
            loop = vc.client.loop
            loop.create_task(self._maybe_update_panel(vc))

        except Exception as e:
            log.exception(f"❌ 播放失敗：{e}")
            self.play_next(voice_client)

    def _after_song(self, error, voice_client, playlist_name, url):
        if error:
            log.error(f"⚠️ 播放錯誤：{error} | {url}")
        # 下一首
        loop = voice_client.client.loop
        loop.call_soon_threadsafe(self.play_next, voice_client)

    def add_to_queue(self, url, title=None, playlist_name=None):
        if not title:
            real_url, title = self.download_audio(url)
        else:
            real_url = url  # 如果已經有 title，代表是資料庫來的，保持原樣

        self.play_queue.append((real_url, title, playlist_name))
        log.info(f"加入佇列：{title} ({real_url}) playlist={playlist_name}")
        return title

    # def add_to_queue(self, url):
    #     """將歌曲加入播放隊列"""
    #     audio_url, title = self.download_audio(url)
    #     self.play_queue.append((audio_url, title))
    #     return title

    USE_FORMAT_5 = True  # 可開關的 flag

    def download_audio(self, url_or_keyword):
        """從 URL 或關鍵字取得音訊"""
        original = url_or_keyword
        if (
            not url_or_keyword.startswith("ytsearch:")
            and "youtube.com" not in url_or_keyword
            and "youtu.be" not in url_or_keyword
        ):
            # 自動加上 ytsearch 前綴
            url_or_keyword = f"ytsearch:{url_or_keyword}"
            log.info(f"使用 ytsearch 搜尋：{original}")

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_or_keyword, download=False)

            if "entries" in info:
                info = info["entries"][0]  # 選取第一筆搜尋結果
                log.info(f"ytsearch 命中：{info.get('title')}")

            title = info.get("title", "未知標題")

            for f in info.get("formats", []):
                if (
                    f.get("acodec") != "none"
                    and f.get("vcodec") == "none"
                    and f.get("url")
                ):
                    log.info(
                        f"選用格式：{f['format_id']} - {f['ext']} - {f.get('acodec')} / {f.get('vcodec')}"
                    )
                    return f["url"], title

            # 備用方案
            log.warning(f"未找到理想音訊格式，改用預設 url：{title}")
            return info["url"], title

    def ensure_start_from_db(self, guild_id: str) -> bool:
        try:
            self.playlist_manager.ensure_playlist_exists(guild_id)
            if not self.current_playlist_id:
                self.current_playlist_id = guild_id
            songs = self.playlist_manager.get_songs(guild_id)
            return bool(songs)
        except Exception as e:
            print(f"[ensure_start_from_db] error: {e}")
            return False


class MusicControlView(ui.View):
    def __init__(self, player):
        super().__init__(timeout=None)
        self.player = player  # 只保存 player

    # 小工具：找指定 custom_id 的按鈕
    def _btn(self, cid: str) -> ui.Button | None:
        for c in self.children:
            if isinstance(c, ui.Button) and getattr(c, "custom_id", None) == cid:
                return c
        return None

    # 同步「暫停/繼續」外觀
    def _set_pause_visual(self, paused: bool):
        b = self._btn("pause")
        if not b:
            return
        if paused:
            b.label = "▶️ 繼續播放"
            b.style = ButtonStyle.green
        else:
            b.label = "⏸️ 暫停"
            b.style = ButtonStyle.blurple

    # 播放鍵啟用/停用
    def _set_play_disabled(self, disabled: bool):
        b = self._btn("play")
        if b:
            b.disabled = disabled

    # 依據目前 voice 狀態同步整體 UI（/panel 初次建立會用）
    def sync_with_voice(self, vc):
        self._set_pause_visual(paused=bool(vc and vc.is_paused()))
        # 若正在播放就把播放鍵禁用，沒在播則啟用
        self._set_play_disabled(bool(vc and vc.is_playing()))

    # ▶️ 播放（公開訊息：直接 edit_message）
    @ui.button(label="▶️ 播放", style=ButtonStyle.green, custom_id="play")
    async def play(self, interaction: Interaction, button: ui.Button):
        try:
            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                await interaction.response.send_message(
                    "❌ 我不在語音頻道裡。先用 `/join` 或 `/panel`。"
                )
                return

            guild_id = str(interaction.guild.id)
            has_db_songs = self.player.ensure_start_from_db(guild_id)
            if not self.player.play_queue and not has_db_songs:
                await interaction.response.send_message(
                    "📭 沒有可播放的歌曲。先用 `/add_song` 加一些吧。"
                )
                return

            if not vc.is_playing():
                self.player.play_next(vc)

            # 播放中把播放鍵禁用
            self._set_play_disabled(True)
            self._set_pause_visual(paused=False)
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("▶️ 開始播放！", ephemeral=True)
            log.info(
                f"[button:play] 觸發者={interaction.user} guild={interaction.guild.id}"
            )

        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ 播放失敗：{e}")
            else:
                await interaction.followup.send(f"⚠️ 播放失敗：{e}")

    # ⏸️/▶️ 暫停/繼續（同一顆按鈕）
    @ui.button(label="⏸️ 暫停", style=ButtonStyle.blurple, custom_id="pause")
    async def pause(self, interaction: Interaction, button: ui.Button):
        try:
            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                await interaction.response.send_message("❌ 我不在語音頻道裡。")
                return

            if vc.is_playing():
                vc.pause()
                self._set_pause_visual(paused=True)
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("⏸️ 已暫停播放。", ephemeral=True)

            elif vc.is_paused():
                vc.resume()
                self._set_pause_visual(paused=False)
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("▶️ 已繼續播放。", ephemeral=True)

            else:
                await interaction.response.send_message("⚠️ 目前沒有正在播放的音樂。")

        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ 暫停/繼續失敗：{e}")
            else:
                await interaction.followup.send(f"⚠️ 暫停/繼續失敗：{e}")

    # ⏭️ 跳過：會觸發 after，進入下一首
    @ui.button(label="⏭️ 跳過", style=ButtonStyle.grey, custom_id="skip")
    async def skip(self, interaction: Interaction, button: ui.Button):
        try:
            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                await interaction.response.send_message("❌ 我不在語音頻道裡。")
                return
            if vc.is_playing() or vc.is_paused():
                vc.stop()
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("⏭️ 已跳過。", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ 沒有歌曲可跳過。")
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ 跳過失敗：{e}")
            else:
                await interaction.followup.send(f"⚠️ 跳過失敗：{e}")

    # ⏹️ 停止：離開語音、恢復播放鍵可按
    @ui.button(label="⏹️ 停止", style=ButtonStyle.red, custom_id="stop")
    async def stop(self, interaction: Interaction, button: ui.Button):
        try:
            vc = interaction.guild.voice_client
            if vc and vc.is_connected():
                await vc.disconnect()
                self._set_pause_visual(paused=False)
                self._set_play_disabled(False)  # 可再次播放
                await interaction.response.edit_message(view=self)
                await interaction.followup.send(
                    "⏹️ 已停止播放並離開語音頻道。", ephemeral=True
                )
            else:
                await interaction.response.send_message("⚠️ 我沒有連線到語音頻道。")
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ 停止失敗：{e}")
            else:
                await interaction.followup.send(f"⚠️ 停止失敗：{e}")


class Music(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot  # ✅ 確保 `bot` 存在
        self.playlist_manager = Playlist(bot)  # ✅ 讓 `Music` 管理歌單
        # ✅ `Music` 內部包含 `MusicPlayer`
        self.player = MusicPlayer(self.playlist_manager)

        # 面板訊息管理：guild_id -> (channel_id, message_id)
        self.panel_map: dict[str, tuple[int, int]] = {}

        # 把刷新函式註冊給 player
        self.player.set_panel_updater(self._refresh_panel_ui)

        # 註冊持久化 View（重開後仍可互動）
        self.bot.add_view(MusicControlView(self.player))
        print("✅ Music Cog 已註冊控制面板 View")

    async def __join(self, interaction: discord.Interaction):

        if interaction.user.voice == None:
            await interaction.response.send_message(
                "你尚未進入任何語音頻道", silent=True
            )
        else:
            voicechannel = interaction.user.voice.channel
            # await interaction.response.send_message(voicechannel.mention, silent=True)
            await voicechannel.connect()
            await interaction.response.send_message("已進入語音頻道", silent=True)

    async def _refresh_panel_ui(self, guild_id: str, vc):
        """被 MusicPlayer 呼叫：刷新該公會的面板按鈕外觀"""
        try:
            rec = self.panel_map.get(guild_id)
            if not rec:
                return
            channel_id, message_id = rec
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(
                channel_id
            )
            msg = await channel.fetch_message(message_id)
            view = MusicControlView(self.player)
            view.sync_with_voice(vc)
            await msg.edit(view=view)
        except Exception as e:
            print(f"[refresh_panel_ui] {e}")

    async def _send_or_replace_panel(self, interaction: discord.Interaction, vc):
        """發送或更新本公會唯一的公開控制面板訊息（已在 /panel 中 defer）"""
        guild_id = str(interaction.guild.id)
        view = MusicControlView(self.player)
        view.sync_with_voice(vc)

        rec = self.panel_map.get(guild_id)

        # 如果有舊面板，嘗試更新
        if rec:
            channel_id, message_id = rec
            try:
                channel = self.bot.get_channel(
                    channel_id
                ) or await self.bot.fetch_channel(channel_id)
                msg = await channel.fetch_message(message_id)
                await msg.edit(content="🎛 音樂控制面板：", view=view)

                # 因為 /panel 已經 defer，所以這裡用 followup
                await interaction.followup.send(
                    "✅ 已更新現有控制面板。", ephemeral=True
                )
                return
            except Exception as e:
                # 舊訊息不見/失敗就重建
                log.warning(f"[panel] 舊面板更新失敗，改為建立新面板：{e}")

        # 沒有舊面板就建立新的（公開訊息）
        sent = await interaction.followup.send("🎛 音樂控制面板：", view=view)
        self.panel_map[guild_id] = (sent.channel.id, sent.id)
        log.info(
            f"[panel] 建立新控制面板 guild={guild_id} ch={sent.channel.id} msg={sent.id}"
        )

    @app_commands.command(name="leave", description="讓機器人離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            await interaction.response.send_message("❌ 機器人不在語音頻道內！")
        else:
            await voice_client.disconnect()
            await interaction.response.send_message("✅ 機器人已離開語音頻道！")

    @app_commands.command(name="join", description="加入語音")
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                "❌ 你沒有加入語音頻道！", ephemeral=True
            )
            return

        # ✅ 自動建立歌單
        guild_id = str(interaction.guild.id)
        self.playlist_manager.ensure_playlist_exists(guild_id)

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await self.__join(interaction)
            voice_client = interaction.guild.voice_client  # 加入後重新取得
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

    @app_commands.command(name="list", description="看播放佇列")
    async def list(self, interaction: discord.Interaction):
        if not self.player.play_queue:
            await interaction.response.send_message("📭 播放清單是空的。")
        else:
            queue_display = "\n".join(
                f"{i+1}. {title}" for i, (title, _) in enumerate(self.player.play_queue)
            )
        await interaction.response.send_message(f"📃 播放清單:\n{queue_display}")

    @app_commands.command(name="create_playlist", description="創建新的歌單 已經停用了")
    async def create_playlist(self, interaction: discord.Interaction, name: str):
        await interaction.response.send_message(f"就跟你說停用了還建 你是看不懂是不是")

    @app_commands.command(
        name="add_song", description="新增歌曲或整份播放清單到伺服器歌單"
    )
    async def add_song(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        guild_id = str(interaction.guild.id)
        log.info(f"[add_song] guild={guild_id} user={interaction.user} url={url}")
        self.playlist_manager.ensure_playlist_exists(guild_id)

        try:
            # ▓▓ Spotify 音樂 ▓▓
            if "open.spotify.com" in url:
                search_titles = extract_spotify_track_info(url)
                if not search_titles:
                    await interaction.followup.send(
                        "❌ Spotify 無法解析或播放清單為空。"
                    )
                    return

                for keyword in search_titles:
                    search_url = f"ytsearch:{keyword}"
                    audio_url, title = self.player.download_audio(search_url)
                    self.playlist_manager.add_song(guild_id, title, audio_url)

                await interaction.followup.send(
                    f"✅ 已新增 `{len(search_titles)}` 首 Spotify 歌曲到歌單"
                )
                log.info(
                    f"[add_song] Spotify → 實際新增 {len(search_titles)} 首到 guild={guild_id}"
                )

                return

            # ▓▓ YouTube 播放清單 ▓▓
            if "playlist?" in url or "list=" in url:
                flat_opts = {
                    **ydl_opts,
                    "extract_flat": "in_playlist",
                    "skip_download": True,
                }
                with youtube_dl.YoutubeDL(flat_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    entries = info.get("entries", [])
                    if not entries:
                        await interaction.followup.send(
                            "⚠️ 播放清單中沒有可加入的歌曲。"
                        )
                        return

                    added_count = 0
                    for video in entries:
                        video_id = video.get("id")
                        title = video.get("title", "未知標題")

                        try:
                            if not video_id:
                                print("⚠️ 無法取得影片 ID，略過")
                                continue

                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            audio_url, confirmed_title = self.player.download_audio(
                                video_url
                            )
                            self.playlist_manager.add_song(
                                guild_id, confirmed_title, audio_url
                            )
                            print(f"✅ 已加入：{confirmed_title}")
                            added_count += 1

                        except Exception as e:
                            print(f"❌ 加入 `{title}` 時失敗：{str(e)}")

                    await interaction.followup.send(
                        f"✅ 已新增 {added_count} 首歌曲到歌單！"
                    )
                    log.info(
                        f"[add_song] YT playlist 解析，共 {len(entries)} 筆，成功加入 {added_count} 首 (guild={guild_id})"
                    )

                return

            # ▓▓ 單首 YouTube 歌曲 ▓▓
            audio_url, title = self.player.download_audio(url)
            self.playlist_manager.add_song(guild_id, title, audio_url)
            await interaction.followup.send(f"✅ 已新增 `{title}` 到本伺服器的歌單")
            log.info(f"[add_song] 單首 YT：{title} 加入 guild={guild_id}")

        except Exception as e:
            await interaction.followup.send(f"❌ 發生錯誤：{str(e)}")

    @app_commands.command(name="play_playlist", description="播放這個伺服器的歌單")
    async def play_playlist(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.playlist_manager.ensure_playlist_exists(guild_id)

        if interaction.user.voice is None:
            await interaction.response.send_message(
                "❌ 你沒有加入語音頻道！", ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        # ✅ 用 helper 確保 current_playlist_id 與 DB 狀態
        has_db_songs = self.player.ensure_start_from_db(guild_id)
        if not has_db_songs and not self.player.play_queue:
            await interaction.response.send_message(
                "📭 這個歌單是空的。先用 `/add_song` 加一些吧。"
            )
            return

        # 開播
        if not voice_client.is_playing():
            self.player.play_next(voice_client)

        await interaction.response.send_message("▶️ 正在播放本伺服器的歌單")
        await self._refresh_panel_ui(
            str(interaction.guild.id), interaction.guild.voice_client
        )
        log.info(f"[play_playlist] guild={guild_id} by {interaction.user}")

    @app_commands.command(name="play", description="撥放音樂")
    async def play(self, interaction: discord.Interaction, url: str):
        try:
            if interaction.user.voice is None:
                await interaction.response.send_message(
                    "你沒有加入任何語音頻道", ephemeral=True
                )
                return
            voice＿channel = interaction.user.voice.channel
            voice＿client = (
                interaction.guild.voice_client
            )  # 機器人在的伺服器的聲音的內容

            if voice_client is None:
                # voice_client = await voice＿channel.connect()
                await self.__join(interaction)
                # print("before")
                # await playmusic()
                await interaction.response.send_message(f"網址{url}", silent=True)
            elif voice＿client.channel != voice_channel:
                # voice_client = discord.VoiceClient
                await voice_client.move_to(self=voice_client, channel=voice_channel)
                # await interaction.response.send_message("test123")
            # else:
            # return
            # downloaded_format = info.get('format')
            # print(f"下载的格式: {downloaded_format}")

            # if not isinstance(voice_client, discord.VoiceClient):
            # await interaction.response.send_message("語音客戶端不可用", silent=True)
            # return

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                songtitle = info.get("title", None)
                # for i, fmt in enumerate(info.get('formats', [])):
                # print(f"Format {i}: {fmt['format_id']} - {fmt['ext']} - {fmt['url']}")
                # (這是詳細的格式也是剛開始看的)

                url2 = info["formats"][6]["url"]  # 第6個格式

                # downloaded_format = info.get('format')
                # print(f"下载的格式: {downloaded_format}")
                # (剛開始拿來看有啥格式能撥用的)

            # await asyncio.gather(play＿next_song(), sendmsg())
            print("哈嚕")

            # voice_client.stop()
            async def playmusic():
                try:
                    voice_client.play(
                        discord.FFmpegPCMAudio(url2, **ffmpeg_options),
                        after=lambda e: print(f"Player error: {e}") if e else None,
                    )
                except Exception as e:
                    await interaction.response.send_message(
                        f"音樂錯誤：{str(e)}", silent=True
                    )

            async def sendmsg():
                try:
                    # print("我自你前面")
                    await interaction.response.send_message(
                        f"{songtitle}\n網址:{url}", silent=True
                    )
                    # print("我自你後面")
                except Exception as e:
                    await interaction.response.send_message(
                        f"訊息錯誤：{str(e)}", silent=True
                    )

            # print(type(voice_client.channel))
            # print(type(voice_channel))

            async def play_next_song(voice_client):
                try:
                    ffmpeg_options = {
                        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                        "options": "-vn",
                    }
                    voice_client = discord.VoiceClient
                    voice_client.play(
                        discord.FFmpegPCMAudio(url2, **ffmpeg_options),
                    )
                except Exception as e:
                    await interaction.response.send_message(
                        f"錯誤:{str(e)}", silent=True
                    )

            # await asyncio.gather(playmusic(), sendmsg())
            # return
            if not voice_client.is_playing():
                print("yes or no")
                await asyncio.gather(playmusic(), sendmsg())
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤：{str(e)}", silent=True)

    @app_commands.command(name="show_playlist", description="查看這個伺服器的歌單")
    async def show_playlist(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.playlist_manager.ensure_playlist_exists(guild_id)

        songs = self.playlist_manager.get_songs(guild_id)
        if not songs:
            await interaction.response.send_message("⚠️ 本伺服器的歌單是空的。")
            return

        display = "\n".join(f"{i+1}. {title}" for i, (title, _) in enumerate(songs))
        await interaction.response.send_message(f"📀 本伺服器歌單內容：\n{display}")

    @app_commands.command(name="clear_playlist", description="清除本伺服器所有歌")
    async def clear_playlist(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        try:
            self.playlist_manager.clear_playlist(guild_id)
            await interaction.response.send_message("🗑 已清除本伺服器歌單")
        except Exception as e:
            await interaction.response.send_message(f"❌ 錯誤：{str(e)}")

    @app_commands.command(name="pause", description="暫停 / 繼續 播放")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None or not voice_client.is_connected():
            await interaction.response.send_message(
                "❌ 我不在任何語音頻道裡。", ephemeral=True
            )
            return

        # 正在播放 → 暫停
        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("⏸️ 已暫停播放。", ephemeral=True)
            return

        # 已暫停 → 繼續
        if voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("▶️ 已繼續播放。", ephemeral=True)
            return

        # 沒有正在播放的來源
        await interaction.response.send_message(
            "⚠️ 目前沒有正在播放的音樂。", ephemeral=True
        )

    @app_commands.command(
        name="panel", description="顯示音樂控制面板（公開訊息，全員可操作）"
    )
    async def panel(self, interaction: discord.Interaction):
        # 必須在語音頻道
        if interaction.user.voice is None:
            await interaction.response.send_message(
                "❌ 你尚未加入語音頻道！", ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        # 先 defer，避免語音連線超過 3 秒導致互動過期
        await interaction.response.defer(thinking=True)

        try:
            if vc is None:
                # 沒有連線 → 直接照 join_test 的寫法連
                vc = await voice_channel.connect(reconnect=False)
                log.info(
                    f"[panel] 新語音連線 guild={interaction.guild.id} ch={voice_channel.id}"
                )

            elif vc.channel != voice_channel:
                # 已連到別的語音 → 移過來
                await vc.move_to(voice_channel)
                log.info(
                    f"[panel] 移動語音連線 guild={interaction.guild.id} ch={voice_channel.id}"
                )

            elif not vc.is_connected():
                # 有 vc 但掛掉了 → 重連
                vc = await voice_channel.connect(reconnect=False)
                log.info(
                    f"[panel] 重新建立語音連線 guild={interaction.guild.id} ch={voice_channel.id}"
                )

        except Exception as e:
            log.exception(f"[panel] 語音連線失敗 guild={interaction.guild.id}")
            await interaction.followup.send(f"❌ 無法連線語音頻道：{e}", ephemeral=True)
            return

        # 語音連線成功 → 建立或更新面板
        await self._send_or_replace_panel(interaction, vc)

    # @app_commands.command()
    # async def skip(): ...

    # @app_commands.command()
    # async def nowplay(): ...

    # @app_commands.command()
    # async def skipto(): ...

    # @app_commands.command()
    # async def shuffle(): ...

    # @app_commands.command()
    # async def repeat(): ...


async def setup(bot):
    await bot.add_cog(Music(bot))
