from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.ai_output import AIGeneratedDocument, AIOutputMetadata

ContractType = Literal["firm_fixed_price", "time_and_materials", "labor_hour", "cost_plus_fixed_fee"]


class LaborCategoryInput(BaseModel):
    title: str
    estimated_hours: int = Field(gt=0)
    location: str = "Washington-Arlington-Alexandria, DC-VA-MD-WV"


class ComparableContract(BaseModel):
    piid: str
    vendor_name: str
    agency: str
    naics: str
    psc: str
    obligated_amount: float
    contract_type: str
    pop_start: str
    pop_end: str
    source: str


class WageBenchmark(BaseModel):
    labor_category: str
    bls_series: str
    hourly_wage: float
    source: str


class RateAnalysisItem(BaseModel):
    labor_category: str
    estimated_hours: int
    benchmark_hourly_wage: float
    proposed_hourly_rate: float
    variance_percent: float
    annual_cost: float
    source: str


class IGCEGenerateRequest(BaseModel):
    title: str = "Generated IGCE"
    package_id: str | None = None
    naics_code: str
    psc: str
    estimated_value: float = Field(gt=0)
    contract_type: ContractType
    labor_categories: list[LaborCategoryInput] = Field(default_factory=list)


class IGCEGeneratePayload(BaseModel):
    igce_id: str
    title: str
    methodology: str
    comparable_contracts: list[ComparableContract]
    wage_benchmarks: list[WageBenchmark]
    rate_analysis: list[RateAnalysisItem]
    narrative: str
    contract_type_recommendation: str
    provenance: list[str]
    used_fallback_data: bool
    generated_at: datetime


class IGCEGenerateResponse(AIGeneratedDocument):
    content: IGCEGeneratePayload
    metadata: AIOutputMetadata


class IGCERetrieveResponse(IGCEGenerateResponse):
    pass
