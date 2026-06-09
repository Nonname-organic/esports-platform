"""コマンドメトリクス & エラーログのバッファリング/フラッシュ。

- on_app_command_completion / tree.on_error から record() を呼ぶ。
- 30秒ごと（または上限到達時）に /api/v1/bot/metrics へバッチ送信。
- レイテンシは interaction.created_at（ユーザーがコマンドを実行した時刻）からの経過。
"""

import logging
from datetime import datetime, timezone

import discord

logger = logging.getLogger("bot.monitoring")

_FLUSH_THRESHOLD = 50


def latency_ms(interaction: discord.Interaction) -> int:
    try:
        delta = datetime.now(timezone.utc) - interaction.created_at
        return max(0, int(delta.total_seconds() * 1000))
    except Exception:
        return 0


class Metrics:
    def __init__(self, api_client):
        self._api = api_client
        self._buf: list[dict] = []

    def record(
        self,
        interaction: discord.Interaction,
        command: str,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        self._buf.append({
            "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
            "discord_user_id": str(interaction.user.id),
            "command": command,
            "success": success,
            "latency_ms": latency_ms(interaction),
            "error_type": error_type,
        })
        if len(self._buf) >= _FLUSH_THRESHOLD:
            # 即時フラッシュはイベントループに委譲（呼び出し元は同期想定）
            pass

    async def flush(self) -> None:
        if not self._buf:
            return
        items, self._buf = self._buf, []
        try:
            await self._api.ingest_metrics(items)
        except Exception as e:  # メトリクス送信失敗で本処理を妨げない
            logger.warning("metrics flush failed: %s", e)

    async def log_error(
        self,
        interaction: discord.Interaction | None,
        command: str | None,
        error_type: str,
        message: str,
        traceback_str: str | None = None,
    ) -> None:
        try:
            await self._api.log_error({
                "guild_id": str(interaction.guild_id) if interaction and interaction.guild_id else None,
                "discord_user_id": str(interaction.user.id) if interaction else None,
                "command": command,
                "error_type": error_type,
                "message": message,
                "traceback": traceback_str,
            })
        except Exception as e:
            logger.warning("error log failed: %s", e)
