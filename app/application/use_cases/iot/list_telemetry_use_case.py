from app.domain.entities.models import TelemetryReading
from app.domain.ports.interfaces import RelationalTelemetryRepositoryPort


class ListTelemetryUseCase:
    def __init__(self, relational_repo: RelationalTelemetryRepositoryPort) -> None:
        self.relational_repo = relational_repo

    async def execute(self, limit: int = 20, device_id: str | None = None) -> list[TelemetryReading]:
        return await self.relational_repo.list_recent(limit=limit, device_id=device_id)
