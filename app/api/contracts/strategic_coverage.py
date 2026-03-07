from datetime import datetime

from pydantic import BaseModel, Field


class AckResponse(BaseModel):
    status: str
    timestamp: datetime


class RequirementCoverageOut(BaseModel):
    requirement_id: str
    title: str
    endpoint: str
    implemented: bool


class RequirementDetailOut(RequirementCoverageOut):
    notes: str


class StrategicFeatureCoverageOut(BaseModel):
    feature: str
    status: str
    evidence: str


class StrategicCoverageReportOut(BaseModel):
    overall_result: str
    matrix: list[StrategicFeatureCoverageOut]
    next_steps: list[str]


class ProductModuleCoverageOut(BaseModel):
    slug: str
    title: str
    stage: str
    status: str
    implemented: bool
    existing_endpoints: list[str] = Field(default_factory=list)
    endpoint: str
    notes: str


class ProductReadinessReportOut(BaseModel):
    summary: str
    modules: list[ProductModuleCoverageOut]
