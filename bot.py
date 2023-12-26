#--coding:utf-8--**
import discord
from discord.ext import commands
import json

with open('setting.json',mode='r',encoding='utf8')as jflie:
    jdata = json.load(jflie)

bot=commands.Bot(intents=discord.Intents.default(),command_prefix= '+') 



@bot.event
async def on_ready():
    print("憨包 啟動")

bot.run(jdata['TOKEN'])
