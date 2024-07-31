import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import random
from core.classes import Cog_Extension


class Math(Cog_Extension):
    @commands.command()
    async def oldchoosenumber(self, ctx: commands.Context, *numbers: int):
        if len(numbers) == 1:
            x = numbers[0]
            random_number = random.randint(1, x)
            await ctx.send(random_number)
        elif len(numbers) == 2:
            x = numbers[0]
            y = numbers[1]
            random_number = random.randint(x, y)
            await ctx.send(random_number)
        else:
            await ctx.send(f"不能一次打3個以上的數字操")

    # @app_commands.command(name="choosenumber", description="隨機選數字")
    # async def choosenumber(self, ctx: commands.Context, *numbers: int): ...


async def setup(bot):
    await bot.add_cog(Math(bot))
