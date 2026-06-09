"""グローバル例外 → ユーザー向けembed 変換。

APIエラー(ApiError)、権限エラー(MissingRole/CheckFailure)、クールダウン等を
わかりやすい日本語embedに整形する。詳細は bot_error_logs に保存（monitoring経由）。
"""

import discord
from discord import app_commands

from core.rbac import MissingRole


class ApiError(Exception):
    """APIクライアントが投げる業務エラー（status + メッセージ）。"""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}")


def error_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=0xE74C3C)


def to_user_embed(error: Exception) -> discord.Embed:
    """例外をユーザー表示用embedへ。"""
    if isinstance(error, MissingRole):
        return error_embed("⛔ 権限がありません", str(error))
    if isinstance(error, app_commands.CheckFailure):
        return error_embed("⛔ 実行できません", str(error) or "権限またはコンテキストが不正です")
    if isinstance(error, app_commands.CommandOnCooldown):
        return error_embed("⏳ クールダウン中", f"{error.retry_after:.1f} 秒後に再実行できます")
    if isinstance(error, ApiError):
        if error.status == 401:
            return error_embed("🔑 連携が必要です", "`/link` でDiscordとアカウントを連携してください")
        if error.status == 403:
            return error_embed("⛔ 権限がありません", error.message or "この操作の権限がありません")
        if error.status == 404:
            return error_embed("🔍 見つかりません", error.message or "対象が存在しません")
        return error_embed("⚠️ エラー", error.message or "処理に失敗しました")
    # 想定外
    return error_embed("⚠️ 予期しないエラー", "処理に失敗しました。時間をおいて再試行してください")
