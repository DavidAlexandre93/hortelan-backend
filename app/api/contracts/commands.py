from pydantic import Field

from app.api.contracts.base import ApiModel, DeviceId, UtcDatetime
from app.domain.entities.models import IrrigationAction


class IrrigationCommandIn(ApiModel):
    device_id: DeviceId = Field(description='Identificador do dispositivo que recebera o comando.')
    action: IrrigationAction = Field(
        default=IrrigationAction.IRRIGATE,
        description='Acao permitida no atuador.',
    )
    duration_seconds: int = Field(gt=0, le=7200, description='Duracao do comando em segundos.')

    model_config = {
        **ApiModel.model_config,
        'json_schema_extra': {
            'example': {
                'device_id': 'esp32-greenhouse-01',
                'action': 'irrigate',
                'duration_seconds': 120,
            }
        },
    }


class CommandSnapshotOut(ApiModel):
    device_id: DeviceId
    action: IrrigationAction
    duration_seconds: int = Field(gt=0, le=7200)
    sent_at: UtcDatetime
