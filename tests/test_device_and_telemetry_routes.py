import asyncio
from datetime import datetime

import pytest

import app.api.routes as routes
from app.domain.entities.models import TelemetryReading

pytestmark = pytest.mark.integration


class _FakeCache:
    def __init__(self, values):
        self.values = values

    async def get(self, key: str):
        return self.values.get(key)


class _FakeRelationalRepo:
    async def list_recent(self, limit: int, device_id: str | None = None):
        _ = (limit, device_id)
        return [
            TelemetryReading(
                device_id='device-1',
                moisture=45.5,
                temperature=21.2,
                ph=6.6,
                metadata={'zone': 'north'},
                captured_at=datetime.fromisoformat('2026-04-05T11:00:00'),
            )
        ]


class _FakeContainer:
    def __init__(self):
        self.cache = _FakeCache(
            {
                'telemetry:device-1': {
                    'device_id': 'device-1',
                    'moisture': 50,
                    'temperature': 25,
                    'ph': 6.5,
                    'captured_at': '2026-03-01T10:00:00',
                    'metadata': {'origin': 'cache'},
                },
                'command:device-1': {
                    'device_id': 'device-1',
                    'action': 'irrigate',
                    'duration_seconds': 60,
                    'sent_at': '2026-03-01T10:01:00',
                },
            }
        )
        self.relational_repo = _FakeRelationalRepo()


def test_list_telemetry_maps_domain_entities_to_contract(monkeypatch):
    monkeypatch.setattr(routes, 'get_container', lambda: _FakeContainer())

    response = asyncio.run(routes.list_telemetry(limit=10, device_id='device-1'))

    assert len(response) == 1
    assert response[0].device_id == 'device-1'
    assert response[0].metadata == {'zone': 'north'}


def test_device_snapshot_returns_cached_telemetry_and_command(monkeypatch):
    monkeypatch.setattr(routes, 'get_container', lambda: _FakeContainer())

    response = asyncio.run(routes.get_device_snapshot('device-1'))

    assert response.device_id == 'device-1'
    assert response.telemetry['metadata']['origin'] == 'cache'
    assert response.command['action'] == 'irrigate'
