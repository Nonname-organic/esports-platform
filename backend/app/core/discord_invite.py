"""Discord招待URLの正規化（API層と通知層で共有）。

招待は「https://discord.gg/xxxx」でも招待コード「xxxx」だけでも入力されうる。
コードのまま href やメッセージに載せると壊れたリンクになるため、
表示・送信の直前に必ずここを通す。
"""
from __future__ import annotations

import re

_DISCORD_INVITE_RE = re.compile(r"^[A-Za-z0-9-]{2,32}$")


def normalize_discord_invite(value) -> str:
    if not isinstance(value, str):
        return ""
    invite = value.strip()
    if not invite:
        return ""
    if invite.startswith(("https://", "http://")):
        return invite
    if invite.startswith(("discord.gg/", "discord.com/invite/", "www.discord.gg/")):
        return f"https://{invite}"
    if _DISCORD_INVITE_RE.match(invite):
        return f"https://discord.gg/{invite}"
    # 判別できない文字列はリンクにしない（javascript: 等を弾く）
    return ""
