import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
from core.classes import Cog_Extension


class Main(Cog_Extension):
    @app_commands.command(name="ping", description="看機器人延遲")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{round(self.bot.latency*1000)}ms", silent=True
        )

    @app_commands.command(name="test", description="測試機器人")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message("ABCDE")


async def setup(bot):
    await bot.add_cog(Main(bot))
