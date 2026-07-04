"""Notification Event Matrix（コード上の SSOT）。

docs/architecture/NOTIFICATION_EVENT_MATRIX.md と1対1で同期する。
「どのイベントが・どのカテゴリで・どのチャネルへ・誰に」通知されるかを定義する。

新イベントの通知化 = 本 MATRIX に1行追加（Registry 登録済みが前提 / ADR-0005, 0008）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.events.registry import Ev


@dataclass(frozen=True)
class NotifRule:
    category: str                       # 通知設定の分類（③のON/OFFキー）
    channels: tuple[str, ...]           # 配信先: "browser" / "discord" / "email"
    recipients: str                     # 受信者解決キー（resolver）
    subtype: str                        # NotificationService の subtype（既存enumマップ用）
    title: str
    body_template: str                  # metadata で format
    action_url_template: str = ""       # metadata で format


# ── Matrix（SSOT） ─────────────────────────────────────────────────────────
MATRIX: dict[str, NotifRule] = {
    Ev.TOURNAMENT_REGISTRATION_APPROVED: NotifRule(
        category="tournament",
        channels=("browser", "discord"),
        recipients="registered_team",
        subtype="application_approved",
        title="参加が承認されました",
        body_template="「{tournament_name}」への参加が承認されました",
        action_url_template="/tournaments/{tournament_id}",
    ),
    Ev.TOURNAMENT_REGISTRATION_REJECTED: NotifRule(
        category="tournament",
        channels=("browser", "discord"),
        recipients="registered_team",
        subtype="application_rejected",
        title="参加が却下されました",
        body_template="「{tournament_name}」への参加申請は却下されました",
        action_url_template="/tournaments/{tournament_id}",
    ),
    # 以降は planned（Matrix ドキュメント参照）。実装時にここへ追加する。
}


def rule_for(event_type: str) -> NotifRule | None:
    return MATRIX.get(event_type)
