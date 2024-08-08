import discord
import discord.context_managers
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import random
from core.classes import Cog_Extension


class Music(Cog_Extension):
    @app_commands.command(name="join", description="join to channel")
    async def join(self, interaction: discord.Interaction):

        if interaction.user.voice == None:
            await interaction.response.send_message("你不在任何語音頻道")
        else:
            voicechannel = interaction.user.voice.channel
            # await interaction.response.send_message(voicechannel.mention, silent=True)
            await voicechannel.connect()
            await interaction.response.send_message("已進入語音頻道")

        # try:(報錯指令)
        # 連接到語音頻道
        # await voicechannel.connect()
        # await interaction.response.send_message(f"已連接到 {voicechannel.name}。")
        # except Exception as e:
        # await interaction.response.send_message(f"發生錯誤：{str(e)}")

    # @app_commands.command(name="join", description="join to chanel")
    # async def join(self, interaction: discord.Interaction, member: discord.Member):
    # await interaction.response.send_message(
    # f"{member.mention}在{member.voice.channel.mention}", silent=True
    # )

    # @app_commands.command()
    # async def play(): ...

    # @app_commands.command()
    # async def pause(): ...

    # @app_commands.command()
    # async def skip(): ...

    # @app_commands.command()
    # async def nowplay(): ...

    # @app_commands.command()
    # async def list(): ...

    # @app_commands.command()
    # async def skipto(): ...

    # @app_commands.command()
    # async def shuffle(): ...

    # @app_commands.command()
    # async def repeat(): ...


async def setup(bot):
    await bot.add_cog(Music(bot))
