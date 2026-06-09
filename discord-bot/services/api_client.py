"""プラットフォームAPIクライアント（Bot Token認証）"""

import httpx

from config import config


class PlatformAPIClient:
    def __init__(self):
        self._base = config.API_BASE_URL
        self._token = config.BOT_API_TOKEN

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def get_tournament(self, tournament_id: str) -> dict | None:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self._base}/api/v1/tournaments/{tournament_id}", headers=self._headers())
            return res.json().get("data") if res.status_code == 200 else None

    async def get_bracket(self, tournament_id: str) -> dict | None:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self._base}/api/v1/tournaments/{tournament_id}/bracket", headers=self._headers())
            return res.json().get("data") if res.status_code == 200 else None

    async def report_result(self, match_id: str, winner_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base}/api/v1/matches/{match_id}/result",
                json={"winner_id": winner_id},
                headers=self._headers(),
            )
            return res.status_code in (200, 204)

    async def update_discord_server(self, discord_server_id: str, payload: dict) -> bool:
        """セットアップ完了をプラットフォームへ通知（role_ids/category_ids保存）"""
        async with httpx.AsyncClient() as client:
            res = await client.patch(
                f"{self._base}/api/v1/discord/internal/{discord_server_id}",
                json=payload,
                headers=self._headers(),
            )
            return res.status_code in (200, 204)


api_client = PlatformAPIClient()
