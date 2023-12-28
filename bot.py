# --coding:utf-8--**
import discord
from discord.ext import commands
import json
import asyncio
import os

with open("setting.json", mode="r", encoding="utf8") as jflie:
    jdata = json.load(jflie)

bot = commands.Bot(intents=discord.Intents.all(), command_prefix="+")


@bot.event
async def on_ready():
    print("憨包 啟動")


@bot.command()
async def say(ctx: commands.Context):
    await ctx.send(ctx.message.content)


async def setup():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
    await bot.start(jdata["TOKEN"])


if __name__ == "__main__":
    asyncio.run(setup())
# bot.run(jdata['TOKEN'])
