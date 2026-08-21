import asyncio
import json
import logging
from dataclasses import asdict

from aiokafka import AIOKafkaProducer

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.exceptions import TransientIntegrationError
from app.core.resilience import ExternalCallPolicy
from app.core.settings import Settings
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import TelemetryPublisherPort

logger = logging.getLogger(__name__)


class KafkaTelemetryAdapter(TelemetryPublisherPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._producer: AIOKafkaProducer | None = None
        self._policy = ExternalCallPolicy.from_settings(
            'kafka_telemetry', 'kafka.publish_telemetry', settings
        )
        self._circuit_breaker = self._policy.circuit_breaker

    async def _producer_or_create(self) -> AIOKafkaProducer | None:
        if self._producer is None:
            try:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.settings.kafka_bootstrap_servers
                )
                async with asyncio.timeout(self.settings.external_timeout_seconds):
                    await self._producer.start()
            except Exception as exc:
                self._producer = None
                logger.exception('Falha ao inicializar produtor Kafka')
                raise TransientIntegrationError('Falha ao inicializar Kafka producer') from exc
        return self._producer

    async def publish_telemetry(self, reading: TelemetryReading) -> None:
        try:
            started = self._policy.start()
        except CircuitBreakerOpenError as exc:
            raise TransientIntegrationError('Circuit breaker aberto para Kafka') from exc

        producer = await self._producer_or_create()
        if producer is None:
            self._circuit_breaker.on_failure()
            raise TransientIntegrationError('Producer Kafka indisponível')

        payload = json.dumps(asdict(reading), default=str).encode('utf-8')
        try:
            async with asyncio.timeout(self.settings.external_timeout_seconds):
                await producer.send_and_wait(self.settings.kafka_topic_telemetry, payload)
        except Exception as exc:
            self._policy.failure(started)
            logger.exception('Falha ao publicar telemetria no Kafka')
            raise TransientIntegrationError('Falha ao publicar telemetria no Kafka') from exc
        else:
            self._policy.success(started)

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
