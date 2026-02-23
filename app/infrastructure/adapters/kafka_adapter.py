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
        self._disabled = False

    async def _producer_or_create(self) -> AIOKafkaProducer | None:
        if self._disabled:
            return None

        if self._producer is None:
            try:
                self._producer = AIOKafkaProducer(bootstrap_servers=self.settings.kafka_bootstrap_servers)
                await self._producer.start()
            except Exception:
                self._disabled = True
                self._producer = None
                return None
        return self._producer

    async def publish_telemetry(self, reading: TelemetryReading) -> None:
        producer = await self._producer_or_create()
        if producer is None:
            return

        payload = json.dumps(asdict(reading), default=str).encode('utf-8')
        try:
            await producer.send_and_wait(self.settings.kafka_topic_telemetry, payload)
        except Exception:
            return

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
