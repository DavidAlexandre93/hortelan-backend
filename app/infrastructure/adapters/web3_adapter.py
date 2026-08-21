import asyncio
import json
import logging

from web3 import Web3

from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.exceptions import InfrastructureError
from app.core.resilience import ExternalCallPolicy
from app.core.settings import Settings
from app.domain.entities.models import LedgerRecord
from app.domain.ports.interfaces import BlockchainPort

logger = logging.getLogger(__name__)


class Web3BlockchainAdapter(BlockchainPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.w3 = Web3(Web3.HTTPProvider(settings.web3_rpc_url))
        abi = json.loads(settings.web3_contract_abi_json)
        self.contract = (
            self.w3.eth.contract(
                address=Web3.to_checksum_address(settings.web3_contract_address), abi=abi
            )
            if settings.web3_contract_address
            else None
        )
        self._policy = ExternalCallPolicy.from_settings(
            'web3_ledger', 'web3.write_record', settings
        )
        self._circuit_breaker = self._policy.circuit_breaker

    def _send_transaction(self, record: LedgerRecord) -> str:
        private_key = self.settings.web3_account_private_key.get_secret_value()
        if self.contract is None:
            raise InfrastructureError('Contrato Web3 nao configurado')
        account = self.w3.eth.account.from_key(private_key)
        nonce = self.w3.eth.get_transaction_count(account.address)
        tx = self.contract.functions.storeRecord(
            record.record_id, json.dumps(record.payload)
        ).build_transaction(
            {
                'from': account.address,
                'nonce': nonce,
                'gas': 400000,
                'gasPrice': self.w3.eth.gas_price,
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    async def write_record(self, record: LedgerRecord) -> LedgerRecord:
        if not self.contract or not self.settings.web3_account_private_key.get_secret_value():
            return record

        try:
            started = self._policy.start()
        except CircuitBreakerOpenError:
            return record

        try:
            tx_hash = await asyncio.wait_for(
                asyncio.to_thread(self._send_transaction, record),
                timeout=self.settings.external_timeout_seconds,
            )
        except Exception as exc:
            self._policy.failure(started)
            logger.exception('Falha ao registrar evento no Web3')
            raise InfrastructureError('Falha ao registrar evento em blockchain') from exc
        else:
            self._policy.success(started)
            record.tx_hash = tx_hash
            record.confirmed = True
            return record

    async def close(self) -> None:
        return None
