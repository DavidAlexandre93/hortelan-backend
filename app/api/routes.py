from datetime import datetime

from fastapi import APIRouter

from app.api.schemas import AckResponse, IrrigationCommandIn, LedgerRecordIn, TelemetryIn
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


@router.post('/ledger', response_model=AckResponse)
async def register_ledger(payload: LedgerRecordIn) -> AckResponse:
    await container.register_ledger_record_use_case.execute(
        LedgerRecord(record_id=payload.record_id, payload=payload.payload)
    )
    return AckResponse(status='ledger_registered', timestamp=datetime.utcnow())
