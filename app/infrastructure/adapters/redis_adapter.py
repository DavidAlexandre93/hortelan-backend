import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.exceptions import TransientIntegrationError
from app.core.settings import Settings
from app.domain.ports.interfaces import CachePort

logger = logging.getLogger(__name__)


class RedisCacheAdapter(CachePort):
    def __init__(self, settings: Settings) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)
        self._fallback_store: dict[str, dict[str, Any]] = {}

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
        self._fallback_store[key] = value
        try:
            await self.client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception as exc:
            logger.warning('Falha ao gravar no Redis; mantendo fallback em memória')
            raise TransientIntegrationError('Falha ao gravar cache no Redis') from exc

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            value = await self.client.get(key)
            if value:
                parsed = json.loads(value)
                self._fallback_store[key] = parsed
                return parsed
        except Exception:
            logger.warning('Falha ao ler Redis; retornando fallback em memória')
            return self._fallback_store.get(key)

        return self._fallback_store.get(key)
