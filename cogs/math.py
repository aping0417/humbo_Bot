import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import random
from core.classes import Cog_Extension
import re
from collections import defaultdict
from core.log_utils import append_log


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


# 1. VoteData（資料模型）
class VoteData:
    def __init__(
        self,
        title: str,
        author: discord.User,
        is_anonymous=False,
        allow_add_option=False,
        allow_remove_option=False,
    ):
        self.title = title
        self.author = author
        self.options = []
        self.votes = defaultdict(set)
        self.is_anonymous = is_anonymous
        self.allow_add_option = allow_add_option
        self.allow_remove_option = allow_remove_option
        self.allow_view_voters = True  # 永遠允許查看投票者名單

    def add_option(self, option: str):
        if option not in self.options:
            self.options.append(option)

    def remove_option(self, option: str):
        if option in self.options:
            self.options.remove(option)
        if option in self.votes:
            del self.votes[option]

    def clear_options(self):
        self.options.clear()
        self.votes.clear()

    def vote(self, user_id: int, option: str):
        # 一次只允許投一個
        for opt in self.options:
            self.votes[opt].discard(user_id)
        self.votes[option].add(user_id)

    def get_results(self):
        return {opt: len(v) for opt, v in self.votes.items() if opt in self.options}

    def get_voters(self):
        result = defaultdict(list)
        for opt, users in self.votes.items():
            for uid in users:
                result[opt].append(uid)
        return result


# 2. VoteButton & VoteOptionView（投票按鈕）
class VoteButton(discord.ui.Button):
    def __init__(self, option: str, vote_data: VoteData):
        super().__init__(label=option, style=discord.ButtonStyle.primary)
        self.option = option
        self.vote_data = vote_data

    async def callback(self, interaction: discord.Interaction):
        self.vote_data.vote(interaction.user.id, self.option)

        # 回覆投票者
        await interaction.response.send_message(
            f"你已投票給：**{self.option}** ✅", ephemeral=True
        )

        # 🔍 投票動作寫入紀錄
        append_log(
            "vote.log",
            [
                "【投票動作】",
                f"Guild : {interaction.guild.name} ({interaction.guild_id})",
                f"Channel : {interaction.channel} ({interaction.channel.id})",
                f"Title : {self.vote_data.title}",
                f"User : {interaction.user} ({interaction.user.id})",
                f"Option : {self.option}",
            ],
        )


class VoteOptionView(discord.ui.View):
    def __init__(self, vote_data: VoteData):
        super().__init__(timeout=None)
        self.vote_data = vote_data
        self.options_message: discord.Message | None = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for option in self.vote_data.options:
            self.add_item(VoteButton(option, self.vote_data))


# 3. 新增／刪除／清除選項（Modals & Views）
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

        # 更新資料與按鈕
        self.vote_data.add_option(new_option)
        self.vote_view.update_buttons()

        # defer — 之後會 followup
        await interaction.response.defer(ephemeral=True)

        # 刪除舊選項訊息
        if self.vote_view.options_message:
            try:
                await self.vote_view.options_message.delete()
            except discord.NotFound:
                pass

        # 發送新選項訊息
        new_msg = await interaction.followup.send(view=self.vote_view)
        self.vote_view.options_message = new_msg

        await interaction.followup.send(
            f"✅ 新增選項：**{new_option}**", ephemeral=True
        )


