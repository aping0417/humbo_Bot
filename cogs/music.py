import discord
import discord.context_managers
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
from pytube import YouTube
import json
import asyncio
from playlist import database
from playlist import Playlist
from core.classes import Cog_Extension

ydl_opts = {
    "format": "bestaudio/best",  # 格式
    "quiet": True,  # 抑制 youtube_dl 的大部分输出
    "extractaudio": True,  # 只抓聲音
    "outtmpl": "downloads/%(title)s.%(ext)s",  # 指定下载文件的输出模板
    "noplaylist": True,  # 禁用播放清單（之後會開放）
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


class Music(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
    # @app_commands.command(name="join", description="join to channel")    下次多寫一個app command 呼叫join


class MusicPlayer:
    def __init__(self):
        self.play_queue = []

    def download_audio(self, url):
        """使用 yt_dlp 取得音訊串流網址"""
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"], info["title"]

    def play_next(self, voice_client):
        """播放下一首歌曲"""
        if self.play_queue:
            url, title = self.play_queue.pop(0)
            source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
            voice_client = discord.VoiceClient
            voice_client.play(
                source, after=lambda e: self.play_next(voice_client))

    def add_to_queue(self, url):
        """將歌曲加入播放隊列"""
        audio_url, title = self.download_audio(url)
        self.play_queue.append((audio_url, title))
        return title

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

        # try:(報錯指令)
        # 連接到語音頻道
        # await voicechannel.connect()
        # await interaction.response.send_message(f"已連接到 {voicechannel.name}。")
        # except Exception as e:
        # await interaction.response.send_message(f"發生錯誤：{str(e)}")

    @app_commands.command(name="leave", description="leave to channel")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            await interaction.response.send_message(
                "你尚未進入任何語音頻道", silent=True
            )
        else:
            await voice_client.disconnect()
            await interaction.response.send_message("已離開語音頻道", silent=True)

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
                voice_client = discord.VoiceClient
                await voice_client.move_to(self=voice_client, channel=voice_channel)
                # await interaction.response.send_message("test123")
            # else:
            # return
            # downloaded_format = info.get('format')
            # print(f"下载的格式: {downloaded_format}")

            # if not isinstance(voice_client, discord.VoiceClient):
            # await interaction.response.send_message("語音客戶端不可用", silent=True)
            # return
            ydl_opts = {
                "format": "bestaudio/best",  # 格式
                "quiet": True,  # 抑制 youtube_dl 的大部分输出
                "extractaudio": True,  # 只抓聲音
                "outtmpl": "downloads/%(title)s.%(ext)s",  # 指定下载文件的输出模板
                "noplaylist": True,  # 禁用播放清單（之後會開放）

                # 'postprocessors': [{
                # 'key': 'FFmpegExtractAudio',
                # 'preferredcodec': 'm4a',  # 转换为 mp3
                # 'preferredquality': '192',  # 设置比特率为192k
                # }], （這些是限制版本）
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                songtitle = info.get("title", None)
                # for i, fmt in enumerate(info.get('formats', [])):
                # print(f"Format {i}: {fmt['format_id']} - {fmt['ext']} - {fmt['url']}")
                # (這是詳細的格式也是剛開始看的)

                url2 = info["formats"][5]["url"]  # 第6個格式

                # downloaded_format = info.get('format')
                # print(f"下载的格式: {downloaded_format}")
                # (剛開始拿來看有啥格式能撥用的)

            # await asyncio.gather(play＿next_song(), sendmsg())
            print("哈嚕")
            ffmpeg_options = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                "options": "-vn",

            }  # 設定 -reconnect 1 （斷線自動重連） -reconnect_streamed 1（處理Streaming Media會自動重連）

            # -reconnect_delay_max 5(斷線5秒內會自動重連) "options": "-vn" （只處理聲音）
            # voice_client.stop()
            async def playmusic():
                try:
                    voice_client.play(
                        discord.FFmpegPCMAudio(url2, **ffmpeg_options),
                        after=lambda e: print(
                            f"Player error: {e}") if e else None,
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

    @app_commands.command(name="pause", description="暫停音樂")
    async def pause(self, interaction: discord.Interaction): ...

    # @app_commands.command()
    # async def skip(): ...

    # @app_commands.command()
    # async def nowplay(): ...

    @app_commands.command(name="list", description="看歌單")
    async def list(self, interaction: discord.Interaction):
        async with self.queue_lock:
            if not self.play_queue:
                await interaction.response.send_message("播放清單是空的。")
            else:
                queue_display = "\n".join(
                    f"{i+1}. {title}" for i, (title, _) in enumerate(self.play_queue)
                )
                await interaction.response.send_message(f"播放清單:\n{queue_display}")

    @app_commands.command(name="create_playlist", description="創建新的歌單")
    async def create_playlist(self, interaction: discord.Interaction, name: str):
        database.add_playlist(name, str(interaction.user.id))
        await interaction.response.send_message(f'✅ 已創建歌單: {name}')

    # 🎵 新增歌曲到歌單
    @app_commands.command(name="add_song", description="新增歌曲到歌單")
    async def add_song(interaction: discord.Interaction, playlist_name: str, title: str, url: str):
        database.add_song(playlist_name, title, url)
        await interaction.response.send_message(f'✅ 已新增 `{title}` 到 `{playlist_name}`')

    # 🎵 播放歌單
    @app_commands.command(name="play_playlist", description="播放整個歌單")
    async def play_playlist(self, interaction: discord.Interaction, playlist_name: str):
        songs = database.get_songs(playlist_name)
        if not songs:
            await interaction.response.send_message("⚠️ 這個歌單是空的。")
            return
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
            voice_client = discord.VoiceClient
            await voice_client.move_to(self=voice_client, channel=voice_channel)
        # voice_client = interaction.guild.voice_client
        # if voice_client is None or not voice_client.is_connected():
            # if interaction.user.voice:
            # voice_channel = interaction.user.voice.channel
            # voice_client = await voice_channel.connect()
            # else:
            # await interaction.response.send_message("❌ 你不在語音頻道內。")
            # return

        for title, url in songs:
            MusicPlayer.add_to_queue(url)

        if not voice_client.is_playing():
            MusicPlayer.play_next(voice_client)

        await interaction.response.send_message(f'▶️ 正在播放 `{playlist_name}` 的歌單')

    # @app_commands.command()
    # async def skipto(): ...

    # @app_commands.command()
    # async def shuffle(): ...

    # @app_commands.command()
    # async def repeat(): ...


async def setup(bot):
    await bot.add_cog(Music(bot))
