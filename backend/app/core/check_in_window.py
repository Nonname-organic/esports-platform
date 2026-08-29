"""チェックイン受付時間幅の判定（Web / Discord bot 共通）。

チェックインは主催者が設定した「開始〜終了」の間だけ受け付ける。
例: 8/30 13:00 〜 8/30 13:05 の5分間。

後方互換のため未設定は緩く解釈する:
  開始・終了とも未設定 → 常時受付（従来どおり）
  開始のみ設定         → 開始以降ずっと受付
  終了のみ設定         → 終了まで受付
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

WindowState = Literal["open", "before", "after"]


def check_in_window_state(tournament) -> WindowState:
    now = datetime.now(timezone.utc)
    start = tournament.check_in_start_at
    end = tournament.check_in_end_at
    if start and now < start:
        return "before"
    if end and now > end:
        return "after"
    return "open"
