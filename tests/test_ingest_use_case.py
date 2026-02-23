import asyncio

from app.application.use_cases.ingest_telemetry import IngestTelemetryUseCase
from app.domain.entities.models import TelemetryReading


class _FakePublisher:
    def __init__(self):
        self.called = False

    async def publish_telemetry(self, reading):
        self.called = reading.device_id == 'sensor-1'


class _FakeCache:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, ttl_seconds=300):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)


class _FakeRepo:
    def __init__(self):
        self.saved = []

    async def save(self, reading):
        self.saved.append(reading)


def test_ingest_telemetry_use_case():
    publisher = _FakePublisher()
    cache = _FakeCache()
    relational = _FakeRepo()
    document = _FakeRepo()

    use_case = IngestTelemetryUseCase(publisher, cache, relational, document)
    reading = TelemetryReading(device_id='sensor-1', moisture=50, temperature=26, ph=6.4)

    asyncio.run(use_case.execute(reading))

    assert publisher.called
    assert len(relational.saved) == 1
    assert len(document.saved) == 1
    assert cache.values['telemetry:sensor-1']['device_id'] == 'sensor-1'
