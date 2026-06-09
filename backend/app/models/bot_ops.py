"""Discord Bot 運用系モデル: コマンド利用履歴 / エラーログ / 試合異議。

既存テーブルは変更せず追加のみ。check-in は tournament_registrations の
カラム追加（migration 008）で扱うため、ここには持たない。
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class CommandMetric(UUIDMixin, Base):
    """Discordスラッシュコマンドの利用履歴（成功可否・レイテンシ）。"""
    __tablename__ = "command_metrics"

    guild_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    discord_user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    command: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True,
    )


class BotErrorLog(UUIDMixin, Base):
    """Bot側で捕捉した例外のログ。"""
    __tablename__ = "bot_error_logs"

    guild_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discord_user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    command: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True,
    )


class MatchDispute(UUIDMixin, Base):
    """試合結果への異議申し立て。"""
    __tablename__ = "match_disputes"

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    raised_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    discord_user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")  # open/resolved/rejected
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
