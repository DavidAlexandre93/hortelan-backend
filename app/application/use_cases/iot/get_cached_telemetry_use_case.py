from typing import Any

from app.domain.ports.interfaces import CachePort


class GetCachedTelemetryUseCase:
    def __init__(self, cache: CachePort) -> None:
        self.cache = cache

    async def execute(self, device_id: str) -> dict[str, Any] | None:
        return await self.cache.get(f'telemetry:{device_id}')
