"""プラットフォームAPIクライアント。

2系統:
- 公開GET: 認証不要の参照系（tournaments/players/teams/career/analytics/scout/match/riot）。
- /bot/*  : X-Bot-Secret（共有秘密）+ 任意で X-Discord-User-Id（代理実行の本人解決）。

エラーは ApiError(status, message) に正規化して投げる（core/errors.py で整形）。
"""

import httpx

from config import config
from core.errors import ApiError


def _extract_message(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except Exception:
        return resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, list):  # FastAPI validation error
        return " / ".join(str(d.get("msg", d)) for d in detail)
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    return str(detail or (data.get("message") if isinstance(data, dict) else None) or f"HTTP {resp.status_code}")


class PlatformAPIClient:
    def __init__(self):
        self._base = config.API_BASE_URL.rstrip("/")
        self._secret = config.BOT_API_TOKEN
        self._client: httpx.AsyncClient | None = None

    def _c(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _bot_headers(self, discord_user_id=None) -> dict:
        h = {"X-Bot-Secret": self._secret or ""}
        if discord_user_id is not None:
            h["X-Discord-User-Id"] = str(discord_user_id)
        return h

    # ── low-level ──────────────────────────────────────────────────────────
    async def _get(self, path: str, params: dict | None = None):
        """公開GET。404はNone、その他4xx/5xxはApiError、成功は .data を返す。"""
        r = await self._c().get(f"{self._base}{path}", params=params)
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise ApiError(r.status_code, _extract_message(r))
        body = r.json()
        return body.get("data") if isinstance(body, dict) else body

    async def _bot(self, method: str, path: str, *, json=None, params=None, discord_user_id=None):
        r = await self._c().request(
            method, f"{self._base}{path}", json=json, params=params,
            headers=self._bot_headers(discord_user_id),
        )
        if r.status_code >= 400:
            raise ApiError(r.status_code, _extract_message(r))
        if r.status_code == 204 or not r.content:
            return None
        body = r.json()
        return body.get("data") if isinstance(body, dict) else body

    # ── 公開 参照系 ────────────────────────────────────────────────────────
    async def get_tournament(self, tid: str):
        return await self._get(f"/api/v1/tournaments/{tid}")

    async def list_tournaments(self, **params):
        return await self._get("/api/v1/tournaments", {k: v for k, v in params.items() if v is not None}) or []

    async def get_bracket(self, tid: str):
        return await self._get(f"/api/v1/tournaments/{tid}/bracket")

    async def get_rankings(self, tid: str, limit: int = 16):
        return await self._get(f"/api/v1/rankings/tournaments/{tid}", {"limit": limit}) or []

    async def get_player(self, pid: str):
        return await self._get(f"/api/v1/players/{pid}")

    async def list_players(self, **params):
        return await self._get("/api/v1/players", {k: v for k, v in params.items() if v is not None}) or []

    async def get_player_career(self, pid: str):
        return await self._get(f"/api/v1/players/{pid}/career")

    async def get_player_achievements(self, pid: str):
        return await self._get(f"/api/v1/players/{pid}/achievements") or []

    async def get_player_rating_history(self, pid: str, game: str = "VALORANT"):
        return await self._get(f"/api/v1/players/{pid}/rating-history", {"game": game}) or []

    async def get_team(self, tid: str):
        return await self._get(f"/api/v1/teams/{tid}")

    async def list_teams(self, **params):
        return await self._get("/api/v1/teams", {k: v for k, v in params.items() if v is not None}) or []

    async def get_team_members(self, tid: str):
        return await self._get(f"/api/v1/teams/{tid}/members") or []

    async def get_team_career(self, tid: str):
        return await self._get(f"/api/v1/teams/{tid}/career")

    async def get_team_achievements(self, tid: str):
        return await self._get(f"/api/v1/teams/{tid}/achievements") or []

    async def get_team_rivals(self, tid: str):
        return await self._get(f"/api/v1/teams/{tid}/rivals") or []

    async def get_match(self, mid: str):
        return await self._get(f"/api/v1/matches/{mid}")

    # analytics
    async def get_player_stats(self, pid: str, game: str, period_type: str = "all_time"):
        return await self._get(
            f"/api/v1/analytics/players/{pid}/stats", {"game": game, "period_type": period_type}
        )

    async def get_map_stats(self, game: str, tournament_id: str | None = None):
        return await self._get(
            "/api/v1/analytics/maps/stats",
            {"game": game, **({"tournament_id": tournament_id} if tournament_id else {})},
        ) or []

    async def get_compositions(self, game: str, **params):
        p = {"game": game, **{k: v for k, v in params.items() if v is not None}}
        return await self._get("/api/v1/analytics/compositions", p) or []

    async def get_tournament_summary(self, tid: str):
        return await self._get(f"/api/v1/analytics/tournaments/{tid}/summary")

    # scout
    async def scout_players(self, **params):
        return await self._get("/api/v1/scout/players", {k: v for k, v in params.items() if v is not None}) or []

    async def scout_teams(self, **params):
        return await self._get("/api/v1/scout/teams", {k: v for k, v in params.items() if v is not None}) or []

    async def list_recruitment(self, **params):
        return await self._get("/api/v1/scout/recruitment", {k: v for k, v in params.items() if v is not None}) or []

    async def recommend_teams(self, player_id: str, limit: int = 10):
        return await self._get(f"/api/v1/scout/recommendations/teams/{player_id}", {"limit": limit}) or []

    async def recommend_players(self, team_id: str, limit: int = 10):
        return await self._get(f"/api/v1/scout/recommendations/players/{team_id}", {"limit": limit}) or []

    # riot
    async def get_riot_profile(self, pid: str):
        return await self._get(f"/api/v1/riot/profile/{pid}")

    # ── /bot/* 操作系（代理実行） ─────────────────────────────────────────────
    async def resolve(self, discord_user_id):
        return await self._bot("GET", "/api/v1/bot/resolve", discord_user_id=discord_user_id)

    async def link(self, code, discord_user_id, discord_username=None):
        return await self._bot("POST", "/api/v1/bot/link",
                               json={"code": code, "discord_username": discord_username},
                               discord_user_id=discord_user_id)

    async def unlink(self, discord_user_id):
        return await self._bot("POST", "/api/v1/bot/unlink", discord_user_id=discord_user_id)

    async def change_tournament_status(self, tid, status, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/tournaments/{tid}/status",
                               json={"status": status}, discord_user_id=discord_user_id)

    async def regenerate_bracket(self, tid, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/tournaments/{tid}/bracket",
                               discord_user_id=discord_user_id)

    async def self_check_in(self, tid, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/tournaments/{tid}/check-in",
                               discord_user_id=discord_user_id)

    async def check_in_all(self, tid, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/tournaments/{tid}/check-in-all",
                               discord_user_id=discord_user_id)

    async def check_in_status(self, tid):
        return await self._bot("GET", f"/api/v1/bot/tournaments/{tid}/check-in-status")

    async def report_result(self, match_id, winner_id, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/matches/{match_id}/report",
                               json={"winner_id": winner_id}, discord_user_id=discord_user_id)

    async def confirm_result(self, match_id, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/matches/{match_id}/confirm",
                               discord_user_id=discord_user_id)

    async def dispute_result(self, match_id, reason, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/matches/{match_id}/dispute",
                               json={"reason": reason}, discord_user_id=discord_user_id)

    async def forfeit_match(self, match_id, winner_id, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/matches/{match_id}/forfeit",
                               json={"winner_id": winner_id}, discord_user_id=discord_user_id)

    async def reopen_match(self, match_id, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/matches/{match_id}/reopen",
                               discord_user_id=discord_user_id)

    async def my_matches(self, discord_user_id, limit: int = 10):
        return await self._bot("GET", f"/api/v1/bot/users/{discord_user_id}/matches",
                               params={"limit": limit}, discord_user_id=discord_user_id) or []

    async def my_notifications(self, discord_user_id, unread: bool = False, limit: int = 10):
        return await self._bot("GET", f"/api/v1/bot/users/{discord_user_id}/notifications",
                               params={"unread": str(unread).lower(), "limit": limit},
                               discord_user_id=discord_user_id)

    async def set_looking(self, player_id, looking: bool, discord_user_id):
        return await self._bot("POST", f"/api/v1/bot/players/{player_id}/looking",
                               json={"looking": looking}, discord_user_id=discord_user_id)

    # monitoring
    async def ingest_metrics(self, items: list[dict]):
        return await self._bot("POST", "/api/v1/bot/metrics", json={"items": items})

    async def log_error(self, payload: dict):
        return await self._bot("POST", "/api/v1/bot/errors", json=payload)

    # 既存: イベントコンシューマがセットアップ完了を通知（互換維持）
    async def update_discord_server(self, discord_server_id: str, payload: dict) -> bool:
        try:
            await self._bot("PATCH", f"/api/v1/discord/internal/{discord_server_id}", json=payload)
            return True
        except ApiError:
            return False


api_client = PlatformAPIClient()
