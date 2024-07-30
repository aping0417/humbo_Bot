# --coding:utf-8--**
import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import os

with open("setting.json", mode="r", encoding="utf8") as jflie:
    jdata = json.load(jflie)

bot = commands.Bot(intents=discord.Intents.all(), command_prefix="+")


@bot.event
async def on_ready():
    slash = await bot.tree.sync()
    print("雪寶 啟動")


@bot.command()
async def load(ctx, extension):
    await bot.load_extension(f"cogs.{extension}")
    await ctx.send(f"loaded {extension} done.")


@bot.command()
async def unload(ctx, extension):
    await bot.unload_extension(f"cogs.{extension}")
    await ctx.send(f"un-loaded {extension} done.")


@bot.command()
async def reload(ctx, extension):
    await bot.reload_extension(f"cogs.{extension}")
    await ctx.send(f"re-loaded {extension} done.")


async def setup():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
    await bot.start(jdata["TOKEN"])


if __name__ == "__main__":
    asyncio.run(setup())
# bot.run(jdata['TOKEN'])
