import discord
from discord.ext import commands
import json
import asyncio
from core.classes import Cog_Extension


class Main(Cog_Extension):
    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"{round(self.bot.latency*1000)}ms")


async def setup(bot):
    await bot.add_cog(Main(bot))
