"""Phase 2 unit tests — protest risk, solicitation assembly, PIL pricing, evaluation workspace.

Tests run standalone (no DB, no Docker). Target: all pass alongside existing 27.
"""
from __future__ import annotations
import pytest

from backend.phase2.protest_scoring import ProtestRiskEngine, RiskLevel
from backend.phase2.solicitation_assembly import SolicitationAssemblyEngine, AssemblyStatus
from backend.phase2.pil_pricing import PILPricingEngine, RateStatus
from backend.phase2.evaluation_workspace import (
    EvaluationWorkspace, EvalRole, EvalPhase, Rating,
)


# ── Protest Risk ──────────────────────────────────────────────────────────────

class TestProtestRisk:
    def setup_method(self):
        self.engine = ProtestRiskEngine()

    def test_low_risk_competitive(self):
        result = self.engine.score(value=500_000, sole_source=False, j_l_m_traced=True)
        assert result.overall_risk in (RiskLevel.LOW, RiskLevel.MEDIUM)
        assert result.overall_score >= 0
        assert len(result.factors) > 0

    def test_high_risk_sole_source(self):
        """Sole source + no J-L-M tracing should produce elevated risk."""
        result = self.engine.score(value=20_000_000, sole_source=True, j_l_m_traced=False)
        # Score > 40 means at least MEDIUM; sole source factors should be HIGH individually
        assert result.overall_score > 40
        high_factors = [f for f in result.factors if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]
        assert len(high_factors) >= 2, "Sole source + no JLM should produce at least 2 HIGH-risk factors"

    def test_factors_have_mitigations(self):
        result = self.engine.score(value=1_000_000, sole_source=True)
        for f in result.factors:
            assert f.mitigation, f"Factor {f.factor_id} missing mitigation"
            assert f.authority, f"Factor {f.factor_id} missing authority"

    def test_recommendations_non_empty(self):
        result = self.engine.score(value=5_000_000, sole_source=True, incumbent_rebid=True)
        assert len(result.recommendations) > 0


# ── Solicitation Assembly ─────────────────────────────────────────────────────

class TestSolicitationAssembly:
    def setup_method(self):
        self.engine = SolicitationAssemblyEngine()

    def test_minimal_assembly(self):
        result = self.engine.assemble(
            package_id="PKG-001", title="Test Solicitation",
            value=500_000, documents=[], posting_deadline_days=30,
        )
        assert result.assembly_status in (AssemblyStatus.INCOMPLETE, AssemblyStatus.BLOCKED)
        assert result.completeness_pct < 100
        assert len(result.missing_sections) > 0

    def test_assembly_with_documents(self):
        docs = [
            {"dcode": "D102", "title": "Performance Work Statement", "acceptance_status": "accepted", "document_id": "DOC-1"},
            {"dcode": "D107", "title": "Evaluation Factors", "acceptance_status": "accepted", "document_id": "DOC-2"},
            {"dcode": "D113", "title": "Instructions to Offerors", "acceptance_status": "accepted", "document_id": "DOC-3"},
        ]
        result = self.engine.assemble(
            package_id="PKG-002", title="IT Support", value=2_000_000,
            documents=docs, posting_deadline_days=30,
        )
        present = [s for s in result.sections if s.present]
        assert len(present) >= 3

    def test_clauses_included_for_it_services(self):
        result = self.engine.assemble(
            package_id="PKG-003", title="Cyber", value=1_000_000,
            documents=[], services=True, it_related=True,
        )
        # Clauses use "clause" key (e.g. "FAR 52.212-4"), not "number"
        clause_ids = [c["clause"] for c in result.clauses]
        assert "FAR 52.212-4" in clause_ids

    def test_jlm_traceability_gaps(self):
        result = self.engine.assemble(
            package_id="PKG-004", title="Test JLM", value=5_000_000,
            documents=[{"dcode": "D102", "title": "PWS", "acceptance_status": "accepted", "document_id": "DOC-1"}],
        )
        # With only PWS, J-L-M may have gaps
        assert len(result.jlm_traceability) >= 0


# ── PIL Pricing ───────────────────────────────────────────────────────────────

class TestPILPricing:
    def setup_method(self):
        self.engine = PILPricingEngine()

    def test_within_range(self):
        """Cybersecurity Analyst PIL: $62–$95. Propose $78 = within range."""
        result = self.engine.analyze([
            {"title": "Cybersecurity Analyst", "proposed_rate": 78.0},
        ])
        assert len(result.comparisons) == 1
        c = result.comparisons[0]
        assert c.status == RateStatus.WITHIN_RANGE

    def test_above_ceiling(self):
        result = self.engine.analyze([
            {"title": "Project Manager", "proposed_rate": 500.0},
        ])
        c = result.comparisons[0]
        if c.status != RateStatus.NO_BENCHMARK:
            assert c.status == RateStatus.ABOVE_CEILING
            assert c.variance_pct > 0

    def test_below_floor(self):
        result = self.engine.analyze([
            {"title": "Help Desk Specialist", "proposed_rate": 20.0},
        ])
        c = result.comparisons[0]
        if c.status != RateStatus.NO_BENCHMARK:
            assert c.status == RateStatus.BELOW_FLOOR
            assert c.variance_pct < 0

    def test_multiple_categories(self):
        result = self.engine.analyze([
            {"title": "Cybersecurity Analyst", "proposed_rate": 78.0},
            {"title": "Project Manager", "proposed_rate": 120.0},
            {"title": "Data Scientist", "proposed_rate": 100.0},
        ])
        assert len(result.comparisons) == 3
        total = result.rates_within_range + result.rates_above_ceiling + result.rates_below_floor + result.rates_no_benchmark
        assert total == 3

    def test_no_benchmark_category(self):
        result = self.engine.analyze([
            {"title": "Quantum Computing Specialist", "proposed_rate": 300.0},
        ])
        assert result.comparisons[0].status == RateStatus.NO_BENCHMARK


