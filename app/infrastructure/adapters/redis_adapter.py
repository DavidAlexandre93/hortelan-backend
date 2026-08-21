import asyncio
import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.exceptions import TransientIntegrationError
from app.core.resilience import ExternalCallPolicy
from app.core.settings import Settings
from app.domain.ports.interfaces import CachePort

logger = logging.getLogger(__name__)


class RedisCacheAdapter(CachePort):
    def __init__(self, settings: Settings) -> None:
        self._timeout_seconds = settings.external_timeout_seconds
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)
        self._fallback_store: dict[str, dict[str, Any]] = {}
        self._policy = ExternalCallPolicy.from_settings('redis_cache', 'redis', settings)
        self._circuit_breaker = self._policy.circuit_breaker

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
        self._fallback_store[key] = value
        try:
            started = self._policy.start()
        except CircuitBreakerOpenError:
            return
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await self.client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception as exc:
            self._policy.failure(started)
            logger.warning('Falha ao gravar no Redis; mantendo fallback em memória')
            raise TransientIntegrationError('Falha ao gravar cache no Redis') from exc
        else:
            self._policy.success(started)

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            started = self._policy.start()
        except CircuitBreakerOpenError:
            return self._fallback_store.get(key)
        try:
            async with asyncio.timeout(self._timeout_seconds):
                value = await self.client.get(key)
        except Exception:
            logger.warning('Falha ao ler Redis; retornando fallback em memória')
            self._policy.failure(started)
            return self._fallback_store.get(key)

        self._policy.success(started)
        if value:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                logger.warning('Valor Redis ignorado por conter JSON invalido')
                return self._fallback_store.get(key)
            if not isinstance(parsed, dict):
                logger.warning('Valor Redis ignorado por nao ser um objeto JSON')
                return self._fallback_store.get(key)
            self._fallback_store[key] = parsed
            return parsed
        return self._fallback_store.get(key)

    async def close(self) -> None:
        await self.client.aclose()
