from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TelemetryIn(BaseModel):
    device_id: str
    moisture: float = Field(ge=0, le=100)
    temperature: float
    ph: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class IrrigationCommandIn(BaseModel):
    device_id: str
    action: str = Field(default='irrigate')
    duration_seconds: int = Field(gt=0, le=7200)


class LedgerRecordIn(BaseModel):
    record_id: str
    payload: dict[str, Any]


class AckResponse(BaseModel):
    status: str
    timestamp: datetime
