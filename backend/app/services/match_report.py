"""対戦チームによる試合結果の報告と、相手チームによる確認（Web と Discord Bot で共通）。

結果の確定は既存の MatchService.register_result に任せる。主催者・管理者は
従来どおり報告を待たずに確定でき、その場合は保留中の報告を superseded にする。
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.redis import RedisCache
from app.models.bot_ops import MatchDispute
from app.models.enums import MatchStatus, MemberRole, TournamentStatus, UserRole
from app.models.match import Match
from app.models.match_report import MatchResultReport
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.match import MatchResultCreate
from app.services.match import MatchService, lock_match

OPEN = ("pending", "disputed")


from app.services.membership import formal_clause


class MatchReportService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def _load(
        self, match_id: uuid.UUID, *, for_update: bool = True,
    ) -> tuple[Match, Tournament | None, MatchResultReport | None]:
        # 報告・確認・異議は試合の行をロックし、主催者の確定や再開と1件ずつ処理する
        match = await lock_match(self._db, match_id) if for_update else await self._db.get(Match, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        tournament = await self._db.get(Tournament, match.tournament_id)
        report = (await self._db.execute(
            select(MatchResultReport).where(MatchResultReport.match_id == match_id)
        )).scalar_one_or_none()
        return match, tournament, report

    @staticmethod
    def _is_manager(tournament: Tournament | None, user: User) -> bool:
        return user.role == UserRole.ADMIN or (tournament is not None and tournament.organizer_id == user.id)

    async def _team_of(self, match: Match, user: User) -> uuid.UUID | None:
        """利用者が代表として報告できる対戦チーム（オーナーかキャプテン）。"""
        teams = [t for t in (match.team1_id, match.team2_id) if t]
        owned = (await self._db.execute(
            select(Team.id).where(Team.id.in_(teams), Team.owner_id == user.id)
        )).scalars().first()
        if owned:
            return owned
        return (await self._db.execute(
            select(TeamMember.team_id)
            .join(Player, Player.id == TeamMember.player_id)
            .where(TeamMember.team_id.in_(teams), Player.user_id == user.id,
                   TeamMember.role == MemberRole.CAPTAIN, TeamMember.left_at.is_(None),
                   await formal_clause(self._db))
        )).scalars().first()

    async def _is_member(self, match: Match, user: User) -> bool:
        """対戦チームのどちらかに在籍しているか（役割は問わない）。"""
        teams = [t for t in (match.team1_id, match.team2_id) if t]
        return bool(teams) and bool(await self._db.scalar(
            select(TeamMember.team_id)
            .join(Player, Player.id == TeamMember.player_id)
            .where(TeamMember.team_id.in_(teams), Player.user_id == user.id, TeamMember.left_at.is_(None))
            .limit(1)
        ))

    async def state(self, match_id: uuid.UUID, user: User) -> dict[str, Any]:
        match, tournament, report = await self._load(match_id, for_update=False)
        team = await self._team_of(match, user)
        manager = self._is_manager(tournament, user)
        open_report = report if report and report.status in OPEN else None
        reportable = match.status in (MatchStatus.SCHEDULED, MatchStatus.ONGOING) and bool(
            match.team1_id and match.team2_id)
        is_opponent = bool(team and open_report and open_report.reported_by_team_id != team)
        # 異議中はチームからは報告し直せない（主催者は結果の登録で裁定できる）
        disputed = report is not None and report.status == "disputed"
        # 異議の理由は当事者（両チームのオーナー・メンバー）と主催者・管理者にだけ返す
        reason = report.dispute_reason if report is not None else None
        if reason and not (manager or team is not None or await self._is_member(match, user)):
            reason = None
        return {
            "report": None if report is None else {
                "status": report.status,
                "winner_id": str(report.winner_id),
                "reported_by_team_id": str(report.reported_by_team_id),
                "dispute_reason": reason,
            },
            "my_team_id": str(team) if team else None,
            "can_report": reportable and (manager or (team is not None and not disputed)),
            "can_confirm": reportable and open_report is not None
            and open_report.status == "pending" and (is_opponent or manager),
            "can_dispute": reportable and open_report is not None
            and open_report.status == "pending" and is_opponent,
        }

    async def _finalize(self, match: Match, winner_id: uuid.UUID, user: User) -> None:
        # 権限はここまでで確認済み（報告者と相手チーム、または主催者）
        service = MatchService(self._db, self._cache)
        if match.status == MatchStatus.SCHEDULED:
            # 開始は出場登録と名簿を固定する。チームの確定で始めるのは、大会が開催中（名簿は固定済み）の
            # ときだけ。それより前は主催者が開始する（チームが大会全体の名簿を固定できないように）
            tournament = await self._db.get(Tournament, match.tournament_id)
            if not self._is_manager(tournament, user) and tournament.status != TournamentStatus.ONGOING:
                raise BusinessRuleError("大会が開催中になってから結果を確定できます（それより前は主催者が試合を開始します）")
            await service.start_match(match.id, user, authorized=True)
        await service.register_result(
            match.id, MatchResultCreate(winner_id=winner_id), user, authorized=True,
        )

    async def report(self, match_id: uuid.UUID, winner_id: uuid.UUID, user: User) -> str:
        match, tournament, report = await self._load(match_id)
        if match.status not in (MatchStatus.SCHEDULED, MatchStatus.ONGOING):
            raise BusinessRuleError("この試合の結果は報告できる状態ではありません")
        if not (match.team1_id and match.team2_id):
            raise BusinessRuleError("対戦チームが確定していません")
        if winner_id not in (match.team1_id, match.team2_id):
            raise BusinessRuleError("勝者はこの試合の参加チームである必要があります")

        if self._is_manager(tournament, user):
            await self._finalize(match, winner_id, user)
            return "confirmed"

        team = await self._team_of(match, user)
        if team is None:
            raise ForbiddenError("結果を報告できるのは対戦チームのオーナー・キャプテンか主催者だけです")

        if report and report.status == "pending" and report.reported_by_team_id != team:
            if report.winner_id == winner_id:  # 双方の報告が一致したら確定
                report.status = "confirmed"
                report.resolved_by_user_id = user.id
                await self._finalize(match, winner_id, user)
                return "confirmed"
            report.status = "disputed"
            report.dispute_reason = "両チームの報告が食い違っています"
            self._db.add(MatchDispute(match_id=match.id, raised_by=user.id,
                                      reason=report.dispute_reason, status="open"))
            await self._db.flush()
            return "disputed"

        if report is None:
            report = MatchResultReport(match_id=match.id)
            self._db.add(report)
        elif report.status == "disputed":
            raise BusinessRuleError("異議が出ているため、主催者の裁定を待ってください")
        report.winner_id = winner_id
        report.reported_by_team_id = team
        report.reported_by_user_id = user.id
        report.status = "pending"
        report.dispute_reason = None
        report.resolved_by_user_id = None
        await self._db.flush()
        return "pending"

    async def _pending_for_response(
        self, match_id: uuid.UUID, user: User,
    ) -> tuple[Match, MatchResultReport, bool]:
        match, tournament, report = await self._load(match_id)
        if report is None or report.status != "pending":
            raise BusinessRuleError("確認待ちの報告がありません")
        if match.status not in (MatchStatus.SCHEDULED, MatchStatus.ONGOING):
            raise BusinessRuleError("この試合の結果は既に確定しています")
        manager = self._is_manager(tournament, user)
        team = await self._team_of(match, user)
        if not manager and (team is None or team == report.reported_by_team_id):
            raise ForbiddenError("確認できるのは相手チームのオーナー・キャプテンか主催者だけです")
        return match, report, manager

    async def confirm(self, match_id: uuid.UUID, user: User) -> str:
        match, report, _ = await self._pending_for_response(match_id, user)
        report.status = "confirmed"
        report.resolved_by_user_id = user.id
        await self._finalize(match, report.winner_id, user)
        return "confirmed"

    async def dispute(self, match_id: uuid.UUID, reason: str, user: User) -> str:
        match, report, manager = await self._pending_for_response(match_id, user)
        if manager:
            raise BusinessRuleError("主催者は異議ではなく結果の登録で裁定してください")
        report.status = "disputed"
        report.dispute_reason = reason
        self._db.add(MatchDispute(match_id=match.id, raised_by=user.id, reason=reason, status="open"))
        await self._db.flush()
        return "disputed"
