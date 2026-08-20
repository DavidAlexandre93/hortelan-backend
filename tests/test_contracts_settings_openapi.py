import asyncio
from datetime import UTC
from types import SimpleNamespace

import pytest
from fastapi import Response
from pydantic import ValidationError

from app.api.contracts import IrrigationCommandIn, LedgerRecordIn, TelemetryIn, TelemetryOut
from app.core.settings import AppEnvironment, Settings
from app.main import app, health_ready


def test_dtos_reject_unknown_fields_and_invalid_domain_values() -> None:
    with pytest.raises(ValidationError, match='extra_forbidden'):
        TelemetryIn(
            device_id='sensor-1',
            moisture=50,
            temperature=22,
            ph=6.5,
            unexpected='not-allowed',
        )
    with pytest.raises(ValidationError):
        TelemetryIn(device_id='sensor 1', moisture=101, temperature=22, ph=6.5)
    with pytest.raises(ValidationError):
        IrrigationCommandIn(device_id='sensor-1', action='delete', duration_seconds=5)
    with pytest.raises(ValidationError):
        LedgerRecordIn(record_id='event-1', payload={})


def test_dtos_normalize_naive_datetimes_to_utc() -> None:
    payload = TelemetryOut(
        device_id='sensor-1',
        moisture=50,
        temperature=22,
        ph=6.5,
        captured_at='2026-08-20T12:00:00',
    )
    assert payload.captured_at.tzinfo is UTC


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('cors_origins', ['ftp://invalid']),
        ('cors_origins', ['https://example.com/path']),
        ('cors_origins', ['https://example.com', 'https://example.com/']),
        ('redis_url', 'http://redis.local'),
        ('mongo_url', 'http://mongo.local'),
        ('web3_rpc_url', 'file:///tmp/socket'),
    ],
)
def test_settings_reject_unsafe_urls(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})


def test_settings_enforce_production_and_circuit_breaker_invariants() -> None:
    with pytest.raises(ValidationError, match='API_KEY e obrigatoria'):
        Settings(app_env=AppEnvironment.PRODUCTION)
    with pytest.raises(ValidationError, match='minimum_calls'):
        Settings(circuit_breaker_sliding_window_size=2, circuit_breaker_minimum_calls=3)

    settings = Settings(app_env='production', api_key='production-secret')
    assert settings.app_env is AppEnvironment.PRODUCTION
    assert 'production-secret' not in repr(settings)


def test_openapi_31_documents_security_errors_headers_and_strict_contracts() -> None:
    schema = app.openapi()
    command = schema['paths']['/api/v1/commands']['post']

    assert schema['openapi'].startswith('3.1')
    assert 'HortelanApiKey' in schema['components']['securitySchemes']
    assert command['security'] == [{'HortelanApiKey': []}]
    assert command['responses']['409']['content']['application/json']['schema']['$ref'].endswith(
        '/ErrorEnvelopeOut'
    )
    header_parameters = [item for item in command['parameters'] if item['in'] == 'header']
    assert any(item['name'] == 'Idempotency-Key' for item in header_parameters)
    assert schema['components']['schemas']['TelemetryIn']['additionalProperties'] is False


class _HealthyRepository:
    async def ping(self) -> None:
        return None


class _UnavailableRepository:
    async def ping(self) -> None:
        raise ConnectionError('database host with secret=password')


@pytest.mark.parametrize(
    ('repository', 'expected_status', 'expected_http_status'),
    [(_HealthyRepository(), 'ready', 200), (_UnavailableRepository(), 'degraded', 503)],
)
def test_readiness_has_typed_safe_status(
    monkeypatch: pytest.MonkeyPatch,
    repository: object,
    expected_status: str,
    expected_http_status: int,
) -> None:
    monkeypatch.setattr(
        'app.main.get_container',
        lambda: SimpleNamespace(relational_repo=repository),
    )
    response = Response()
    result = asyncio.run(health_ready(response))

    assert result.status == expected_status
    assert response.status_code == expected_http_status
    assert 'secret' not in result.model_dump_json()
