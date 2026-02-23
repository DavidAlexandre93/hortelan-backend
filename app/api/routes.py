from datetime import datetime

from fastapi import APIRouter, Query

from app.api.schemas import (
    AckResponse,
    DeviceSnapshotOut,
    IrrigationCommandIn,
    LedgerRecordIn,
    TelemetryIn,
    TelemetryOut,
)
from app.core.dependencies import container
from app.domain.entities.models import IrrigationCommand, LedgerRecord, TelemetryReading

router = APIRouter(prefix='/api/v1')


@router.post('/telemetry', response_model=AckResponse)
async def ingest_telemetry(payload: TelemetryIn) -> AckResponse:
    await container.ingest_telemetry_use_case.execute(
        TelemetryReading(
            device_id=payload.device_id,
            moisture=payload.moisture,
            temperature=payload.temperature,
            ph=payload.ph,
            metadata=payload.metadata,
        )
    )
    return AckResponse(status='telemetry_ingested', timestamp=datetime.utcnow())


@router.get('/telemetry', response_model=list[TelemetryOut])
async def list_telemetry(
    limit: int = Query(default=20, ge=1, le=200),
    device_id: str | None = Query(default=None),
) -> list[TelemetryOut]:
    items = await container.relational_repo.list_recent(limit=limit, device_id=device_id)
    return [
        TelemetryOut(
            device_id=item.device_id,
            moisture=item.moisture,
            temperature=item.temperature,
            ph=item.ph,
            captured_at=item.captured_at,
            metadata=item.metadata,
        )
        for item in items
    ]


@router.get('/telemetry/latest/{device_id}', response_model=TelemetryOut | None)
async def latest_telemetry(device_id: str) -> TelemetryOut | None:
    cached = await container.cache.get(f'telemetry:{device_id}')
    if not cached:
        return None

    return TelemetryOut(
        device_id=cached['device_id'],
        moisture=cached['moisture'],
        temperature=cached['temperature'],
        ph=cached['ph'],
        captured_at=datetime.fromisoformat(cached['captured_at']),
        metadata=cached.get('metadata', {}),
    )


@router.post('/commands', response_model=AckResponse)
async def dispatch_command(payload: IrrigationCommandIn) -> AckResponse:
    await container.dispatch_irrigation_command_use_case.execute(
        IrrigationCommand(
            device_id=payload.device_id,
            action=payload.action,
            duration_seconds=payload.duration_seconds,
        )
    )
    return AckResponse(status='command_dispatched', timestamp=datetime.utcnow())


@router.get('/commands/latest/{device_id}', response_model=dict)
async def latest_command(device_id: str) -> dict:
    return await container.cache.get(f'command:{device_id}') or {}


@router.post('/ledger', response_model=AckResponse)
async def register_ledger(payload: LedgerRecordIn) -> AckResponse:
    await container.register_ledger_record_use_case.execute(
        LedgerRecord(record_id=payload.record_id, payload=payload.payload)
    )
    return AckResponse(status='ledger_registered', timestamp=datetime.utcnow())


@router.get('/devices/{device_id}/snapshot', response_model=DeviceSnapshotOut)
async def get_device_snapshot(device_id: str) -> DeviceSnapshotOut:
    telemetry = await container.cache.get(f'telemetry:{device_id}')
    command = await container.cache.get(f'command:{device_id}')
    return DeviceSnapshotOut(device_id=device_id, telemetry=telemetry, command=command)
