"""Season 時間窓のユーティリティ（ADR-0016 / テーブルなし）。

season key: all（全期間） / current（今四半期） / previous（前四半期）。
将来 seasons テーブルへ移行する際は、ここが唯一の境界になる。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

SEASON_KEYS = ("all", "current", "previous")


def _quarter_start(year: int, q: int) -> datetime:
    """q=0..3 の四半期開始（UTC）。"""
    return datetime(year, q * 3 + 1, 1, tzinfo=timezone.utc)


def _current_quarter(now: datetime) -> tuple[int, int]:
    return now.year, (now.month - 1) // 3


def season_window(key: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """[start, end) を返す。all は (None, None)。"""
    if key == "all":
        return None, None
    now = datetime.now(timezone.utc)
    year, q = _current_quarter(now)
    if key == "previous":
        q -= 1
        if q < 0:
            q = 3
            year -= 1
    start = _quarter_start(year, q)
    end = _quarter_start(year + 1, 0) if q == 3 else _quarter_start(year, q + 1)
    return start, end


def season_label(key: str) -> str:
    if key == "all":
        return "All Time"
    now = datetime.now(timezone.utc)
    year, q = _current_quarter(now)
    if key == "previous":
        q -= 1
        if q < 0:
            q, year = 3, year - 1
    return f"{year} Q{q + 1}"


def season_id(key: str) -> str:
    """安定ID（将来の materialize 時の season_id 相当）。"""
    if key == "all":
        return "all-time"
    now = datetime.now(timezone.utc)
    year, q = _current_quarter(now)
    if key == "previous":
        q -= 1
        if q < 0:
            q, year = 3, year - 1
    return f"{year}-Q{q + 1}"
