from typing import Any

from pydantic import Field

from app.api.contracts.base import ApiModel, RecordId


class LedgerRecordIn(ApiModel):
    record_id: RecordId = Field(description='Identificador unico do evento no ledger.')
    payload: dict[str, Any] = Field(
        min_length=1,
        max_length=64,
        description='Conteudo JSON serializavel do evento registrado.',
    )

    model_config = {
        **ApiModel.model_config,
        'json_schema_extra': {
            'example': {
                'record_id': 'evt-2026-02-telemetry-001',
                'payload': {'type': 'telemetry_ingested', 'device_id': 'esp32-greenhouse-01'},
            }
        },
    }
