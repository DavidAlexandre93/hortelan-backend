import asyncio

import pytest

from app.core.observability import metrics_registry
from app.main import health_live, health_ready, metrics, root_status

pytestmark = pytest.mark.integration


def test_health_readiness_and_liveness_endpoints():
    live = asyncio.run(health_live())
    ready = asyncio.run(health_ready())

    assert live['status'] == 'alive'
    assert ready['status'] in {'ready', 'degraded'}
    assert ready['checks']['database'] in {'ok', 'error'}


def test_root_status_message_is_available_in_english():
    response = asyncio.run(root_status())

    assert response['message'] == 'Service available'


def test_metrics_output_contains_http_measurements():
    metrics_registry.track_start()
    metrics_registry.track_end('GET', '/health', 200, 0.01)

    response = asyncio.run(metrics())
    payload = response.body.decode('utf-8')

    assert 'http_server_requests_total' in payload
    assert 'http_server_inflight_requests' in payload
    assert 'http_server_request_duration_seconds_avg' in payload
    assert 'http_server_request_duration_seconds_p95' in payload
    assert 'http_server_request_duration_seconds_p99' in payload
    assert 'http_server_request_error_rate' in payload
    assert 'http_server_throughput_rps' in payload


def test_metrics_output_contains_db_and_external_measurements():
    metrics_registry.track_db_query('telemetry.list_recent', 0.002, ok=True)
    metrics_registry.track_external_call('redis.get', 0.001, ok=False)

    response = asyncio.run(metrics())
    payload = response.body.decode('utf-8')

    assert 'db_query_duration_seconds_avg' in payload
    assert 'db_query_duration_seconds_p95' in payload
    assert 'db_query_errors_total' in payload
    assert 'external_call_duration_seconds_avg' in payload
    assert 'external_call_duration_seconds_p95' in payload
    assert 'external_call_errors_total' in payload