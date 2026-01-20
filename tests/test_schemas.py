from __future__ import annotations

from pathlib import Path

import pytest

from meridian.artifacts.schemas import (
    APIEndpoint,
    BaselineResults,
    BusinessCaseScorecard,
    CodeGenerationPlan,
    ConfigSpec,
    CostModel,
    DatasetFingerprint,
    DecisionIntelProfile,
    DeliveryManifest,
    DriftReport,
    ExecutionOpsScorecard,
    Explanation,
    InterpretationPackage,
    FeasibilityReport,
    Hypothesis,
    KPITrace,
    Mode0GatePacket,
    ModelCandidate,
    ModelRecommendations,
    Opportunity,
    OpportunityBacklog,
    OpportunityBrief,
    OutputSpec,
    PipelineSpec,
    ProbeResult,
    QualityAssessment,
    RuntimeMetrics,
    Scenarios,
    SignalValidation,
    SplitInfo,
    TestSpec,
    ThresholdFramework,
    ValueModel,
)
from meridian.core.gates import GateVerdict


def test_each_schema_validates():
    _ = OpportunityBacklog(opportunities=[Opportunity(
        id="o1",
        type="prediction",
        description="desc",
        target_entity="customer",
        feasibility_score=50,
        business_value="MEDIUM",
    )])

    _ = OpportunityBrief(
        selected_opportunity_id="o1",
        problem_statement="ps",
        stakeholder_brief="sb",
        data_requirements=["a"],
    )

    _ = Mode0GatePacket(
        dataset_fingerprint=DatasetFingerprint(n_rows=1, n_cols=1),
        quality_assessment=QualityAssessment(),
        distribution_summary={},
        risks=[],
    )

    _ = DecisionIntelProfile(
        kpi_trace=KPITrace(business_kpi="kpi"),
        hypotheses=[Hypothesis(statement="h1"), Hypothesis(statement="h2")],
        gate_verdict=GateVerdict.GO,
    )

    _ = FeasibilityReport(
        split_info=SplitInfo(train_size=1, val_size=1, test_size=1),
        baseline_results=BaselineResults(model_type="LogisticRegression", metrics={"auc": 0.7}),
        probe_results={"label_shuffle": ProbeResult(status="PASS", details={})},
        signal_validation=SignalValidation(baseline_metric=0.7, random_metric=0.5, lift=0.4, signal_present=True),
        gate_verdict=GateVerdict.GO,
    )

    _ = ModelRecommendations(
        candidates=[ModelCandidate(name="a"), ModelCandidate(name="b")],
        recommended="a",
        rationale="because",
    )

    _ = ThresholdFramework(
        prediction_thresholds={"t": 0.5},
        operational_thresholds={"latency_p99_ms": 100},
        governance_thresholds={"psi_warn": 0.1},
        business_rules=[],
    )

    _ = BusinessCaseScorecard(
        options=[],
        cost_model=CostModel(),
        value_model=ValueModel(),
        scenarios=Scenarios(),
        recommendation="go",
        gate_verdict=GateVerdict.GO,
    )

    _ = ExecutionOpsScorecard(
        runtime_metrics=RuntimeMetrics(),
        compliance_status={"status": "ok"},  # type: ignore[arg-type]
        drift_report=DriftReport(),
        incidents=[],
    )

    _ = PipelineSpec(steps=["ingest"])
    _ = TestSpec(tests=["test_x"])
    _ = CodeGenerationPlan(
        pipeline_spec=PipelineSpec(steps=["ingest"]),
        test_spec=TestSpec(tests=["test_smoke"]),
        config_spec=ConfigSpec(entries={"x": 1}),
        output_path="PROJECT",
    )
    _ = OutputSpec(name="ExecutiveSummary.md")
    _ = APIEndpoint(method="GET", path="/health")
    _ = Explanation(text="x")
    _ = InterpretationPackage(explanations={"x": Explanation(text="hello", confidence="LOW")}, audience_versions={"executive": "x"})
    _ = DeliveryManifest(
        outputs=[OutputSpec(name="ExecutiveSummary.md", path="ExecutiveSummary.md")],
        api_endpoints=[APIEndpoint(method="GET", path="/health")],
        distribution_channels=["api"],
    )


def test_each_schema_serializes(tmp_path: Path):
    a = OpportunityBacklog(opportunities=[Opportunity(
        id="o1",
        type="prediction",
        description="desc",
        target_entity="customer",
        feasibility_score=50,
        business_value="MEDIUM",
    )])
    path = tmp_path / "a.json"
    a.to_file(path)
    a2 = OpportunityBacklog.from_file(path)
    assert a2.artifact_id == a.artifact_id


def test_required_validators():
    with pytest.raises(Exception):
        DecisionIntelProfile(kpi_trace=KPITrace(business_kpi="kpi"), hypotheses=[Hypothesis(statement="h1")], gate_verdict=GateVerdict.GO)

    with pytest.raises(Exception):
        ModelRecommendations(candidates=[ModelCandidate(name="a")], recommended="a", rationale="x")


def test_auto_fields_populated():
    a = OpportunityBacklog(opportunities=[Opportunity(
        id="o1",
        type="prediction",
        description="desc",
        target_entity="customer",
        feasibility_score=50,
        business_value="MEDIUM",
    )])
    assert a.artifact_id
    assert a.created_at is not None
    assert a.artifact_type == "OpportunityBacklog"

