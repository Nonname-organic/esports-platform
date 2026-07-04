"""EventEnvelope — 全ドメインイベント共通の契約（P0-2）。

設計: docs/architecture/PHASED_ARCHITECTURE.md §3
- domain_events テーブル（P0-3/P0-4）の各列にマップされる。
- trace_id / correlation_id / actor_ip は RequestContext から自動補完される。
- この時点では「契約（型）」のみを定義し、永続化（emit）は EventService（P0-3）で行う。
"""

from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.context import (
    get_actor_id,
    get_client_ip,
    get_correlation_id,
    get_trace_id,
)

# このプロセスがどの実行体か（api / worker）。worker は SERVICE_NAME=worker を設定。
SERVICE_NAME: str = os.getenv("SERVICE_NAME", "api")


class ActorType(str, enum.Enum):
    USER = "user"
    SYSTEM = "system"
    BOT = "bot"


class Visibility(str, enum.Enum):
    INTERNAL = "internal"  # 監査（内部のみ）
    PUBLIC = "public"      # 活動（公開タイムライン）


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventEnvelope(BaseModel):
    """イベントの標準封筒。emit 前に Registry で type/version が検証される（P0-3）。"""

    # 識別・版
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_version: int = 1
    type: str  # Registry 管理の型名 "domain.entity.action"
    occurred_at: datetime = Field(default_factory=_utcnow)

    # 実行主体
    actor_id: Optional[str] = None
    actor_type: ActorType = ActorType.USER
    actor_ip: Optional[str] = None

    # 発生元
    producer: str = "core"          # bounded context（tournament / team / scout ...）
    service: str = SERVICE_NAME      # api / worker

    # 対象
    entity_type: str
    entity_id: str

    # 変更内容（before/after は PII を格納しない：user_id 参照）
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None

    # 相関・冪等
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None

    # 可視性（監査 or 公開活動）
    visibility: Visibility = Visibility.INTERNAL

    @classmethod
    def build(
        cls,
        *,
        type: str,
        entity_type: str,
        entity_id: str,
        producer: str = "core",
        actor_id: Optional[str] = None,
        actor_type: ActorType = ActorType.USER,
        before: Optional[dict[str, Any]] = None,
        after: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        visibility: Visibility = Visibility.INTERNAL,
        idempotency_key: Optional[str] = None,
        event_version: int = 1,
    ) -> "EventEnvelope":
        """RequestContext（trace_id / correlation_id / actor_ip / actor_id）を自動補完して構築。

        actor_id 未指定時はコンテキストの認証ユーザーを採用（system/bot は明示 None + actor_type 指定）。
        """
        return cls(
            type=type,
            event_version=event_version,
            entity_type=entity_type,
            entity_id=str(entity_id),
            producer=producer,
            actor_id=str(actor_id) if actor_id else get_actor_id(),
            actor_type=actor_type,
            actor_ip=get_client_ip(),
            before=before,
            after=after,
            metadata=metadata,
            visibility=visibility,
            trace_id=get_trace_id(),
            correlation_id=get_correlation_id(),
            idempotency_key=idempotency_key,
        )
