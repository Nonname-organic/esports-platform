"""Event Registry — イベント定義の Single Source of Truth（ADR-0005 / PHASED §4）。

イベント名・version・payload schema・visibility・dispatch可否を一元管理する。
`EventService.emit()` は必ずここで検証する（未登録の野良イベントは拒否）。

命名規則: <domain>.<entity>.<action>  すべて小文字・ドット区切り
  domain: bounded context (team, tournament, player, ...)
  entity: 集約/対象 (member, registration, bracket, status, ...)
  action: 動作 (created, updated, added, removed, approved, published, ...)

新イベント追加 = 定数1つ + REGISTRY に1エントリ（マイグレーション不要）。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.events.envelope import Visibility


class EventSpec(BaseModel):
    """1イベント型の仕様。"""
    version: int = 1
    visibility: Visibility = Visibility.INTERNAL
    dispatch: bool = False              # True=Outboxで consumer へ fan-out（副作用あり）
    payload: Optional[type[BaseModel]] = None  # after の期待スキーマ（任意・段階導入）

    model_config = {"arbitrary_types_allowed": True}


class UnknownEventError(ValueError):
    """Registry 未登録のイベント型を emit しようとした。"""


# ── イベント名定数（domain.entity.action） ─────────────────────────────────
class Ev:
    # Team（監査）
    TEAM_CREATED            = "team.created"
    TEAM_UPDATED            = "team.updated"
    TEAM_LOGO_CHANGED       = "team.logo.changed"
    TEAM_BANNER_CHANGED     = "team.banner.changed"
    TEAM_MEMBER_ADDED       = "team.member.added"
    TEAM_MEMBER_REMOVED     = "team.member.removed"
    TEAM_MEMBER_ROLE_CHANGED= "team.member.role_changed"
    TEAM_OWNER_CHANGED      = "team.owner.changed"

    # Player（公開活動 / Activity Feed）
    PLAYER_TEAM_JOINED      = "player.team.joined"

    # Tournament（監査 + 一部 dispatch）
    TOURNAMENT_CREATED          = "tournament.created"
    TOURNAMENT_UPDATED          = "tournament.updated"
    TOURNAMENT_PUBLISHED        = "tournament.published"
    TOURNAMENT_UNPUBLISHED      = "tournament.unpublished"
    TOURNAMENT_STATUS_CHANGED   = "tournament.status.changed"
    TOURNAMENT_BRACKET_GENERATED= "tournament.bracket.generated"
    TOURNAMENT_BRACKET_DELETED  = "tournament.bracket.deleted"
    TOURNAMENT_MATCH_RESULT_UPDATED = "tournament.match.result_updated"
    TOURNAMENT_REGISTRATION_APPROVED = "tournament.registration.approved"
    TOURNAMENT_REGISTRATION_REJECTED = "tournament.registration.rejected"
    TOURNAMENT_CHECKIN_PERFORMED= "tournament.checkin.performed"
    TOURNAMENT_COMPLETED        = "tournament.completed"


# ── Registry（SSOT） ───────────────────────────────────────────────────────
# dispatch=True: consumer への fan-out が必要（通知/レポート等・P0-4以降で配線）
# dispatch=False: 純監査（記録のみ・Outboxキューに載せない）
_AUDIT = EventSpec(visibility=Visibility.INTERNAL, dispatch=False)


REGISTRY: dict[str, EventSpec] = {
    # Team（すべて純監査）
    Ev.TEAM_CREATED: _AUDIT,
    Ev.TEAM_UPDATED: _AUDIT,
    Ev.TEAM_LOGO_CHANGED: _AUDIT,
    Ev.TEAM_BANNER_CHANGED: _AUDIT,
    Ev.TEAM_MEMBER_ADDED: _AUDIT,
    Ev.TEAM_MEMBER_REMOVED: _AUDIT,
    Ev.TEAM_MEMBER_ROLE_CHANGED: _AUDIT,
    Ev.TEAM_OWNER_CHANGED: _AUDIT,

    # Player（公開活動 / Activity Feed・consumer不要のため dispatch=False）
    Ev.PLAYER_TEAM_JOINED: EventSpec(visibility=Visibility.PUBLIC, dispatch=False),

    # Tournament（純監査）
    Ev.TOURNAMENT_CREATED: _AUDIT,
    Ev.TOURNAMENT_UPDATED: _AUDIT,
    Ev.TOURNAMENT_PUBLISHED: _AUDIT,
    Ev.TOURNAMENT_UNPUBLISHED: _AUDIT,
    Ev.TOURNAMENT_STATUS_CHANGED: _AUDIT,
    Ev.TOURNAMENT_BRACKET_GENERATED: _AUDIT,
    Ev.TOURNAMENT_BRACKET_DELETED: _AUDIT,
    Ev.TOURNAMENT_CHECKIN_PERFORMED: _AUDIT,

    # Tournament（副作用あり = dispatch。P1/P0-4 で consumer 配線）
    Ev.TOURNAMENT_MATCH_RESULT_UPDATED: EventSpec(dispatch=True),
    Ev.TOURNAMENT_REGISTRATION_APPROVED: EventSpec(dispatch=True),
    Ev.TOURNAMENT_REGISTRATION_REJECTED: EventSpec(dispatch=True),
    Ev.TOURNAMENT_COMPLETED: EventSpec(visibility=Visibility.PUBLIC, dispatch=True),
}


def get_spec(event_type: str) -> EventSpec:
    spec = REGISTRY.get(event_type)
    if spec is None:
        raise UnknownEventError(f"未登録のイベント型です: {event_type!r}（Event Registry に追加してください）")
    return spec


def is_registered(event_type: str) -> bool:
    return event_type in REGISTRY


def all_types() -> list[str]:
    return sorted(REGISTRY.keys())
