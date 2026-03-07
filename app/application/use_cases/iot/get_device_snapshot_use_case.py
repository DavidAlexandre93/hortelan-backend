from typing import Any

from app.domain.ports.interfaces import CachePort


class GetDeviceSnapshotUseCase:
    def __init__(self, cache: CachePort) -> None:
        self.cache = cache

    async def execute(self, device_id: str) -> dict[str, Any]:
        telemetry = await self.cache.get(f'telemetry:{device_id}')
        command = await self.cache.get(f'command:{device_id}')
        return {'device_id': device_id, 'telemetry': telemetry, 'command': command}
