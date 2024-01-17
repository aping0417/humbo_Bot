import discord
from discord.ext import commands
import json
import asyncio
from core.classes import Cog_Extension


class Say(Cog_Extension):
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(1189847061277982720)
        await channel.send(f"{member}嗚呼!!有人來囉")

    @commands.command()
    async def where(self, ctx, extension:discord.member.Member):
        #user = [ctx.message.raw_mentions]
        #memberid = user[0]
        member = extension
        await ctx.send(f'{extension.mention}在{member.voice.channel.mention}')
        #await ctx.send(type(member))
    @commands.command()
    async def who(self, ctx: commands.Context):
        await ctx.send(ctx.author())

    @commands.command()
    async def say(self, ctx: commands.Context):
        await ctx.send(ctx.message.content)


async def setup(bot):
    await bot.add_cog(Say(bot))
