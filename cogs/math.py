import discord
from discord.ext import commands
from discord import app_commands  # 斜線指令
import json  # 設定檔、資料儲存
import asyncio  # 等待、延遲
import random
from core.classes import Cog_Extension
import re  # 字串比對、驗證格式
from collections import defaultdict  # 建立具有預設值的字典


class RPSGame:  # Rock-Paper-Scissors Game
    def __init__(self):
        self.players = {}  # 玩家選擇
        self.choices = {"剪刀": "✌️", "石頭": "✊", "布": "✋"}
        self.started = False  # 遊戲是否開始

    def add_player(self, player: discord.Member):
        if player.id not in self.players:  # 玩家加入但尚未出拳
            self.players[player.id] = None
            return True
        return False

    def set_choice(self, player: discord.Member, choice: str):
        self.players[player.id] = choice  # 更新玩家的選擇

    def all_players_chosen(self):
        return all(choice is not None for choice in self.players.values())

    def determine_winners(self):
        if not self.all_players_chosen():
            return None  # 尚未全員選擇

        choices = list(self.players.values())  # 取得所有玩家的出拳
        unique_choices = set(choices)  # 所有人選擇的集合

        # 如果所有人選擇相同->集合長度為1
        # 如果出現剪刀、石頭、布三種手勢->集合長度為3
        if len(unique_choices) == 1 or len(unique_choices) == 3:
            return "再猜一次!"

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


class RPSView(discord.ui.View):  # 剪刀石頭布的按鈕
    def __init__(self, game: RPSGame):
        super().__init__()  # 呼叫 父類別 discord.ui.View 的建構子（初始化方法）
        self.game = game

    @discord.ui.button(label="加入遊戲", style=discord.ButtonStyle.secondary)
    async def join_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
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
            f"{interaction.user.mention} 已選擇!", silent=True  # mention->@使用者
        )

        if self.game.all_players_chosen():
            result = self.game.determine_winners()

            choices_text = "\n".join(
                f"<@{pid}> 選擇了 {self.game.choices[choice]}"
                for pid, choice in self.game.players.items()  # 所有玩家的選擇情況
            )

            if result == "再猜一次!":
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

    @discord.ui.button(
        label="剪刀", style=discord.ButtonStyle.primary, emoji="✌️"
    )  # primary->藍色
    async def scissors(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.handle_choice(interaction, "剪刀")

    @discord.ui.button(
        label="石頭", style=discord.ButtonStyle.success, emoji="✊"
    )  # success->綠色
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "石頭")

    @discord.ui.button(
        label="布", style=discord.ButtonStyle.danger, emoji="✋"
    )  # danger->紅色
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "布")


class RPSCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


class VoteData:
    def __init__(self, title: str, author: discord.User):
        self.title = title
        self.author = author
        self.options = []
        self.votes = defaultdict(set)  # 初始化為一個空的集合

    def add_option(self, option: str):
        if option not in self.options:
            self.options.append(option)

    def remove_option(self, option: str):
        if option in self.options:
            self.options.remove(option)
            self.votes.pop(option, None)  # 刪除並回傳

    def clear_options(self):
        self.options.clear()
        self.votes.clear()

    def vote(self, user_id: int, option: str):
        for opt in self.options:
            self.votes[opt].discard(user_id)  # 移除他之前的投票
        self.votes[option].add(user_id)

    def get_results(self):
        return {
            option: len(users)
            for option, users in self.votes.items()
            if option in self.options  # 過濾非正式選項（如果有的話）
        }

    def get_voters(self):
        result = defaultdict(list)
        for option, users in self.votes.items():  # 使用者集合
            for uid in users:
                result[option].append(uid)
        return result


