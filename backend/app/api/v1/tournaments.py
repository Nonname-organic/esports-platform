import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.check_in_window import check_in_window_state
from app.core.discord_invite import normalize_discord_invite
from app.core.dependencies import Cache, CurrentUser, DBSession, OrganizerUser
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.storage import sign_attachments, resign_stored_url
from app.models.enums import GameType, RegistrationStatus, TournamentStatus
from app.models.tournament import Tournament
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.rules import ApplyTemplateRequest, RulesDocRequest
from app.schemas.tournament import (
    BracketResponse,
    RegistrationInfo,
    RegistrationRequest,
    StatusChangeRequest,
    TournamentCreate,
    TournamentDetail,
    TournamentSummary,
    TournamentUpdate,
)
from app.services.tournament import TournamentService

router = APIRouter(prefix="/tournaments", tags=["大会管理"])




def _public_rules(rules):
    """
    大会詳細は未認証でも取得できるため、rules から秘密情報を落とす。

    Discord Webhook URL は、知られると誰でもそのチャンネルへ投稿できてしまう
    実質的な認証情報。設定済みかどうかだけを別フィールドで伝える。
    """
    if not isinstance(rules, dict):
        return rules
    sanitized = dict(rules)
    discord = sanitized.get("discord")
    if isinstance(discord, dict):
        discord = dict(discord)
        discord.pop("webhook_url", None)
        discord["invite_url"] = normalize_discord_invite(discord.get("invite_url"))
        sanitized["discord"] = discord
    return sanitized


def _build_detail(tournament, count: int) -> TournamentDetail:
    return TournamentDetail(
        id=str(tournament.id),
        name=tournament.name,
        game=tournament.game,
        format=tournament.format,
        status=tournament.status,
        max_teams=tournament.max_teams,
        registered_teams=count,
        start_at=tournament.start_at,
        prize_pool=tournament.prize_pool,
        banner_url=resign_stored_url(tournament.banner_url),
        description=tournament.description,
        rules=_public_rules(tournament.rules),
        attachments=sign_attachments(tournament.attachments),
        organizer_id=str(tournament.organizer_id),
        registration_start_at=tournament.registration_start_at,
        registration_end_at=tournament.registration_end_at,
        check_in_start_at=tournament.check_in_start_at,
        check_in_end_at=tournament.check_in_end_at,
        end_at=tournament.end_at,
        require_check_in=tournament.require_check_in,
        created_at=tournament.created_at,
        updated_at=tournament.updated_at,
        # 編集フォームの初期値として読み戻す項目（作成フォームと対応）
        subtitle=tournament.subtitle,
        thumbnail_url=resign_stored_url(tournament.thumbnail_url),
        season=tournament.season,
        split=tournament.split,
        tier=tournament.tier,
        visibility=tournament.visibility,
        seeding_type=tournament.seeding_type,
        min_teams=tournament.min_teams,
        prize_currency=tournament.prize_currency,
        require_team_membership=tournament.require_team_membership,
        approval_mode=tournament.approval_mode,
        age_restriction=tournament.age_restriction,
        region_restriction=tournament.region_restriction,
        rank_restriction=tournament.rank_restriction,
        # Webhook URL自体は返さない（実質的な認証情報のため）
        discord_webhook_url=None,
        discord_webhook_configured=bool(
            (tournament.discord_webhook_url or "").strip()
            or ((tournament.rules or {}).get("discord") or {}).get("webhook_url")
        ),
        analytics_enabled=tournament.analytics_enabled,
        player_stats_enabled=tournament.player_stats_enabled,
        ranking_enabled=tournament.ranking_enabled,
        is_public=tournament.is_public,
    )


