import json
from dataclasses import asdict

from aiokafka import AIOKafkaProducer

from app.core.settings import Settings
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import TelemetryPublisherPort


class KafkaTelemetryAdapter(TelemetryPublisherPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def _producer_or_create(self) -> AIOKafkaProducer:
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.settings.kafka_bootstrap_servers)
            await self._producer.start()
        return self._producer

    async def publish_telemetry(self, reading: TelemetryReading) -> None:
        producer = await self._producer_or_create()
        payload = json.dumps(asdict(reading), default=str).encode('utf-8')
        await producer.send_and_wait(self.settings.kafka_topic_telemetry, payload)

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
