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
    print(f"裝了{len(slash)}個斜線")


@bot.command()
async def load(ctx, extension):
    await bot.load_extension(f"cogs.{extension}")
    await ctx.send(f" {extension} 已安裝完畢!", silent=True)


@bot.command()
async def unload(ctx, extension):
    await bot.unload_extension(f"cogs.{extension}")
    await ctx.send(f" {extension} 以卸載完畢!", silent=True)


@bot.command()
async def reload(ctx, extension):
    await bot.reload_extension(f"cogs.{extension}")
    await ctx.send(f" {extension} 以重裝完畢!", silent=True)


@bot.tree.command(name="reload")
async def newreload(interaction: discord.Interaction, extension: str):
    try:
        await bot.reload_extension(f"cogs.{extension}")
        await interaction.response.send_message(
            f" {extension} 以重裝完畢!", silent=True
        )
    except Exception as e:
        await interaction.response.send_message(f"發生錯誤：{str(e)}")


@bot.tree.command(name="unload")
async def newunload(interaction: discord.Interaction, extension: str):
    await bot.unload_extension(f"cogs.{extension}")
    await interaction.response.send_message(f" {extension} 以卸載完畢!", silent=True)


@bot.tree.command(name="load")
async def newload(interaction: discord.Interaction, extension: str):
    await bot.load_extension(f"cogs.{extension}")
    await interaction.response.send_message(f" {extension} 已安裝完畢!", silent=True)


@bot.tree.command(name="hellow", description="test")
async def hellow(interaction: discord.Interaction):
    await interaction.response.send_message("hellow")


async def setup():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
    await bot.start(jdata["TOKEN"])


if __name__ == "__main__":
    asyncio.run(setup())
# bot.run(jdata['TOKEN'])
