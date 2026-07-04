"""SearchProvider 実装（ADR-0013）。

各 Provider がエンティティ固有の検索・公開フィルタ・score正規化を持つ。
検索実装は pg_trgm similarity + ILIKE（Provider 内に隠蔽。将来 PGroonga へ差し替え可能）。
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.storage import resign_stored_url
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.search.base import SearchHit


def _like(q: str) -> str:
    # ILIKE のワイルドカードをエスケープ
    esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


class TeamSearchProvider:
    name = "team"

    async def search(self, db: AsyncSession, q: str, limit: int) -> list[SearchHit]:
        sim = func.similarity(Team.name, q)
        rows = (await db.execute(
            select(Team, sim.label("score"))
            .where(Team.is_active == True,
                   or_(Team.name.ilike(_like(q)), Team.tag.ilike(_like(q))))
            .order_by(sim.desc())
            .limit(limit)
        )).all()
        return [SearchHit(
            type="team", id=str(t.id), label=t.name, sub=f"[{t.tag}]",
            image_url=resign_stored_url(t.logo_url), url=f"/teams/{t.id}", score=float(s or 0),
        ) for t, s in rows]


class PlayerSearchProvider:
    name = "player"

    async def search(self, db: AsyncSession, q: str, limit: int) -> list[SearchHit]:
        sim = func.similarity(Player.in_game_name, q)
        rows = (await db.execute(
            select(Player, sim.label("score"))
            .where(Player.in_game_name.ilike(_like(q)))
            .order_by(sim.desc())
            .limit(limit)
        )).all()
        return [SearchHit(
            type="player", id=str(p.id), label=p.in_game_name,
            sub=(p.game.value if hasattr(p.game, "value") else str(p.game)),
            url=f"/players/{p.id}", score=float(s or 0),
        ) for p, s in rows]


class TournamentSearchProvider:
    name = "tournament"

    async def search(self, db: AsyncSession, q: str, limit: int) -> list[SearchHit]:
        sim = func.similarity(Tournament.name, q)
        rows = (await db.execute(
            select(Tournament, sim.label("score"))
            .where(Tournament.is_public == True, Tournament.name.ilike(_like(q)))
            .order_by(sim.desc())
            .limit(limit)
        )).all()
        return [SearchHit(
            type="tournament", id=str(t.id), label=t.name,
            sub=(t.game.value if hasattr(t.game, "value") else str(t.game)),
            image_url=resign_stored_url(t.banner_url), url=f"/tournaments/{t.id}", score=float(s or 0),
        ) for t, s in rows]


class MatchSearchProvider:
    """対戦チーム名で試合を検索（公開大会のみ）。"""
    name = "match"

    async def search(self, db: AsyncSession, q: str, limit: int) -> list[SearchHit]:
        T1 = aliased(Team)
        T2 = aliased(Team)
        rows = (await db.execute(
            select(Match, T1.name, T2.name, Tournament.name, Tournament.is_public)
            .join(Tournament, Tournament.id == Match.tournament_id)
            .outerjoin(T1, T1.id == Match.team1_id)
            .outerjoin(T2, T2.id == Match.team2_id)
            .where(Tournament.is_public == True,
                   or_(T1.name.ilike(_like(q)), T2.name.ilike(_like(q))))
            .order_by(Match.created_at.desc())
            .limit(limit)
        )).all()
        hits: list[SearchHit] = []
        for m, t1, t2, tour_name, _pub in rows:
            label = f"{t1 or 'TBD'} vs {t2 or 'TBD'}"
            # 単純一致スコア（名前が q を含む＝一定スコア）。pg_trgm対象外のため固定寄与。
            hits.append(SearchHit(
                type="match", id=str(m.id), label=label, sub=tour_name,
                url=f"/matches/{m.id}", score=0.5,
            ))
        return hits


DEFAULT_PROVIDERS = [
    TeamSearchProvider(),
    PlayerSearchProvider(),
    TournamentSearchProvider(),
    MatchSearchProvider(),
]
