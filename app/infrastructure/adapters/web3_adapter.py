import asyncio
import json
import logging
import time

from web3 import Web3

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from app.core.observability import metrics_registry
from app.core.exceptions import InfrastructureError
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
            self.w3.eth.contract(address=Web3.to_checksum_address(settings.web3_contract_address), abi=abi)
            if settings.web3_contract_address
            else None
        )
        self._circuit_breaker = CircuitBreaker(
            name='web3_ledger',
            config=CircuitBreakerConfig(
                failure_rate_threshold=settings.circuit_breaker_failure_rate_threshold,
                sliding_window_size=settings.circuit_breaker_sliding_window_size,
                minimum_number_of_calls=settings.circuit_breaker_minimum_calls,
                wait_duration_in_open_state_seconds=settings.circuit_breaker_wait_duration_seconds,
                permitted_calls_in_half_open_state=settings.circuit_breaker_permitted_half_open_calls,
            ),
        )

    def _send_transaction(self, record: LedgerRecord) -> str:
        account = self.w3.eth.account.from_key(self.settings.web3_account_private_key)
        nonce = self.w3.eth.get_transaction_count(account.address)
        tx = self.contract.functions.storeRecord(record.record_id, json.dumps(record.payload)).build_transaction(
            {
                'from': account.address,
                'nonce': nonce,
                'gas': 400000,
                'gasPrice': self.w3.eth.gas_price,
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.settings.web3_account_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    async def write_record(self, record: LedgerRecord) -> LedgerRecord:
        if not self.contract or not self.settings.web3_account_private_key:
            return record

        try:
            self._circuit_breaker.call_permitted()
        except CircuitBreakerOpenError:
            return record

        started = time.perf_counter()
        try:
            tx_hash = await asyncio.wait_for(
                asyncio.to_thread(self._send_transaction, record),
                timeout=self.settings.external_timeout_seconds,
            )
        except Exception as exc:
            self._circuit_breaker.on_failure()
            metrics_registry.track_external_call('web3.write_record', time.perf_counter() - started, ok=False)
            logger.exception('Falha ao registrar evento no Web3')
            raise InfrastructureError('Falha ao registrar evento em blockchain') from exc
        else:
            self._circuit_breaker.on_success()
            metrics_registry.track_external_call('web3.write_record', time.perf_counter() - started, ok=True)
            record.tx_hash = tx_hash
            record.confirmed = True
            return record
