from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ThresholdItem(BaseModel):
    name: str
    value: float
    unit: str
    effective_date: date
    expiration_date: date | None = None
    authority: str
    overlay_level: int


class ThresholdTierResponse(BaseModel):
    tier_name: str
    docs_required: str
    competition: str
    acquisition_plan_required: bool
    approver: str
    posting_days: int


class ThresholdMatrixResponse(BaseModel):
    thresholds: list[ThresholdItem]


class ThresholdUpdateRequest(BaseModel):
    name: str
    value: float = Field(gt=0)
    authority: str
    effective_date: date
    overlay_level: int = Field(default=3, ge=0)
    unit: str = "USD"


class AcquisitionParams(BaseModel):
    title: str
    value: float = Field(gt=0)
    naics: str
    psc: str
    services: bool
    it_related: bool
    sole_source: bool = False
    commercial_item: bool = False
    emergency: bool = False
    vendor_on_site: bool = False
    competition_type: str = "full_and_open"
    as_of_date: date | None = None


class RulesEvaluationResponse(BaseModel):
    tier: ThresholdTierResponse
    required_dcodes: list[str]
    q_codes_evaluated: list[str]
    approvers: dict[str, str]
    posting_deadline_days: int
    authority_chain: list[str]
    notes: list[str]
