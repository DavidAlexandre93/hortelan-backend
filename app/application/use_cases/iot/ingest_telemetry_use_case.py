import logging
from dataclasses import asdict

from app.core.exceptions import TransientIntegrationError
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import (
    CachePort,
    DocumentTelemetryRepositoryPort,
    RelationalTelemetryRepositoryPort,
    TelemetryPublisherPort,
)

logger = logging.getLogger(__name__)


class IngestTelemetryUseCase:
    def __init__(
        self,
        telemetry_publisher: TelemetryPublisherPort,
        cache: CachePort,
        relational_repo: RelationalTelemetryRepositoryPort,
        document_repo: DocumentTelemetryRepositoryPort,
    ) -> None:
        self.telemetry_publisher = telemetry_publisher
        self.cache = cache
        self.relational_repo = relational_repo
        self.document_repo = document_repo

    async def execute(self, reading: TelemetryReading) -> None:
        await self.relational_repo.save(reading)
        await self.document_repo.save(reading)

        try:
            await self.telemetry_publisher.publish_telemetry(reading)
        except TransientIntegrationError:
            logger.warning('Falha transitória ao publicar telemetria; persistência local mantida.')

        try:
            await self.cache.set(f'telemetry:{reading.device_id}', asdict(reading), ttl_seconds=600)
        except TransientIntegrationError:
            logger.warning('Falha transitória ao atualizar cache de telemetria.')
