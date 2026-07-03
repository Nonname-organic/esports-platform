import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlayerLFT(Base):
    __tablename__ = "players_lft"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    current_rank: Mapped[str] = mapped_column(String(50), nullable=False)
    peak_rank: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_time: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    experience: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    premier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    agents: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discord: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    twitter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
