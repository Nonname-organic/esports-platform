import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class DiscordServer(UUIDMixin, Base):
    """大会↔Discordサーバー紐付け + 自動生成リソース管理"""
    __tablename__ = "discord_servers"

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    guild_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # {"admin": "id", "organizer": "id", "captain": "id", "player": "id", "spectator": "id"}
    role_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"INFORMATION": "id", "TOURNAMENT": "id", "MATCHES": "id", "STREAM": "id", "SUPPORT": "id", "ARCHIVE": "id"}
    category_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DiscordChannel(UUIDMixin, Base):
    """自動生成チャンネル管理（試合チャンネル含む）"""
    __tablename__ = "discord_channels"

    discord_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discord_servers.id", ondelete="CASCADE"), nullable=False,
    )
    channel_id: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DiscordLink(UUIDMixin, Base):
    """ユーザー↔Discord OAuth紐付け"""
    __tablename__ = "discord_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    discord_user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    discord_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
