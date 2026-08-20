from dataclasses import asdict
from typing import Any

from pymongo import AsyncMongoClient

from app.core.settings import Settings
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import DocumentTelemetryRepositoryPort


class MongoTelemetryRepository(DocumentTelemetryRepositoryPort):
    def __init__(self, settings: Settings) -> None:
        timeout_ms = int(settings.external_timeout_seconds * 1_000)
        self.client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
            settings.mongo_url,
            serverSelectionTimeoutMS=timeout_ms,
            timeoutMS=timeout_ms,
        )
        self.collection = self.client[settings.mongo_db_name]['telemetry_readings']

    async def save(self, reading: TelemetryReading) -> None:
        await self.collection.insert_one(asdict(reading))
