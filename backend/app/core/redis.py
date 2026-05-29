import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


class RedisCache:
    """キャッシュ操作のユーティリティクラス。"""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def get(self, key: str) -> Any | None:
        value = await self._redis.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._redis.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        keys = await self._redis.keys(pattern)
        if keys:
            return await self._redis.delete(*keys)
        return 0

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(key))

    async def acquire_lock(self, lock_key: str, ttl: int = 10) -> bool:
        """分散ロック取得。成功すれば True。"""
        result = await self._redis.set(lock_key, "1", nx=True, ex=ttl)
        return result is True

    async def release_lock(self, lock_key: str) -> None:
        await self._redis.delete(lock_key)

    async def increment(self, key: str, ttl: int | None = None) -> int:
        count = await self._redis.incr(key)
        if ttl and count == 1:
            await self._redis.expire(key, ttl)
        return count

    async def publish(self, channel: str, message: Any) -> None:
        await self._redis.publish(channel, json.dumps(message, default=str))


# キャッシュキー定数
class CacheKeys:
    TOURNAMENT_LIST = "cache:tournament:list:{game}:{status}:{cursor}"
    TOURNAMENT_DETAIL = "cache:tournament:{id}"
    BRACKET = "cache:bracket:{tournament_id}"
    RANKING_TOURNAMENT = "cache:ranking:tournament:{id}"
    RANKING_GLOBAL = "cache:ranking:global:{game}"
    PLAYER_STATS = "cache:player:{id}:stats:{period}"
    TEAM_STATS = "cache:team:{id}:stats:{period}"
    MAP_STATS = "cache:map:stats:{game}"
    COMPOSITION_STATS = "cache:composition:{game}:{map_id}"
    MATCH_DETAIL = "cache:match:{id}"
    RATE_LIMIT = "ratelimit:{user_id}:{endpoint}"
    REFRESH_TOKEN = "refresh:{user_id}:{jti}"
    WS_MATCH_CHANNEL = "ws:match:{match_id}"
    WS_BRACKET_CHANNEL = "ws:bracket:{tournament_id}"
    LOCK_MATCH_RESULT = "lock:match:{match_id}:result"


# TTL定数（秒）
class CacheTTL:
    TOURNAMENT_LIST = 300       # 5分
    TOURNAMENT_DETAIL = 300     # 5分
    BRACKET = 60                # 1分（試合中は短く）
    RANKING = 900               # 15分
    PLAYER_STATS = 1800         # 30分
    TEAM_STATS = 1800           # 30分
    MAP_STATS = 3600            # 1時間
    COMPOSITION_STATS = 3600    # 1時間
    MATCH_DETAIL = 60           # 1分（リアルタイム更新のため短く）
    REFRESH_TOKEN = 60 * 60 * 24 * 7  # 7日
