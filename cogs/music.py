import discord
import discord.context_managers
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
from pytube import YouTube
import json
import asyncio
import random
from core.classes import Cog_Extension


class Music(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.play_queue = []
        self.queue_lock = asyncio.Lock()

    # @app_commands.command(name="join", description="join to channel")    下次多寫一個app command 呼叫join
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
            # play_queue = []  # 播放清單
            # queue_lock = asyncio.Lock()
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
            async with self.queue_lock:
                self.play_queue.append((songtitle, url))
            await interaction.response.send_message(
                f"{songtitle} 已添加到播放清單。", silent=True
            )
            # print("你好")
            # await interaction.response.send_message("i am here")
            if not voice_client.is_playing():
                print("yes or no")
                await play_next_song(voice_client)
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
                    async with self.queue_lock:
                        if self.play_queue:
                            print("有有嗎")
                            songtitle, song_url = self.play_queue.pop(0)
                            print("有嗎")
                            ffmpeg_options = {
                                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                                "options": "-vn",
                            }
                        voice_client = discord.VoiceClient
                        voice_client.play(
                            discord.FFmpegPCMAudio(song_url, **ffmpeg_options),
                            after=lambda e: (
                                asyncio.run_coroutine_threadsafe(
                                    play_next_song(voice_client),
                                    asyncio.get_running_loop(),
                                )
                                if e is None
                                else print(f"播放错误：{e}")
                            ),
                        )
                        await interaction.channel.send(f"正在播放: {songtitle}")
                except Exception as e:
                    await interaction.response.send_message(
                        f"錯誤:{str(e)}", silent=True
                    )

            # return
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

    # @app_commands.command()
    # async def skipto(): ...

    # @app_commands.command()
    # async def shuffle(): ...

    # @app_commands.command()
    # async def repeat(): ...


async def setup(bot):
    await bot.add_cog(Music(bot))
