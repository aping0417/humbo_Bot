import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import random
from core.classes import Cog_Extension


class RPSGame:
    def __init__(self):
        self.players = {}  # 存儲玩家的選擇 {玩家ID: 選擇}
        self.choices = {"剪刀": "✌️", "石頭": "✊", "布": "✋"}
        self.started = False  # 遊戲是否開始

    def add_player(self, player: discord.Member):
        """新增玩家到遊戲"""
        if player.id not in self.players:
            self.players[player.id] = None  # 尚未選擇
            return True
        return False  # 已經在遊戲內

    def set_choice(self, player: discord.Member, choice: str):
        """設定玩家的選擇"""
        self.players[player.id] = choice

    def all_players_chosen(self):
        """檢查是否所有玩家都已選擇"""
        return all(choice is not None for choice in self.players.values())

    def determine_winners(self):
        """計算結果"""
        if not self.all_players_chosen():
            return None  # 尚未全員選擇

        choices = list(self.players.values())
        unique_choices = set(choices)

        # 如果所有人選擇相同，或出現剪刀、石頭、布三種手勢，則重新猜拳
        if len(unique_choices) == 1 or len(unique_choices) == 3:
            return "再猜一次!"

        # 獲勝條件
        winning_combos = {"剪刀": "布", "石頭": "剪刀", "布": "石頭"}

        winners = [
            pid
            for pid, choice in self.players.items()
            if any(
                choice == win and lose in choices
                for win, lose in winning_combos.items()
            )
        ]

        if not winners:
            return "再猜一次!"  # 仍然平手則再猜一次

        winner_mentions = ", ".join(f"<@{pid}>" for pid in winners)
        return f"贏家是: {winner_mentions}! 🎉"


class RPSView(discord.ui.View):
    def __init__(self, game: RPSGame):
        super().__init__()
        self.game = game

    @discord.ui.button(label="加入遊戲", style=discord.ButtonStyle.secondary)
    async def join_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """玩家點擊加入遊戲"""
        if not self.game.started:
            if self.game.add_player(interaction.user):
                await interaction.response.send_message(
                    f"{interaction.user.mention} 加入了猜拳!", silent=True
                )
            else:
                await interaction.response.send_message(
                    "你已經加入遊戲了!", ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "遊戲已經開始，無法加入!", ephemeral=True
            )

    @discord.ui.button(label="開始遊戲", style=discord.ButtonStyle.success)
    async def start_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """開始遊戲"""
        if len(self.game.players) < 2:
            await interaction.response.send_message(
                "至少需要 2 名玩家才能開始!", ephemeral=True
            )
            return

        self.game.started = True
        await interaction.channel.send(
            "遊戲開始! 所有人請選擇你的手勢!",
            view=RPSChoiceView(self.game),
            silent=True,
        )


class RPSChoiceView(discord.ui.View):
    def __init__(self, game: RPSGame):
        super().__init__()
        self.game = game

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        """處理玩家的選擇"""
        if interaction.user.id not in self.game.players:
            await interaction.response.send_message(
                "你不是這場遊戲的玩家!", ephemeral=True, silent=True
            )
            return

        if self.game.players[interaction.user.id] is not None:
            await interaction.response.send_message("你已經選擇過了!", ephemeral=True)
            return

        self.game.set_choice(interaction.user, choice)
        await interaction.response.send_message(
            f"{interaction.user.mention} 已選擇!", silent=True
        )

        # 所有人選擇後，計算結果
        if self.game.all_players_chosen():
            result = self.game.determine_winners()

            # 顯示所有人的選擇
            choices_text = "\n".join(
                f"<@{pid}> 選擇了 {self.game.choices[choice]}"
                for pid, choice in self.game.players.items()
            )

            if result == "再猜一次!":
                # 清除玩家選擇，讓大家重新選
                for pid in self.game.players.keys():
                    self.game.players[pid] = None

                await interaction.channel.send(
                    f"{choices_text}\n\n⚠️ {result}，請重新選擇!",
                    view=RPSChoiceView(self.game),
                )
            else:
                await interaction.channel.send(
                    f"{choices_text}\n\n🎉 {result}", silent=True
                )

    @discord.ui.button(label="剪刀", style=discord.ButtonStyle.primary, emoji="✌️")
    async def scissors(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.handle_choice(interaction, "剪刀")

    @discord.ui.button(label="石頭", style=discord.ButtonStyle.success, emoji="✊")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "石頭")

    @discord.ui.button(label="布", style=discord.ButtonStyle.danger, emoji="✋")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "布")


class RPSCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


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
    async def choose(self, interaction: discord.Interaction, msg: str):
        any = msg.split(" ")
        random_num = random.randint(0, len(any))
        await interaction.response.send_message(any[random_num], silent=True)
        # print(any[random_num])

    @app_commands.command(name="猜拳", description="多人一起玩猜拳!")
    async def rps(self, interaction: discord.Interaction):
        """開始猜拳遊戲"""
        game = RPSGame()
        await interaction.response.send_message(
            "猜拳遊戲開始! 點擊按鈕加入!", view=RPSView(game)
        )


async def setup(bot):
    await bot.add_cog(Math(bot))
