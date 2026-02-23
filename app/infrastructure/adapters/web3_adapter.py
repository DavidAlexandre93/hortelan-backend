import json

from web3 import Web3

from app.core.settings import Settings
from app.domain.entities.models import LedgerRecord
from app.domain.ports.interfaces import BlockchainPort


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

    async def write_record(self, record: LedgerRecord) -> LedgerRecord:
        if not self.contract or not self.settings.web3_account_private_key:
            return record

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

        record.tx_hash = tx_hash.hex()
        record.confirmed = True
        return record
