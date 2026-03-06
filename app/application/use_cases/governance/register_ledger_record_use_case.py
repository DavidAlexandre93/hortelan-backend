from app.domain.entities.models import LedgerRecord
from app.domain.ports.interfaces import BlockchainPort


class RegisterLedgerRecordUseCase:
    def __init__(self, blockchain_port: BlockchainPort) -> None:
        self.blockchain_port = blockchain_port

    async def execute(self, record: LedgerRecord) -> LedgerRecord:
        return await self.blockchain_port.write_record(record)
