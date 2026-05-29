import asyncio
import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis import CacheKeys, get_redis

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """WebSocket 接続管理。"""

    def __init__(self):
        # match_id → WebSocket のセット
        self._match_connections: dict[str, set[WebSocket]] = {}
        # tournament_id → WebSocket のセット
        self._bracket_connections: dict[str, set[WebSocket]] = {}

    def add_match(self, match_id: str, ws: WebSocket) -> None:
        self._match_connections.setdefault(match_id, set()).add(ws)

    def remove_match(self, match_id: str, ws: WebSocket) -> None:
        if match_id in self._match_connections:
            self._match_connections[match_id].discard(ws)
            if not self._match_connections[match_id]:
                del self._match_connections[match_id]

    def add_bracket(self, tournament_id: str, ws: WebSocket) -> None:
        self._bracket_connections.setdefault(tournament_id, set()).add(ws)

    def remove_bracket(self, tournament_id: str, ws: WebSocket) -> None:
        if tournament_id in self._bracket_connections:
            self._bracket_connections[tournament_id].discard(ws)
            if not self._bracket_connections[tournament_id]:
                del self._bracket_connections[tournament_id]

    async def broadcast_match(self, match_id: str, message: dict) -> None:
        conns = self._match_connections.get(match_id, set()).copy()
        dead = set()
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.remove_match(match_id, ws)

    async def broadcast_bracket(self, tournament_id: str, message: dict) -> None:
        conns = self._bracket_connections.get(tournament_id, set()).copy()
        dead = set()
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.remove_bracket(tournament_id, ws)


manager = ConnectionManager()


async def redis_pubsub_listener(redis: aioredis.Redis) -> None:
    """Redis Pub/Sub を購読してWebSocketへブロードキャストするバックグラウンドタスク。"""
    pubsub = redis.pubsub()
    await pubsub.psubscribe("ws:match:*", "ws:bracket:*")

    async for message in pubsub.listen():
        if message["type"] not in ("pmessage", "message"):
            continue
        channel: str = message.get("channel", "")
        data = message.get("data", "")
        if not data:
            continue

        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue

        if channel.startswith("ws:match:"):
            match_id = channel.removeprefix("ws:match:")
            await manager.broadcast_match(match_id, payload)
        elif channel.startswith("ws:bracket:"):
            tournament_id = channel.removeprefix("ws:bracket:")
            await manager.broadcast_bracket(tournament_id, payload)


@router.websocket("/ws/matches/{match_id}")
async def match_websocket(websocket: WebSocket, match_id: uuid.UUID):
    await websocket.accept()
    match_id_str = str(match_id)
    manager.add_match(match_id_str, websocket)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # 30秒無通信でpingを送信してコネクション確認
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.remove_match(match_id_str, websocket)


@router.websocket("/ws/brackets/{tournament_id}")
async def bracket_websocket(websocket: WebSocket, tournament_id: uuid.UUID):
    await websocket.accept()
    tournament_id_str = str(tournament_id)
    manager.add_bracket(tournament_id_str, websocket)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.remove_bracket(tournament_id_str, websocket)
