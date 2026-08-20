from typing import Any

from pydantic import Field

from app.api.contracts.base import ApiModel, DeviceId, UtcDatetime


class TelemetryIn(ApiModel):
    device_id: DeviceId = Field(description='Identificador unico do dispositivo IoT.')
    moisture: float = Field(ge=0, le=100, description='Umidade do solo em percentual.')
    temperature: float = Field(ge=-50, le=100, description='Temperatura em graus Celsius.')
    ph: float = Field(ge=0, le=14, description='pH estimado do solo.')
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=32)

    model_config = {
        **ApiModel.model_config,
        'json_schema_extra': {
            'example': {
                'device_id': 'esp32-greenhouse-01',
                'moisture': 45.2,
                'temperature': 24.8,
                'ph': 6.3,
                'metadata': {'battery': 88, 'firmware': '1.0.4'},
            }
        },
    }


class TelemetryOut(ApiModel):
    device_id: DeviceId
    moisture: float = Field(ge=0, le=100)
    temperature: float = Field(ge=-50, le=100)
    ph: float = Field(ge=0, le=14)
    captured_at: UtcDatetime
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=32)
