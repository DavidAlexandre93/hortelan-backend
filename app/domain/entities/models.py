from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TelemetryReading:
    device_id: str
    moisture: float
    temperature: float
    ph: float
    captured_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IrrigationCommand:
    device_id: str
    action: str
    duration_seconds: int
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class LedgerRecord:
    record_id: str
    payload: dict[str, Any]
    tx_hash: str | None = None
    confirmed: bool = False
