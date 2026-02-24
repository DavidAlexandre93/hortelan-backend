from datetime import datetime

from fastapi import APIRouter, Query

from app.api.schemas import (
    AckResponse,
    CommandSnapshotOut,
    DeviceSnapshotOut,
    IrrigationCommandIn,
    LedgerRecordIn,
    ProductModuleCoverageOut,
    ProductReadinessReportOut,
    RequirementCoverageOut,
    RequirementDetailOut,
    StrategicCoverageReportOut,
    TelemetryIn,
    TelemetryOut,
)
from app.application.services.coverage_service import (
    IMPLEMENTED_REQUIREMENTS,
    PRODUCT_MODULES,
    REQUIREMENT_CATALOG,
    STRATEGIC_COVERAGE_MATRIX,
    STRATEGIC_NEXT_STEPS,
    _build_requirement_detail,
    _slugify_requirement,
)
from app.core.dependencies import get_container
from app.domain.entities.models import IrrigationCommand, LedgerRecord, TelemetryReading

router = APIRouter(prefix='/api/v1')


def _container():
    return get_container()


@router.post('/telemetry', response_model=AckResponse, tags=['telemetria'])
async def ingest_telemetry(payload: TelemetryIn) -> AckResponse:
    await _container().ingest_telemetry_use_case.execute(
        TelemetryReading(
            device_id=payload.device_id,
            moisture=payload.moisture,
            temperature=payload.temperature,
            ph=payload.ph,
            metadata=payload.metadata,
        )
    )
    return AckResponse(status='telemetry_ingested', timestamp=datetime.utcnow())


@router.get('/telemetry', response_model=list[TelemetryOut], tags=['telemetria'])
async def list_telemetry(
    limit: int = Query(default=20, ge=1, le=200),
    device_id: str | None = Query(default=None),
) -> list[TelemetryOut]:
    items = await _container().relational_repo.list_recent(limit=limit, device_id=device_id)
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


@router.get('/telemetry/latest/{device_id}', response_model=TelemetryOut | dict, tags=['telemetria'])
async def latest_telemetry(device_id: str) -> TelemetryOut | dict:
    return await _container().cache.get(f'telemetry:{device_id}') or {}


@router.post('/commands', response_model=AckResponse, tags=['comandos'])
async def dispatch_command(payload: IrrigationCommandIn) -> AckResponse:
    await _container().dispatch_irrigation_command_use_case.execute(
        IrrigationCommand(
            device_id=payload.device_id,
            action=payload.action,
            duration_seconds=payload.duration_seconds,
        )
    )
    return AckResponse(status='command_dispatched', timestamp=datetime.utcnow())


@router.get('/commands/latest/{device_id}', response_model=CommandSnapshotOut | dict, tags=['comandos'])
async def latest_command(device_id: str) -> CommandSnapshotOut | dict:
    return await _container().cache.get(f'command:{device_id}') or {}


@router.post('/ledger', response_model=AckResponse, tags=['ledger'])
async def register_ledger(payload: LedgerRecordIn) -> AckResponse:
    await _container().register_ledger_record_use_case.execute(
        LedgerRecord(record_id=payload.record_id, payload=payload.payload)
    )
    return AckResponse(status='ledger_registered', timestamp=datetime.utcnow())


@router.get('/devices/{device_id}/snapshot', response_model=DeviceSnapshotOut, tags=['dispositivos'])
async def get_device_snapshot(device_id: str) -> DeviceSnapshotOut:
    telemetry = await _container().cache.get(f'telemetry:{device_id}')
    command = await _container().cache.get(f'command:{device_id}')
    return DeviceSnapshotOut(device_id=device_id, telemetry=telemetry, command=command)


@router.get('/requirements', response_model=list[RequirementCoverageOut], tags=['cobertura estratégica'])
async def list_requirement_coverage() -> list[RequirementCoverageOut]:
    return _container().coverage_service.list_requirement_coverage()


@router.get('/strategic/coverage', response_model=StrategicCoverageReportOut, tags=['cobertura estratégica'])
async def strategic_coverage_report() -> StrategicCoverageReportOut:
    return _container().coverage_service.strategic_coverage_report()


@router.get('/product/readiness', response_model=ProductReadinessReportOut, tags=['cobertura estratégica'])
async def product_readiness_report() -> ProductReadinessReportOut:
    return _container().coverage_service.product_readiness_report()


@router.get('/product/modules/{module_slug}', response_model=ProductModuleCoverageOut, tags=['cobertura estratégica'])
async def product_module_detail(module_slug: str) -> ProductModuleCoverageOut:
    return _container().coverage_service.product_module_detail(module_slug)


def _requirement_endpoint(requirement_id: str, title: str):
    async def _handler() -> RequirementDetailOut:
        return _container().coverage_service.requirement_detail(requirement_id, title)

    _handler.__name__ = f"requirement_{requirement_id.replace('.', '_')}"
    return _handler


for _requirement_id, _title in REQUIREMENT_CATALOG:
    _slug = _slugify_requirement(_requirement_id, _title)
    router.add_api_route(
        f'/requirements/{_slug}',
        _requirement_endpoint(_requirement_id, _title),
        methods=['GET'],
        response_model=RequirementDetailOut,
        tags=['requirements'],
        summary=f'Cobertura do requisito {_requirement_id}',
    )
