from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


class IrrigationAction(StrEnum):
    IRRIGATE = 'irrigate'
    STOP = 'stop'


class IdempotencyState(StrEnum):
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    UNKNOWN = 'unknown'


class OutboxState(StrEnum):
    PENDING = 'pending'
    PUBLISHED = 'published'


@dataclass(slots=True)
class TelemetryReading:
    device_id: str
    moisture: float
    temperature: float
    ph: float
    captured_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IrrigationCommand:
    device_id: str
    action: IrrigationAction
    duration_seconds: int
    idempotency_key: str = ''
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class LedgerRecord:
    record_id: str
    payload: dict[str, Any]
    tx_hash: str | None = None
    confirmed: bool = False


@dataclass(slots=True)
class IdempotencyRecord:
    key: str
    operation: str
    fingerprint: str
    state: IdempotencyState
    response: dict[str, Any] | None = None


@dataclass(slots=True)
class OutboxEvent:
    event_id: str
    event_type: str
    aggregate_id: str
    payload: dict[str, Any]
    state: OutboxState = OutboxState.PENDING
    occurred_at: datetime = field(default_factory=utc_now)
    attempt_count: int = 0
