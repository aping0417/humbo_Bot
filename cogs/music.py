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

load_dotenv()


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

    def play_next(self, voice_client):
        if not voice_client or not voice_client.is_connected():
            print("⚠️ Voice client 不存在或未連線")
            return

        if self.play_queue:
            url, title, playlist_name = self.play_queue.pop(0)
        elif self.current_playlist_id:
            result = self.playlist_manager.pop_next_song(self.current_playlist_id)
            if result:
                title, url = result
                playlist_name = self.current_playlist_id
            else:
                print("📭 播放清單已空")
                self.current_playlist_id = None
                return
        else:
            return

        try:
            source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
            voice_client.play(
                source,
                after=lambda e: self._after_song(e, voice_client, playlist_name, url),
            )
            print(f"▶️ 正在播放：{title}")
        except Exception as e:
            print(f"❌ 播放失敗：{e}")
            self.play_next(voice_client)

    def _after_song(self, error, voice_client, playlist_name, url):
        if error:
            print(f"⚠️ 播放錯誤：{error}")
        # elif playlist_name:
        #    print(f"🗑 播完後從 `{playlist_name}` 移除歌曲")
        #   self.playlist_manager.delete_song_by_url(playlist_name, url)

        self.play_next(voice_client)

    def add_to_queue(self, url, title=None, playlist_name=None):
        if not title:
            real_url, title = self.download_audio(url)
        else:
            real_url = url  # 如果已經有 title，代表是資料庫來的，保持原樣

        print(f"📌 加入隊列的網址：{real_url}")
        self.play_queue.append((real_url, title, playlist_name))
        return title

    # def add_to_queue(self, url):
    #     """將歌曲加入播放隊列"""
    #     audio_url, title = self.download_audio(url)
    #     self.play_queue.append((audio_url, title))
    #     return title

    USE_FORMAT_5 = True  # 可開關的 flag

    def download_audio(self, url):
        """安全地抓取穩定的音訊格式"""
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # ✅ 若是 ytsearch: 回傳的是多個 entry（搜尋結果）
            if "entries" in info:
                info = info["entries"][0]  # 取第一個搜尋結果

            songtitle = info.get("title", "未知標題")

            # 只抓 m4a itag=140 或 webm itag=251
            for f in info.get("formats", []):
                if f["format_id"] in ["140", "251"]:
                    return f["url"], songtitle

            return info["url"], songtitle

    # @app_commands.command(name="join", description="join to channel")    下次多寫一個app command 呼叫join


class Music(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot  # ✅ 確保 `bot` 存在
        self.playlist_manager = Playlist(bot)  # ✅ 讓 `Music` 管理歌單
        # ✅ `Music` 內部包含 `MusicPlayer`
        self.player = MusicPlayer(self.playlist_manager)

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

    @app_commands.command(name="leave", description="讓機器人離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            await interaction.response.send_message("❌ 機器人不在語音頻道內！")
        else:
            await voice_client.disconnect()
            await interaction.response.send_message("✅ 機器人已離開語音頻道！")

    @app_commands.command(name="join", description="加入語音")
    async def join(self, interaction: discord.Interaction, url: str):
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

        title = self.player.add_to_queue(url, title=None, playlist_name=guild_id)

        if not voice_client.is_playing():
            self.player.play_next(voice_client)

        await interaction.response.send_message(f"🎵 `{title}` 已加入播放列表！")

    @app_commands.command(name="pause", description="暫停音樂")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        voice_client = discord.VoiceClient
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("⏸️ 音樂暫停！")
        else:
            await interaction.response.send_message("❌ 沒有正在播放的音樂！")

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
                return

            # ▓▓ YouTube 播放清單 ▓▓
            if "playlist?" in url or "list=" in url:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    entries = info.get("entries", [])
                    if not entries:
                        await interaction.followup.send(
                            "⚠️ 播放清單中沒有可加入的歌曲。"
                        )
                        return

                    for video in entries:
                        video_url = f"https://www.youtube.com/watch?v={video['id']}"
                        title = video.get("title", "未知標題")
                        self.playlist_manager.add_song(guild_id, title, video_url)

                    await interaction.followup.send(
                        f"✅ 已新增 {len(entries)} 首歌到歌單"
                    )
                return

            # ▓▓ 單首 YouTube 歌曲 ▓▓
            audio_url, title = self.player.download_audio(url)
            self.playlist_manager.add_song(guild_id, title, audio_url)
            await interaction.followup.send(f"✅ 已新增 `{title}` 到本伺服器的歌單")

        except Exception as e:
            await interaction.followup.send(f"❌ 發生錯誤：{str(e)}")

    @app_commands.command(name="play_playlist", description="播放這個伺服器的歌單")
    async def play_playlist(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.playlist_manager.ensure_playlist_exists(guild_id)

        songs = self.playlist_manager.get_songs(guild_id)
        if not songs:
            await interaction.response.send_message("⚠️ 這個歌單是空的。")
            return

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

        self.player.current_playlist_id = guild_id  # ✅ 記錄當前播放的歌單 ID

        self.player.play_next(voice_client)

        await interaction.response.send_message("▶️ 正在播放本伺服器的歌單")

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

    @app_commands.command(name="pause", description="暫停音樂")
    async def pause(self, interaction: discord.Interaction): ...

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
