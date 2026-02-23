from dataclasses import asdict

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.settings import Settings
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import DocumentTelemetryRepositoryPort


class MongoTelemetryRepository(DocumentTelemetryRepositoryPort):
    def __init__(self, settings: Settings) -> None:
        self.client = AsyncIOMotorClient(settings.mongo_url)
        self.collection = self.client[settings.mongo_db_name]['telemetry_readings']

    async def save(self, reading: TelemetryReading) -> None:
        await self.collection.insert_one(asdict(reading))
