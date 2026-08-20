import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.services.idempotency_service import IdempotencyService
from app.core.exceptions import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyKeyRequiredError,
    InfrastructureError,
)
from app.core.settings import Settings
from app.domain.entities.models import IdempotencyRecord, IdempotencyState, TelemetryReading
from app.infrastructure.persistence import relational_repository as relational_module
from app.infrastructure.persistence.relational_repository import SqlAlchemyTelemetryRepository


class MemoryIdempotencyRepository:
    def __init__(self) -> None:
        self.records: dict[str, IdempotencyRecord] = {}
        self.lock = asyncio.Lock()

    async def reserve(self, record: IdempotencyRecord) -> tuple[bool, IdempotencyRecord]:
        async with self.lock:
            existing = self.records.get(record.key)
            if existing:
                return False, existing
            self.records[record.key] = record
            return True, record

    async def complete(self, key: str, response: dict[str, Any]) -> None:
        record = self.records[key]
        record.state = IdempotencyState.COMPLETED
        record.response = response

    async def mark_unknown(self, key: str) -> None:
        self.records[key].state = IdempotencyState.UNKNOWN


async def _execute(
    service: IdempotencyService,
    action: Callable[[], Awaitable[dict[str, Any]]],
    *,
    key: str | None = 'command-key-0001',
    operation: str = 'commands.dispatch',
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await service.execute(
        key=key,
        operation=operation,
        payload=payload or {'duration': 10},
        action=action,
    )


@pytest.mark.asyncio
async def test_idempotency_replays_completed_response_without_repeating_effect() -> None:
    repository = MemoryIdempotencyRepository()
    service = IdempotencyService(repository)
    effects = 0

    async def action() -> dict[str, Any]:
        nonlocal effects
        effects += 1
        return {'status': 'done'}

    first = await _execute(service, action)
    second = await _execute(service, action)

    assert effects == 1
    assert first == {
        'status': 'done',
        'idempotency_key': 'command-key-0001',
        'replayed': False,
    }
    assert second['replayed'] is True


@pytest.mark.asyncio
async def test_idempotency_rejects_invalid_conflicting_and_uncertain_requests() -> None:
    repository = MemoryIdempotencyRepository()
    service = IdempotencyService(repository)

    async def action() -> dict[str, Any]:
        return {'ok': True}

    with pytest.raises(IdempotencyKeyRequiredError):
        await _execute(service, action, key='short')

    await _execute(service, action)
    with pytest.raises(IdempotencyConflictError):
        await _execute(service, action, payload={'duration': 20})

    repository.records['processing-key-1'] = IdempotencyRecord(
        key='processing-key-1',
        operation='commands.dispatch',
        fingerprint=service._fingerprint('commands.dispatch', {'duration': 10}),
        state=IdempotencyState.PROCESSING,
    )
    with pytest.raises(IdempotencyInProgressError):
        await _execute(service, action, key='processing-key-1')


@pytest.mark.asyncio
async def test_idempotency_marks_unknown_when_effect_raises() -> None:
    repository = MemoryIdempotencyRepository()
    service = IdempotencyService(repository)

    async def action() -> dict[str, Any]:
        raise RuntimeError('external outcome unknown')

    with pytest.raises(RuntimeError):
        await _execute(service, action, key='unknown-key-001')

    assert repository.records['unknown-key-001'].state is IdempotencyState.UNKNOWN


@pytest.mark.asyncio
async def test_concurrent_idempotent_requests_execute_effect_once() -> None:
    repository = MemoryIdempotencyRepository()
    service = IdempotencyService(repository)
    effects = 0

    async def action() -> dict[str, Any]:
        nonlocal effects
        effects += 1
        await asyncio.sleep(0.01)
        return {'status': 'done'}

    results = await asyncio.gather(
        _execute(service, action, key='concurrent-key-1'),
        _execute(service, action, key='concurrent-key-1'),
        return_exceptions=True,
    )

    assert effects == 1
    assert sum(isinstance(result, IdempotencyInProgressError) for result in results) == 1
    assert sum(isinstance(result, dict) for result in results) == 1


def _repository_settings(database: Path) -> Settings:
    return Settings(
        relational_db_url=f'sqlite+aiosqlite:///{database.as_posix()}',
        otel_enabled=False,
    )


@pytest.mark.asyncio
async def test_relational_repository_commits_telemetry_and_outbox_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SqlAlchemyTelemetryRepository(_repository_settings(tmp_path / 'outbox.db'))
    await repository.init_schema()
    await repository.ping()
    reading = TelemetryReading(
        device_id='sensor-atomic',
        moisture=52.5,
        temperature=24.0,
        ph=6.4,
        captured_at=datetime(2026, 8, 20, 12, tzinfo=UTC),
        metadata={'zone': 'north'},
    )
    monkeypatch.setattr(relational_module.uuid, 'uuid4', lambda: SimpleNamespace(hex='fixed-event'))

    event_id = await repository.save_with_outbox(reading)
    assert event_id == 'fixed-event'
    assert (await repository.list_recent())[0] == reading
    assert [event.event_id for event in await repository.list_pending_outbox()] == ['fixed-event']

    with pytest.raises(InfrastructureError):
        await repository.save_with_outbox(reading)
    assert len(await repository.list_recent()) == 1

    await repository.mark_outbox_published(event_id)
    assert await repository.list_pending_outbox() == []
    with pytest.raises(InfrastructureError, match='outbox inexistente'):
        await repository.mark_outbox_published('missing-event')
    await repository.engine.dispose()


@pytest.mark.asyncio
async def test_relational_idempotency_unique_constraint_and_state_transitions(
    tmp_path: Path,
) -> None:
    repository = SqlAlchemyTelemetryRepository(_repository_settings(tmp_path / 'idempotency.db'))
    await repository.init_schema()
    record = IdempotencyRecord(
        key='unique-key-0001',
        operation='ledger.register',
        fingerprint='a' * 64,
        state=IdempotencyState.PROCESSING,
    )

    created, _ = await repository.reserve(record)
    duplicate_created, duplicate = await repository.reserve(record)
    assert created is True
    assert duplicate_created is False
    assert duplicate.state is IdempotencyState.PROCESSING

    await repository.complete(record.key, {'status': 'done'})
    _, completed = await repository.reserve(record)
    assert completed.state is IdempotencyState.COMPLETED
    assert completed.response == {'status': 'done'}

    second = IdempotencyRecord(
        key='unique-key-0002',
        operation='ledger.register',
        fingerprint='b' * 64,
        state=IdempotencyState.PROCESSING,
    )
    await repository.reserve(second)
    await repository.mark_unknown(second.key)
    _, unknown = await repository.reserve(second)
    assert unknown.state is IdempotencyState.UNKNOWN
    await repository.engine.dispose()
