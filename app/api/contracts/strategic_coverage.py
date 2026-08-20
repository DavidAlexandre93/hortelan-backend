from enum import StrEnum

from pydantic import Field

from app.api.contracts.base import ApiModel, UtcDatetime


class AckStatus(StrEnum):
    TELEMETRY_INGESTED = 'telemetry_ingested'
    COMMAND_DISPATCHED = 'command_dispatched'
    LEDGER_REGISTERED = 'ledger_registered'


class AckResponse(ApiModel):
    status: AckStatus
    timestamp: UtcDatetime
    idempotency_key: str | None = None
    replayed: bool = False


class RequirementCoverageOut(ApiModel):
    requirement_id: str
    title: str
    endpoint: str
    implemented: bool


class RequirementDetailOut(RequirementCoverageOut):
    notes: str


class StrategicFeatureCoverageOut(ApiModel):
    feature: str
    status: str
    evidence: str


class StrategicCoverageReportOut(ApiModel):
    overall_result: str
    matrix: list[StrategicFeatureCoverageOut]
    next_steps: list[str]


class ProductModuleCoverageOut(ApiModel):
    slug: str
    title: str
    stage: str
    status: str
    implemented: bool
    existing_endpoints: list[str] = Field(default_factory=list)
    endpoint: str
    notes: str


class ProductReadinessReportOut(ApiModel):
    summary: str
    modules: list[ProductModuleCoverageOut]
