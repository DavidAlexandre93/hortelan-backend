import asyncio
import json
import logging
import sys
from types import SimpleNamespace

from fastapi import Request, Response

from app.core.observability import (
    JsonFormatter,
    MetricsRegistry,
    ObservabilityMiddleware,
    RateLimiter,
    incident_id_ctx,
    request_id_ctx,
    trace_id_ctx,
)
from app.core.settings import Settings


def _request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            'type': 'http',
            'http_version': '1.1',
            'method': 'GET',
            'scheme': 'http',
            'path': '/devices/private-device',
            'raw_path': b'/devices/private-device',
            'query_string': b'token=secret',
            'headers': headers or [],
            'client': ('127.0.0.1', 9000),
            'server': ('testserver', 80),
            'route': SimpleNamespace(path='/devices/{device_id}'),
        }
    )


def test_json_formatter_emits_diagnostics_and_redacts_pii() -> None:
    formatter = JsonFormatter('hortelan-test', 'test')
    try:
        raise RuntimeError(r'email=person@example.com token=abc123 path=C:\Users\Maria\private.txt')
    except RuntimeError:
        record = logging.LogRecord(
            name='test.logger',
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg='operation failed for person@example.com',
            args=(),
            exc_info=sys.exc_info(),
        )
        record.event = 'operation.failed'
        record.password = 'must-not-be-serialized'
        payload = json.loads(formatter.format(record))

    assert payload['event'] == 'operation.failed'
    assert payload['exception']['class'] == 'RuntimeError'
    assert payload['exception']['file'].endswith('.py')
    assert isinstance(payload['exception']['line'], int)
    serialized = json.dumps(payload)
    assert 'person@example.com' not in serialized
    assert 'abc123' not in serialized
    assert 'Maria' not in serialized
    assert 'must-not-be-serialized' not in serialized
    assert '[REDACTED' in serialized


def test_metrics_escape_labels_and_calculate_quantiles_and_errors() -> None:
    registry = MetricsRegistry()
    registry.track_start()
    registry.track_end('GET"bad', '/route\nline', 500, 0.4)
    registry.track_db_query('query"unsafe', 0.2, ok=False)
    registry.track_external_call('redis', 0.1)

    output = registry.render_prometheus()
    assert 'GET\\"bad' in output
    assert 'path="/route\\nline"' in output
    assert 'http_server_request_error_rate' in output
    assert 'db_query_errors_total{operation="query\\"unsafe"} 1' in output


def test_rate_limiter_rejects_excess_and_expires_window(monkeypatch) -> None:
    clock = iter([100.0, 101.0, 102.0, 162.0])
    monkeypatch.setattr('app.core.observability.time.monotonic', lambda: next(clock))
    limiter = RateLimiter(2)

    assert limiter.allow('client') is True
    assert limiter.allow('client') is True
    assert limiter.allow('client') is False
    assert limiter.allow('client') is True


def test_observability_middleware_validates_ids_adds_headers_and_restores_context() -> None:
    middleware = ObservabilityMiddleware(
        app=lambda *_: None,
        logger=logging.getLogger('test.middleware'),
        settings=Settings(rate_limit_per_minute=2, otel_enabled=False),
    )
    request = _request(
        [
            (b'x-request-id', b'valid-request-1'),
            (b'x-trace-id', b'0123456789abcdef0123456789abcdef'),
        ]
    )

    async def call_next(_: Request) -> Response:
        assert request_id_ctx.get() == 'valid-request-1'
        assert trace_id_ctx.get() == '0123456789abcdef0123456789abcdef'
        return Response('ok')

    response = asyncio.run(middleware.dispatch(request, call_next))

    assert response.headers['x-request-id'] == 'valid-request-1'
    assert response.headers['x-trace-id'] == '0123456789abcdef0123456789abcdef'
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert request_id_ctx.get() == ''
    assert trace_id_ctx.get() == ''
    assert incident_id_ctx.get() == ''


def test_observability_middleware_returns_typed_429_with_correlation() -> None:
    middleware = ObservabilityMiddleware(
        app=lambda *_: None,
        logger=logging.getLogger('test.middleware'),
        settings=Settings(rate_limit_per_minute=1, otel_enabled=False),
    )
    calls = 0

    async def call_next(_: Request) -> Response:
        nonlocal calls
        calls += 1
        return Response('ok')

    first = asyncio.run(middleware.dispatch(_request(), call_next))
    limited = asyncio.run(middleware.dispatch(_request(), call_next))
    payload = json.loads(bytes(limited.body))

    assert first.status_code == 200
    assert limited.status_code == 429
    assert limited.headers['retry-after'] == '60'
    assert limited.headers['x-request-id']
    assert payload['error']['code'] == 'RATE_LIMITED'
    assert payload['error']['diagnostics']['incident_id']
    assert calls == 1