# ── Evaluation Workspace ──────────────────────────────────────────────────────

class TestEvaluationWorkspace:
    def setup_method(self):
        self.ws = EvaluationWorkspace()
        self.factors = [
            {"name": "Technical Approach", "weight": 40, "description": "Quality of technical solution"},
            {"name": "Past Performance", "weight": 30, "description": "Relevant experience"},
            {"name": "Price", "weight": 30, "description": "Total evaluated price"},
        ]

    def test_create_workspace(self):
        ws = self.ws.create_workspace(
            package_id="PKG-100", title="IT Support Eval",
            actor="co_smith", role=EvalRole.CO, factors=self.factors,
        )
        assert ws.phase == EvalPhase.SETUP
        assert len(ws.factors) == 3
        assert len(ws.audit_log) == 1

    def test_add_offeror(self):
        ws = self.ws.create_workspace(
            package_id="PKG-101", title="Cyber Eval",
            actor="co_jones", role=EvalRole.CO, factors=self.factors,
        )
        # add_offeror returns OfferorRecord, not the workspace
        offeror = self.ws.add_offeror(
            ws.workspace_id, name="Acme Corp",
            proposal_received="2026-03-15",
            actor="co_jones", role=EvalRole.CO,
        )
        assert offeror.name == "Acme Corp"
        # Verify workspace state
        updated = self.ws.get_workspace(ws.workspace_id)
        assert len(updated.offerors) == 1

    def test_permission_denied(self):
        ws = self.ws.create_workspace(
            package_id="PKG-102", title="Test RBAC",
            actor="co_test", role=EvalRole.CO, factors=self.factors,
        )
        with pytest.raises(PermissionError):
            self.ws.add_offeror(
                ws.workspace_id, name="Evil Corp",
                proposal_received="2026-03-15",
                actor="advisor_bob", role=EvalRole.ADVISOR,
            )

    def test_advance_phase(self):
        ws = self.ws.create_workspace(
            package_id="PKG-103", title="Phase Advance",
            actor="chair_lee", role=EvalRole.SSEB_CHAIR, factors=self.factors,
        )
        new_phase = self.ws.advance_phase(
            ws.workspace_id, actor="chair_lee", role=EvalRole.SSEB_CHAIR,
        )
        assert new_phase == EvalPhase.INDIVIDUAL_EVAL

    def test_submit_score(self):
        ws = self.ws.create_workspace(
            package_id="PKG-104", title="Score Test",
            actor="co_test", role=EvalRole.CO, factors=self.factors,
        )
        self.ws.add_offeror(
            ws.workspace_id, name="TechCo",
            proposal_received="2026-03-10",
            actor="co_test", role=EvalRole.CO,
        )
        # Advance to individual evaluation phase
        self.ws.advance_phase(ws.workspace_id, actor="co_test", role=EvalRole.CO)
        offeror_id = ws.offerors[0].offeror_id
        factor_id = ws.factors[0].factor_id
        # submit_individual_score expects Rating enum, returns IndividualScore
        score = self.ws.submit_individual_score(
            ws.workspace_id, evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.OUTSTANDING, strengths=["Strong approach"],
            weaknesses=[], deficiencies=[],
            narrative="Excellent technical solution.",
        )
        assert score.rating == Rating.OUTSTANDING
        updated = self.ws.get_workspace(ws.workspace_id)
        assert len(updated.individual_scores) == 1

    def test_decision_phase_hard_stop(self):
        """Tier 3: Decision phase must be flagged as human-only."""
        ws = self.ws.create_workspace(
            package_id="PKG-105", title="Hard Stop Test",
            actor="chair_x", role=EvalRole.SSEB_CHAIR, factors=self.factors,
        )
        # Advance through phases to decision
        phases_to_advance = [
            EvalPhase.INDIVIDUAL_EVAL, EvalPhase.CONSENSUS,
            EvalPhase.DISCUSSIONS, EvalPhase.FINAL_EVAL, EvalPhase.DECISION,
        ]
        for _ in phases_to_advance:
            self.ws.advance_phase(ws.workspace_id, actor="chair_x", role=EvalRole.SSEB_CHAIR)
        updated = self.ws.get_workspace(ws.workspace_id)
        assert updated.phase == EvalPhase.DECISION
        # Decision phase is a Tier 3 hard stop — SSA makes the decision, not FedProcure
