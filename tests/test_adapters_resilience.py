import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.circuit_breaker import CircuitState
from app.core.exceptions import InfrastructureError, TransientIntegrationError
from app.core.settings import Settings
from app.domain.entities.models import IrrigationCommand, LedgerRecord, TelemetryReading
from app.infrastructure.adapters import kafka_adapter as kafka_module
from app.infrastructure.adapters.aws_iot_adapter import AwsIotCoreAdapter
from app.infrastructure.adapters.kafka_adapter import KafkaTelemetryAdapter
from app.infrastructure.adapters.redis_adapter import RedisCacheAdapter
from app.infrastructure.adapters.web3_adapter import Web3BlockchainAdapter
from app.infrastructure.persistence.document_repository import MongoTelemetryRepository


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.fail_set = False
        self.fail_get = False

    async def set(self, key: str, value: str, ex: int) -> None:
        if self.fail_set:
            raise ConnectionError('redis unavailable')
        self.values[key] = value

    async def get(self, key: str) -> str | None:
        if self.fail_get:
            raise ConnectionError('redis unavailable')
        return self.values.get(key)


@pytest.mark.asyncio
async def test_redis_success_fallback_invalid_payload_and_open_circuit() -> None:
    adapter = RedisCacheAdapter(Settings(otel_enabled=False))
    client = FakeRedis()
    adapter.client = client  # type: ignore[assignment]

    await adapter.set('key', {'status': 'ok'}, ttl_seconds=10)
    assert await adapter.get('key') == {'status': 'ok'}

    client.values['key'] = '[]'
    assert await adapter.get('key') == {'status': 'ok'}
    client.values['key'] = 'invalid-json'
    assert await adapter.get('key') == {'status': 'ok'}

    adapter._circuit_breaker._state = CircuitState.OPEN
    adapter._circuit_breaker._opened_at = datetime.now(UTC)
    await adapter.set('open-key', {'fallback': True})
    assert await adapter.get('open-key') == {'fallback': True}


@pytest.mark.asyncio
async def test_redis_write_failure_is_typed_and_read_failure_uses_fallback() -> None:
    adapter = RedisCacheAdapter(Settings(otel_enabled=False))
    client = FakeRedis()
    adapter.client = client  # type: ignore[assignment]
    client.fail_set = True

    with pytest.raises(TransientIntegrationError):
        await adapter.set('key', {'cached': True})
    client.fail_get = True
    assert await adapter.get('key') == {'cached': True}


class FakeKafkaProducer:
    def __init__(self, *, fail_start: bool = False, fail_send: bool = False) -> None:
        self.fail_start = fail_start
        self.fail_send = fail_send
        self.started = False
        self.stopped = False
        self.messages: list[tuple[str, bytes]] = []

    async def start(self) -> None:
        if self.fail_start:
            raise ConnectionError('kafka start failed')
        self.started = True

    async def send_and_wait(self, topic: str, payload: bytes) -> None:
        if self.fail_send:
            raise ConnectionError('kafka send failed')
        self.messages.append((topic, payload))

    async def stop(self) -> None:
        self.stopped = True


def _reading() -> TelemetryReading:
    return TelemetryReading(
        device_id='sensor-1',
        moisture=50,
        temperature=23,
        ph=6.5,
        captured_at=datetime(2026, 8, 20, 12, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_kafka_lazy_start_publish_close_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    producer = FakeKafkaProducer()
    monkeypatch.setattr(kafka_module, 'AIOKafkaProducer', lambda **_: producer)
    adapter = KafkaTelemetryAdapter(Settings(otel_enabled=False))

    await adapter.publish_telemetry(_reading())
    assert producer.started is True
    assert producer.messages[0][0] == 'hortelan.telemetry'
    assert json.loads(producer.messages[0][1])['device_id'] == 'sensor-1'
    await adapter.close()
    assert producer.stopped is True

    failing_start = FakeKafkaProducer(fail_start=True)
    monkeypatch.setattr(kafka_module, 'AIOKafkaProducer', lambda **_: failing_start)
    with pytest.raises(TransientIntegrationError, match='inicializar Kafka'):
        await KafkaTelemetryAdapter(Settings(otel_enabled=False)).publish_telemetry(_reading())

    failing_send = FakeKafkaProducer(fail_send=True)
    adapter = KafkaTelemetryAdapter(Settings(otel_enabled=False))
    adapter._producer = failing_send  # type: ignore[assignment]
    with pytest.raises(TransientIntegrationError, match='publicar telemetria'):
        await adapter.publish_telemetry(_reading())


class FakeAwsClient:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def publish(self, **kwargs: object) -> None:
        if self.fail:
            raise ConnectionError('aws unavailable')
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_aws_iot_propagates_idempotency_and_maps_failures() -> None:
    command = IrrigationCommand(
        device_id='sensor-1',
        action='irrigate',
        duration_seconds=30,
        idempotency_key='command-key-0001',
    )
    adapter = AwsIotCoreAdapter(Settings(otel_enabled=False))
    client = FakeAwsClient()
    adapter._client = client
    await adapter.send_command(command)

    sent = json.loads(str(client.calls[0]['payload']))
    assert sent['idempotency_key'] == 'command-key-0001'
    assert client.calls[0]['qos'] == 1

    adapter._client = FakeAwsClient(fail=True)
    with pytest.raises(InfrastructureError, match='publicar comando'):
        await adapter.send_command(command)

    adapter._circuit_breaker._state = CircuitState.OPEN
    adapter._circuit_breaker._opened_at = datetime.now(UTC)
    with pytest.raises(InfrastructureError, match='Circuit breaker aberto'):
        await adapter.send_command(command)


@pytest.mark.asyncio
async def test_web3_noop_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    record = LedgerRecord(record_id='record-1', payload={'kind': 'test'})
    noop = Web3BlockchainAdapter(Settings(otel_enabled=False))
    assert await noop.write_record(record) is record

    configured = Web3BlockchainAdapter(
        Settings(web3_account_private_key='private-test-key', otel_enabled=False)
    )
    configured.contract = SimpleNamespace()
    monkeypatch.setattr(configured, '_send_transaction', lambda _: '0xabc')
    result = await configured.write_record(record)
    assert result.tx_hash == '0xabc'
    assert result.confirmed is True

    def fail(_: LedgerRecord) -> str:
        raise ConnectionError('rpc unavailable')

    monkeypatch.setattr(configured, '_send_transaction', fail)
    with pytest.raises(InfrastructureError, match='blockchain'):
        await configured.write_record(LedgerRecord(record_id='record-2', payload={'x': 1}))


@pytest.mark.asyncio
async def test_mongo_repository_uses_async_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = MongoTelemetryRepository(Settings(otel_enabled=False))
    inserted: list[dict[str, object]] = []

    class Collection:
        async def insert_one(self, value: dict[str, object]) -> None:
            inserted.append(value)

    repository.collection = Collection()  # type: ignore[assignment]
    await repository.save(_reading())
    assert inserted[0]['device_id'] == 'sensor-1'
    await repository.client.close()
