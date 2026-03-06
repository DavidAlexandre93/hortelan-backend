from datetime import datetime

from pydantic import BaseModel, Field


class IrrigationCommandIn(BaseModel):
    device_id: str = Field(description='Identificador do dispositivo que receberá o comando.')
    action: str = Field(default='irrigate', description='Ação desejada no atuador.')
    duration_seconds: int = Field(gt=0, le=7200, description='Duração do comando em segundos (máx. 2h).')

    model_config = {
        'json_schema_extra': {
            'example': {'device_id': 'esp32-greenhouse-01', 'action': 'irrigate', 'duration_seconds': 120}
        }
    }


class CommandSnapshotOut(BaseModel):
    device_id: str
    action: str
    duration_seconds: int
    sent_at: datetime
