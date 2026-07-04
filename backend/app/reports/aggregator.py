"""Report Aggregator — DB から集計する責務（ADR-0009）。

Generator はここを呼ぶだけで、自身は集計しない。ゲーム名はハードコードしない・Riot非依存。
現フェーズは大会内 matches / registrations / teams から算出できる項目を集計する。
MVP / 人気Agent/Map / ベストマッチ は stats が揃った段階で拡張（data は安定契約なので後付け可）。
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MatchStatus, RegistrationStatus
from app.models.match import Match
from app.models.team import Team
from app.models.tournament import Tournament, TournamentRegistration


class TournamentReportAggregator:
    """1大会の終了レポート用データを集計する。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def aggregate(self, tournament_id: uuid.UUID) -> dict:
        t = await self._db.scalar(select(Tournament).where(Tournament.id == tournament_id))
        if not t:
            raise ValueError(f"tournament not found: {tournament_id}")

        # 承認済み参加チーム（id -> name）
        reg_rows = (await self._db.execute(
            select(Team.id, Team.name)
            .join(TournamentRegistration, TournamentRegistration.team_id == Team.id)
            .where(TournamentRegistration.tournament_id == tournament_id,
                   TournamentRegistration.status == RegistrationStatus.APPROVED)
        )).all()
        team_names = {tid: name for tid, name in reg_rows}
        participant_count = len(team_names)

        # 完了した試合
        matches = list((await self._db.execute(
            select(Match).where(Match.tournament_id == tournament_id,
                                Match.status == MatchStatus.COMPLETED)
        )).scalars().all())
        match_count = len(matches)

        # チーム別 勝敗（winner_id ベース）
        wins: dict[uuid.UUID, int] = {}
        losses: dict[uuid.UUID, int] = {}
        for m in matches:
            if m.winner_id:
                wins[m.winner_id] = wins.get(m.winner_id, 0) + 1
                loser = m.team2_id if m.winner_id == m.team1_id else m.team1_id
                if loser:
                    losses[loser] = losses.get(loser, 0) + 1

        # 名前解決を補完（参加登録に無いチームIDも拾う）
        for tid in set(list(wins) + list(losses)):
            if tid not in team_names:
                nm = await self._db.scalar(select(Team.name).where(Team.id == tid))
                team_names[tid] = nm or "Unknown"

        def _tref(tid: Optional[uuid.UUID]) -> Optional[dict]:
            if not tid:
                return None
            return {"team_id": str(tid), "team_name": team_names.get(tid, "Unknown")}

        # 優勝/準優勝: 決勝（完了試合の最大 round_number）から。無ければ勝ち数最多。
        champion = runner_up = None
        if matches:
            final = max(matches, key=lambda m: m.round_number)
            if final.winner_id:
                champion = _tref(final.winner_id)
                runner_up = _tref(final.team2_id if final.winner_id == final.team1_id else final.team1_id)
        if champion is None and wins:
            top = max(wins, key=lambda k: wins[k])
            champion = _tref(top)

        # 順位表（勝ち数降順）
        standings = []
        for tid in sorted(team_names, key=lambda k: wins.get(k, 0), reverse=True):
            w, l = wins.get(tid, 0), losses.get(tid, 0)
            total = w + l
            standings.append({
                "team_id": str(tid), "team_name": team_names[tid],
                "wins": w, "losses": l,
                "win_rate": round(w / total, 4) if total else 0.0,
            })

        most_wins = None
        if wins:
            mw = max(wins, key=lambda k: wins[k])
            most_wins = {"team_name": team_names.get(mw, "Unknown"), "wins": wins[mw]}

        return {
            "schema_version": 1,
            "tournament": {
                "id": str(t.id), "name": t.name,
                "game": t.game.value if hasattr(t.game, "value") else str(t.game),
                "format": t.format.value if hasattr(t.format, "value") else str(t.format),
            },
            "participant_count": participant_count,
            "match_count": match_count,
            "champion": champion,
            "runner_up": runner_up,
            "most_wins": most_wins,
            "standings": standings,
            # 以下は stats 拡充時に埋める（安定契約 / null 許容）
            "mvp": None,
            "popular_agent": None,
            "popular_map": None,
            "best_match": None,
        }
