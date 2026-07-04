"""NotificationPreference — ユーザーごとの通知 ON/OFF（機能③ / ADR-0010）。

prefs(JSONB) の構造・キー・デフォルト・precedence を知るのは PreferenceService だけ。
本モデルは保存箱に徹する（他層は PreferenceService 経由でのみアクセスする）。

prefs 例:
  { "channels":   {"browser": true, "email": false, "discord": true},
    "categories": {"tournament": true, "team": true, "scout": true, "match": true} }
未設定キーは default ON（後方互換）。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    prefs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
