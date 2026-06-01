"""
Match Analytics Service
- ACS (Average Combat Score) 算出
- MVP 自動算出
- Glicko-2 レーティング更新
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match, PlayerStat
from app.core.events import publish_event, EventType


class ACSCalculator:
    """Average Combat Score 算出 (VALORANT準拠)"""

    @staticmethod
    def calculate(kills: int, deaths: int, assists: int, score: int, rounds: int) -> float:
        if rounds == 0:
            return 0.0
        # VALORANT ACS: スコア / ラウンド数
        return round(score / rounds, 1)

    @staticmethod
    def calculate_kpr(kills: int, rounds: int) -> float:
        if rounds == 0:
            return 0.0
        return round(kills / rounds, 2)

    @staticmethod
    def calculate_first_blood_rate(first_bloods: int, rounds: int) -> float:
        if rounds == 0:
            return 0.0
        return round(first_bloods / rounds * 100, 1)


class MVPCalculator:
    """
    MVP 算出アルゴリズム
    Score = w1*ACS + w2*KDA + w3*FirstKill% + w4*WinContribution
    """

    WEIGHTS = {
        "acs": 0.35,
        "kda": 0.25,
        "first_kill_rate": 0.20,
        "win_contribution": 0.20,
    }

    @classmethod
    def calculate_mvp_score(
        cls,
        stats: PlayerStat,
        rounds: int,
        team_won: bool,
    ) -> float:
        kda = (stats.kills + stats.assists) / max(stats.deaths, 1)
        acs = ACSCalculator.calculate(stats.kills, stats.deaths, stats.assists, stats.score, rounds)
        fb_rate = ACSCalculator.calculate_first_blood_rate(stats.first_bloods, rounds)

        # 正規化 (0-1スケール)
        acs_norm = min(acs / 300, 1.0)
        kda_norm = min(kda / 5.0, 1.0)
        fb_norm = min(fb_rate / 30, 1.0)
        win_factor = 1.2 if team_won else 0.9

        score = (
            cls.WEIGHTS["acs"] * acs_norm +
            cls.WEIGHTS["kda"] * kda_norm +
            cls.WEIGHTS["first_kill_rate"] * fb_norm +
            cls.WEIGHTS["win_contribution"] * win_factor * 0.5
        ) * 100

        return round(score, 2)

    @classmethod
    def find_mvp(
        cls,
        player_stats: list[PlayerStat],
        rounds: int,
        winner_team_id: Optional[uuid.UUID],
    ) -> Optional[PlayerStat]:
        if not player_stats:
            return None

        best = None
        best_score = -1.0

        for stat in player_stats:
            team_won = stat.team_id == winner_team_id if winner_team_id else False
            score = cls.calculate_mvp_score(stat, rounds, team_won)
            if score > best_score:
                best_score = score
                best = stat

        return best


class Glicko2:
    """
    Glicko-2 レーティングシステム
    https://www.glicko.net/glicko/glicko2.pdf
    """

    TAU = 0.5  # システム定数 (0.3-1.2 推奨)
    EPSILON = 0.000001
    SCALE = 173.7178  # 変換定数

    @classmethod
    def update_rating(
        cls,
        rating: float,
        deviation: float,
        volatility: float,
        opponents: list[tuple[float, float, float]],  # (opponent_rating, opponent_rd, score)
    ) -> tuple[float, float, float]:
        """
        レーティング更新
        Returns: (new_rating, new_deviation, new_volatility)
        """
        if not opponents:
            # 試合なし: 偏差のみ増加
            new_rd = min(math.sqrt(deviation ** 2 + volatility ** 2), 350)
            return rating, new_rd, volatility

        # Glicko-2スケールに変換
        mu = (rating - 1500) / cls.SCALE
        phi = deviation / cls.SCALE

        # 対戦相手の変換
        mu_js = [(r - 1500) / cls.SCALE for r, _, _ in opponents]
        phi_js = [rd / cls.SCALE for _, rd, _ in opponents]
        scores = [s for _, _, s in opponents]

        # 期待スコア計算
        g_phis = [1 / math.sqrt(1 + 3 * pj ** 2 / math.pi ** 2) for pj in phi_js]
        E_values = [1 / (1 + math.exp(-g * (mu - mj))) for g, mj in zip(g_phis, mu_js)]

        # v (推定分散の逆数)
        v = 1 / sum(g ** 2 * E * (1 - E) for g, E in zip(g_phis, E_values))

        # delta (推定改善量)
        delta = v * sum(g * (s - E) for g, E, s in zip(g_phis, E_values, scores))

        # volatility 更新 (Illinois algorithm)
        a = math.log(volatility ** 2)
        A = a
        f = lambda x: (
            math.exp(x) * (delta ** 2 - phi ** 2 - v - math.exp(x)) /
            (2 * (phi ** 2 + v + math.exp(x)) ** 2) -
            (x - a) / cls.TAU ** 2
        )

        B = a - cls.TAU * math.sqrt(delta ** 2 + phi ** 2 + v) if delta ** 2 > phi ** 2 + v else a - cls.TAU

        fA, fB = f(A), f(B)
        for _ in range(100):
            C = A + (A - B) * fA / (fB - fA)
            fC = f(C)
            if fB * fC < 0:
                A, fA = B, fB
            else:
                fA = fA / 2
            B, fB = C, fC
            if abs(B - A) < cls.EPSILON:
                break

        new_volatility = math.exp(A / 2)

        # 新しい偏差
        phi_star = math.sqrt(phi ** 2 + new_volatility ** 2)
        new_phi = 1 / math.sqrt(1 / phi_star ** 2 + 1 / v)

        # 新しいレーティング
        new_mu = mu + new_phi ** 2 * sum(g * (s - E) for g, E, s in zip(g_phis, E_values, scores))

        # Glicko-1スケールに戻す
        new_rating = cls.SCALE * new_mu + 1500
        new_deviation = cls.SCALE * new_phi

        return round(new_rating, 2), round(new_deviation, 2), round(new_volatility, 6)


class MatchAnalyticsService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def calculate_and_save_mvp(self, match: Match) -> None:
        """試合終了後にMVPを算出してDBに保存"""
        from app.models.match import PlayerMatchStats
        from app.models.tournament import match_mvps

        if not match.games:
            return

        all_stats = []
        total_rounds = 0
        for game in match.games:
            total_rounds += game.team1_score + game.team2_score
            all_stats.extend(game.player_stats)

        mvp_stat = MVPCalculator.find_mvp(all_stats, max(total_rounds, 1), match.winner_id)
        if not mvp_stat:
            return

        rounds = max(total_rounds, 1)
        kda = (mvp_stat.kills + mvp_stat.assists) / max(mvp_stat.deaths, 1)
        acs = ACSCalculator.calculate(mvp_stat.kills, mvp_stat.deaths, mvp_stat.assists, mvp_stat.score, rounds)
        mvp_score = MVPCalculator.calculate_mvp_score(mvp_stat, rounds, mvp_stat.team_id == match.winner_id)

        # DB保存
        from app.models.match import MatchMVP
        mvp = MatchMVP(
            match_id=match.id,
            player_id=mvp_stat.player_id,
            player_name=mvp_stat.player_name,
            team_id=mvp_stat.team_id,
            acs=acs,
            kda=kda,
            mvp_score=mvp_score,
            stats_snapshot={
                "kills": mvp_stat.kills,
                "deaths": mvp_stat.deaths,
                "assists": mvp_stat.assists,
                "score": mvp_stat.score,
                "first_bloods": mvp_stat.first_bloods,
                "acs": acs,
                "kda": kda,
            },
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(mvp)
        await self._db.flush()

        await publish_event(
            EventType.MVP_CALCULATED,
            str(match.id),
            "Match",
            {"player_id": str(mvp_stat.player_id), "mvp_score": mvp_score},
        )
