"""リクエストスコープのコンテキスト（trace_id / correlation_id / client_ip / actor_id）。

EventEnvelope や監査が「どのリクエストで・誰が」を、引数を全層に通さず取得するための
contextvars ベースの実装。ミドルウェア（API）や worker ループの先頭で set する。

- trace_id:       1リクエスト（または1 worker ジョブ）を貫く相関ID
- correlation_id: 因果連鎖（イベント→派生イベント）。既定は trace_id と同一
- client_ip:      X-Forwarded-For 先頭（CloudFront→nginx 経由）
- actor_id:       認証済みユーザーID（依存性解決後に set）
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional

_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
_actor_id: ContextVar[Optional[str]] = ContextVar("actor_id", default=None)


def new_id() -> str:
    return str(uuid.uuid4())


def set_request_context(
    *,
    trace_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> str:
    """リクエスト/ジョブ開始時に呼ぶ。trace_id を返す（未指定なら生成）。"""
    tid = trace_id or new_id()
    _trace_id.set(tid)
    _correlation_id.set(correlation_id or tid)  # 既定は trace_id と同一
    _client_ip.set(client_ip)
    _actor_id.set(None)
    return tid


def set_actor(actor_id: Optional[str]) -> None:
    _actor_id.set(str(actor_id) if actor_id else None)


def get_trace_id() -> Optional[str]:
    return _trace_id.get()


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def get_client_ip() -> Optional[str]:
    return _client_ip.get()


def get_actor_id() -> Optional[str]:
    return _actor_id.get()
