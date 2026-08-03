"""ランキング週次スナップショット（順位変動▲▼の基準点 / ADR-0015 Future の第一歩）。

RankingAggregator は読み取り専用のまま、週次cron（etl_scheduler）だけがここに書き込む。
リーダーボード表示時に直近スナップショットと比較して rank_change を算出する。
"""

import uuid
from datetime import date

from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(10), nullable=False)  # 'team' | 'player'
    season: Mapped[str] = mapped_column(String(10), nullable=False)  # 'all' | 'current'
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    rp: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_at: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        Index("ix_ranking_snapshots_lookup", "scope", "season", "captured_at"),
    )
