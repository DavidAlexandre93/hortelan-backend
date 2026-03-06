import asyncio
import json
import logging
import time

import boto3

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from app.core.observability import metrics_registry
from app.core.exceptions import InfrastructureError
from app.core.settings import Settings
from app.domain.entities.models import IrrigationCommand
from app.domain.ports.interfaces import DeviceCommandPort

logger = logging.getLogger(__name__)


class AwsIotCoreAdapter(DeviceCommandPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = boto3.client(
            'iot-data',
            region_name=settings.aws_region,
            endpoint_url=f"https://{settings.aws_iot_endpoint}" if settings.aws_iot_endpoint else None,
        )
        self._circuit_breaker = CircuitBreaker(
            name='aws_iot',
            config=CircuitBreakerConfig(
                failure_rate_threshold=settings.circuit_breaker_failure_rate_threshold,
                sliding_window_size=settings.circuit_breaker_sliding_window_size,
                minimum_number_of_calls=settings.circuit_breaker_minimum_calls,
                wait_duration_in_open_state_seconds=settings.circuit_breaker_wait_duration_seconds,
                permitted_calls_in_half_open_state=settings.circuit_breaker_permitted_half_open_calls,
            ),
        )

    async def send_command(self, command: IrrigationCommand) -> None:
        topic = f"{self.settings.aws_iot_topic_prefix}/{command.device_id}/commands"
        payload = json.dumps(
            {
                'action': command.action,
                'duration_seconds': command.duration_seconds,
                'created_at': command.created_at.isoformat(),
            }
        )

        try:
            self._circuit_breaker.call_permitted()
        except CircuitBreakerOpenError:
            raise InfrastructureError('Circuit breaker aberto para AWS IoT')

        started = time.perf_counter()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self.client.publish, topic=topic, qos=1, payload=payload),
                timeout=self.settings.external_timeout_seconds,
            )
        except Exception as exc:
            self._circuit_breaker.on_failure()
            metrics_registry.track_external_call('aws_iot.publish', time.perf_counter() - started, ok=False)
            logger.exception('Falha ao enviar comando para AWS IoT')
            raise InfrastructureError('Falha ao publicar comando no AWS IoT') from exc
        else:
            self._circuit_breaker.on_success()
            metrics_registry.track_external_call('aws_iot.publish', time.perf_counter() - started, ok=True)
