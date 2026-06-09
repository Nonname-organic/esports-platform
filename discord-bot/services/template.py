"""Discordサーバーテンプレート生成"""

import discord

from config import SERVER_TEMPLATE


async def build_tournament_server(guild: discord.Guild) -> dict:
    """
    ギルド内にカテゴリ・チャンネル・ロールを生成。
    Returns: {role_ids, category_ids}
    """
    role_ids: dict[str, str] = {}
    category_ids: dict[str, str] = {}

    # ── ロール生成 ──
    for role_def in SERVER_TEMPLATE["roles"]:
        existing = discord.utils.get(guild.roles, name=role_def["name"])
        if existing:
            role_ids[role_def["name"].lower()] = str(existing.id)
            continue
        perms = discord.Permissions.none()
        if role_def["permissions"] == "admin":
            perms = discord.Permissions.all()
        elif role_def["permissions"] == "manage":
            perms = discord.Permissions(manage_channels=True, manage_messages=True, kick_members=True)
        elif role_def["permissions"] == "view":
            perms = discord.Permissions(read_messages=True)
        else:
            perms = discord.Permissions(read_messages=True, send_messages=True)

        role = await guild.create_role(
            name=role_def["name"],
            colour=discord.Colour(role_def["color"]),
            permissions=perms,
            reason="Tournament setup",
        )
        role_ids[role_def["name"].lower()] = str(role.id)

    # ── カテゴリ + チャンネル生成 ──
    for cat_def in SERVER_TEMPLATE["categories"]:
        category = await guild.create_category(cat_def["name"], reason="Tournament setup")
        key = cat_def["name"].split(" ", 1)[-1] if " " in cat_def["name"] else cat_def["name"]
        category_ids[key] = str(category.id)
        for ch_name in cat_def["channels"]:
            await guild.create_text_channel(ch_name, category=category, reason="Tournament setup")

    # ── アーカイブカテゴリ ──
    archive = await guild.create_category(SERVER_TEMPLATE["archive_category"], reason="Tournament setup")
    category_ids["ARCHIVE"] = str(archive.id)

    return {"role_ids": role_ids, "category_ids": category_ids}


async def create_match_channel(guild: discord.Guild, channel_name: str, category_id: str | None) -> str | None:
    """試合用チャンネルを🏆 MATCHESカテゴリ配下に作成"""
    category = None
    if category_id:
        category = guild.get_channel(int(category_id))
    channel = await guild.create_text_channel(channel_name, category=category, reason="Match started")
    return str(channel.id)


async def archive_channel(guild: discord.Guild, channel_id: str, archive_category_id: str | None) -> None:
    """試合チャンネルをアーカイブカテゴリへ移動"""
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return
    if archive_category_id:
        archive_cat = guild.get_channel(int(archive_category_id))
        if archive_cat:
            await channel.edit(category=archive_cat, reason="Match finished")
    # 読み取り専用化
    overwrite = channel.overwrites_for(guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(guild.default_role, overwrite=overwrite)