@router.get("", response_model=ListResponse[TournamentSummary])
async def list_tournaments(
    db: DBSession,
    cache: Cache,
    game: GameType | None = Query(default=None),
    status: TournamentStatus | None = Query(default=None),
    cursor: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    month: str | None = Query(default=None, description="YYYY-MM。指定月に受付/開催する大会のみ"),
):
    from_at = to_at = None
    if month:
        try:
            y, m = (int(x) for x in month.split("-"))
            from_at = datetime(y, m, 1, tzinfo=timezone.utc)
            to_at = datetime(y + 1, 1, 1, tzinfo=timezone.utc) if m == 12 else datetime(y, m + 1, 1, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            from_at = to_at = None  # 不正な月指定は無視（全件）

    service = TournamentService(db, cache)
    tournaments, has_next = await service._repo.list_by_game_status(
        game=game, status=status, limit=limit, cursor=cursor, from_at=from_at, to_at=to_at
    )

    items = []
    for t in tournaments:
        count = await service._repo.get_registered_teams_count(t.id)
        items.append(TournamentSummary(
            id=str(t.id),
            name=t.name,
            game=t.game,
            format=t.format,
            status=t.status,
            max_teams=t.max_teams,
            registered_teams=count,
            registration_start_at=t.registration_start_at,
            registration_end_at=t.registration_end_at,
            start_at=t.start_at,
            end_at=t.end_at,
            prize_pool=t.prize_pool,
            banner_url=resign_stored_url(t.banner_url),
        ))

    next_cursor = str(tournaments[-1].id) if has_next and tournaments else None
    return ListResponse(data=items, meta=Meta(has_next=has_next, cursor=next_cursor))


@router.get("/mine", response_model=Response[list[TournamentDetail]])
async def list_my_tournaments(db: DBSession, cache: Cache, current_user: OrganizerUser):
    """主催者自身の大会一覧"""
    service = TournamentService(db, cache)
    tournaments = await service.get_my_tournaments(current_user.id)
    items = []
    for t in tournaments:
        count = await service._repo.get_registered_teams_count(t.id)
        items.append(_build_detail(t, count))
    return Response(data=items, meta=None)


@router.post("", response_model=Response[TournamentDetail], status_code=201)
async def create_tournament(
    data: TournamentCreate, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    service = TournamentService(db, cache)
    tournament = await service.create(data, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.get("/{tournament_id}", response_model=Response[TournamentDetail])
async def get_tournament(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TournamentService(db, cache)
    tournament = await service.get_detail(tournament_id)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


# ── 没入型 大会詳細 Read Model（ADR-0017・公開・追加のみ / 既存API不変） ──────────
@router.get("/{tournament_id}/overview", response_model=Response[dict])
async def get_tournament_overview(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    """Hero/Stream/Results 用の集約（現在の試合・配信・完了結果を含む）。"""
    from app.services.tournament_immersion import TournamentImmersionService
    data = await TournamentImmersionService(db, cache).overview(tournament_id)
    return Response(data=data, meta=None)


@router.get("/{tournament_id}/live", response_model=Response[dict])
async def get_tournament_live(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    """Live Status / Live Ticker / Upcoming 用（進行率・現在試合・次の試合）。"""
    from app.services.tournament_immersion import TournamentImmersionService
    data = await TournamentImmersionService(db, cache).live_status(tournament_id)
    return Response(data=data, meta=None)


@router.get("/{tournament_id}/statistics", response_model=Response[dict])
async def get_tournament_statistics(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    """Statistics カード用（参加数・消化率・賞金・MVP・優勝）。"""
    from app.services.tournament_immersion import TournamentImmersionService
    data = await TournamentImmersionService(db, cache).statistics(tournament_id)
    return Response(data=data, meta=None)


@router.patch("/{tournament_id}", response_model=Response[TournamentDetail])
async def update_tournament(
    tournament_id: uuid.UUID, data: TournamentUpdate,
    db: DBSession, cache: Cache, current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    tournament = await service.update(tournament_id, data, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.patch("/{tournament_id}/status", response_model=Response[TournamentDetail])
async def change_tournament_status(
    tournament_id: uuid.UUID, data: StatusChangeRequest,
    db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """大会ステータス変更（ドラフト→受付開始→受付終了→開催中→完了）"""
    service = TournamentService(db, cache)
    tournament = await service.change_status(tournament_id, data.status, current_user)
    count = await service._repo.get_registered_teams_count(tournament.id)
    return Response(data=_build_detail(tournament, count), meta=None)


@router.delete("/{tournament_id}", status_code=204)
async def delete_tournament(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    service = TournamentService(db, cache)
    await service.delete(tournament_id, current_user)


# ── 大会ルール（機能⑧: Section構造Markdown + テンプレート） ──────────────────
@router.get("/rules/templates", response_model=Response[list[dict]])
async def list_rules_templates():
    """ルールテンプレート一覧（VALORANT標準など）。"""
    from app.schemas.rules import list_templates
    return Response(data=list_templates(), meta=None)


@router.get("/{tournament_id}/rules", response_model=Response[dict])
async def get_tournament_rules(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    """ルール（Section構造）。未設定なら全固定Sectionの空雛形（公開）。"""
    service = TournamentService(db, cache)
    return Response(data=await service.get_rules(tournament_id), meta=None)


@router.put("/{tournament_id}/rules", response_model=Response[dict])
async def update_tournament_rules(
    tournament_id: uuid.UUID, data: RulesDocRequest,
    db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """ルールを差し替え保存（organizer/Admin のみ）。"""
    service = TournamentService(db, cache)
    return Response(data=await service.update_rules(tournament_id, data.model_dump(), current_user), meta=None)


@router.post("/{tournament_id}/rules/apply-template", response_model=Response[dict])
async def apply_tournament_rules_template(
    tournament_id: uuid.UUID, data: ApplyTemplateRequest,
    db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """テンプレートを適用（organizer/Admin のみ）。"""
    service = TournamentService(db, cache)
    return Response(data=await service.apply_rules_template(tournament_id, data.template_id, current_user), meta=None)


# ── 大会監査ログ（ADR-0012: organizer/Admin のみ・internal限定） ──────────────
@router.get("/{tournament_id}/audit", response_model=Response[list[dict]])
async def get_tournament_audit(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    service = TournamentService(db, cache)
    items = await service.get_audit(tournament_id, current_user, limit=limit, offset=offset)
    return Response(data=items, meta=None)


# ── 大会終了レポート（ADR-0009: Event経由で非同期生成・APIは読むだけ） ────────
@router.get("/{tournament_id}/report")
async def get_tournament_report(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    """生成済みの大会終了レポートを返す（未生成は404）。"""
    service = TournamentService(db, cache)
    report = await service.get_report(tournament_id)
    if not report:
        raise NotFoundError("レポート", str(tournament_id))
    return {"data": {
        "tournament_id": str(report.tournament_id),
        "data": report.data,
        "markdown": report.markdown,
        "version": report.version,
        "generated_at": report.generated_at.isoformat(),
    }, "meta": None}


@router.post("/{tournament_id}/report/generate", status_code=202)
async def generate_tournament_report(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """レポート生成を要求（同期生成しない・Workerが非同期生成）。"""
    service = TournamentService(db, cache)
    await service.request_report_generation(tournament_id, current_user)
    return {"data": {"status": "queued"}, "meta": None}


@router.get("/{tournament_id}/registrations", response_model=Response[list[RegistrationInfo]])
async def list_registrations(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: OrganizerUser,
):
    """大会への参加申請一覧（主催者専用）"""
    service = TournamentService(db, cache)
    regs = await service.list_registrations(tournament_id, current_user)
    items = [
        RegistrationInfo(
            id=str(r.id),
            team_id=str(r.team_id),
            team_name=r.team.name if r.team else "Unknown",
            team_tag=r.team.tag if r.team else "???",
            team_logo_url=resign_stored_url(r.team.logo_url) if r.team else None,
            status=r.status.value,
            notes=r.notes,
            registered_at=r.registered_at,
        )
        for r in regs
    ]
    return Response(data=items, meta=None)


@router.patch("/{tournament_id}/registrations/{registration_id}", response_model=Response[RegistrationInfo])
async def update_registration(
    tournament_id: uuid.UUID,
    registration_id: uuid.UUID,
    status: RegistrationStatus = Query(..., description="approve/reject/pending"),
    db: DBSession = ...,
    cache: Cache = ...,
    current_user: OrganizerUser = ...,
):
    """参加申請を承認・却下"""
    service = TournamentService(db, cache)
    reg = await service.update_registration(tournament_id, registration_id, status, current_user)
    return Response(
        data=RegistrationInfo(
            id=str(reg.id),
            team_id=str(reg.team_id),
            team_name=reg.team.name if reg.team else "Unknown",
            team_tag=reg.team.tag if reg.team else "???",
            team_logo_url=resign_stored_url(reg.team.logo_url) if reg.team else None,
            status=reg.status.value,
            notes=reg.notes,
            registered_at=reg.registered_at,
        ),
        meta=None,
    )


@router.post("/{tournament_id}/register", response_model=Response[dict], status_code=201)
async def register_team(
    tournament_id: uuid.UUID, data: RegistrationRequest,
    db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """チームの参加申請。

    自動承認の大会では即時 approved、定員超過なら waitlisted になるため、
    確定したステータスを返してフロントで結果を出し分けられるようにする。
    """
    service = TournamentService(db, cache)
    status = await service.register_team(
        tournament_id, uuid.UUID(data.team_id), data.notes, current_user,
    )
    return Response(data={"status": status.value}, meta=None)


async def _user_registration(db, tournament_id: uuid.UUID, user):
    """ログインユーザーの所属チームの、この大会への登録を解決。

    「所属」はオーナーとメンバーの両方を含む。申請は大抵オーナーが出すため、
    選手登録（player）を持たないオーナーもチェックインできる必要がある。
    """
    from app.models.player import Player
    from app.models.team import Team, TeamMember

    team_ids: set[uuid.UUID] = set(
        (await db.execute(select(Team.id).where(Team.owner_id == user.id)))
        .scalars().all()
    )
    player = (await db.execute(
        select(Player).where(Player.user_id == user.id)
    )).scalar_one_or_none()
    if player:
        team_ids.update(
            (await db.execute(
                select(TeamMember.team_id).where(
                    TeamMember.player_id == player.id,
                    TeamMember.left_at.is_(None),
                )
            )).scalars().all()
        )
    if not team_ids:
        return None
    from app.models.tournament import TournamentRegistration
    return (
        await db.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.team_id.in_(team_ids),
            )
        )
    ).scalar_one_or_none()


@router.get("/{tournament_id}/my-registration")
async def my_registration(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """ログインユーザーのチームの申請状況（エントリー欄の表示用）。

    申請済みかどうかだけでなく審査中・当選・補欠まで返し、
    参加者が自分の当落を大会ページで確認できるようにする。
    """
    from app.models.team import Team

    tournament = await db.get(Tournament, tournament_id)
    if not tournament:
        raise NotFoundError("大会", str(tournament_id))
    reg = await _user_registration(db, tournament_id, current_user)
    if not reg:
        return {"data": {"registered": False}}
    team = await db.get(Team, reg.team_id)
    return {"data": {
        "registered": True,
        "status": reg.status.value,
        "team_id": str(reg.team_id),
        "team_name": team.name if team else None,
    }}


@router.get("/{tournament_id}/check-in/me")
async def my_check_in(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """自分のチームのチェックイン状態（フロントのボタン表示用）。"""
    tournament = await db.get(Tournament, tournament_id)
    if not tournament:
        raise NotFoundError("大会", str(tournament_id))
    # 時間判定はサーバー時刻で行い、クライアントの時計ズレに依存させない
    window = {
        "state": check_in_window_state(tournament),
        "start_at": tournament.check_in_start_at.isoformat()
        if tournament.check_in_start_at else None,
        "end_at": tournament.check_in_end_at.isoformat()
        if tournament.check_in_end_at else None,
    }
    reg = await _user_registration(db, tournament_id, current_user)
    if not reg:
        return {"data": {"registered": False, "checked_in": False, "window": window}}
    return {"data": {
        "registered": True,
        "approved": reg.status == RegistrationStatus.APPROVED,
        "checked_in": reg.checked_in_at is not None,
        "team_id": str(reg.team_id),
        "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
        "window": window,
    }}


@router.post("/{tournament_id}/check-in", status_code=200)
async def check_in(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    """Webからチェックイン（自分の所属チームの登録を出席にする）。"""
    tournament = await db.get(Tournament, tournament_id)
    if not tournament:
        raise NotFoundError("大会", str(tournament_id))
    state = check_in_window_state(tournament)
    if state == "before":
        raise BusinessRuleError("チェックイン受付はまだ始まっていません")
    if state == "after":
        raise BusinessRuleError("チェックイン受付は終了しました。主催者に連絡してください")
    reg = await _user_registration(db, tournament_id, current_user)
    if not reg:
        raise NotFoundError("登録", "この大会にあなたのチームは登録されていません")
    if reg.status != RegistrationStatus.APPROVED:
        raise BusinessRuleError("承認済みの登録のみチェックインできます")
    reg.checked_in_at = datetime.now(timezone.utc)
    reg.checked_in_via = "web"
    await db.flush()
    return {"data": {"checked_in": True, "team_id": str(reg.team_id),
                     "checked_in_at": reg.checked_in_at.isoformat()}}


@router.post("/{tournament_id}/bracket", response_model=Response[BracketResponse], status_code=201)
async def generate_bracket(
    tournament_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser,
):
    service = TournamentService(db, cache)
    bracket = await service.generate_bracket(tournament_id, current_user)
    return Response(data=bracket)


@router.get("/{tournament_id}/bracket", response_model=Response[BracketResponse])
async def get_bracket(tournament_id: uuid.UUID, db: DBSession, cache: Cache):
    service = TournamentService(db, cache)
    bracket = await service.get_bracket(tournament_id)
    return Response(data=bracket)
