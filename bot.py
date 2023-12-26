import discord
from discord.ext import commands

bot=commands.Bot(intents=discord.Intents.default(),command_prefix= '+')

@bot.event
async def on_ready():
    print("憨包 啟動")

bot.run('MTE4OTEzMTExMjA4NjI0NTQxNw.GhgJQg.6vfF0PlCWOi5xJOnOM1PooShHM_Ie7-Opmya1E')
