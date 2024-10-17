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
            await ctx.send(random_number, silent=True)
        elif len(numbers) == 2:
            x = numbers[0]
            y = numbers[1]
            random_number = random.randint(x, y)
            await ctx.send(random_number, silent=True)
        else:
            await ctx.send(f"不能一次打3個以上的數字操", silent=True)

    @app_commands.command(name="dice", description="隨機選數字")
    async def dice(self, interaction: discord.Interaction, numbers: str):
        x = numbers.split(" ")
        if len(x) == 1:
            random_number = random.randint(1, int(x[0]))
            await interaction.response.send_message(random_number, silent=True)
        elif len(x) == 2:
            random_number = random.randint(int(x[0]), int(x[1]))
            await interaction.response.send_message(random_number, silent=True)
        else:
            await interaction.response.send_message(
                f"不能一次打3個以上的數字操", silent=True
            )

    @app_commands.command(name="隨機選擇", description="選擇")
    async def choose(self, interaction: discord.Interaction, *msg: str):
        any = msg.split(" ")
        random_num = random.randint(0, len(any))
        await interaction.response.send_message(any[random_num], silent=True)
        # print(any[random_num])


async def setup(bot):
    await bot.add_cog(Math(bot))
