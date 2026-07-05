"""SeasonService — シーズン（時間窓）の列挙（ADR-0016 / read-only・テーブルなし）。

将来 seasons テーブルへ移行する際も、公開IF（current/previous/list）は不変に保つ。
"""

from __future__ import annotations

from app.seasons.utils import season_id, season_label, season_window


def _info(key: str) -> dict:
    start, end = season_window(key)
    return {
        "key": key,
        "id": season_id(key),
        "label": season_label(key),
        "start_at": start.isoformat() if start else None,
        "end_at": end.isoformat() if end else None,
        "is_current": key == "current",
    }


class SeasonService:
    def current(self) -> dict:
        return _info("current")

    def previous(self) -> dict:
        return _info("previous")

    def all_time(self) -> dict:
        return _info("all")

    def list(self) -> list[dict]:
        """Current / Previous / All Time。"""
        return [_info("current"), _info("previous"), _info("all")]
