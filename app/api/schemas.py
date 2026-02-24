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
    sent_at: str


class DeviceSnapshotOut(BaseModel):
    device_id: str
    telemetry: dict[str, Any] | None = None
    command: dict[str, Any] | None = None


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


class AckResponse(BaseModel):
    status: str
    timestamp: datetime


class RequirementCoverageOut(BaseModel):
    requirement_id: str
    title: str
    endpoint: str
    implemented: bool


class RequirementDetailOut(RequirementCoverageOut):
    notes: str


class StrategicFeatureCoverageOut(BaseModel):
    feature: str
    status: str
    evidence: str


class StrategicCoverageReportOut(BaseModel):
    overall_result: str
    matrix: list[StrategicFeatureCoverageOut]
    next_steps: list[str]


class ProductModuleCoverageOut(BaseModel):
    slug: str
    title: str
    stage: str
    status: str
    implemented: bool
    existing_endpoints: list[str] = Field(default_factory=list)
    endpoint: str
    notes: str


class ProductReadinessReportOut(BaseModel):
    summary: str
    modules: list[ProductModuleCoverageOut]
