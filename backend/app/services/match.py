import json
import uuid
from datetime import datetime, timezone

import boto3
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.redis import CacheKeys, RedisCache
from app.models.enums import MatchStatus
from app.models.user import User
from app.repositories.match import MatchRepository
from app.repositories.tournament import TournamentRepository
from app.schemas.match import (
    BanPickCreate,
    MatchDetail,
    MatchResultCreate,
    ScoreUpdate,
)


class MatchService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._repo = MatchRepository(db)
        self._tournament_repo = TournamentRepository(db)
        self._cache = cache
        self._db = db

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

    async def start_match(self, match_id: uuid.UUID, current_user: User) -> None:
        match = await self._repo.get_by_id(match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

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
        match = await self._repo.get_by_id(match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

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

    async def register_ban_pick(
        self, match_id: uuid.UUID, data: BanPickCreate
    ) -> None:
        match = await self._repo.get_by_id(match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

        if match.status not in (MatchStatus.SCHEDULED, MatchStatus.ONGOING):
            raise BusinessRuleError("Ban/Pickを登録できる状態ではありません")

        await self._repo.create_ban_pick(
            match_id=match_id,
            team_id=uuid.UUID(data.team_id),
            action=data.action,
            map_id=uuid.UUID(data.map_id),
            order=data.order,
        )

    async def register_result(
        self,
        match_id: uuid.UUID,
        data: MatchResultCreate,
        current_user: User,
    ) -> None:
        # 分散ロック（重複登録防止）
        lock_key = CacheKeys.LOCK_MATCH_RESULT.replace("{match_id}", str(match_id))
        if not await self._cache.acquire_lock(lock_key, ttl=10):
            raise ConflictError("結果を処理中です。しばらく待ってから再試行してください")

        try:
            match = await self._repo.get_full_detail(match_id)
            if not match:
                raise NotFoundError("試合", str(match_id))

            if match.status == MatchStatus.COMPLETED:
                raise BusinessRuleError("この試合の結果は既に登録されています")

            if match.status != MatchStatus.ONGOING:
                raise BusinessRuleError("進行中の試合の結果のみ登録できます")

            winner_id = uuid.UUID(data.winner_id)
            if winner_id not in (match.team1_id, match.team2_id):
                raise BusinessRuleError("勝者はこの試合の参加チームである必要があります")

            loser_id = (
                match.team1_id if winner_id == match.team2_id else match.team2_id
            )

            # ゲーム数からスコアを計算
            games = match.games
            winner_game_wins = sum(
                1 for g in games if g.winner_id == winner_id
            )
            loser_game_wins = len(games) - winner_game_wins

            # ゲーム別統計の保存
            if data.game_stats:
                for game_stat in data.game_stats:
                    game = await self._repo.upsert_game_score(
                        match_id=match_id,
                        game_number=game_stat.game_number,
                        map_id=uuid.UUID(game_stat.map_id),
                        team1_score=game_stat.team1_score,
                        team2_score=game_stat.team2_score,
                        winner_id=uuid.UUID(game_stat.winner_id),
                        side_first_team1=game_stat.side_first_team1,
                        duration_seconds=game_stat.duration_seconds,
                        ended_at=datetime.now(timezone.utc),
                    )
                    if game_stat.player_stats:
                        await self._repo.bulk_create_player_stats([
                            {
                                "match_game_id": game.id,
                                "player_id": uuid.UUID(ps.player_id),
                                "team_id": uuid.UUID(ps.team_id),
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
            await self._db.flush()

            # 次の試合にチームを自動セット
            await self._advance_bracket(match, winner_id)

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

    async def _advance_bracket(self, match, winner_id: uuid.UUID) -> None:
        if match.next_match_id:
            next_match = await self._repo.get_by_id(match.next_match_id)
            if next_match:
                if next_match.team1_id is None:
                    next_match.team1_id = winner_id
                else:
                    next_match.team2_id = winner_id
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
                logo_url=match.team1.logo_url,
            ) if match.team1 else None,
            team2=MatchTeam(
                id=str(match.team2.id),
                name=match.team2.name,
                tag=match.team2.tag,
                logo_url=match.team2.logo_url,
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
