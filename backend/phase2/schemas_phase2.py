"""Phase 2 Pydantic schemas for protest risk, solicitation assembly, PIL pricing, evaluation workspace."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# --- Protest Risk ---
class ProtestRiskRequest(BaseModel):
    value: float
    sole_source: bool = False
    incumbent_rebid: bool = False
    evaluation_type: str = "tradeoff"
    num_offerors_expected: int = 3
    has_discussions: bool = False
    set_aside_type: str | None = None
    has_oci_plan: bool = False
    j_l_m_traced: bool = True
    price_analysis_method: str = "competitive"
    past_performance_weighted: bool = True
    debriefing_required: bool = False


class RiskFactorResponse(BaseModel):
    factor_id: str
    name: str
    description: str
    risk_level: str
    score: int
    mitigation: str
    authority: str


class ProtestRiskResponse(BaseModel):
    overall_score: int
    overall_risk: str
    factors: list[RiskFactorResponse]
    summary: str
    recommendations: list[str]
    source_provenance: list[str]
    confidence_score: float
    requires_acceptance: bool = True


# --- Solicitation Assembly ---
class AssembleRequest(BaseModel):
    package_id: str
    title: str
    value: float
    documents: list[dict] = Field(default_factory=list)
    posting_deadline_days: int = 30
    services: bool = True
    it_related: bool = True


class SectionMappingResponse(BaseModel):
    section: str
    dcode: str
    document_type: str
    title: str
    required: bool
    present: bool
    accepted: bool
    document_id: str | None = None


class JLMTraceResponse(BaseModel):
    j_reference: str
    l_instruction: str
    m_factor: str
    traced: bool
    gap: str | None = None


class AssemblyResponse(BaseModel):
    package_id: str
    title: str
    assembly_status: str
    sections: list[SectionMappingResponse]
    jlm_traceability: list[JLMTraceResponse]
    completeness_pct: float
    missing_sections: list[str]
    clauses: list[dict]
    posting_deadline_days: int
    warnings: list[str]
    source_provenance: list[str]
    confidence_score: float
    requires_acceptance: bool


# --- PIL Pricing ---
class PILAnalysisRequest(BaseModel):
    labor_categories: list[dict]  # [{title, proposed_rate}]


class RateComparisonResponse(BaseModel):
    labor_category: str
    proposed_rate: float
    pil_min: float
    pil_max: float
    pil_avg: float
    status: str
    variance_pct: float
    vehicle: str
    recommendation: str


class PILAnalysisResponse(BaseModel):
    comparisons: list[RateComparisonResponse]
    rates_within_range: int
    rates_above_ceiling: int
    rates_below_floor: int
    rates_no_benchmark: int
    overall_assessment: str
    recommended_vehicle: str | None
    source_provenance: list[str]
    confidence_score: float
    requires_acceptance: bool


# --- Evaluation Workspace ---
class CreateWorkspaceRequest(BaseModel):
    package_id: str
    title: str
    actor: str
    role: str = "co"
    factors: list[dict] = Field(default_factory=list)


class AddOfferorRequest(BaseModel):
    name: str
    proposal_received: str
    actor: str
    role: str = "co"


class SubmitScoreRequest(BaseModel):
    evaluator: str
    role: str = "sseb_member"
    offeror_id: str
    factor_id: str
    rating: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    deficiencies: list[str] = Field(default_factory=list)
    narrative: str = ""


class AdvancePhaseRequest(BaseModel):
    actor: str
    role: str = "sseb_chair"


class WorkspaceResponse(BaseModel):
    workspace_id: str
    package_id: str
    title: str
    phase: str
    factors: list[dict]
    offerors: list[dict]
    score_count: int
    consensus_count: int
    audit_log_count: int
