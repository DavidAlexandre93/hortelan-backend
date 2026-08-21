import asyncio
import json
import logging
from typing import Any

import boto3

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.exceptions import InfrastructureError
from app.core.resilience import ExternalCallPolicy
from app.core.settings import Settings
from app.domain.entities.models import IrrigationCommand
from app.domain.ports.interfaces import DeviceCommandPort

logger = logging.getLogger(__name__)


class AwsIotCoreAdapter(DeviceCommandPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any | None = None
        self._policy = ExternalCallPolicy.from_settings('aws_iot', 'aws_iot.publish', settings)
        self._circuit_breaker = self._policy.circuit_breaker

    async def send_command(self, command: IrrigationCommand) -> None:
        topic = f'{self.settings.aws_iot_topic_prefix}/{command.device_id}/commands'
        payload = json.dumps(
            {
                'action': command.action,
                'duration_seconds': command.duration_seconds,
                'created_at': command.created_at.isoformat(),
                'idempotency_key': command.idempotency_key,
            }
        )

        try:
            started = self._policy.start()
        except CircuitBreakerOpenError as exc:
            raise InfrastructureError('Circuit breaker aberto para AWS IoT') from exc

        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    self._client_or_create().publish, topic=topic, qos=1, payload=payload
                ),
                timeout=self.settings.external_timeout_seconds,
            )
        except Exception as exc:
            self._policy.failure(started)
            logger.exception('Falha ao enviar comando para AWS IoT')
            raise InfrastructureError('Falha ao publicar comando no AWS IoT') from exc
        else:
            self._policy.success(started)

    def _client_or_create(self) -> Any:
        if self._client is None:
            self._client = boto3.client(
                'iot-data',
                region_name=self.settings.aws_region,
                endpoint_url=(
                    f'https://{self.settings.aws_iot_endpoint}'
                    if self.settings.aws_iot_endpoint
                    else None
                ),
            )
        return self._client

    async def close(self) -> None:
        self._client = None
