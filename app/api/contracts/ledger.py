from typing import Any

from pydantic import BaseModel, Field


class LedgerRecordIn(BaseModel):
    record_id: str = Field(description='Identificador único do evento no ledger.')
    payload: dict[str, Any] = Field(description='Conteúdo serializável do evento registrado.')

    model_config = {
        'json_schema_extra': {
            'example': {
                'record_id': 'evt-2026-02-telemetry-001',
                'payload': {'type': 'telemetry_ingested', 'device_id': 'esp32-greenhouse-01'},
            }
        }
    }
