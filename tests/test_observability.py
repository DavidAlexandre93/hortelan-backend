import asyncio

from app.core.observability import metrics_registry
from app.main import health_live, health_ready, metrics, root_status


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
