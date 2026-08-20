from enum import StrEnum

from app.api.contracts.base import ApiModel, UtcDatetime


class HealthStatus(StrEnum):
    OK = 'ok'
    ALIVE = 'alive'
    READY = 'ready'
    DEGRADED = 'degraded'
    UNAVAILABLE = 'unavailable'


class DependencyStatus(StrEnum):
    OK = 'ok'
    ERROR = 'error'


class RootStatusOut(ApiModel):
    message: str
    version: str


class HealthOut(ApiModel):
    status: HealthStatus
    environment: str
    version: str
    timestamp: UtcDatetime


class LivenessOut(ApiModel):
    status: HealthStatus
    timestamp: UtcDatetime


class ReadinessOut(ApiModel):
    status: HealthStatus
    checks: dict[str, DependencyStatus]
    environment: str
    version: str
    timestamp: UtcDatetime
