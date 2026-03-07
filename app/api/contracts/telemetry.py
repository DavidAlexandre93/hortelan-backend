from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TelemetryIn(BaseModel):
    device_id: str = Field(description='Identificador único do dispositivo IoT.')
    moisture: float = Field(ge=0, le=100, description='Umidade do solo em percentual (0 a 100).')
    temperature: float = Field(description='Temperatura medida pelo sensor, em graus Celsius.')
    ph: float = Field(description='pH estimado do solo.')
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        'json_schema_extra': {
            'example': {
                'device_id': 'esp32-greenhouse-01',
                'moisture': 45.2,
                'temperature': 24.8,
                'ph': 6.3,
                'metadata': {'battery': 88, 'firmware': '1.0.4'},
            }
        }
    }


class TelemetryOut(BaseModel):
    device_id: str
    moisture: float
    temperature: float
    ph: float
    captured_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
