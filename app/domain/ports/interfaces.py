from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.models import IrrigationCommand, LedgerRecord, TelemetryReading


class TelemetryPublisherPort(ABC):
    @abstractmethod
    async def publish_telemetry(self, reading: TelemetryReading) -> None: ...


class DeviceCommandPort(ABC):
    @abstractmethod
    async def send_command(self, command: IrrigationCommand) -> None: ...


class CachePort(ABC):
    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None: ...


class BlockchainPort(ABC):
    @abstractmethod
    async def write_record(self, record: LedgerRecord) -> LedgerRecord: ...


class RelationalTelemetryRepositoryPort(ABC):
    @abstractmethod
    async def save(self, reading: TelemetryReading) -> None: ...


class DocumentTelemetryRepositoryPort(ABC):
    @abstractmethod
    async def save(self, reading: TelemetryReading) -> None: ...