class VoteControlView(discord.ui.View):
    def __init__(self, vote_data: VoteData):
        super().__init__(timeout=None)
        self.vote_data = vote_data
        self.vote_view = VoteOptionView(vote_data)

    @discord.ui.button(label="➕ 加選項", style=discord.ButtonStyle.primary)
    async def add_option(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            AddOptionModal(self.vote_data, self.vote_view)
        )

    @discord.ui.button(label="➖ 刪選項", style=discord.ButtonStyle.secondary)
    async def remove_option(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not self.vote_data.options:
            await interaction.response.send_message(
                "目前沒有可刪除的選項。", ephemeral=True
            )
            return
        await interaction.response.send_message(
            view=RemoveOptionView(self.vote_data, self.vote_view), ephemeral=True
        )

    @discord.ui.button(label="🗑 刪除全部選項", style=discord.ButtonStyle.danger)
    async def clear_all(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.vote_data.author:
            await interaction.response.send_message(
                "❗ 只有指令發起者才能清除所有選項。", ephemeral=True
            )
            return
        self.vote_data.clear_options()
        await interaction.response.send_message("✅ 所有選項已清除！", ephemeral=True)
        await interaction.message.channel.send(view=self.vote_view)

    @discord.ui.button(label="📊 顯示投票結果", style=discord.ButtonStyle.success)
    async def show_results(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        results = self.vote_data.get_results()
        if not results:
            await interaction.response.send_message(
                "目前沒有投票紀錄。", ephemeral=True
            )
        else:
            result_text = "\n".join(
                f"{opt}: {count} 票" for opt, count in results.items()
            )
            await interaction.response.send_message(
                f"📊 投票結果：\n{result_text}", ephemeral=True
            )

    @discord.ui.button(label="👀 查看投票者", style=discord.ButtonStyle.secondary)
    async def show_voters(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.vote_data.author:
            await interaction.response.send_message(
                "❗ 只有指令發起者能查看投票者。", ephemeral=True
            )
            return
        voters = self.vote_data.get_voters()
        if not voters:
            await interaction.response.send_message("目前沒有人投票。", ephemeral=True)
            return
        lines = []
        for opt, users in voters.items():
            names = ", ".join(f"<@{uid}>" for uid in users)
            lines.append(f"{opt}: {names}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


class VoteOptionView(discord.ui.View):
    def __init__(self, vote_data: VoteData):
        super().__init__(timeout=None)
        self.vote_data = vote_data
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for option in self.vote_data.options:
            self.add_item(VoteButton(option, self.vote_data))


class VoteButton(discord.ui.Button):
    def __init__(self, option: str, vote_data: VoteData):
        super().__init__(label=option, style=discord.ButtonStyle.primary)
        self.option = option
        self.vote_data = vote_data

    async def callback(self, interaction: discord.Interaction):
        self.vote_data.vote(interaction.user.id, self.option)
        await interaction.response.send_message(
            f"你已投票給：**{self.option}** ✅", ephemeral=True
        )


class AddOptionModal(discord.ui.Modal, title="新增投票選項"):
    option = discord.ui.TextInput(label="請輸入選項內容", max_length=100)

    def __init__(self, vote_data: VoteData, vote_view: VoteOptionView):
        super().__init__()
        self.vote_data = vote_data
        self.vote_view = vote_view

    async def on_submit(self, interaction: discord.Interaction):
        new_option = self.option.value.strip()
        if not new_option:
            await interaction.response.send_message("❗ 選項不得為空！", ephemeral=True)
            return
        self.vote_data.add_option(new_option)
        self.vote_view.update_buttons()
        await interaction.response.send_message(
            f"✅ 新增選項：**{new_option}**", ephemeral=True
        )
        await interaction.channel.send(view=self.vote_view)


class RemoveOptionView(discord.ui.View):
    def __init__(self, vote_data: VoteData, vote_view: VoteOptionView):
        super().__init__(timeout=30)
        self.add_item(RemoveOptionSelect(vote_data, vote_view))


class RemoveOptionSelect(discord.ui.Select):
    def __init__(self, vote_data: VoteData, vote_view: VoteOptionView):
        self.vote_data = vote_data
        self.vote_view = vote_view
        options = [discord.SelectOption(label=opt) for opt in vote_data.options]
        super().__init__(
            placeholder="選擇要刪除的選項", options=options, min_values=1, max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        self.vote_data.remove_option(selected)
        self.vote_view.update_buttons()
        await interaction.response.send_message(
            f"已刪除選項：**{selected}**", ephemeral=True
        )
        await interaction.channel.send(view=self.vote_view)


class VoteCog(commands.Cog):
    def __init__(self, bot):
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

    @app_commands.command(name="骰骰子", description="多面骰子")
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

    @app_commands.command(
        name="隨機選擇", description="從輸入的選項中隨機選出指定數量的選項"
    )
    @app_commands.describe(
        set="請輸入要讓機器人選出幾個選項?",
        options="請輸入選項，使用空格、逗號或頓號分隔",
    )
    async def choose(self, interaction: discord.Interaction, set: int, options: str):
        items = re.split(r"[、,，\s]+", options.strip())
        items = [item for item in items if item]

        if not items or len(items) < 2:
            await interaction.response.send_message(
                "請提供至少兩個可選項目。", ephemeral=True
            )
            return

        if set <= 0:
            await interaction.response.send_message(
                "選擇的數量必須大於 0。", ephemeral=True
            )
            return

        if set > len(items):
            await interaction.response.send_message(
                f"你只提供了 {len(items)} 項，無法選出 {set} 個。", ephemeral=True
            )
            return

        chosen = random.sample(items, set)
        options_text = "、".join(items)
        chosen_text = "、".join(chosen)

        await interaction.response.send_message(
            f"從以下選項中隨機選出 {set} 個：\n> {options_text}\n\n🎯 選中的項目是：**{chosen_text}**",
            silent=True,
        )

    @app_commands.command(name="猜拳", description="多人一起玩猜拳!")
    async def rps(self, interaction: discord.Interaction):
        """開始猜拳遊戲"""
        game = RPSGame()
        await interaction.response.send_message(
            "猜拳遊戲開始! 點擊按鈕加入!", view=RPSView(game)
        )

    @app_commands.command(name="投票", description="建立一個互動式投票")
    @app_commands.describe(title="投票的主題")
    async def vote(self, interaction: discord.Interaction, title: str):
        vote_data = VoteData(title, interaction.user)
        control_view = VoteControlView(vote_data)
        await interaction.response.send_message(
            f"📢 **{title}**\n請使用下方按鈕進行操作", view=control_view
        )
        await interaction.channel.send(view=control_view.vote_view)


async def setup(bot):
    await bot.add_cog(Math(bot))
