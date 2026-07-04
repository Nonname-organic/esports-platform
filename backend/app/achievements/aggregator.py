"""AchievementAggregator — 既存データから読み取り専用で実績カードを集約する。

責務: 大会 → 順位 → 勝敗 → 実績 → DTO。ここまで。
  - DB更新は禁止（純 read-only）。
  - Generator は持たない（Report/ADR-0009 とは責務を分ける。Report は materialize、こちらは都度集約）。
  - 出典: Tournament / TournamentReport / Match / TournamentRegistration / CareerAggregationService。
  - 新しい achievements テーブルは作らない（Growth Policy: Additive・保存しない）。

順位の決め方（1大会あたり）:
  materialized な TournamentReport があれば優先し、無ければ TournamentReportAggregator で
  オンザフライ集計（Report と同一ロジックを再利用）。champion / runner_up は決勝結果、
  top4 は勝ち数順の順位表 top4 を用いる（排他バケット: champion/runner_up は除く）。

キャッシュ: Redis `team:achievement:{team_id}`（無くても cache-miss で再集約でき、動作する）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import RedisCache
from app.models.enums import RegistrationStatus, TournamentStatus
from app.models.team import Team
from app.models.tournament import Tournament, TournamentRegistration
from app.models.tournament_report import TournamentReport
from app.reports.aggregator import TournamentReportAggregator
from app.services.career_service import CareerAggregationService

ACHIEVEMENT_CACHE_TTL = 600      # 10分
RECENT_TITLES_LIMIT = 5
TOP4_CUTOFF = 4


class AchievementAggregator:
    """1チームの公開実績カードを集約する（read-only）。"""

    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache

    async def get_team_card(self, team_id: uuid.UUID) -> dict:
        cache_key = f"team:achievement:{team_id}"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached  # type: ignore[return-value]
        card = await self._aggregate_team(team_id)
        await self._cache.set(cache_key, card, ttl=ACHIEVEMENT_CACHE_TTL)
        return card

    async def invalidate_team(self, team_id: uuid.UUID) -> None:
        """実績が変化した際に呼ぶ（tournament.completed → 将来の team.achievement.updated 接合点）。"""
        await self._cache.delete(f"team:achievement:{team_id}")

    # ── 集約本体 ──────────────────────────────────────────────────────────────
    async def _aggregate_team(self, team_id: uuid.UUID) -> dict:
        team = await self._db.scalar(select(Team).where(Team.id == team_id))
        if not team:
            raise NotFoundError("チーム", str(team_id))

        # 勝敗系は既存の CareerAggregationService を再利用（DRY・キャッシュも共有）
        career = await CareerAggregationService(self._db, self._cache).get_team_career(team_id)

        # 参加した「完了大会」（承認済み登録のみ）
        rows = (await self._db.execute(
            select(Tournament.id, Tournament.name, Tournament.end_at)
            .join(TournamentRegistration, TournamentRegistration.tournament_id == Tournament.id)
            .where(
                TournamentRegistration.team_id == team_id,
                TournamentRegistration.status == RegistrationStatus.APPROVED,
                Tournament.status == TournamentStatus.COMPLETED,
            )
        )).all()

        championships = runner_ups = top4 = 0
        titles: list[dict] = []
        for tid, tname, end_at in rows:
            placement = await self._placement(tid, team_id)
            if placement == "champion":
                championships += 1
            elif placement == "runner_up":
                runner_ups += 1
            elif placement == "top4":
                top4 += 1
            if placement:
                titles.append({
                    "placement": placement,
                    "tournament_id": str(tid),
                    "tournament_name": tname,
                    "ended_at": end_at.isoformat() if end_at else None,
                })

        # 終了日の新しい順（未定=末尾）
        titles.sort(key=lambda t: t["ended_at"] or "", reverse=True)

        return {
            "team_id": str(team_id),
            "team_name": team.name,
            "team_tag": team.tag,
            "game": team.game.value if hasattr(team.game, "value") else str(team.game),
            "championships": championships,
            "runner_ups": runner_ups,
            "top4": top4,
            "tournaments": len(rows),
            "matches": career["total_matches"],
            "wins": career["total_wins"],
            "losses": career["total_losses"],
            "win_rate": career["win_rate"],
            "mvps": await self._count_mvps(team_id),
            "recent_titles": titles[:RECENT_TITLES_LIMIT],
            # Team に founded_at 列は無いため、作成日を「発足日(Since)」として扱う（設計差分に記載）
            "founded_at": team.created_at.isoformat() if team.created_at else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _placement(self, tournament_id: uuid.UUID, team_id: uuid.UUID) -> Optional[str]:
        """順位ラベル（champion / runner_up / top4 / None）を返す。"""
        report = await self._db.scalar(
            select(TournamentReport).where(TournamentReport.tournament_id == tournament_id)
        )
        if report and report.data:
            data = report.data
        else:
            data = await TournamentReportAggregator(self._db).aggregate(tournament_id)

        tid = str(team_id)
        champion = data.get("champion") or {}
        runner_up = data.get("runner_up") or {}
        if champion.get("team_id") == tid:
            return "champion"
        if runner_up.get("team_id") == tid:
            return "runner_up"
        for idx, s in enumerate(data.get("standings") or []):
            if s.get("team_id") == tid:
                return "top4" if idx < TOP4_CUTOFF else None
        return None

    async def _count_mvps(self, team_id: uuid.UUID) -> int:
        """チームのMVP数。現状データ源が未整備のため 0 を返す（DTOは 0/null 許容）。

        将来: match_mvps を「その試合で当該チームに所属していた選手」で集約して算出する。
        Aggregator へ本メソッドを実装追加するだけで DTO 契約は不変（拡張ポイント）。
        """
        return 0
