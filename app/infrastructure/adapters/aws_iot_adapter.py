import json

import boto3

from app.core.settings import Settings
from app.domain.entities.models import IrrigationCommand
from app.domain.ports.interfaces import DeviceCommandPort


class AwsIotCoreAdapter(DeviceCommandPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = boto3.client(
            'iot-data',
            region_name=settings.aws_region,
            endpoint_url=f"https://{settings.aws_iot_endpoint}" if settings.aws_iot_endpoint else None,
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
            self.client.publish(topic=topic, qos=1, payload=payload)
        except Exception:
            return
