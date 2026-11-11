import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class MatchResultReport(UUIDMixin, TimestampMixin, Base):
    """対戦チームからの結果報告（1試合1件。報告し直すと上書き）。

    pending   : 報告済み・相手チームの確認待ち
    confirmed : 相手チームか主催者が確認し、結果を確定した
    disputed  : 相手チームが異議を出した、または両チームの報告が食い違った（主催者が裁定）
    superseded: 主催者が報告を待たずに結果を確定した
    """
    __tablename__ = "match_result_reports"

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    winner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False,
    )
    reported_by_team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False,
    )
    reported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
