"""Season DTO（ADR-0016）。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SeasonInfo(BaseModel):
    key: str          # all | current | previous
    id: str           # 安定ID（例: 2026-Q3 / all-time）
    label: str        # 表示名（例: 2026 Q3 / All Time）
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    is_current: bool = False
