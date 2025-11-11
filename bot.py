# --coding:utf-8--**
import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import os
import logging


with open("setting.json", mode="r", encoding="utf8") as jflie:
    jdata = json.load(jflie)

# 設定全域 logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # 顯示在終端機
        logging.FileHandler("bot.log", encoding="utf-8"),  # 輸出到檔案
    ],
)

logger = logging.getLogger("bot")

bot = commands.Bot(intents=discord.Intents.all(), command_prefix="+")


@bot.event
async def on_ready():
    print("雪寶 啟動")
    logger.info("雪寶 啟動")
    # await bot.tree.sync()  # 🚀 手動同步 Slash 指令
    # print("✅ Slash 指令已同步！")

    # 顯示已載入的 Cogs
    # print("🔍 已載入的 Cogs:")
    # for ext in bot.extensions:
    # print(f"  - {ext}")


@bot.command()
async def load(ctx, extension):
    await bot.load_extension(f"cogs.{extension}")
    await ctx.send(f" {extension} 已安裝完畢!", silent=True)


@bot.command()
async def unload(ctx, extension):
    await bot.unload_extension(f"cogs.{extension}")
    await ctx.send(f" {extension} 已卸載完畢!", silent=True)


@bot.command()
async def reload(ctx, extension):
    await bot.reload_extension(f"cogs.{extension}")
    await ctx.send(f" {extension} 已重裝完畢!", silent=True)


@bot.tree.command(name="reload")
async def newreload(interaction: discord.Interaction, extension: str):
    try:
        await bot.reload_extension(f"cogs.{extension}")
        await interaction.response.send_message(
            f" {extension} 已重裝完畢!", silent=True
        )
    except Exception as e:
        await interaction.response.send_message(f"發生錯誤：{str(e)}")


@bot.tree.command(name="unload")
async def newunload(interaction: discord.Interaction, extension: str):
    await bot.unload_extension(f"cogs.{extension}")
    await interaction.response.send_message(f" {extension} 已卸載完畢!", silent=True)


@bot.tree.command(name="load")
async def newload(interaction: discord.Interaction, extension: str):
    await bot.load_extension(f"cogs.{extension}")
    await interaction.response.send_message(f" {extension} 已安裝完畢!", silent=True)


@bot.tree.command(name="hellow", description="test")
async def hellow(interaction: discord.Interaction):
    await interaction.response.send_message("hellow")


@bot.tree.command(name="slash", description="同步指令")
async def slash(interaction: discord.Interaction):
    slash = await bot.tree.sync()
    print(f"裝了{len(slash)}個斜線")
    # await bot.tree.sync()  # 🚀 手動同步 Slash 指令
    print("✅ Slash 指令已同步！")
    await interaction.response.send_message("✅ Slash 指令已同步！")


@bot.command()
async def slash(ctx):
    slash = await bot.tree.sync()
    print(f"裝了{len(slash)}個斜線")
    # await bot.tree.sync()  # 🚀 手動同步 Slash 指令
    print("✅ Slash 指令已同步！")
    await ctx.send(f"✅ Slash 指令已同步！")


async def setup():
    for filename in os.listdir("./cogs"):
        if (
            filename.endswith(".py") and filename != "__init__.py"
        ):  # ✅ 跳過 `__init__.py`
            # if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
    await bot.start(jdata["TOKEN"])


if __name__ == "__main__":
    asyncio.run(setup())
# bot.run(jdata['TOKEN'])
