import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
from core.classes import Cog_Extension
from core.log_utils import append_log


class Say(Cog_Extension):
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(1189847061277982720)
        await channel.send(f"{member}嗚呼!!有人來囉")

    @commands.command()
    async def oldwhere(self, ctx, extension: discord.Member):
        # user = [ctx.message.raw_mentions]
        # memberid = user[0]
        member = extension
        await ctx.send(
            f"{extension.mention}在{member.voice.channel.mention}", silent=True
        )
        # await ctx.send(type(member))

    @commands.command()
    async def oldwho(self, ctx: commands.Context):
        await ctx.send(ctx.author())

    @commands.command()
    async def oldsay(self, ctx: commands.Context, *, msg):
        await ctx.message.delete()
        await ctx.send(msg)

    @app_commands.command(
        name="找人在哪", description="來找找您的朋友正在哪個語音頻道呢?"
    )
    @app_commands.describe(member="請點選一個你要找的人")
    async def where(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{member.mention}在{member.voice.channel.mention}", silent=True
        )

    # 1
    @app_commands.command(
        name="匿名留言", description="ㄏㄏㄏ你們絕對不知道是我在講話!"
    )
    @app_commands.describe(msg="愛講甚麼就講甚麼!")
    async def say(self, interaction: discord.Interaction, msg: str):
        await interaction.response.send_message("訊息成功", ephemeral=True)

        sent_msg: discord.Message = await interaction.channel.send(msg)

        mentions = sent_msg.mentions

        if mentions:
            # 把被 mention 的成員整理成文字
            mention_str = ", ".join(f"{m} ({m.id})" for m in mentions)

            append_log(
                "anonymous_messages.log",
                [
                    "【匿名留言（含 mention）】",
                    f"Guild : {interaction.guild.name} ({interaction.guild_id})",
                    f"Channel : {interaction.channel} ({interaction.channel.id})",
                    f"Sender : {interaction.user} ({interaction.user.id})",
                    f"Message : {msg}",
                    f"Mentions : {mention_str}",
                ],
            )
        else:
            append_log(
                "anonymous_messages.log",
                [
                    "【匿名留言】",
                    f"Guild : {interaction.guild.name} ({interaction.guild_id})",
                    f"Channel : {interaction.channel} ({interaction.channel.id})",
                    f"Sender : {interaction.user} ({interaction.user.id})",
                    f"Message : {msg}",
                ],
            )


async def setup(bot):
    await bot.add_cog(Say(bot))
