from functools import lru_cache

from app.application.services.coverage_service import CoverageService
from app.application.use_cases.dispatch_command import DispatchIrrigationCommandUseCase
from app.application.use_cases.ingest_telemetry import IngestTelemetryUseCase
from app.application.use_cases.register_ledger import RegisterLedgerRecordUseCase
from app.core.settings import Settings, get_settings
from app.infrastructure.adapters.aws_iot_adapter import AwsIotCoreAdapter
from app.infrastructure.adapters.kafka_adapter import KafkaTelemetryAdapter
from app.infrastructure.adapters.redis_adapter import RedisCacheAdapter
from app.infrastructure.adapters.web3_adapter import Web3BlockchainAdapter
from app.infrastructure.persistence.document_repository import MongoTelemetryRepository
from app.infrastructure.persistence.relational_repository import SqlAlchemyTelemetryRepository


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        self.cache = RedisCacheAdapter(settings)
        self.telemetry_publisher = KafkaTelemetryAdapter(settings)
        self.command_adapter = AwsIotCoreAdapter(settings)
        self.blockchain_adapter = Web3BlockchainAdapter(settings)
        self.relational_repo = SqlAlchemyTelemetryRepository(settings)
        self.document_repo = MongoTelemetryRepository(settings)
        self.coverage_service = CoverageService()

        self.ingest_telemetry_use_case = IngestTelemetryUseCase(
            telemetry_publisher=self.telemetry_publisher,
            cache=self.cache,
            relational_repo=self.relational_repo,
            document_repo=self.document_repo,
        )
        self.dispatch_irrigation_command_use_case = DispatchIrrigationCommandUseCase(
            command_port=self.command_adapter,
            cache=self.cache,
        )
        self.register_ledger_record_use_case = RegisterLedgerRecordUseCase(
            blockchain_port=self.blockchain_adapter,
        )


@lru_cache
def get_container() -> Container:
    return Container(get_settings())
