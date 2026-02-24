import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.exceptions import TransientIntegrationError
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from app.core.settings import Settings
from app.domain.ports.interfaces import CachePort

logger = logging.getLogger(__name__)


class RedisCacheAdapter(CachePort):
    def __init__(self, settings: Settings) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)
        self._fallback_store: dict[str, dict[str, Any]] = {}
        self._circuit_breaker = CircuitBreaker(
            name='redis_cache',
            config=CircuitBreakerConfig(
                failure_rate_threshold=settings.circuit_breaker_failure_rate_threshold,
                sliding_window_size=settings.circuit_breaker_sliding_window_size,
                minimum_number_of_calls=settings.circuit_breaker_minimum_calls,
                wait_duration_in_open_state_seconds=settings.circuit_breaker_wait_duration_seconds,
                permitted_calls_in_half_open_state=settings.circuit_breaker_permitted_half_open_calls,
            ),
        )

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
        self._fallback_store[key] = value
        try:
            self._circuit_breaker.call_permitted()
        except CircuitBreakerOpenError:
            return

        try:
            await self.client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception as exc:
            logger.warning('Falha ao gravar no Redis; mantendo fallback em memória')
            raise TransientIntegrationError('Falha ao gravar cache no Redis') from exc
            self._circuit_breaker.on_success()
        except Exception:
            self._circuit_breaker.on_failure()
            return

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            self._circuit_breaker.call_permitted()
        except CircuitBreakerOpenError:
            return self._fallback_store.get(key)

        try:
            value = await self.client.get(key)
            if value:
                parsed = json.loads(value)
                self._fallback_store[key] = parsed
                self._circuit_breaker.on_success()
                return parsed
            self._circuit_breaker.on_success()
        except Exception:
            logger.warning('Falha ao ler Redis; retornando fallback em memória')
            self._circuit_breaker.on_failure()
            return self._fallback_store.get(key)

        return self._fallback_store.get(key)