class RemoveOptionSelect(discord.ui.Select):
    def __init__(self, vote_data: VoteData, vote_view: VoteOptionView):
        self.vote_data = vote_data
        self.vote_view = vote_view
        options = [discord.SelectOption(label=opt) for opt in vote_data.options]

        super().__init__(
            placeholder="選擇要刪除的選項",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        await interaction.response.defer(ephemeral=True)

        # 刪除資料
        self.vote_data.remove_option(selected)
        self.vote_view.update_buttons()

        # 刪掉舊按鈕訊息
        if self.vote_view.options_message:
            try:
                await self.vote_view.options_message.delete()
            except discord.NotFound:
                pass

        # 發送新的按鈕訊息
        new_msg = await interaction.followup.send(view=self.vote_view)
        self.vote_view.options_message = new_msg

        await interaction.followup.send(f"已刪除選項：**{selected}**", ephemeral=True)


class RemoveOptionView(discord.ui.View):
    def __init__(self, vote_data: VoteData, vote_view: VoteOptionView):
        super().__init__(timeout=30)
        self.add_item(RemoveOptionSelect(vote_data, vote_view))


class ClearAllOptionsView(discord.ui.View):
    def __init__(self, vote_data: VoteData, vote_view: VoteOptionView):
        super().__init__(timeout=None)
        self.vote_data = vote_data
        self.vote_view = vote_view

    @discord.ui.button(label="🗑 確認刪除全部選項", style=discord.ButtonStyle.danger)
    async def confirm_clear(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        await interaction.response.defer(ephemeral=True)

        # 🔴 在清空之前先寫 log（或清空之後也可以，差別不大）
        append_log(
            "vote.log",
            [
                "【刪除全部投票選項】",
                f"Guild : {interaction.guild.name} ({interaction.guild_id})",
                f"Channel : {interaction.channel} ({interaction.channel.id})",
                f"User : {interaction.user} ({interaction.user.id})",
                f"Title : {self.vote_data.title}",
            ],
        )

        # 清空資料
        self.vote_data.clear_options()
        self.vote_view.update_buttons()

        # 刪掉舊訊息
        if self.vote_view.options_message:
            try:
                await self.vote_view.options_message.delete()
            except discord.NotFound:
                pass
            self.vote_view.options_message = None

        # 新的空訊息（ephemeral）
        msg = await interaction.followup.send(
            "目前沒有任何投票選項，請使用控制台新增選項。", ephemeral=True
        )
        self.vote_view.options_message = msg

        await interaction.followup.send("✅ 所有選項已清除！", ephemeral=True)

        # 停用按鈕
        button.disabled = True
        await interaction.message.edit(view=self)


# 4. 投票控制台（VoteControlView）
class VoteControlView(discord.ui.View):
    def __init__(self, vote_data: VoteData):
        super().__init__(timeout=None)
        self.vote_data = vote_data
        self.vote_view = VoteOptionView(vote_data)

    @discord.ui.button(label="➕ 加選項", style=discord.ButtonStyle.primary)
    async def add_option(self, interaction, button):
        if (
            interaction.user != self.vote_data.author
            and not self.vote_data.allow_add_option
        ):
            await interaction.response.send_message(
                "❗ 你沒有權限新增選項。", ephemeral=True
            )
            return

        await interaction.response.send_modal(
            AddOptionModal(self.vote_data, self.vote_view)
        )

    @discord.ui.button(label="➖ 刪選項", style=discord.ButtonStyle.secondary)
    async def remove_option(self, interaction, button):
        if (
            interaction.user != self.vote_data.author
            and not self.vote_data.allow_remove_option
        ):
            await interaction.response.send_message(
                "❗ 你沒有權限刪除選項。", ephemeral=True
            )
            return

        if not self.vote_data.options:
            await interaction.response.send_message(
                "目前沒有可刪除的選項。", ephemeral=True
            )
            return

        await interaction.response.send_message(
            view=RemoveOptionView(self.vote_data, self.vote_view), ephemeral=True
        )

    @discord.ui.button(label="🗑 刪除全部選項", style=discord.ButtonStyle.danger)
    async def clear_all(self, interaction, button):
        await interaction.response.send_message(
            "⚠️ 你確定要刪除所有選項嗎？此操作不可逆！",
            view=ClearAllOptionsView(self.vote_data, self.vote_view),
            ephemeral=True,
        )

    @discord.ui.button(label="📊 顯示投票結果", style=discord.ButtonStyle.success)
    async def show_results(self, interaction, button):
        # 僅允許創建者使用
        if interaction.user != self.vote_data.author:
            await interaction.response.send_message(
                "❌ 只有投票創建者可以顯示投票結果。", ephemeral=True
            )
            return

        results = self.vote_data.get_results()
        if not results:
            await interaction.response.send_message(
                "目前沒有投票紀錄。", ephemeral=True
            )
            return

        lines = [f"📊 **投票結果：{self.vote_data.title}**"]
        if self.vote_data.is_anonymous:
            for opt, count in results.items():
                lines.append(f"{opt}: {count} 票")
        else:
            voters = self.vote_data.get_voters()
            for opt, count in results.items():
                user_list = ", ".join(f"<@{uid}>" for uid in voters.get(opt, []))
                lines.append(f"{opt}: {count} 票 — {user_list if user_list else ''}")

        await interaction.response.send_message("\n".join(lines), ephemeral=False)

        # 結束投票：停用所有按鈕
        for child in self.children:
            child.disabled = True
        for child in self.vote_view.children:
            child.disabled = True

        # 更新控制台與選項按鈕訊息
        try:
            await interaction.message.edit(view=self)
        except:
            pass
        if self.vote_view.options_message:
            try:
                await self.vote_view.options_message.edit(view=self.vote_view)
            except:
                pass

    @discord.ui.button(label="👀 目前投票狀況", style=discord.ButtonStyle.secondary)
    async def show_status(self, interaction, button):
        results = self.vote_data.get_results()
        if not results:
            await interaction.response.send_message(
                "目前沒有投票紀錄。", ephemeral=True
            )
            return

        lines = ["👀 **目前投票狀況**"]
        if self.vote_data.is_anonymous:
            # 匿名投票：只顯示選項與票數
            for opt, count in results.items():
                lines.append(f"{opt}: {count} 票")
        else:
            # 公開投票：顯示選項、票數與投票者
            voters = self.vote_data.get_voters()
            for opt, count in results.items():
                user_list = ", ".join(f"<@{uid}>" for uid in voters.get(opt, []))
                lines.append(f"{opt}: {count} 票 — {user_list if user_list else ''}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


# 5. 投票設定頁（VoteSettingsView）
class VoteSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.is_anonymous = False
        self.allow_add_option = False
        self.allow_remove_option = False

    @discord.ui.button(label="匿名投票 ❌", style=discord.ButtonStyle.secondary)
    async def toggle_anonymous(self, interaction, button):
        self.is_anonymous = not self.is_anonymous
        button.label = f"匿名投票 {'✅' if self.is_anonymous else '❌'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="允許新增選項 ❌", style=discord.ButtonStyle.secondary)
    async def toggle_add(self, interaction, button):
        self.allow_add_option = not self.allow_add_option
        button.label = f"允許新增選項 {'✅' if self.allow_add_option else '❌'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="允許刪除選項 ❌", style=discord.ButtonStyle.secondary)
    async def toggle_remove(self, interaction, button):
        self.allow_remove_option = not self.allow_remove_option
        button.label = f"允許刪除選項 {'✅' if self.allow_remove_option else '❌'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="✅ 完成設定", style=discord.ButtonStyle.success)
    async def finish(self, interaction, button):
        await interaction.response.send_modal(
            InputTitleModal(
                self.is_anonymous,
                self.allow_add_option,
                self.allow_remove_option,
                interaction.user,
            )
        )


# 6. 輸入投票主題（InputTitleModal）
class InputTitleModal(discord.ui.Modal, title="輸入投票主題"):
    title_input = discord.ui.TextInput(label="投票主題", max_length=200)

    def __init__(self, is_anonymous, allow_add, allow_remove, author):
        super().__init__()
        self.is_anonymous = is_anonymous
        self.allow_add = allow_add
        self.allow_remove = allow_remove
        self.author = author

    async def on_submit(self, interaction):
        vote_data = VoteData(
            title=self.title_input.value,
            author=self.author,
            is_anonymous=self.is_anonymous,
            allow_add_option=self.allow_add,
            allow_remove_option=self.allow_remove,
        )

        vote_view = VoteOptionView(vote_data)
        control_view = VoteControlView(vote_data)

        # 🔍 建立投票時寫入紀錄
        append_log(
            "vote.log",
            [
                "【建立投票】",
                f"Guild : {interaction.guild.name} ({interaction.guild_id})",
                f"Channel : {interaction.channel} ({interaction.channel.id})",
                f"Author : {self.author} ({self.author.id})",
                f"Title : {self.title_input.value}",
                f"Anonymous : {self.is_anonymous}",
                f"Allow Add Option : {self.allow_add}",
                f"Allow Remove Option : {self.allow_remove}",
            ],
        )

        # 發送控制台
        await interaction.response.send_message(
            f"📢 **{self.title_input.value}** 開始投票！\n請使用下方按鈕管理投票或投票。",
            view=control_view,
            silent=True,
        )

        # 實際的投票按鈕訊息
        msg = await interaction.channel.send(view=vote_view)
        vote_view.options_message = msg


# 7. Cog（入口點）
class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


# ------------------- 領身分組 -------------------


class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role):
        # 按鈕標籤 = 身分組名稱，顏色固定用藍色就好
        super().__init__(label=role.name, style=discord.ButtonStyle.primary)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        role = self.role
        guild = interaction.guild

        # 取得機器人在這個伺服器的身分
        bot_member = guild.me

        # 檢查是不是有「管理身分組」權限
        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ 我沒有 `管理身分組` 的權限，不能幫你加/移除身分組。",
                ephemeral=True,
            )
            return

        # 檢查順位：機器人的最高身分組要在目標身分組上面
        if role >= bot_member.top_role:
            await interaction.response.send_message(
                f"❌ 我的身分組順位在 `{role.name}` 下面，無法管理這個身分組。\n"
                f"請把機器人的身分組拖到 `{role.name}` 之上。",
                ephemeral=True,
            )
            return

        # 加或移除角色
        if role in member.roles:
            await member.remove_roles(role, reason="自助移除身分組")
            msg = f"❌ 你已移除身分組 **{role.name}**"
        else:
            await member.add_roles(role, reason="自助領取身分組")
            msg = f"✅ 你已領取身分組 **{role.name}**"

        # ✅ 不動原本的面板，只給這個人看結果
        await interaction.response.send_message(msg, ephemeral=True)


class RoleButtonView(discord.ui.View):
    def __init__(self, roles: list[discord.Role]):
        super().__init__(timeout=None)  # 面板可以一直存在
        for role in roles:
            self.add_item(RoleButton(role))


# === 一鍵清除全部按鈕的互動介面 ===
class ClearView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🧹 清除全部訊息", style=discord.ButtonStyle.danger)
    async def clear_all(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # 檢查權限
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ 你沒有權限使用此功能。", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = 0

        async for msg in interaction.channel.history(limit=1000):
            try:
                await msg.delete()
                deleted += 1
            except:
                pass

        await interaction.followup.send(f"🧹 已清除 {deleted} 則訊息。", ephemeral=True)


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
    @app_commands.describe(
        numbers="一個數字表示(1~n)，兩個數字表示範圍(a~b)，不能打三個數字!!!"
    )
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
    async def vote(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "請設定投票參數：", view=VoteSettingsView(), ephemeral=True  # 給自己看即可
        )

    @app_commands.command(name="領取身分組", description="顯示可領取的身分組按鈕")
    async def role_command(self, interaction: discord.Interaction):
        guild = interaction.guild
        bot_member = guild.me

        # 伺服器裡所有身分組（從高到低）
        roles = guild.roles

        # 🔹 自動抓「這個伺服器」裡可領的身分組：
        # 1. 不是 @everyone
        # 2. 不是整合/managed 身分組（給別的 bot 用的那種）
        # 3. 排在機器人最高身分組下面（不然 bot 管不到）
        # 4. （可選）名字前面有特定前綴，例如「自取-」
        claimable_roles = [
            r
            for r in roles
            if not r.managed and r.name != "@everyone" and r < bot_member.top_role
            # and r.name.startswith("自取-") # 前綴控制 需要時啟用
        ]

        if not claimable_roles:
            await interaction.response.send_message(
                "這個伺服器目前沒有可領取的身分組。\n"
                "（可能是：沒設前綴、或是我的身分組順位太低、或是完全沒有自取用的身分組）",
                ephemeral=True,
            )
            return

        # 排序一下，讓上面的位置先顯示
        claimable_roles = sorted(
            claimable_roles, key=lambda r: r.position, reverse=True
        )

        embed = discord.Embed(
            title=f"🎭 領取 {guild.name} 的身分組",
            description="點擊下方按鈕即可領取或移除身分組：",
            color=discord.Color.blue(),
        )

        view = RoleButtonView(claimable_roles)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="查詢身分組", description="顯示伺服器中每個身分組的成員")
    async def roles_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        roles = [r for r in guild.roles if r.name != "@everyone" and not r.managed]

        if not roles:
            await interaction.response.send_message(
                "這個伺服器沒有可查詢的身分組。", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📜 {guild.name} 的身分組成員列表", color=discord.Color.gold()
        )

        for role in reversed(roles):  # 從高到低顯示
            members = [m.mention for m in role.members]
            if len(members) == 0:
                member_text = "（無成員）"
            elif len(members) > 10:
                # 超過 10 人時只顯示部分，避免 embed 過長
                member_text = "、".join(members[:10]) + f" ...（共 {len(members)} 人）"
            else:
                member_text = "、".join(members)

            embed.add_field(
                name=f"{role.name}（{len(role.members)} 人）",
                value=member_text,
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="清除訊息", description="清除訊息（可輸入數字或按按鈕刪除全部）"
    )
    @app_commands.describe(amount="要清除的訊息數量（可不填）")
    async def clear(self, interaction: discord.Interaction, amount: int = None):
        # 權限檢查
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ 你沒有權限使用此指令。", ephemeral=True
            )
            return

        # 使用者有輸入數字 -> 清除指定數量
        if amount is not None:
            if amount < 1 or amount > 1000:
                await interaction.response.send_message(
                    "⚠️ 請輸入 1~1000 之間的數字。", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(
                f"🧹 已清除 {len(deleted)} 則訊息。", ephemeral=True
            )
        else:
            # 沒輸入數字 -> 顯示按鈕
            view = ClearView()
            await interaction.response.send_message(
                "請選擇要執行的清除操作：", view=view, ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Math(bot))
