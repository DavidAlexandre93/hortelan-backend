from typing import Any

from pydantic import Field

from app.api.contracts.base import ApiModel, UtcDatetime


class ValidationIssueOut(ApiModel):
    location: list[str | int]
    kind: str
    message: str


class ErrorDiagnosticsOut(ApiModel):
    timestamp: UtcDatetime
    status_code: int = Field(ge=400, le=599)
    incident_id: str
    request_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None


class ErrorBodyOut(ApiModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
    diagnostics: ErrorDiagnosticsOut


class ErrorEnvelopeOut(ApiModel):
    error: ErrorBodyOut
