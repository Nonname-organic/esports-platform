"""Discord側RBAC（即時UXゲート）。

権威判定はバックエンド(/api/v1/bot/*)が DiscordLink→User のrole/所有権で行う。
ここは「明らかに権限が無い操作をAPI往復前に弾く」高速ゲートに徹する。
Discordロール名（テンプレ生成の Admin/Organizer/Captain/Player/Spectator）と
guild_permissions から最小ロールを推定する。
"""

from enum import IntEnum

import discord
from discord import app_commands


class Role(IntEnum):
    SPECTATOR = 0
    PLAYER = 1
    CAPTAIN = 2
    ORGANIZER = 3
    ADMIN = 4


LABEL = {
    Role.SPECTATOR: "Spectator",
    Role.PLAYER: "Player",
    Role.CAPTAIN: "Captain",
    Role.ORGANIZER: "Organizer",
    Role.ADMIN: "Admin",
}

_NAME_TO_ROLE = {
    "admin": Role.ADMIN,
    "organizer": Role.ORGANIZER,
    "captain": Role.CAPTAIN,
    "player": Role.PLAYER,
    "spectator": Role.SPECTATOR,
}


def member_role(user: discord.abc.User) -> Role:
    """Discordメンバーの推定ロール。DM等メンバー情報が無い場合はPLAYER扱い。"""
    if not isinstance(user, discord.Member):
        # DMでは権限判定不可。閲覧+自分の操作までは許可するためPLAYER。
        return Role.PLAYER
    perms = user.guild_permissions
    if perms.administrator:
        return Role.ADMIN
    best = Role.SPECTATOR
    for r in user.roles:
        mapped = _NAME_TO_ROLE.get(r.name.lower())
        if mapped is not None and mapped > best:
            best = mapped
    # manage_guild を持つなら最低でもOrganizer扱い
    if perms.manage_guild and best < Role.ORGANIZER:
        best = Role.ORGANIZER
    return best


class MissingRole(app_commands.CheckFailure):
    def __init__(self, required: Role):
        self.required = required
        super().__init__(f"このコマンドには **{LABEL[required]}** 以上の権限が必要です")


def requires(min_role: Role):
    """app_commands用チェックデコレータ。"""

    async def predicate(interaction: discord.Interaction) -> bool:
        if member_role(interaction.user) < min_role:
            raise MissingRole(min_role)
        return True

    return app_commands.check(predicate)
