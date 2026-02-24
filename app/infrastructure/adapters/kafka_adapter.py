import json
from dataclasses import asdict

from aiokafka import AIOKafkaProducer

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from app.core.settings import Settings
from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import TelemetryPublisherPort


class KafkaTelemetryAdapter(TelemetryPublisherPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._producer: AIOKafkaProducer | None = None
        self._disabled = False
        self._circuit_breaker = CircuitBreaker(
            name='kafka_telemetry',
            config=CircuitBreakerConfig(
                failure_rate_threshold=settings.circuit_breaker_failure_rate_threshold,
                sliding_window_size=settings.circuit_breaker_sliding_window_size,
                minimum_number_of_calls=settings.circuit_breaker_minimum_calls,
                wait_duration_in_open_state_seconds=settings.circuit_breaker_wait_duration_seconds,
                permitted_calls_in_half_open_state=settings.circuit_breaker_permitted_half_open_calls,
            ),
        )

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
        try:
            self._circuit_breaker.call_permitted()
        except CircuitBreakerOpenError:
            return

        producer = await self._producer_or_create()
        if producer is None:
            self._circuit_breaker.on_failure()
            return

        payload = json.dumps(asdict(reading), default=str).encode('utf-8')
        try:
            await producer.send_and_wait(self.settings.kafka_topic_telemetry, payload)
            self._circuit_breaker.on_success()
        except Exception:
            self._circuit_breaker.on_failure()
            return

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
