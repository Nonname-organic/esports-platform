import json
import uuid
from datetime import datetime, timezone

import boto3
from sqlalchemy import ColumnElement, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.redis import CacheKeys, RedisCache
from app.models.enums import MatchStatus, UserRole
from app.models.match import Map, Match, MatchGame
from app.models.team import TeamMember
from app.models.tournament import Tournament
from app.models.user import User
from app.repositories.match import MatchRepository
from app.repositories.tournament import TournamentRepository
from app.schemas.match import (
    BanPickCreate,
    GamePlayerStatsUpdate,
    MatchDetail,
    MatchResultCreate,
    PlayerStatsCreate,
    ScoreUpdate,
)
from app.core.storage import resign_stored_url


async def ensure_can_manage_match(db: AsyncSession, match: Match, user: User) -> None:
    """試合を操作できるのは、その大会の主催者か管理者だけ。

    organizer ロールは誰でも自分で付けられるため、ロールだけで通すと
    他人の大会の試合を開始・採点・確定できてしまう。
    """
    if user.role == UserRole.ADMIN:
        return
    tournament = await db.get(Tournament, match.tournament_id)
    if tournament is None or tournament.organizer_id != user.id:
        raise ForbiddenError("この大会の試合を操作する権限がありません")


async def lock_match(db: AsyncSession, match_id: uuid.UUID) -> Match | None:
    """試合の行をコミットまでロックし、最新の状態で読み直す。

    開始・スコア・成績・結果の確定・再開・チームの報告を、同じ試合について1件ずつ
    処理する。並行した操作で状態の更新が消えたり、成績が二重に入ったりしないように
    する（ロックを待った後は、相手が確定した状態を読んでから判定する）。
    """
    return (await db.execute(
        select(Match).where(Match.id == match_id).with_for_update()
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()


class MatchService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._repo = MatchRepository(db)
        self._tournament_repo = TournamentRepository(db)
        self._cache = cache
        self._db = db

    async def _resolve_map_id(self, value: str | None) -> uuid.UUID | None:
        """画面から来た map_id を maps.id へ解決する。

        マップ選択欄は "ascent" のような内部名を値に持つため、UUID 前提で
        変換すると選んだだけで 500 になる。内部名とUUIDのどちらも受ける。
        """
        if not value:
            return None
        try:
            return uuid.UUID(str(value))
        except ValueError:
            pass

        found = (
            await self._db.execute(
                select(Map.id).where(Map.internal_name == str(value))
            )
        ).scalar_one_or_none()
        if found is None:
            raise ValidationError(f"マップ「{value}」が見つかりません")
        return found

    async def get_detail(self, match_id: uuid.UUID) -> MatchDetail:
        cache_key = CacheKeys.MATCH_DETAIL.replace("{id}", str(match_id))
        cached = await self._cache.get(cache_key)
        if cached:
            return MatchDetail(**cached)

        match = await self._repo.get_full_detail(match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

        detail = self._to_detail(match)
        await self._cache.set(cache_key, detail.model_dump(), ttl=60)
        return detail

    async def require_organizer_authority(
        self, match_id: uuid.UUID, current_user: User
    ) -> None:
        """この試合を運営として操作できるか確かめる（ADMIN か、その大会の主催者）。

        REST の試合操作 route は matches.py の Dependency からこれを通し、拒否した
        リクエストをサービス層・OCR・結果登録のロックに届かせない。判定は
        ensure_can_manage_match に一本化してある。各 mutation メソッドも同じ判定を
        自分で行うので、Bot など REST 以外の呼び出し元も守られる。呼び出し側で権限を
        確かめ済みの経路（Bot・Web の結果報告の確定）だけが authorized=True で省略する。
        """
        match = await self._db.get(Match, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        await ensure_can_manage_match(self._db, match, current_user)

    async def start_match(
        self, match_id: uuid.UUID, current_user: User, *, authorized: bool = False,
    ) -> None:
        """authorized=True は、呼び出し側で権限を確認済みの経路（Bot の結果確定）専用。"""
        match = await lock_match(self._db, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        if not authorized:
            await ensure_can_manage_match(self._db, match, current_user)

        if match.status != MatchStatus.SCHEDULED:
            raise BusinessRuleError("スケジュール済みの試合のみ開始できます")

        if not match.team1_id or not match.team2_id:
            raise BusinessRuleError("対戦チームが確定していません")

        match.status = MatchStatus.ONGOING
        match.started_at = datetime.now(timezone.utc)
        await self._db.flush()
        await self._invalidate_match_cache(match_id)

        # 自動進行: Discord試合チャンネルを生成（Discord未設定なら何もしない）
        from app.services.discord_service import DiscordService
        await DiscordService(self._db, self._cache).notify_match_start(
            match.id, match.tournament_id, match.match_number
        )

    async def update_game_score(
        self,
        match_id: uuid.UUID,
        game_number: int,
        data: ScoreUpdate,
        current_user: User,
    ) -> None:
        match = await lock_match(self._db, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        await ensure_can_manage_match(self._db, match, current_user)

        if match.status != MatchStatus.ONGOING:
            raise BusinessRuleError("進行中の試合のスコアのみ更新できます")

        winner_id = None
        if data.team1_score != data.team2_score:
            if data.team1_score > data.team2_score:
                winner_id = match.team1_id
            else:
                winner_id = match.team2_id

        await self._repo.upsert_game_score(
            match_id=match_id,
            game_number=game_number,
            map_id=None,
            team1_score=data.team1_score,
            team2_score=data.team2_score,
            winner_id=winner_id,
            side_first_team1=data.side_first_team1,
            duration_seconds=data.duration_seconds,
        )

        # WebSocket でリアルタイム配信
        await self._cache.publish(
            CacheKeys.WS_MATCH_CHANNEL.replace("{match_id}", str(match_id)),
            {
                "type": "score_update",
                "match_id": str(match_id),
                "game_number": game_number,
                "team1_score": data.team1_score,
                "team2_score": data.team2_score,
            },
        )
        await self._invalidate_match_cache(match_id)

    async def save_game_player_stats(
        self,
        match_id: uuid.UUID,
        game_number: int,
        data: GamePlayerStatsUpdate,
        current_user: User,
    ) -> None:
        """
        1マップ分のスコアと選手成績を保存する（スコアボード取り込みの保存先）。

        試合を完了させずマップ単位で確定できるようにしてある。撮り直しや修正に
        備えて、同一ゲームの選手成績は追記ではなく毎回置き換える。
        """
        match = await lock_match(self._db, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        await ensure_can_manage_match(self._db, match, current_user)

        if match.status not in (MatchStatus.ONGOING, MatchStatus.COMPLETED):
            raise BusinessRuleError("進行中または完了した試合にのみ成績を登録できます")
        await self._check_player_stats(match, data.player_stats)

        winner_id = None
        if data.team1_score != data.team2_score:
            winner_id = (
                match.team1_id
                if data.team1_score > data.team2_score
                else match.team2_id
            )

        game = await self._repo.upsert_game_score(
            match_id=match_id,
            game_number=game_number,
            map_id=await self._resolve_map_id(data.map_id),
            team1_score=data.team1_score,
            team2_score=data.team2_score,
            winner_id=winner_id,
            duration_seconds=data.duration_seconds,
        )

        await self._repo.replace_player_stats(
            game.id,
            [
                {
                    "match_game_id": game.id,
                    "player_id": ps.player_id,
                    "team_id": ps.team_id,
                    "agent": ps.agent,
                    "kills": ps.kills,
                    "deaths": ps.deaths,
                    "assists": ps.assists,
                    "score": ps.score,
                    "first_bloods": ps.first_bloods,
                    "custom_stats": ps.custom_stats,
                }
                for ps in data.player_stats
            ],
        )

        await self._invalidate_match_cache(match_id)

    async def _check_player_stats(
        self, match: Match, stats: list[PlayerStatsCreate] | None
    ) -> None:
        """成績は、この試合に出る2チームの所属選手のぶんだけ受け付ける（S8）。

        主催者や管理者でも、出場していない選手の ID を入れると、その選手の公開の
        通算成績を書き換えられてしまう。所属は「試合の開始時点でまだ抜けていない」
        所属行で見る（あとでチームを抜けた選手の成績も直せるように）。同じ選手を
        1マップに2回入れると二重に数えるので断る。
        """
        if not stats:
            return
        teams = {match.team1_id, match.team2_id} - {None}
        players = [ps.player_id for ps in stats]
        if any(ps.team_id not in teams for ps in stats):
            raise BusinessRuleError("成績を登録できるのは、この試合に出場するチームの選手だけです")
        if len(set(players)) != len(players):
            raise BusinessRuleError("同じ選手の成績が重複しています")

        still_member: ColumnElement[bool] = TeamMember.left_at.is_(None)
        if match.started_at is not None:  # 開始時刻が無い試合は、今の所属だけを見る
            still_member = or_(still_member, TeamMember.left_at >= match.started_at)
        members = {
            (r.team_id, r.player_id)
            for r in (await self._db.execute(
                select(TeamMember.team_id, TeamMember.player_id).where(
                    TeamMember.team_id.in_(teams),
                    TeamMember.player_id.in_(players),
                    still_member,
                )
            )).all()
        }
        if any((ps.team_id, ps.player_id) not in members for ps in stats):
            raise BusinessRuleError("チームに所属していない選手の成績は登録できません")

    async def _require_ban_pick_authority(
        self, match, team_id: uuid.UUID, current_user: User
    ) -> None:
        """Ban/Pick を登録できる相手を絞る。

        運営（ADMIN と大会の主催者）は、その試合に出る両チームぶんを入れられる。
        チーム側は自分のチームぶんだけで、オーナーか現役キャプテンに限る。
        一般メンバー・控え・コーチ・アナリストは入れられない。
        スタッフ権限は Ban/Pick の対象に入れていない。
        """
        from app.core.exceptions import ForbiddenError
        from app.models.enums import MemberRole, UserRole
        from app.models.player import Player
        from app.models.team import Team, TeamMember
        from app.models.tournament import Tournament

        if current_user.role == UserRole.ADMIN:
            return

        tournament = await self._db.get(Tournament, match.tournament_id)
        if tournament is not None and tournament.organizer_id == current_user.id:
            return

        team = await self._db.get(Team, team_id)
        if team is not None and team.owner_id == current_user.id:
            return

        # 現役キャプテンかどうかは「有効な所属行があるか」で見る。role を取り出す形に
        # すると、同じチームに所属行が複数あったときに例外になる。
        is_captain = (
            await self._db.execute(
                select(TeamMember.id)
                .join(Player, Player.id == TeamMember.player_id)
                .where(
                    TeamMember.team_id == team_id,
                    Player.user_id == current_user.id,
                    TeamMember.left_at.is_(None),
                    TeamMember.role == MemberRole.CAPTAIN,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if is_captain is not None:
            return

        raise ForbiddenError(
            "Ban/Pickを登録できるのは大会の運営か、"
            "出場チームのオーナー・キャプテンだけです"
        )

    async def register_ban_pick(
        self, match_id: uuid.UUID, data: BanPickCreate, current_user: User
    ) -> None:
        match = await self._repo.get_by_id(match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

        if match.status not in (MatchStatus.SCHEDULED, MatchStatus.ONGOING):
            raise BusinessRuleError("Ban/Pickを登録できる状態ではありません")

        # 出場チームかどうかは権限の話より前に見る。無関係なチームのIDは
        # 「権限が無い」ではなく「この試合の話ではない」ので、勝者チェック
        # （register_result）と同じ扱いにする。
        if data.team_id not in (match.team1_id, match.team2_id):
            raise BusinessRuleError(
                "Ban/Pickを登録できるのはこの試合に出場するチームだけです"
            )

        await self._require_ban_pick_authority(match, data.team_id, current_user)

        await self._repo.create_ban_pick(
            match_id=match_id,
            team_id=data.team_id,
            action=data.action,
            map_id=await self._resolve_map_id(data.map_id),
            order=data.order,
        )

    async def register_result(
        self,
        match_id: uuid.UUID,
        data: MatchResultCreate,
        current_user: User,
        *,
        authorized: bool = False,
    ) -> None:
        """authorized=True は、呼び出し側で権限を確認済みの経路（Bot の結果確定）専用。"""
        # 分散ロック（重複登録防止）
        lock_key = CacheKeys.LOCK_MATCH_RESULT.replace("{match_id}", str(match_id))
        if not await self._cache.acquire_lock(lock_key, ttl=10):
            raise ConflictError("結果を処理中です。しばらく待ってから再試行してください")

        try:
            await lock_match(self._db, match_id)
            match = await self._repo.get_full_detail(match_id)
            if not match:
                raise NotFoundError("試合", str(match_id))
            if not authorized:
                await ensure_can_manage_match(self._db, match, current_user)

            if match.status == MatchStatus.COMPLETED:
                raise BusinessRuleError("この試合の結果は既に登録されています")

            if match.status != MatchStatus.ONGOING:
                raise BusinessRuleError("進行中の試合の結果のみ登録できます")

            winner_id = data.winner_id
            if winner_id not in (match.team1_id, match.team2_id):
                raise BusinessRuleError("勝者はこの試合の参加チームである必要があります")

            loser_id = (
                match.team1_id if winner_id == match.team2_id else match.team2_id
            )

            # ゲーム別統計の保存
            if data.game_stats:
                for game_stat in data.game_stats:
                    if game_stat.winner_id not in (match.team1_id, match.team2_id):
                        raise BusinessRuleError(
                            "ゲームの勝者はこの試合の参加チームである必要があります"
                        )
                    await self._check_player_stats(match, game_stat.player_stats)
                for game_stat in data.game_stats:
                    game = await self._repo.upsert_game_score(
                        match_id=match_id,
                        game_number=game_stat.game_number,
                        map_id=await self._resolve_map_id(game_stat.map_id),
                        team1_score=game_stat.team1_score,
                        team2_score=game_stat.team2_score,
                        winner_id=game_stat.winner_id,
                        side_first_team1=game_stat.side_first_team1,
                        duration_seconds=game_stat.duration_seconds,
                        ended_at=datetime.now(timezone.utc),
                    )
                    if game_stat.player_stats:
                        # 再開後の登録し直しや、マップごとに保存済みの成績と重ならないよう置き換える
                        await self._repo.replace_player_stats(game.id, [
                            {
                                "match_game_id": game.id,
                                "player_id": ps.player_id,
                                "team_id": ps.team_id,
                                "agent": ps.agent,
                                "kills": ps.kills,
                                "deaths": ps.deaths,
                                "assists": ps.assists,
                                "score": ps.score,
                                "first_bloods": ps.first_bloods,
                                "custom_stats": ps.custom_stats,
                            }
                            for ps in game_stat.player_stats
                        ])

            # マップ取得数はこのリクエストで保存したゲームも含めて数える。
            # 先に読み込んだ match.games は保存前の状態なので使わない。
            games = (
                await self._db.execute(select(MatchGame).where(MatchGame.match_id == match_id))
            ).scalars().all()
            winner_game_wins = sum(1 for g in games if g.winner_id == winner_id)
            loser_game_wins = sum(1 for g in games if g.winner_id == loser_id)

            # 試合結果の保存
            await self._repo.create_result(
                match_id=match_id,
                winner_id=winner_id,
                loser_id=loser_id,
                winner_score=winner_game_wins,
                loser_score=loser_game_wins,
                was_forfeit=data.was_forfeit,
                confirmed_by=current_user.id,
            )

            match.status = MatchStatus.COMPLETED
            match.winner_id = winner_id
            match.ended_at = datetime.now(timezone.utc)
            # 確認待ち・異議中のチーム報告は、主催者の確定で決着したものとして閉じる
            from app.models.match_report import MatchResultReport
            await self._db.execute(
                update(MatchResultReport)
                .where(MatchResultReport.match_id == match_id,
                       MatchResultReport.status.in_(("pending", "disputed")))
                .values(status="superseded", resolved_by_user_id=current_user.id)
            )
            await self._db.flush()

            # 次の試合にチームを自動セット
            await self._advance_bracket(match, winner_id, loser_id)

            # 自動進行: Discord試合チャンネルをArchiveへ
            from app.services.discord_service import DiscordService
            await DiscordService(self._db, self._cache).notify_match_end(match_id, match.tournament_id)

            # SQSへイベント送信（ランキング更新・通知）
            await self._publish_result_event(match_id, winner_id, loser_id, match.tournament_id)

            # WebSocket配信
            await self._cache.publish(
                CacheKeys.WS_MATCH_CHANNEL.replace("{match_id}", str(match_id)),
                {
                    "type": "match_complete",
                    "match_id": str(match_id),
                    "winner_id": str(winner_id),
                    "winner_score": winner_game_wins,
                    "loser_score": loser_game_wins,
                },
            )
            await self._cache.publish(
                CacheKeys.WS_BRACKET_CHANNEL.replace(
                    "{tournament_id}", str(match.tournament_id)
                ),
                {
                    "type": "bracket_update",
                    "tournament_id": str(match.tournament_id),
                    "updated_match_id": str(match_id),
                },
            )

            await self._invalidate_match_cache(match_id)
            await self._cache.delete(
                CacheKeys.BRACKET.replace("{tournament_id}", str(match.tournament_id))
            )

        finally:
            await self._cache.release_lock(lock_key)

    async def reopen_match(self, match_id: uuid.UUID, current_user: User) -> None:
        """確定済みの試合を進行中へ戻す（結果の入力ミスの訂正用・主催者と管理者のみ）。

        勝者・敗者を送り込んだ次の試合がまだ始まっていない場合に限り、送り込んだ
        チームを取り除いてから戻す。始まっていれば、その試合から先に直す必要がある。
        """
        from app.models.match import MatchResult
        from app.models.match_report import MatchResultReport

        match = await lock_match(self._db, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        await ensure_can_manage_match(self._db, match, current_user)
        if match.status not in (MatchStatus.COMPLETED, MatchStatus.FORFEIT):
            raise BusinessRuleError("結果が確定した試合だけを再開できます")

        winner_id = match.winner_id
        loser_id = match.team1_id if winner_id == match.team2_id else match.team2_id
        moves = [(match.next_match_id, winner_id), (match.loser_next_match_id, loser_id)]
        targets = []
        for next_id, team_id in moves:
            if not next_id or not team_id:
                continue
            nxt = await lock_match(self._db, next_id)
            if nxt is None:
                continue
            if nxt.status != MatchStatus.SCHEDULED:
                raise BusinessRuleError("次の試合が既に始まっているため再開できません")
            targets.append((nxt, team_id))
        for nxt, team_id in targets:
            if nxt.team1_id == team_id:
                nxt.team1_id = None
            elif nxt.team2_id == team_id:
                nxt.team2_id = None

        await self._db.execute(delete(MatchResult).where(MatchResult.match_id == match_id))
        # チームの報告・確認・異議は、再開した試合と、チームを外した次の試合から消して最初からにする。
        # 残すと、相手が入れ替わった後の古い報告を、片方のチームの確認だけで確定できてしまう
        await self._db.execute(delete(MatchResultReport).where(
            MatchResultReport.match_id.in_([match_id, *(nxt.id for nxt, _ in targets)])
        ))
        match.status = MatchStatus.ONGOING
        match.winner_id = None
        match.ended_at = None
        await self._db.flush()

        await self._invalidate_match_cache(match_id)
        await self._cache.delete(CacheKeys.BRACKET.replace("{tournament_id}", str(match.tournament_id)))
        await self._cache.publish(
            CacheKeys.WS_BRACKET_CHANNEL.replace("{tournament_id}", str(match.tournament_id)),
            {"type": "bracket_update", "tournament_id": str(match.tournament_id),
             "updated_match_id": str(match_id)},
        )

    async def _advance_bracket(
        self, match, winner_id: uuid.UUID, loser_id: uuid.UUID | None = None
    ) -> None:
        """勝者を次の試合へ、敗者を敗者側ブラケットへ送る。

        loser_next_match_id はダブルエリミネーションの Winners 側にのみ
        設定される。シングルエリミでは None なので敗者はそのまま敗退。
        """
        if match.next_match_id:
            next_match = await self._repo.get_by_id(match.next_match_id)
            if next_match:
                if next_match.team1_id is None:
                    next_match.team1_id = winner_id
                else:
                    next_match.team2_id = winner_id
                await self._db.flush()

        if loser_id and match.loser_next_match_id:
            loser_match = await self._repo.get_by_id(match.loser_next_match_id)
            if loser_match:
                if loser_match.team1_id is None:
                    loser_match.team1_id = loser_id
                else:
                    loser_match.team2_id = loser_id
                await self._db.flush()

    async def _publish_result_event(
        self,
        match_id: uuid.UUID,
        winner_id: uuid.UUID,
        loser_id: uuid.UUID,
        tournament_id: uuid.UUID,
    ) -> None:
        if not settings.SQS_MATCH_QUEUE_URL:
            return
        try:
            sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
            sqs.send_message(
                QueueUrl=settings.SQS_MATCH_QUEUE_URL,
                MessageBody=json.dumps({
                    "event_type": "match_result_registered",
                    "match_id": str(match_id),
                    "winner_id": str(winner_id),
                    "loser_id": str(loser_id),
                    "tournament_id": str(tournament_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }),
            )
        except Exception:
            pass  # SQS失敗はノンクリティカル（ログだけ）

    async def _invalidate_match_cache(self, match_id: uuid.UUID) -> None:
        await self._cache.delete(
            CacheKeys.MATCH_DETAIL.replace("{id}", str(match_id))
        )

    async def list_by_tournament(
        self, tournament_id: uuid.UUID, status: MatchStatus | None = None
    ) -> list["MatchSummary"]:
        """大会の試合一覧。ブラケット表示・試合タブが使う。"""
        from app.schemas.match import MatchSummary, MatchTeam

        matches = await self._repo.get_tournament_matches(tournament_id, status)

        # マップ取得数は match_games から数える。1クエリでまとめて取得する
        game_wins: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
        if matches:
            rows = (await self._db.execute(
                select(MatchGame.match_id, MatchGame.winner_id, func.count())
                .where(
                    MatchGame.match_id.in_([m.id for m in matches]),
                    MatchGame.winner_id.is_not(None),
                )
                .group_by(MatchGame.match_id, MatchGame.winner_id)
            )).all()
            for match_id, winner_id, count in rows:
                game_wins.setdefault(match_id, {})[winner_id] = count

        def team(t):
            if not t:
                return None
            return MatchTeam(
                id=str(t.id), name=t.name, tag=t.tag,
                logo_url=resign_stored_url(t.logo_url),
            )

        summaries: list[MatchSummary] = []
        for m in matches:
            wins = game_wins.get(m.id, {})
            summaries.append(MatchSummary(
                id=str(m.id),
                tournament_id=str(m.tournament_id),
                format=m.format,
                status=m.status,
                round_number=m.round_number,
                match_number=m.match_number,
                team1=team(m.team1),
                team2=team(m.team2),
                team1_wins=wins.get(m.team1_id, 0),
                team2_wins=wins.get(m.team2_id, 0),
                winner_id=str(m.winner_id) if m.winner_id else None,
                scheduled_at=m.scheduled_at,
                started_at=m.started_at,
                ended_at=m.ended_at,
                stream_url=m.stream_url,
            ))
        return summaries

    def _to_detail(self, match) -> MatchDetail:
        from app.schemas.match import (
            BanPickResponse,
            MatchGameResponse,
            MatchTeam,
            PlayerStatsResponse,
        )

        return MatchDetail(
            id=str(match.id),
            tournament_id=str(match.tournament_id),
            format=match.format,
            status=match.status,
            round_number=match.round_number,
            team1=MatchTeam(
                id=str(match.team1.id),
                name=match.team1.name,
                tag=match.team1.tag,
                logo_url=resign_stored_url(match.team1.logo_url),
            ) if match.team1 else None,
            team2=MatchTeam(
                id=str(match.team2.id),
                name=match.team2.name,
                tag=match.team2.tag,
                logo_url=resign_stored_url(match.team2.logo_url),
            ) if match.team2 else None,
            winner_id=str(match.winner_id) if match.winner_id else None,
            scheduled_at=match.scheduled_at,
            started_at=match.started_at,
            ended_at=match.ended_at,
            games=[
                MatchGameResponse(
                    id=str(g.id),
                    game_number=g.game_number,
                    map_id=str(g.map_id) if g.map_id else None,
                    map_name=g.map.display_name if g.map else None,
                    team1_score=g.team1_score,
                    team2_score=g.team2_score,
                    winner_id=str(g.winner_id) if g.winner_id else None,
                    duration_seconds=g.duration_seconds,
                    player_stats=[
                        PlayerStatsResponse(
                            player_id=str(ps.player_id),
                            player_name=ps.player.in_game_name if ps.player else "",
                            team_id=str(ps.team_id),
                            agent=ps.agent,
                            kills=ps.kills,
                            deaths=ps.deaths,
                            assists=ps.assists,
                            kda=ps.kda(),
                            score=ps.score,
                            first_bloods=ps.first_bloods,
                            custom_stats=ps.custom_stats,
                        )
                        for ps in g.player_stats
                    ],
                )
                for g in match.games
            ],
            ban_picks=[
                BanPickResponse(
                    team_id=str(bp.team_id),
                    action=bp.action,
                    map_id=str(bp.map_id),
                    map_name=bp.map.display_name,
                    order=bp.order,
                )
                for bp in match.ban_picks
            ],
            stream_url=match.stream_url,
            vod_url=match.vod_url,
        )

    async def set_stream_url(
        self, match_id: uuid.UUID, stream_url: str | None, current_user: User,
    ) -> str | None:
        """配信対象の試合として URL を設定する。空なら解除（主催者・管理者のみ）。"""
        from app.models.match import Match

        match = await self._db.get(Match, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))
        await ensure_can_manage_match(self._db, match, current_user)

        url = (stream_url or "").strip() or None
        match.stream_url = url
        await self._db.flush()
        # ブラケットはキャッシュして返しているので、ここで消さないと
        # 配信の印が画面に反映されない。
        await self._cache.delete(
            CacheKeys.BRACKET.replace("{tournament_id}", str(match.tournament_id))
        )
        await self._cache.delete(
            CacheKeys.TOURNAMENT_DETAIL.replace("{id}", str(match.tournament_id))
        )
        return url
