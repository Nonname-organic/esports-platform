import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TeamRecruitment(Base):
    __tablename__ = "teams_recruitments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    min_rank: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_time: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    activity_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    tournaments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    age_requirement: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    team_intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discord: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
