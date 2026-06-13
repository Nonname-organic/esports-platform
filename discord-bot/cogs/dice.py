"""進行用ユーティリティ: ダイス / コイントス / ランダム選択。

大会進行（先攻後攻・マップ先選択・抽選）でチャンネル内に使う。
権限制限なし（同一チャンネルの参加者なら誰でも）。
"""

import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from ui.common import brand_embed, info_embed

_DICE_RE = re.compile(r"^\s*(\d*)d(\d+)\s*$", re.IGNORECASE)


class DiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roll", description="ダイスを振る（例: 1d100, 2d6）")
    @app_commands.describe(dice="NdM 形式（省略時 1d100）")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d100"):
        m = _DICE_RE.match(dice)
        if not m:
            await interaction.response.send_message(
                embed=info_embed("⚠️ 形式エラー", "`1d100` や `2d6` の形式で指定してください"), ephemeral=True
            )
            return
        count = int(m.group(1) or 1)
        sides = int(m.group(2))
        if not (1 <= count <= 50) or not (2 <= sides <= 1000):
            await interaction.response.send_message(
                embed=info_embed("⚠️ 範囲外", "個数は1〜50、面は2〜1000まで"), ephemeral=True
            )
            return
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        e = brand_embed("🎲 ダイス", f"**{dice}** → 合計 **{total}**")
        if count > 1:
            e.add_field(name="内訳", value=" + ".join(map(str, rolls))[:1024], inline=False)
        e.set_footer(text=f"{interaction.user.display_name} が振りました")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="coinflip", description="コイントス（表/裏）")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["🪙 表 (Heads)", "🪙 裏 (Tails)"])
        e = brand_embed("コイントス", f"結果: **{result}**")
        e.set_footer(text=f"{interaction.user.display_name}")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="pick", description="候補からランダムに1つ選ぶ（カンマ区切り）")
    @app_commands.describe(options="例: TeamA, TeamB / Ascent, Bind, Haven")
    async def pick(self, interaction: discord.Interaction, options: str):
        choices = [o.strip() for o in options.split(",") if o.strip()]
        if len(choices) < 2:
            await interaction.response.send_message(
                embed=info_embed("⚠️ 候補不足", "カンマ区切りで2つ以上指定してください"), ephemeral=True
            )
            return
        chosen = random.choice(choices)
        e = brand_embed("🎯 ランダム選択", f"選ばれたのは… **{chosen}**")
        e.set_footer(text=f"候補: {', '.join(choices)}"[:2048])
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(DiceCog(bot))
