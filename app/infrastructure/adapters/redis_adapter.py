import json
from typing import Any

from redis.asyncio import Redis

from app.core.settings import Settings
from app.domain.ports.interfaces import CachePort


class RedisCacheAdapter(CachePort):
    def __init__(self, settings: Settings) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
        await self.client.set(key, json.dumps(value, default=str), ex=ttl_seconds)

    async def get(self, key: str) -> dict[str, Any] | None:
        value = await self.client.get(key)
        return json.loads(value) if value else None
