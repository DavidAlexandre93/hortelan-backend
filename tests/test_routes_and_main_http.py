import asyncio
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import app, settings


class FakeUseCase:
    def __init__(self, result: Any = None) -> None:
        self.calls: list[Any] = []
        self.result = result

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        return self.result


class FakeIdempotencyService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        result = await kwargs['action']()
        return {**result, 'idempotency_key': kwargs['key'], 'replayed': False}


def test_mutating_routes_map_dtos_and_propagate_idempotency(monkeypatch) -> None:
    ingest = FakeUseCase()
    dispatch = FakeUseCase()
    ledger = FakeUseCase()
    idempotency = FakeIdempotencyService()
    container = SimpleNamespace(
        ingest_telemetry_use_case=ingest,
        dispatch_irrigation_command_use_case=dispatch,
        register_ledger_record_use_case=ledger,
        idempotency_service=idempotency,
    )
    monkeypatch.setattr(routes, 'get_container', lambda: container)

    telemetry_ack = asyncio.run(
        routes.ingest_telemetry(
            routes.TelemetryIn(
                device_id='sensor-1',
                moisture=55,
                temperature=24,
                ph=6.5,
                metadata={'zone': 'a'},
            )
        )
    )
    command_ack = asyncio.run(
        routes.dispatch_command(
            routes.IrrigationCommandIn(
                device_id='sensor-1',
                action='irrigate',
                duration_seconds=30,
            ),
            idempotency_key='command-key-0001',
        )
    )
    ledger_ack = asyncio.run(
        routes.register_ledger(
            routes.LedgerRecordIn(record_id='record-1', payload={'kind': 'watering'}),
            idempotency_key='ledger-key-00001',
        )
    )

    assert telemetry_ack.status == 'telemetry_ingested'
    assert ingest.calls[0][0][0].metadata == {'zone': 'a'}
    assert command_ack.idempotency_key == 'command-key-0001'
    assert dispatch.calls[0][0][0].idempotency_key == 'command-key-0001'
    assert ledger_ack.status == 'ledger_registered'
    assert idempotency.calls[0]['operation'] == 'commands.dispatch'
    assert idempotency.calls[1]['operation'] == 'ledger.register'


def test_latest_routes_validate_cached_contracts(monkeypatch) -> None:
    container = SimpleNamespace(
        get_cached_telemetry_use_case=FakeUseCase(
            {
                'device_id': 'sensor-1',
                'moisture': 50,
                'temperature': 20,
                'ph': 6.4,
                'captured_at': '2026-08-20T12:00:00Z',
                'metadata': {},
            }
        ),
        get_cached_command_use_case=FakeUseCase(None),
    )
    monkeypatch.setattr(routes, 'get_container', lambda: container)

    telemetry = asyncio.run(routes.latest_telemetry('sensor-1'))
    command = asyncio.run(routes.latest_command('sensor-1'))

    assert telemetry is not None
    assert telemetry.device_id == 'sensor-1'
    assert command is None


def test_http_surface_docs_health_errors_and_security_headers() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        root = client.get('/')
        health = client.get('/health')
        live = client.get('/health/live')
        ready = client.get('/health/ready')
        docs = client.get('/docs')
        redoc = client.get('/redoc')
        favicon = client.get('/favicon.svg')
        missing = client.get('/definitely-missing')
        invalid = client.post('/api/v1/telemetry', json={'device_id': 'invalid id'})

    assert root.json()['version'] == settings.app_version
    assert health.json()['status'] == 'ok'
    assert live.json()['status'] == 'alive'
    assert ready.status_code == 200
    assert 'swagger-ui' in docs.text
    assert '/_vercel/insights/script.js' in docs.text
    assert 'redoc' in redoc.text.lower()
    assert favicon.headers['content-type'].startswith('image/svg+xml')
    assert missing.json()['error']['code'] == 'HTTP_ERROR'
    assert invalid.status_code == 422
    assert 'input' not in invalid.json()['error']['details']['errors'][0]
    for response in (root, health, live, ready, missing, invalid):
        assert response.headers['x-request-id']
        assert response.headers['x-content-type-options'] == 'nosniff'


def test_metrics_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, 'enable_metrics', False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/metrics')
    assert response.status_code == 404
    assert response.text == 'metrics disabled\n'
