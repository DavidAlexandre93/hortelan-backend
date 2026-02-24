import logging

from app.core.exceptions import TransientIntegrationError
from app.domain.entities.models import IrrigationCommand
from app.domain.ports.interfaces import CachePort, DeviceCommandPort

logger = logging.getLogger(__name__)


class DispatchIrrigationCommandUseCase:
    def __init__(self, command_port: DeviceCommandPort, cache: CachePort) -> None:
        self.command_port = command_port
        self.cache = cache

    async def execute(self, command: IrrigationCommand) -> None:
        await self.command_port.send_command(command)

        try:
            await self.cache.set(
                f'command:{command.device_id}',
                {
                    'device_id': command.device_id,
                    'action': command.action,
                    'duration_seconds': command.duration_seconds,
                    'created_at': command.created_at.isoformat(),
                },
                ttl_seconds=120,
            )
        except TransientIntegrationError:
            logger.warning('Falha transitória ao atualizar cache de comando.')
