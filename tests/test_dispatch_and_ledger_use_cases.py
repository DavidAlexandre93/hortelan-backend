import asyncio

from app.application.use_cases.governance.register_ledger_record_use_case import RegisterLedgerRecordUseCase
from app.application.use_cases.iot.dispatch_irrigation_command_use_case import DispatchIrrigationCommandUseCase
from app.core.exceptions import TransientIntegrationError
from app.domain.entities.models import IrrigationCommand, LedgerRecord


class _FakeCommandPort:
    def __init__(self):
        self.sent = []

    async def send_command(self, command):
        self.sent.append(command)


class _FakeCache:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.values = {}

    async def set(self, key, value, ttl_seconds=300):
        if self.should_fail:
            raise TransientIntegrationError('cache indisponível')
        self.values[key] = {'value': value, 'ttl_seconds': ttl_seconds}


class _FakeBlockchainPort:
    def __init__(self):
        self.received = []

    async def write_record(self, record):
        self.received.append(record)
        return LedgerRecord(record_id=record.record_id, payload={**record.payload, 'hash': '0xabc'})


def test_dispatch_irrigation_command_sends_command_and_caches_snapshot():
    command_port = _FakeCommandPort()
    cache = _FakeCache()
    use_case = DispatchIrrigationCommandUseCase(command_port=command_port, cache=cache)

    command = IrrigationCommand(device_id='device-1', action='irrigate', duration_seconds=90)
    asyncio.run(use_case.execute(command))

    assert len(command_port.sent) == 1
    snapshot = cache.values['command:device-1']
    assert snapshot['ttl_seconds'] == 120
    assert snapshot['value']['action'] == 'irrigate'
    assert snapshot['value']['duration_seconds'] == 90
    assert 'sent_at' in snapshot['value']


def test_dispatch_irrigation_command_tolerates_transient_cache_failure():
    command_port = _FakeCommandPort()
    cache = _FakeCache(should_fail=True)
    use_case = DispatchIrrigationCommandUseCase(command_port=command_port, cache=cache)

    command = IrrigationCommand(device_id='device-1', action='irrigate', duration_seconds=90)

    asyncio.run(use_case.execute(command))

    assert len(command_port.sent) == 1
    assert cache.values == {}


def test_register_ledger_record_returns_blockchain_response():
    blockchain = _FakeBlockchainPort()
    use_case = RegisterLedgerRecordUseCase(blockchain_port=blockchain)

    record = LedgerRecord(record_id='rec-1', payload={'event': 'watering'})
    result = asyncio.run(use_case.execute(record))

    assert len(blockchain.received) == 1
    assert result.record_id == 'rec-1'
    assert result.payload['event'] == 'watering'
    assert result.payload['hash'] == '0xabc'
