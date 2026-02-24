from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TelemetryIn(BaseModel):
    device_id: str
    moisture: float = Field(ge=0, le=100)
    temperature: float
    ph: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryOut(BaseModel):
    device_id: str
    moisture: float
    temperature: float
    ph: float
    captured_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class IrrigationCommandIn(BaseModel):
    device_id: str
    action: str = Field(default='irrigate')
    duration_seconds: int = Field(gt=0, le=7200)


class DeviceSnapshotOut(BaseModel):
    device_id: str
    telemetry: dict[str, Any] | None = None
    command: dict[str, Any] | None = None


class LedgerRecordIn(BaseModel):
    record_id: str
    payload: dict[str, Any]


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
