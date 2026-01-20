from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Self
from uuid import uuid4

from pydantic import BaseModel, Field

from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    artifact_type: str = ""
    schema_version: str = "2.3.1"
    created_at: datetime = Field(default_factory=_utcnow)
    fingerprint_id: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        # Auto-populate artifact_type from class name.
        if not self.artifact_type:
            self.artifact_type = self.__class__.__name__

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_file(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_file(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


# ---- Mode 0.5 ----


class Opportunity(BaseModel):
    id: str
    type: Literal["prediction", "detection", "segmentation", "optimization", "explanation"]
    description: str
    target_entity: str
    feasibility_score: int = Field(ge=0, le=100)
    business_value: Literal["HIGH", "MEDIUM", "LOW"]


class OpportunityBacklog(BaseArtifact):
    opportunities: List[Opportunity]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OpportunityBrief(BaseArtifact):
    selected_opportunity_id: str
    problem_statement: str
    stakeholder_brief: str
    data_requirements: List[str] = Field(default_factory=list)


# ---- Mode 0 ----


class DatasetFingerprint(BaseModel):
    n_rows: int
    n_cols: int
    column_types: Dict[str, str] = Field(default_factory=dict)
    memory_usage_mb: float = 0.0
    file_hash: str = ""


class QualityAssessment(BaseModel):
    missing_pct: Dict[str, float] = Field(default_factory=dict)
    duplicate_rows: int = 0
    constant_columns: List[str] = Field(default_factory=list)
    high_cardinality_columns: List[str] = Field(default_factory=list)
    outlier_columns: List[str] = Field(default_factory=list)


class DistributionStats(BaseModel):
    stats: Dict[str, Any] = Field(default_factory=dict)


class Risk(BaseModel):
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    description: str
    mitigation: Optional[str] = None


class Mode0GatePacket(BaseArtifact):
    dataset_fingerprint: DatasetFingerprint
    quality_assessment: QualityAssessment
    distribution_summary: Dict[str, DistributionStats] = Field(default_factory=dict)
    risks: List[Risk] = Field(default_factory=list)


# ---- Mode 1 ----


class KPITrace(BaseModel):
    business_kpi: str = ""
    proxy_metric: Optional[str] = None
    measurement: Optional[str] = None


class Hypothesis(BaseModel):
    statement: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class Constraint(BaseModel):
    description: str
    value: Optional[str] = None


class Assumption(BaseModel):
    description: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class DecisionIntelProfile(BaseArtifact):
    kpi_trace: KPITrace
    hypotheses: List[Hypothesis] = Field(min_length=2)
    constraint_matrix: Dict[str, Constraint] = Field(default_factory=dict)
    definitions_of_done: Dict[str, str] = Field(default_factory=dict)
    assumptions: List[Assumption] = Field(default_factory=list)
    gate_verdict: GateVerdict


# ---- Mode 2 ----


class SplitInfo(BaseModel):
    train_size: int = 0
    val_size: int = 0
    test_size: int = 0
    split_method: str = ""
    split_params: Dict[str, Any] = Field(default_factory=dict)


class BaselineResults(BaseModel):
    model_type: str = ""
    metrics: Dict[str, float] = Field(default_factory=dict)
    feature_importances: Optional[Dict[str, float]] = None


class ProbeResult(BaseModel):
    status: Literal["PASS", "WARN", "FAIL"]
    details: Dict[str, Any] = Field(default_factory=dict)


class SignalValidation(BaseModel):
    baseline_metric: float = 0.0
    random_metric: float = 0.0
    lift: float = 0.0
    signal_present: bool = False


class FeasibilityReport(BaseArtifact):
    split_info: SplitInfo
    baseline_results: BaselineResults
    probe_results: Dict[str, ProbeResult] = Field(default_factory=dict)
    signal_validation: SignalValidation
    gate_verdict: GateVerdict


# ---- Mode 3 ----


class Feature(BaseModel):
    name: str
    derivation: str
    source_columns: List[str] = Field(default_factory=list)
    temporal_safe: bool = True
    compute_cost: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    importance_rank: Optional[int] = None


class FeatureRegistry(BaseArtifact):
    features: List[Feature] = Field(default_factory=list)


class ModelCandidate(BaseModel):
    name: str
    rationale: Optional[str] = None


class ModelRecommendations(BaseArtifact):
    candidates: List[ModelCandidate] = Field(min_length=2)
    recommended: str
    rationale: str


# ---- Mode 4 ----


class BusinessRule(BaseModel):
    rule_id: str
    condition: str
    action: str


class ThresholdFramework(BaseArtifact):
    prediction_thresholds: Dict[str, float] = Field(default_factory=dict)
    operational_thresholds: Dict[str, float] = Field(default_factory=dict)
    governance_thresholds: Dict[str, float] = Field(default_factory=dict)
    business_rules: List[BusinessRule] = Field(default_factory=list)


class Option(BaseModel):
    name: str
    description: Optional[str] = None


class CostModel(BaseModel):
    notes: Optional[str] = None


class ValueModel(BaseModel):
    notes: Optional[str] = None


class Scenarios(BaseModel):
    downside: Dict[str, Any] = Field(default_factory=dict)
    base: Dict[str, Any] = Field(default_factory=dict)
    upside: Dict[str, Any] = Field(default_factory=dict)


class BusinessCaseScorecard(BaseArtifact):
    options: List[Option] = Field(default_factory=list)
    cost_model: CostModel = Field(default_factory=CostModel)
    value_model: ValueModel = Field(default_factory=ValueModel)
    scenarios: Scenarios = Field(default_factory=Scenarios)
    recommendation: str
    gate_verdict: GateVerdict


# ---- Mode 5 ----


class PipelineSpec(BaseModel):
    steps: List[str] = Field(default_factory=list)


class TestSpec(BaseModel):
    tests: List[str] = Field(default_factory=list)


class ConfigSpec(BaseModel):
    entries: Dict[str, Any] = Field(default_factory=dict)


class CodeGenerationPlan(BaseArtifact):
    pipeline_spec: PipelineSpec
    test_spec: TestSpec
    config_spec: ConfigSpec
    output_path: str


# ---- Mode 6 ----


class RuntimeMetrics(BaseModel):
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ComplianceStatus(BaseModel):
    status: str = "unknown"


class DriftReport(BaseModel):
    psi: Dict[str, float] = Field(default_factory=dict)


class Incident(BaseModel):
    id: str
    severity: Literal["SEV0", "SEV1", "SEV2"]
    description: str


class ExecutionOpsScorecard(BaseArtifact):
    runtime_metrics: RuntimeMetrics
    compliance_status: ComplianceStatus
    drift_report: DriftReport
    incidents: List[Incident] = Field(default_factory=list)


# ---- Mode 6.5 ----


class Explanation(BaseModel):
    text: str
    confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None


class InterpretationPackage(BaseArtifact):
    explanations: Dict[str, Explanation] = Field(default_factory=dict)
    audience_versions: Dict[str, str] = Field(default_factory=dict)


class OutputSpec(BaseModel):
    name: str
    path: Optional[str] = None


class APIEndpoint(BaseModel):
    method: str
    path: str


class DeliveryManifest(BaseArtifact):
    outputs: List[OutputSpec] = Field(default_factory=list)
    api_endpoints: List[APIEndpoint] = Field(default_factory=list)
    distribution_channels: List[str] = Field(default_factory=list)


# ---- Mode 7 ----


class GateUpdate(BaseModel):
    id: str
    description: str


class PriorUpdate(BaseModel):
    id: str
    description: str


class Check(BaseModel):
    id: str
    description: str


class PolicyUpdates(BaseArtifact):
    gate_updates: List[GateUpdate] = Field(default_factory=list)
    prior_updates: List[PriorUpdate] = Field(default_factory=list)
    new_checks: List[Check] = Field(default_factory=list)
    feedback_routing: Dict[str, Mode] = Field(default_factory=dict)

