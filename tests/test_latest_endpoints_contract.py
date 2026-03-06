import asyncio

import app.api.routes as routes


class _FakeCache:
    def __init__(self, payload):
        self._payload = payload

    async def get(self, _key: str):
        return self._payload


class _FakeContainer:
    def __init__(self, payload):
        self.cache = _FakeCache(payload)


def test_latest_telemetry_returns_none_for_missing_payload(monkeypatch):
    monkeypatch.setattr(routes, 'get_container', lambda: _FakeContainer(None))

    response = asyncio.run(routes.latest_telemetry('device-1'))

    assert response is None


def test_latest_command_maps_legacy_created_at_to_sent_at(monkeypatch):
    legacy_payload = {
        'device_id': 'device-1',
        'action': 'irrigate',
        'duration_seconds': 60,
        'created_at': '2026-03-01T10:00:00',
    }
    monkeypatch.setattr(routes, 'get_container', lambda: _FakeContainer(legacy_payload))

    response = asyncio.run(routes.latest_command('device-1'))

    assert response is not None
    assert response.sent_at.isoformat().startswith('2026-03-01T10:00:00')
