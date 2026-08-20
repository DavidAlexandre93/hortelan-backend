import asyncio

from app.application.use_cases.ingest_telemetry import IngestTelemetryUseCase
from app.core.exceptions import TransientIntegrationError
from app.domain.entities.models import OutboxEvent, TelemetryReading


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
        self.published = []

    async def save(self, reading):
        self.saved.append(reading)

    async def save_with_outbox(self, reading):
        self.saved.append(reading)
        return 'event-1'

    async def mark_outbox_published(self, event_id):
        self.published.append(event_id)

    async def list_pending_outbox(self, limit=100):
        return []


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
    assert relational.published == ['event-1']
    assert len(document.saved) == 1
    assert cache.values['telemetry:sensor-1']['device_id'] == 'sensor-1'


def test_ingest_tolerates_projection_publish_and_cache_failures():
    class FailingPublisher:
        async def publish_telemetry(self, reading):
            raise TransientIntegrationError(str(reading.device_id))

    class FailingCache(_FakeCache):
        async def set(self, key, value, ttl_seconds=300):
            raise TransientIntegrationError(key)

    class FailingDocument(_FakeRepo):
        async def save(self, reading):
            raise ConnectionError(str(reading.device_id))

    relational = _FakeRepo()
    use_case = IngestTelemetryUseCase(
        FailingPublisher(), FailingCache(), relational, FailingDocument()
    )

    asyncio.run(
        use_case.execute(
            TelemetryReading(device_id='sensor-1', moisture=50, temperature=26, ph=6.4)
        )
    )

    assert relational.published == []


def test_reconcile_pending_outbox_marks_only_successful_events():
    class ReconciliationRepo(_FakeRepo):
        async def list_pending_outbox(self, limit=100):
            return [
                OutboxEvent(
                    event_id='event-ok',
                    event_type='telemetry.ingested',
                    aggregate_id='sensor-1',
                    payload={
                        'device_id': 'sensor-1',
                        'moisture': 50,
                        'temperature': 26,
                        'ph': 6.4,
                        'captured_at': '2026-08-20T12:00:00+00:00',
                        'metadata': {},
                    },
                )
            ]

    relational = ReconciliationRepo()
    publisher = _FakePublisher()
    use_case = IngestTelemetryUseCase(publisher, _FakeCache(), relational, _FakeRepo())

    assert asyncio.run(use_case.reconcile_pending()) == 1
    assert relational.published == ['event-ok']
