import json
import logging
from dataclasses import asdict

from aiokafka import AIOKafkaProducer

from app.core.settings import Settings
from app.core.exceptions import TransientIntegrationError
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import TelemetryPublisherPort

logger = logging.getLogger(__name__)


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
            except Exception as exc:
                self._disabled = True
                self._producer = None
                logger.exception('Falha ao inicializar produtor Kafka')
                raise TransientIntegrationError('Falha ao inicializar Kafka producer') from exc
        return self._producer

    async def publish_telemetry(self, reading: TelemetryReading) -> None:
        producer = await self._producer_or_create()
        if producer is None:
            raise TransientIntegrationError('Producer Kafka indisponível')

        payload = json.dumps(asdict(reading), default=str).encode('utf-8')
        try:
            await producer.send_and_wait(self.settings.kafka_topic_telemetry, payload)
        except Exception as exc:
            logger.exception('Falha ao publicar telemetria no Kafka')
            raise TransientIntegrationError('Falha ao publicar telemetria no Kafka') from exc

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
