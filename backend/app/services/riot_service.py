"""
Riot Integration Service (VALORANT)

Riot API:
  - account-v1: Riot ID (gameName#tagLine) → PUUID
  - val-match-v1: PUUID → match list / match detail
  - val-ranked-v1: ランク情報（簡略）

同期フロー:
  link → PUUID解決 → sync → match取得 → riot_matches保存
       → Career/Scout Rating へ反映（キャッシュinvalidate）

設計:
  - RIOT_API_KEY 未設定時は graceful degradation（連携不可エラー）
  - Redisキャッシュ: riot:profile:{player_id} TTL 1h
  - レート制限: 簡易トークンバケット（Redisカウンタ）
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.redis import RedisCache
from app.models.player import Player
from app.models.riot import RiotProfile, RiotMatch


RIOT_CACHE_TTL = 3600  # 1時間


class RiotAPIClient:
    """Riot API HTTP クライアント（レート制限対応）"""

    def __init__(self, cache: RedisCache):
        self._cache = cache
        self._key = settings.RIOT_API_KEY
        self._account_region = settings.RIOT_ACCOUNT_REGION
        self._val_region = settings.RIOT_VAL_REGION

    @property
    def enabled(self) -> bool:
        return bool(self._key)

    def _headers(self) -> dict:
        return {"X-Riot-Token": self._key or ""}

    async def _rate_limit(self) -> None:
        """簡易レート制限: 20req/sec, 100req/2min を超えないよう間隔調整"""
        try:
            redis = getattr(self._cache, "_redis", None)
            if redis:
                cnt = await redis.incr("riot:ratelimit:sec")
                if cnt == 1:
                    await redis.expire("riot:ratelimit:sec", 1)
                if cnt > 18:  # マージンを持たせる
                    await asyncio.sleep(1)
        except Exception:
            pass

    async def resolve_puuid(self, game_name: str, tag_line: str) -> Optional[str]:
        if not self.enabled:
            return None
        await self._rate_limit()
        url = f"https://{self._account_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers=self._headers())
            if res.status_code == 200:
                return res.json().get("puuid")
            return None

    async def fetch_match_ids(self, puuid: str, size: int = 20) -> list[str]:
        if not self.enabled:
            return []
        await self._rate_limit()
        url = f"https://{self._val_region}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}"
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers=self._headers())
            if res.status_code == 200:
                history = res.json().get("history", [])
                return [h["matchId"] for h in history[:size]]
            return []

    async def fetch_match(self, match_id: str) -> Optional[dict]:
        if not self.enabled:
            return None
        await self._rate_limit()
        url = f"https://{self._val_region}.api.riotgames.com/val/match/v1/matches/{match_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(url, headers=self._headers())
            if res.status_code == 200:
                return res.json()
            return None


class RiotService:
    def __init__(self, db: AsyncSession, cache: RedisCache):
        self._db = db
        self._cache = cache
        self._client = RiotAPIClient(cache)

    # ── Riot ID 紐付け ─────────────────────────────────────────────────────────
    async def link(self, player_id: uuid.UUID, riot_id: str) -> RiotProfile:
        player = await self._db.scalar(select(Player).where(Player.id == player_id))
        if not player:
            raise NotFoundError("プレイヤー", str(player_id))

        if "#" not in riot_id:
            raise BusinessRuleError("Riot IDは Name#TAG 形式で入力してください")
        game_name, tag_line = riot_id.split("#", 1)

        # PUUID解決（APIキーがあれば）
        puuid = await self._client.resolve_puuid(game_name.strip(), tag_line.strip())

        existing = await self._db.scalar(
            select(RiotProfile).where(RiotProfile.player_id == player_id)
        )
        now = datetime.now(timezone.utc)
        if existing:
            existing.game_name = game_name.strip()
            existing.tag_line = tag_line.strip()
            existing.puuid = puuid or existing.puuid
            existing.region = settings.RIOT_VAL_REGION
            await self._db.flush()
            profile = existing
        else:
            profile = RiotProfile(
                player_id=player_id,
                game_name=game_name.strip(),
                tag_line=tag_line.strip(),
                puuid=puuid,
                region=settings.RIOT_VAL_REGION,
                created_at=now,
            )
            self._db.add(profile)
            await self._db.flush()

        return profile

    async def get_profile(self, player_id: uuid.UUID) -> Optional[RiotProfile]:
        return await self._db.scalar(
            select(RiotProfile).where(RiotProfile.player_id == player_id)
        )

    # ── 同期 ────────────────────────────────────────────────────────────────────
    async def sync(self, player_id: uuid.UUID) -> dict:
        profile = await self.get_profile(player_id)
        if not profile:
            raise NotFoundError("Riot連携", str(player_id))

        if not self._client.enabled:
            raise BusinessRuleError("Riot API連携が未設定です（RIOT_API_KEYが必要）")

        # PUUIDがなければ解決
        if not profile.puuid:
            profile.puuid = await self._client.resolve_puuid(profile.game_name, profile.tag_line)
            if not profile.puuid:
                raise BusinessRuleError("Riot IDが見つかりません")
            await self._db.flush()

        # 既存試合IDを取得（重複回避）
        existing_ids = set((await self._db.execute(
            select(RiotMatch.riot_match_id).where(RiotMatch.player_id == player_id)
        )).scalars().all())

        match_ids = await self._client.fetch_match_ids(profile.puuid, size=20)
        new_count = 0

        for mid in match_ids:
            if mid in existing_ids:
                continue
            match_data = await self._client.fetch_match(mid)
            if not match_data:
                continue
            parsed = self._parse_match(match_data, profile.puuid)
            if not parsed:
                continue
            self._db.add(RiotMatch(
                player_id=player_id,
                riot_match_id=mid,
                created_at=datetime.now(timezone.utc),
                **parsed,
            ))
            new_count += 1

        profile.synced_at = datetime.now(timezone.utc)
        await self._db.flush()

        # Career/Scout への反映（キャッシュ無効化）
        await self._cache.delete(f"career:player:{player_id}")

        return {"synced_matches": new_count, "synced_at": profile.synced_at.isoformat()}

    def _parse_match(self, match_data: dict, puuid: str) -> Optional[dict]:
        """Riot match-v1 レスポンスから対象プレイヤーの統計を抽出"""
        try:
            players = match_data.get("players", [])
            me = next((p for p in players if p.get("puuid") == puuid), None)
            if not me:
                return None
            stats = me.get("stats", {})
            info = match_data.get("matchInfo", {})
            rounds = info.get("roundsPlayed", stats.get("roundsPlayed", 0)) or 1

            kills = stats.get("kills", 0)
            deaths = stats.get("deaths", 0)
            assists = stats.get("assists", 0)
            score = stats.get("score", 0)

            # チーム勝敗
            my_team = me.get("teamId")
            teams = match_data.get("teams", [])
            won = next((t.get("won") for t in teams if t.get("teamId") == my_team), None)

            map_name = info.get("mapId", "").split("/")[-1] if info.get("mapId") else None
            agent = me.get("characterId")

            return {
                "agent": agent,
                "map_name": map_name,
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "acs": round(score / rounds, 1) if rounds else 0.0,
                "hs_rate": None,  # round詳細から算出可能（簡略化）
                "won": won,
                "rounds": rounds,
                "played_at": None,
            }
        except Exception:
            return None

    # ── Competitive 集計（RiotMatch から算出。未取得メトリクスは None） ──────────
    async def get_competitive_summary(self, player_id: uuid.UUID) -> dict:
        """Riot（Competitive）データを集計。

        RiotMatch に保存された agent/map/K/D/A/ACS/HS/won から算出する。
        RR・Episode・Act・ADR・KAST・FK/Clutch 等は未保存のため None（空データ対応）。
        """
        profile = await self.get_profile(player_id)
        rows = list((await self._db.execute(
            select(RiotMatch)
            .where(RiotMatch.player_id == player_id)
            .order_by(RiotMatch.created_at.desc())
        )).scalars().all())

        def _agg(ms: list[RiotMatch]) -> dict:
            n = len(ms)
            if n == 0:
                return {
                    "matches": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                    "avg_kills": 0.0, "avg_deaths": 0.0, "avg_assists": 0.0,
                    "kd": 0.0, "kda": 0.0, "acs": 0.0, "hs_rate": None,
                }
            wins = sum(1 for m in ms if m.won is True)
            losses = sum(1 for m in ms if m.won is False)
            decided = wins + losses
            k = sum(m.kills for m in ms)
            d = sum(m.deaths for m in ms)
            a = sum(m.assists for m in ms)
            acs_vals = [m.acs for m in ms if m.acs is not None]
            hs_vals = [m.hs_rate for m in ms if m.hs_rate is not None]
            return {
                "matches": n,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / decided, 4) if decided else 0.0,
                "avg_kills": round(k / n, 1),
                "avg_deaths": round(d / n, 1),
                "avg_assists": round(a / n, 1),
                "kd": round(k / d, 2) if d else float(k),
                "kda": round((k + a) / d, 2) if d else float(k + a),
                "acs": round(sum(acs_vals) / len(acs_vals), 1) if acs_vals else 0.0,
                "hs_rate": round(sum(hs_vals) / len(hs_vals), 4) if hs_vals else None,
            }

        summary = _agg(rows)
        recent20 = _agg(rows[:20])

        # エージェント別集計
        agents: dict[str, list[RiotMatch]] = {}
        maps: dict[str, list[RiotMatch]] = {}
        for m in rows:
            if m.agent:
                agents.setdefault(m.agent, []).append(m)
            if m.map_name:
                maps.setdefault(m.map_name, []).append(m)

        total = len(rows) or 1
        agent_stats = []
        for name, ms in agents.items():
            g = _agg(ms)
            agent_stats.append({
                "agent": name, "games": g["matches"], "wins": g["wins"],
                "win_rate": g["win_rate"], "pick_rate": round(len(ms) / total, 4),
                "acs": g["acs"], "kd": g["kd"], "kda": g["kda"], "hs_rate": g["hs_rate"],
                "avg_kills": g["avg_kills"], "avg_deaths": g["avg_deaths"], "avg_assists": g["avg_assists"],
            })
        agent_stats.sort(key=lambda x: x["games"], reverse=True)

        map_stats = []
        for name, ms in maps.items():
            g = _agg(ms)
            map_stats.append({
                "map": name, "games": g["matches"], "wins": g["wins"],
                "win_rate": g["win_rate"], "acs": g["acs"], "kd": g["kd"], "kda": g["kda"],
                "attack_win_rate": None, "defense_win_rate": None, "first_kill_rate": None,
            })
        map_stats.sort(key=lambda x: x["games"], reverse=True)

        matches = [{
            "match_id": m.riot_match_id,
            "agent": m.agent,
            "map_name": m.map_name,
            "kills": m.kills, "deaths": m.deaths, "assists": m.assists,
            "kd": round(m.kills / m.deaths, 2) if m.deaths else float(m.kills),
            "kda": round((m.kills + m.assists) / m.deaths, 2) if m.deaths else float(m.kills + m.assists),
            "acs": m.acs, "adr": None, "hs_rate": m.hs_rate, "mmr": None,
            "won": m.won,
            "played_at": m.played_at.isoformat() if m.played_at else (m.created_at.isoformat() if m.created_at else None),
        } for m in rows[:20]]

        return {
            "linked": profile is not None,
            "riot_id": profile.riot_id if profile else None,
            "synced_at": profile.synced_at.isoformat() if profile and profile.synced_at else None,
            "rank": {
                "current_rank": profile.current_rank if profile else None,
                "peak_rank": profile.peak_rank if profile else None,
                "peak_rr": None, "current_rr": None, "episode": None, "act": None,
            },
            "summary": {
                **summary,
                "recent20_win_rate": recent20["win_rate"],
                # 未保存メトリクス（拡張余地）
                "adr": None, "kast": None, "fk_rate": None, "fd_rate": None,
                "clutch_rate": None, "damage_per_round": None, "mvp_rate": None,
            },
            "agents": agent_stats,
            "maps": map_stats,
            "matches": matches,
            "rank_history": [],  # RR/Episode 履歴は未保存（将来のRiot ranked連携で拡張）
        }

    # ── 取得済みデータ（Analytics表示用） ──────────────────────────────────────
    async def get_riot_matches(self, player_id: uuid.UUID, limit: int = 20) -> list[dict]:
        rows = (await self._db.execute(
            select(RiotMatch)
            .where(RiotMatch.player_id == player_id)
            .order_by(RiotMatch.created_at.desc())
            .limit(limit)
        )).scalars().all()
        return [{
            "match_id": m.riot_match_id,
            "agent": m.agent,
            "map_name": m.map_name,
            "kills": m.kills,
            "deaths": m.deaths,
            "assists": m.assists,
            "acs": m.acs,
            "won": m.won,
        } for m in rows]
