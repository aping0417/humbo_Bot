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
    async def where(self, ctx: commands.Context):
        member = ctx.author
        await ctx.send(f"{ctx.author.mention}在{member.voice.channel.mention}")

    async def who(self, ctx: commands.context):
        await ctx.send(ctx.author())


async def setup(bot):
    await bot.add_cog(Say(bot))
