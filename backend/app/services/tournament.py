import math
import uuid
from datetime import datetime, timezone
from itertools import combinations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.redis import CacheKeys, CacheTTL, RedisCache
from app.models.enums import (
    MatchStatus,
    RegistrationStatus,
    TournamentFormat,
    TournamentStatus,
    UserRole,
)
from app.models.match import Match
from app.models.tournament import Tournament
from app.models.user import User
from app.repositories.tournament import RankingRepository, TournamentRepository
from app.schemas.tournament import (
    BracketMatch,
    BracketMatchTeam,
    BracketResponse,
    TournamentCreate,
    TournamentUpdate,
)
from app.core.storage import resign_stored_url
from app.events import Ev, EventEnvelope, EventService


def _is_scalar(v) -> bool:
    return isinstance(v, (str, int, float, bool)) or v is None or hasattr(v, "value")


def _scalar(v):
    """イベント payload 用にスカラー化（Enum は .value、Decimal/日時は str）。"""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if hasattr(v, "value"):  # Enum
        return v.value
    return str(v)


class TournamentService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._repo = TournamentRepository(db)
        self._ranking_repo = RankingRepository(db)
        self._cache = cache
        self._db = db

    async def _emit(self, event_type: str, entity_id, *, before=None, after=None, metadata=None) -> None:
        """ドメインイベントを同一Txで記録（ADR-0008）。actor/trace はコンテキストが自動補完。"""
        await EventService(self._db).emit(EventEnvelope.build(
            type=event_type, entity_type="tournament", entity_id=entity_id,
            producer="tournament", before=before, after=after, metadata=metadata,
        ))

    async def create(self, data: TournamentCreate, organizer: User) -> Tournament:
        import re
        slug_base = re.sub(r"[^\w\s-]", "", data.name.lower()).strip()
        slug_base = re.sub(r"[\s_-]+", "-", slug_base) or "tournament"
        slug = slug_base
        counter = 1
        while True:
            existing = await self._db.execute(
                __import__("sqlalchemy").select(Tournament).where(Tournament.slug == slug)
            )
            if not existing.scalar_one_or_none():
                break
            slug = f"{slug_base}-{counter}"
            counter += 1

        tournament = await self._repo.create(
            **data.model_dump(exclude_none=True),
            slug=slug,
            organizer_id=organizer.id,
        )
        await self._emit(Ev.TOURNAMENT_CREATED, tournament.id, after={
            "name": tournament.name,
            "game": tournament.game.value if hasattr(tournament.game, "value") else str(tournament.game),
            "format": tournament.format.value if hasattr(tournament.format, "value") else str(tournament.format),
        })
        await self._cache.delete_pattern("cache:tournament:list:*")
        return tournament

    async def get_detail(self, tournament_id: uuid.UUID) -> Tournament:
        cache_key = CacheKeys.TOURNAMENT_DETAIL.replace("{id}", str(tournament_id))
        cached = await self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[return-value]

        tournament = await self._repo.get_with_details(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        return tournament

    async def update(
        self, tournament_id: uuid.UUID, data: TournamentUpdate, current_user: User
    ) -> Tournament:
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))

        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("この大会を編集する権限がありません")

        update_data = data.model_dump(exclude_none=True)
        # 変更対象フィールドのスカラー値のみ before に記録（差分・PII非対象 / ADR-0008）
        keys = [k for k in update_data if _is_scalar(getattr(tournament, k, None))]
        before = {k: _scalar(getattr(tournament, k, None)) for k in keys}
        tournament = await self._repo.update(tournament, **update_data)
        after = {k: _scalar(getattr(tournament, k, None)) for k in keys}
        await self._emit(Ev.TOURNAMENT_UPDATED, tournament.id, before=before, after=after,
                         metadata={"fields": list(update_data.keys())})

        await self._cache.delete(
            CacheKeys.TOURNAMENT_DETAIL.replace("{id}", str(tournament_id))
        )
        await self._cache.delete_pattern("cache:tournament:list:*")
        return tournament

    async def register_team(
        self, tournament_id: uuid.UUID, team_id: uuid.UUID, notes: str | None
    ) -> None:
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))

        if tournament.status != TournamentStatus.REGISTRATION_OPEN:
            raise BusinessRuleError("現在参加申請を受け付けていません")

        registered_count = await self._repo.get_registered_teams_count(tournament_id)
        if registered_count >= tournament.max_teams:
            raise BusinessRuleError("参加チームが上限に達しています")

        existing = await self._repo.get_registration(tournament_id, team_id)
        if existing:
            raise BusinessRuleError("既に参加申請済みです")

        await self._repo.create_registration(tournament_id, team_id, notes)

    async def generate_bracket(
        self, tournament_id: uuid.UUID, current_user: User
    ) -> BracketResponse:
        tournament = await self._repo.get_with_details(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))

        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("ブラケット生成の権限がありません")

        # 受付終了/チェックイン/開催中で生成可能。
        # 日程ベースの自動ステータス更新により受付終了→開催中へ即遷移し得るため、
        # 開催中も許可する（フロントの生成ボタン活性条件と一致させる）。
        if tournament.status not in (
            TournamentStatus.REGISTRATION_CLOSED,
            TournamentStatus.CHECK_IN,
            TournamentStatus.ONGOING,
        ):
            raise BusinessRuleError("参加受付終了後にブラケットを生成してください")

        # 冪等性: 既にブラケットが生成済みなら重複生成しない（二重クリック/再訪対策）。
        existing = await self._repo.get_brackets_with_matches(tournament_id)
        if existing:
            raise BusinessRuleError(
                "ブラケットは既に生成されています。再生成が必要な場合は既存のブラケットを削除してください"
            )

        registrations = await self._repo.get_approved_registrations(tournament_id)
        if len(registrations) < tournament.min_teams:
            raise BusinessRuleError(
                f"ブラケット生成には最低{tournament.min_teams}チームの参加承認が必要です"
            )

        if tournament.format == TournamentFormat.SINGLE_ELIMINATION:
            result = await self._generate_single_elimination(tournament, registrations)
        elif tournament.format == TournamentFormat.ROUND_ROBIN:
            result = await self._generate_round_robin(tournament, registrations)
        else:
            raise BusinessRuleError(f"{tournament.format} のブラケット自動生成は未対応です")

        await self._emit(Ev.TOURNAMENT_BRACKET_GENERATED, tournament.id, after={
            "format": _scalar(tournament.format),
            "teams": len(registrations),
        })
        return result

    async def _generate_single_elimination(
        self, tournament: Tournament, registrations: list
    ) -> BracketResponse:
        teams = [reg.team for reg in registrations]
        n = len(teams)
        rounds_count = math.ceil(math.log2(n))
        total_slots = 2**rounds_count

        # バイ（不戦勝）の処理: チーム数が2の累乗でない場合
        byes = total_slots - n
        padded_teams = teams + [None] * byes

        matches_by_round: dict[int, list] = {}
        created_matches: list[Match] = []

        # ラウンド1のブラケット作成
        bracket_r1 = await self._repo.create_brackets(
            tournament.id,
            [
                {
                    "round_number": 1,
                    "bracket_type": "winners",
                    "created_at": datetime.now(timezone.utc),
                }
            ],
        )

        match_number = 1
        round1_matches = []
        for i in range(0, len(padded_teams), 2):
            t1 = padded_teams[i]
            t2 = padded_teams[i + 1] if i + 1 < len(padded_teams) else None
            match = Match(
                tournament_id=tournament.id,
                bracket_id=bracket_r1[0].id,
                team1_id=t1.id if t1 else None,
                team2_id=t2.id if t2 else None,
                winner_id=t1.id if t2 is None and t1 else None,  # バイ
                format=tournament.rules.get("bo_format", "BO3") if tournament.rules else "BO3",
                status=MatchStatus.SCHEDULED if t2 else MatchStatus.COMPLETED,
                round_number=1,
                match_number=match_number,
            )
            self._db.add(match)
            round1_matches.append(match)
            match_number += 1

        await self._db.flush()
        matches_by_round[1] = round1_matches

        # 後続ラウンドのプレースホルダー作成
        prev_matches = round1_matches
        for r in range(2, rounds_count + 1):
            bracket = await self._repo.create_brackets(
                tournament.id,
                [
                    {
                        "round_number": r,
                        "bracket_type": "winners",
                        "created_at": datetime.now(timezone.utc),
                    }
                ],
            )
            round_matches = []
            for i in range(0, len(prev_matches), 2):
                match = Match(
                    tournament_id=tournament.id,
                    bracket_id=bracket[0].id,
                    format=tournament.rules.get("bo_format", "BO3") if tournament.rules else "BO3",
                    status=MatchStatus.SCHEDULED,
                    round_number=r,
                    match_number=i // 2 + 1,
                )
                self._db.add(match)
                round_matches.append(match)
            await self._db.flush()

            # 前ラウンドのnext_match_idを設定
            for j, m in enumerate(prev_matches):
                m.next_match_id = round_matches[j // 2].id
            await self._db.flush()

            matches_by_round[r] = round_matches
            prev_matches = round_matches

        # レスポンス構築
        rounds = {}
        for round_num, matches in matches_by_round.items():
            rounds[round_num] = [
                BracketMatch(
                    id=str(m.id),
                    round_number=m.round_number,
                    match_number=m.match_number,
                    team1=BracketMatchTeam(
                        id=str(m.team1_id) if m.team1_id else None,
                        name=None, tag=None, logo_url=None,
                    ) if m.team1_id else None,
                    team2=BracketMatchTeam(
                        id=str(m.team2_id) if m.team2_id else None,
                        name=None, tag=None, logo_url=None,
                    ) if m.team2_id else None,
                    winner_id=str(m.winner_id) if m.winner_id else None,
                    status=m.status.value,
                    scheduled_at=None,
                )
                for m in matches
            ]

        await self._cache.delete(
            CacheKeys.BRACKET.replace("{tournament_id}", str(tournament.id))
        )
        return BracketResponse(
            tournament_id=str(tournament.id),
            format=tournament.format,
            rounds=rounds,
        )

    async def _generate_round_robin(
        self, tournament: Tournament, registrations: list
    ) -> BracketResponse:
        teams = [reg.team for reg in registrations]
        bracket = await self._repo.create_brackets(
            tournament.id,
            [
                {
                    "round_number": 1,
                    "bracket_type": "winners",
                    "created_at": datetime.now(timezone.utc),
                }
            ],
        )

        matches_by_round: dict[int, list] = {1: []}
        match_number = 1
        for t1, t2 in combinations(teams, 2):
            match = Match(
                tournament_id=tournament.id,
                bracket_id=bracket[0].id,
                team1_id=t1.id,
                team2_id=t2.id,
                format=tournament.rules.get("bo_format", "BO1") if tournament.rules else "BO1",
                status=MatchStatus.SCHEDULED,
                round_number=1,
                match_number=match_number,
            )
            self._db.add(match)
            matches_by_round[1].append(match)
            match_number += 1

        await self._db.flush()
        return BracketResponse(
            tournament_id=str(tournament.id),
            format=tournament.format,
            rounds={
                1: [
                    BracketMatch(
                        id=str(m.id),
                        round_number=1,
                        match_number=m.match_number,
                        team1=None, team2=None,
                        winner_id=None,
                        status=m.status.value,
                        scheduled_at=None,
                    )
                    for m in matches_by_round[1]
                ]
            },
        )

    async def get_my_tournaments(self, organizer_id: uuid.UUID) -> list[Tournament]:
        return await self._repo.list_by_organizer(organizer_id)

    async def delete(self, tournament_id: uuid.UUID, current_user: User) -> None:
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("この大会を削除する権限がありません")
        if tournament.status == TournamentStatus.ONGOING:
            raise BusinessRuleError("開催中の大会は削除できません")
        await self._repo.delete(tournament)
        await self._cache.delete_pattern("cache:tournament:*")

    async def change_status(
        self, tournament_id: uuid.UUID, new_status: TournamentStatus, current_user: User
    ) -> Tournament:
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("ステータス変更の権限がありません")

        # 主催者は任意のステータスへ手動変更できる。
        # 手動変更後は status_locked=True にし、日程による自動更新の対象外とする。
        old_status = tournament.status
        tournament = await self._repo.update(
            tournament, status=new_status, status_locked=True
        )

        # 遷移先に応じて1イベントを発火（ADR-0008: 1操作=1イベント）
        if new_status == TournamentStatus.COMPLETED:
            event_type = Ev.TOURNAMENT_COMPLETED            # public + dispatch（P1-3でReport）
        elif old_status == TournamentStatus.DRAFT and new_status == TournamentStatus.REGISTRATION_OPEN:
            event_type = Ev.TOURNAMENT_PUBLISHED
        else:
            event_type = Ev.TOURNAMENT_STATUS_CHANGED
        await self._emit(event_type, tournament.id,
                         before={"status": old_status.value}, after={"status": new_status.value})

        await self._cache.delete(CacheKeys.TOURNAMENT_DETAIL.replace("{id}", str(tournament_id)))
        return tournament

    async def get_audit(self, tournament_id: uuid.UUID, current_user: User, *, limit: int = 50, offset: int = 0) -> list[dict]:
        """大会監査ログ（organizer/Admin のみ / ADR-0012）。"""
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("監査ログを閲覧する権限がありません")
        from app.services.audit_service import AuditService
        return await AuditService(self._db).list(
            entity_type="tournament", entity_id=tournament_id, limit=limit, offset=offset,
        )

    async def get_rules(self, tournament_id: uuid.UUID) -> dict:
        """ルール（Section構造）を取得。未設定なら全固定Sectionの空雛形を返す。"""
        from app.schemas.rules import empty_doc
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        return tournament.rules_doc or empty_doc()

    async def update_rules(self, tournament_id: uuid.UUID, doc: dict, current_user: User) -> dict:
        """ルールを差し替え（organizer/Admin のみ）。固定id以外のSectionは無視。"""
        from app.schemas.rules import SECTION_IDS
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("ルールを編集する権限がありません")
        sections = [s for s in (doc.get("sections") or []) if s.get("id") in SECTION_IDS]
        clean = {"sections": sections}
        await self._repo.update(tournament, rules_doc=clean)
        await self._cache.delete(CacheKeys.TOURNAMENT_DETAIL.replace("{id}", str(tournament_id)))
        return clean

    async def apply_rules_template(self, tournament_id: uuid.UUID, template_id: str, current_user: User) -> dict:
        """テンプレート（VALORANT標準等）を適用（organizer/Admin のみ）。"""
        from app.schemas.rules import get_template_doc
        doc = get_template_doc(template_id)
        if doc is None:
            raise NotFoundError("テンプレート", template_id)
        return await self.update_rules(tournament_id, doc, current_user)

    async def get_report(self, tournament_id: uuid.UUID):
        """生成済み大会レポートを取得（無ければ None）。"""
        from app.repositories.tournament_report import TournamentReportRepository
        return await TournamentReportRepository(self._db).get_by_tournament(tournament_id)

    async def request_report_generation(self, tournament_id: uuid.UUID, current_user: User) -> None:
        """レポート生成を要求（同期生成せず tournament.completed を emit / ADR-0009）。"""
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("レポート生成の権限がありません")
        if tournament.status != TournamentStatus.COMPLETED:
            raise BusinessRuleError("完了した大会のみレポートを生成できます")
        # 同期生成せず、同じイベントで非同期生成（Worker の ReportConsumer が拾う）
        await self._emit(Ev.TOURNAMENT_COMPLETED, tournament.id,
                         after={"status": tournament.status.value}, metadata={"regenerate": True})

    async def list_registrations(self, tournament_id: uuid.UUID, current_user: User) -> list:
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("登録一覧を閲覧する権限がありません")
        return await self._repo.get_all_registrations(tournament_id)

    async def update_registration(
        self,
        tournament_id: uuid.UUID,
        registration_id: uuid.UUID,
        status: RegistrationStatus,
        current_user: User,
    ):
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))
        if current_user.role != UserRole.ADMIN and tournament.organizer_id != current_user.id:
            raise ForbiddenError("この操作を行う権限がありません")
        reg = await self._repo.get_registration_by_id(registration_id)
        if not reg or reg.tournament_id != tournament_id:
            raise NotFoundError("登録", str(registration_id))
        reg = await self._repo.update_registration_status(reg, status)

        # 承認/却下のみイベント化（dispatch=True → P1-2 で通知 consumer）
        if status == RegistrationStatus.APPROVED:
            await self._emit(Ev.TOURNAMENT_REGISTRATION_APPROVED, tournament_id,
                             after={"registration_id": str(registration_id), "team_id": str(reg.team_id)})
        elif status == RegistrationStatus.REJECTED:
            await self._emit(Ev.TOURNAMENT_REGISTRATION_REJECTED, tournament_id,
                             after={"registration_id": str(registration_id), "team_id": str(reg.team_id)})
        return reg

    async def get_bracket(self, tournament_id: uuid.UUID) -> BracketResponse:
        cache_key = CacheKeys.BRACKET.replace("{tournament_id}", str(tournament_id))
        # ブラケットはリアルタイム性が高いためキャッシュTTLは短め
        tournament = await self._repo.get_by_id(tournament_id)
        if not tournament:
            raise NotFoundError("大会", str(tournament_id))

        brackets = await self._repo.get_brackets_with_matches(tournament_id)
        rounds: dict[int, list[BracketMatch]] = {}
        for bracket in brackets:
            r = bracket.round_number
            if r not in rounds:
                rounds[r] = []
            for match in bracket.matches:
                rounds[r].append(
                    BracketMatch(
                        id=str(match.id),
                        round_number=match.round_number,
                        match_number=match.match_number,
                        team1=BracketMatchTeam(
                            id=str(match.team1.id),
                            name=match.team1.name,
                            tag=match.team1.tag,
                            logo_url=resign_stored_url(match.team1.logo_url),
                        ) if match.team1 else None,
                        team2=BracketMatchTeam(
                            id=str(match.team2.id),
                            name=match.team2.name,
                            tag=match.team2.tag,
                            logo_url=resign_stored_url(match.team2.logo_url),
                        ) if match.team2 else None,
                        winner_id=str(match.winner_id) if match.winner_id else None,
                        status=match.status.value,
                        scheduled_at=match.scheduled_at,
                    )
                )

        return BracketResponse(
            tournament_id=str(tournament_id),
            format=tournament.format,
            rounds=rounds,
        )
