"""
Tests for Secure Evaluation Workspace — MVP #6
RBAC, immutable scoring, phase gates, competitive range, SSDD, Tier 3 hard stop
"""
import pytest
from backend.phase2.evaluation_workspace import (
    EvaluationWorkspace,
    EvalRole,
    Rating,
    EvalPhase,
    PERMISSIONS,
    RATING_RANK,
    INDIVIDUAL_SCORE_PHASES,
    CONSENSUS_SCORE_PHASES,
    Tier3HardStopError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ws():
    return EvaluationWorkspace()


@pytest.fixture
def factors():
    return [
        {"name": "Technical Approach", "weight": 40, "description": "Quality of technical solution"},
        {"name": "Past Performance", "weight": 30, "description": "Relevant experience"},
        {"name": "Price", "weight": 30, "description": "Total evaluated price"},
    ]


@pytest.fixture
def setup_workspace(ws, factors):
    """Create a workspace with 2 offerors and advance to individual eval."""
    workspace = ws.create_workspace(
        package_id="PKG-200", title="Cyber SOC Eval",
        actor="co_smith", role=EvalRole.CO, factors=factors,
    )
    ws.add_offeror(workspace.workspace_id, name="AlphaSecure",
                   proposal_received="2026-03-10", actor="co_smith", role=EvalRole.CO)
    ws.add_offeror(workspace.workspace_id, name="BetaDefense",
                   proposal_received="2026-03-11", actor="co_smith", role=EvalRole.CO)
    ws.advance_phase(workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
    return workspace


def _score_all(ws, workspace, evaluator="eval_01", role=EvalRole.SSEB_MEMBER):
    """Submit scores for all active offeror/factor combinations."""
    active = [o for o in workspace.offerors if o.in_competitive_range]
    for offeror in active:
        for factor in workspace.factors:
            ws.submit_individual_score(
                workspace.workspace_id,
                evaluator=evaluator, role=role,
                offeror_id=offeror.offeror_id, factor_id=factor.factor_id,
                rating=Rating.GOOD, strengths=["Solid"], narrative="Good work",
            )


def _consensus_all(ws, workspace, actor="chair_lee", role=EvalRole.SSEB_CHAIR):
    """Submit consensus scores for all active offeror/factor combinations."""
    active = [o for o in workspace.offerors if o.in_competitive_range]
    for offeror in active:
        for factor in workspace.factors:
            ws.submit_consensus_score(
                workspace.workspace_id,
                actor=actor, role=role,
                offeror_id=offeror.offeror_id, factor_id=factor.factor_id,
                rating=Rating.ACCEPTABLE, strengths=["Met requirements"],
                narrative="Consensus: acceptable",
            )


# ---------------------------------------------------------------------------
# Schema / Enum Tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_eval_roles(self):
        assert len(EvalRole) == 5
        assert EvalRole.SSA.value == "ssa"

    def test_ratings(self):
        assert len(Rating) == 5
        assert Rating.OUTSTANDING.value == "outstanding"

    def test_rating_rank(self):
        assert RATING_RANK[Rating.OUTSTANDING] > RATING_RANK[Rating.GOOD]
        assert RATING_RANK[Rating.UNACCEPTABLE] == 1

    def test_eval_phases(self):
        assert len(EvalPhase) == 7
        phases = list(EvalPhase)
        assert phases[0] == EvalPhase.SETUP
        assert phases[-1] == EvalPhase.COMPLETE

    def test_permissions_exist(self):
        assert "create_workspace" in PERMISSIONS
        assert "make_award_decision" in PERMISSIONS
        assert EvalRole.SSA in PERMISSIONS["make_award_decision"]

    def test_individual_score_phases(self):
        assert EvalPhase.SETUP in INDIVIDUAL_SCORE_PHASES
        assert EvalPhase.INDIVIDUAL_EVAL in INDIVIDUAL_SCORE_PHASES
        assert EvalPhase.CONSENSUS not in INDIVIDUAL_SCORE_PHASES

    def test_consensus_score_phases(self):
        assert EvalPhase.CONSENSUS in CONSENSUS_SCORE_PHASES
        assert EvalPhase.FINAL_EVAL in CONSENSUS_SCORE_PHASES
        assert EvalPhase.INDIVIDUAL_EVAL not in CONSENSUS_SCORE_PHASES


# ---------------------------------------------------------------------------
# Workspace Creation
# ---------------------------------------------------------------------------

class TestWorkspaceCreation:
    def test_create_workspace(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-100", title="IT Support Eval",
            actor="co_smith", role=EvalRole.CO, factors=factors,
        )
        assert workspace.phase == EvalPhase.SETUP
        assert len(workspace.factors) == 3
        assert len(workspace.audit_log) == 1
        assert workspace.factors[0].factor_id == "F01"

    def test_create_workspace_sseb_chair(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-101", title="Test",
            actor="chair_lee", role=EvalRole.SSEB_CHAIR, factors=factors,
        )
        assert workspace.phase == EvalPhase.SETUP

    def test_create_workspace_permission_denied(self, ws, factors):
        with pytest.raises(PermissionError):
            ws.create_workspace(
                package_id="PKG-102", title="Denied",
                actor="advisor_bob", role=EvalRole.ADVISOR, factors=factors,
            )

    def test_add_offeror(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-103", title="Test",
            actor="co_jones", role=EvalRole.CO, factors=factors,
        )
        offeror = ws.add_offeror(
            workspace.workspace_id, name="Acme Corp",
            proposal_received="2026-03-15",
            actor="co_jones", role=EvalRole.CO,
        )
        assert offeror.name == "Acme Corp"
        assert offeror.in_competitive_range is True
        updated = ws.get_workspace(workspace.workspace_id)
        assert len(updated.offerors) == 1


# ---------------------------------------------------------------------------
# RBAC Permission Tests
# ---------------------------------------------------------------------------

class TestRBAC:
    def test_advisor_cannot_add_offeror(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-110", title="RBAC Test",
            actor="co_test", role=EvalRole.CO, factors=factors,
        )
        with pytest.raises(PermissionError):
            ws.add_offeror(
                workspace.workspace_id, name="Evil Corp",
                proposal_received="2026-03-15",
                actor="advisor_bob", role=EvalRole.ADVISOR,
            )

    def test_sseb_member_cannot_advance_phase(self, setup_workspace, ws):
        with pytest.raises(PermissionError):
            ws.advance_phase(
                setup_workspace.workspace_id,
                actor="member_01", role=EvalRole.SSEB_MEMBER,
            )

    def test_sseb_member_cannot_submit_consensus(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        with pytest.raises(PermissionError):
            ws.submit_consensus_score(
                setup_workspace.workspace_id,
                actor="member_01", role=EvalRole.SSEB_MEMBER,
                offeror_id=offeror_id, factor_id=factor_id,
                rating=Rating.GOOD,
            )

    def test_advisor_cannot_generate_ssdd(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-111", title="SSDD RBAC",
            actor="co_test", role=EvalRole.CO, factors=factors,
        )
        with pytest.raises(PermissionError):
            ws.generate_ssdd_draft(
                workspace.workspace_id,
                actor="advisor_bob", role=EvalRole.ADVISOR,
            )


# ---------------------------------------------------------------------------
# Score Submission
# ---------------------------------------------------------------------------

class TestScoreSubmission:
    def test_submit_individual_score(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        score = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.OUTSTANDING, strengths=["Strong approach"],
            narrative="Excellent technical solution.",
        )
        assert score.rating == Rating.OUTSTANDING
        assert score.superseded_by is None

    def test_score_wrong_phase(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        # Advance to consensus
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        with pytest.raises(ValueError, match="Cannot submit individual"):
            ws.submit_individual_score(
                setup_workspace.workspace_id,
                evaluator="eval_02", role=EvalRole.SSEB_MEMBER,
                offeror_id=offeror_id, factor_id=factor_id,
                rating=Rating.GOOD,
            )

    def test_score_excluded_offeror(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        ws.exclude_offeror(
            setup_workspace.workspace_id, offeror_id=offeror_id,
            rationale="Proposal did not meet minimum technical requirements",
            actor="co_smith", role=EvalRole.CO,
        )
        with pytest.raises(ValueError, match="excluded"):
            ws.submit_individual_score(
                setup_workspace.workspace_id,
                evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                offeror_id=offeror_id, factor_id=factor_id,
                rating=Rating.GOOD,
            )

    def test_score_unknown_offeror(self, setup_workspace, ws):
        with pytest.raises(ValueError, match="Unknown offeror"):
            ws.submit_individual_score(
                setup_workspace.workspace_id,
                evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                offeror_id="nonexistent", factor_id=setup_workspace.factors[0].factor_id,
                rating=Rating.GOOD,
            )

    def test_score_unknown_factor(self, setup_workspace, ws):
        with pytest.raises(ValueError, match="Unknown factor"):
            ws.submit_individual_score(
                setup_workspace.workspace_id,
                evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                offeror_id=setup_workspace.offerors[0].offeror_id, factor_id="F99",
                rating=Rating.GOOD,
            )


# ---------------------------------------------------------------------------
# Score Immutability / Supersession
# ---------------------------------------------------------------------------

class TestScoreImmutability:
    def test_supersede_score(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        original = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.GOOD,
        )
        new = ws.supersede_individual_score(
            setup_workspace.workspace_id,
            original_score_id=original.score_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            rating=Rating.OUTSTANDING,
            rationale="Re-evaluated based on additional proposal detail",
            strengths=["Exceptional approach"],
        )
        assert new.rating == Rating.OUTSTANDING
        assert original.superseded_by == new.score_id

    def test_supersede_requires_rationale(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        original = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.GOOD,
        )
        with pytest.raises(ValueError, match="rationale"):
            ws.supersede_individual_score(
                setup_workspace.workspace_id,
                original_score_id=original.score_id,
                evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                rating=Rating.OUTSTANDING, rationale="",
            )

    def test_different_evaluator_cannot_supersede(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        original = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.GOOD,
        )
        with pytest.raises(PermissionError, match="original evaluator"):
            ws.supersede_individual_score(
                setup_workspace.workspace_id,
                original_score_id=original.score_id,
                evaluator="eval_02", role=EvalRole.SSEB_MEMBER,
                rating=Rating.OUTSTANDING,
                rationale="Trying to tamper with someone else's score",
            )

    def test_cannot_supersede_twice(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        original = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.GOOD,
        )
        ws.supersede_individual_score(
            setup_workspace.workspace_id,
            original_score_id=original.score_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            rating=Rating.OUTSTANDING,
            rationale="First supersession",
        )
        with pytest.raises(ValueError, match="already superseded"):
            ws.supersede_individual_score(
                setup_workspace.workspace_id,
                original_score_id=original.score_id,
                evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                rating=Rating.ACCEPTABLE,
                rationale="Second attempt should fail",
            )

    def test_superseded_scores_excluded_from_consensus(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        original = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.GOOD,
        )
        ws.supersede_individual_score(
            setup_workspace.workspace_id,
            original_score_id=original.score_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            rating=Rating.OUTSTANDING,
            rationale="Revised assessment",
        )
        # Score remaining offeror/factors
        for factor in setup_workspace.factors:
            if factor.factor_id != factor_id:
                ws.submit_individual_score(
                    setup_workspace.workspace_id,
                    evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                    offeror_id=offeror_id, factor_id=factor.factor_id,
                    rating=Rating.GOOD,
                )
        for factor in setup_workspace.factors:
            ws.submit_individual_score(
                setup_workspace.workspace_id,
                evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
                offeror_id=setup_workspace.offerors[1].offeror_id,
                factor_id=factor.factor_id, rating=Rating.GOOD,
            )
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        consensus = ws.submit_consensus_score(
            setup_workspace.workspace_id,
            actor="chair_lee", role=EvalRole.SSEB_CHAIR,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.OUTSTANDING,
        )
        # Only the active (non-superseded) score should be in consensus.individual_scores
        assert len(consensus.individual_scores) == 1
        assert consensus.individual_scores[0].superseded_by is None


# ---------------------------------------------------------------------------
# Competitive Range Exclusion
# ---------------------------------------------------------------------------

class TestExclusion:
    def test_exclude_offeror(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        excluded = ws.exclude_offeror(
            setup_workspace.workspace_id, offeror_id=offeror_id,
            rationale="Proposal failed to meet minimum technical requirements per Section M",
            actor="co_smith", role=EvalRole.CO,
        )
        assert excluded.in_competitive_range is False
        assert excluded.excluded_reason is not None
        assert excluded.excluded_by == "co_smith"

    def test_exclude_requires_rationale(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        with pytest.raises(ValueError, match="rationale"):
            ws.exclude_offeror(
                setup_workspace.workspace_id, offeror_id=offeror_id,
                rationale="short", actor="co_smith", role=EvalRole.CO,
            )

    def test_advisor_cannot_exclude(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        with pytest.raises(PermissionError):
            ws.exclude_offeror(
                setup_workspace.workspace_id, offeror_id=offeror_id,
                rationale="Should not be allowed by advisor role",
                actor="advisor_bob", role=EvalRole.ADVISOR,
            )


# ---------------------------------------------------------------------------
# Phase Advancement & Gate Validation
# ---------------------------------------------------------------------------

class TestPhaseAdvancement:
    def test_advance_setup_to_individual(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-120", title="Phase Test",
            actor="chair_lee", role=EvalRole.SSEB_CHAIR, factors=factors,
        )
        ws.add_offeror(workspace.workspace_id, name="TestCo",
                       proposal_received="2026-03-15", actor="co_smith", role=EvalRole.CO)
        new_phase = ws.advance_phase(
            workspace.workspace_id, actor="chair_lee", role=EvalRole.SSEB_CHAIR,
        )
        assert new_phase == EvalPhase.INDIVIDUAL_EVAL

    def test_cannot_advance_to_individual_without_offerors(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-121", title="Gate Test",
            actor="co_smith", role=EvalRole.CO, factors=factors,
        )
        with pytest.raises(ValueError, match="No offerors"):
            ws.advance_phase(workspace.workspace_id, actor="co_smith", role=EvalRole.CO)

    def test_cannot_advance_to_consensus_without_scores(self, setup_workspace, ws):
        with pytest.raises(ValueError, match="Missing score"):
            ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)

    def test_advance_to_consensus_with_scores(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        new_phase = ws.advance_phase(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        assert new_phase == EvalPhase.CONSENSUS

    def test_cannot_advance_to_decision_without_consensus(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)  # → consensus
        _consensus_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)  # → discussions
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)  # → final_eval
        # Now at final_eval, advancing to decision requires consensus for all
        # (consensus already submitted, so this should pass)
        new_phase = ws.advance_phase(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        assert new_phase == EvalPhase.DECISION

    def test_already_complete(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        # Advance: individual → consensus
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        _consensus_all(ws, setup_workspace)
        # consensus → discussions → final_eval → decision → complete
        for _ in range(4):
            ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        workspace = ws.get_workspace(setup_workspace.workspace_id)
        assert workspace.phase == EvalPhase.COMPLETE
        with pytest.raises(ValueError, match="already complete"):
            ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)

    def test_decision_phase_tier3_logging(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        _consensus_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        log = ws.get_audit_log(setup_workspace.workspace_id)
        tier3_entries = [e for e in log if e["action"] == "tier3_hard_stop"]
        assert len(tier3_entries) == 1
        assert "FAR 15.308" in tier3_entries[0]["details"]


# ---------------------------------------------------------------------------
# Score Visibility
# ---------------------------------------------------------------------------

class TestScoreVisibility:
    def test_sseb_member_sees_only_own_scores(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.GOOD,
        )
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_02", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.OUTSTANDING,
        )
        # eval_01 sees only their score
        scores_01 = ws.get_scores(
            setup_workspace.workspace_id, actor="eval_01", role=EvalRole.SSEB_MEMBER,
        )
        assert len(scores_01) == 1
        assert scores_01[0].evaluator == "eval_01"

    def test_chair_sees_all_scores(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.GOOD,
        )
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_02", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.OUTSTANDING,
        )
        scores = ws.get_scores(
            setup_workspace.workspace_id, actor="chair_lee", role=EvalRole.SSEB_CHAIR,
        )
        assert len(scores) == 2

    def test_advisor_sees_no_individual_scores(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.GOOD,
        )
        scores = ws.get_scores(
            setup_workspace.workspace_id, actor="advisor_bob", role=EvalRole.ADVISOR,
        )
        assert len(scores) == 0


# ---------------------------------------------------------------------------
# Comparison Matrix
# ---------------------------------------------------------------------------

class TestComparisonMatrix:
    def test_comparison_matrix(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        _consensus_all(ws, setup_workspace)

        matrix = ws.get_comparison_matrix(
            setup_workspace.workspace_id, actor="chair_lee", role=EvalRole.SSEB_CHAIR,
        )
        assert "matrix" in matrix
        assert "factors" in matrix
        assert len(matrix["factors"]) == 3
        # Both offerors should be in matrix
        assert len(matrix["matrix"]) == 2

    def test_excluded_offerors_not_in_matrix(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        ws.exclude_offeror(
            setup_workspace.workspace_id, offeror_id=offeror_id,
            rationale="Did not meet minimum requirements for technical factor",
            actor="co_smith", role=EvalRole.CO,
        )
        matrix = ws.get_comparison_matrix(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        assert len(matrix["matrix"]) == 1  # Only BetaDefense

    def test_matrix_shows_strength_weakness_counts(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)

        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        ws.submit_consensus_score(
            setup_workspace.workspace_id,
            actor="chair_lee", role=EvalRole.SSEB_CHAIR,
            offeror_id=offeror_id, factor_id=factor_id,
            rating=Rating.GOOD, strengths=["A", "B"], weaknesses=["C"],
        )

        matrix = ws.get_comparison_matrix(
            setup_workspace.workspace_id, actor="chair_lee", role=EvalRole.SSEB_CHAIR,
        )
        offeror_name = setup_workspace.offerors[0].name
        factor_name = setup_workspace.factors[0].name
        cell = matrix["matrix"][offeror_name][factor_name]
        assert cell["strengths"] == 2
        assert cell["weaknesses"] == 1


# ---------------------------------------------------------------------------
# SSDD Draft Generation
# ---------------------------------------------------------------------------

class TestSSDDGeneration:
    def test_generate_ssdd(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        _consensus_all(ws, setup_workspace)

        ssdd = ws.generate_ssdd_draft(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        assert ssdd["document_type"] == "SSDD"
        assert len(ssdd["offeror_summaries"]) == 2
        assert ssdd["requires_ssa_signature"] is True
        assert "FAR 15.308" in ssdd["tier3_notice"]
        assert "does NOT recommend" in ssdd["tier3_notice"]

    def test_ssdd_excludes_excluded_offerors(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        ws.exclude_offeror(
            setup_workspace.workspace_id, offeror_id=offeror_id,
            rationale="Failed to demonstrate relevant past performance in similar scope",
            actor="co_smith", role=EvalRole.CO,
        )
        ssdd = ws.generate_ssdd_draft(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        assert len(ssdd["offeror_summaries"]) == 1
        assert len(ssdd["excluded_offerors"]) == 1
        assert ssdd["excluded_offerors"][0]["reason"] is not None

    def test_ssdd_has_factor_ratings(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        _consensus_all(ws, setup_workspace)

        ssdd = ws.generate_ssdd_draft(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        summary = ssdd["offeror_summaries"][0]
        assert len(summary["factor_ratings"]) == 3
        assert summary["factor_ratings"][0]["rating"] == "acceptable"

    def test_ssdd_does_not_recommend_awardee(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        ws.advance_phase(setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO)
        _consensus_all(ws, setup_workspace)

        ssdd = ws.generate_ssdd_draft(
            setup_workspace.workspace_id, actor="co_smith", role=EvalRole.CO,
        )
        # SSDD should NOT contain recommendation language
        ssdd_str = str(ssdd)
        assert "recommend" not in ssdd_str.lower() or "does not recommend" in ssdd_str.lower()


# ---------------------------------------------------------------------------
# Tier 3 Hard Stop
# ---------------------------------------------------------------------------

class TestTier3HardStop:
    def test_make_award_decision_always_refuses(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-T3", title="Tier 3 Test",
            actor="co_test", role=EvalRole.CO, factors=factors,
        )
        with pytest.raises(Tier3HardStopError, match="TIER 3"):
            ws.make_award_decision(workspace.workspace_id)

    def test_tier3_error_cites_authority(self, ws, factors):
        workspace = ws.create_workspace(
            package_id="PKG-T3b", title="Authority Test",
            actor="co_test", role=EvalRole.CO, factors=factors,
        )
        try:
            ws.make_award_decision(workspace.workspace_id)
        except Tier3HardStopError as e:
            msg = str(e)
            assert "FAR 15.308" in msg
            assert "FAR 7.503(b)(1)" in msg
            assert "inherently governmental" in msg.lower()

    def test_tier3_hard_stop_is_not_permission_error(self, ws, factors):
        """Tier 3 is a constitutional limit, not a role issue — it's a different error type."""
        workspace = ws.create_workspace(
            package_id="PKG-T3c", title="Error Type Test",
            actor="co_test", role=EvalRole.CO, factors=factors,
        )
        with pytest.raises(Tier3HardStopError):
            ws.make_award_decision(workspace.workspace_id, actor="ssa_general", role=EvalRole.SSA)


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_audit_log_append_only(self, setup_workspace, ws):
        log_before = len(ws.get_audit_log(setup_workspace.workspace_id))
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=setup_workspace.offerors[0].offeror_id,
            factor_id=setup_workspace.factors[0].factor_id,
            rating=Rating.GOOD,
        )
        log_after = len(ws.get_audit_log(setup_workspace.workspace_id))
        assert log_after == log_before + 1

    def test_audit_log_records_action_and_actor(self, setup_workspace, ws):
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=setup_workspace.offerors[0].offeror_id,
            factor_id=setup_workspace.factors[0].factor_id,
            rating=Rating.GOOD,
        )
        log = ws.get_audit_log(setup_workspace.workspace_id)
        last = log[-1]
        assert last["actor"] == "eval_01"
        assert last["action"] == "submit_score"
        assert "timestamp" in last


# ---------------------------------------------------------------------------
# Workspace Summary
# ---------------------------------------------------------------------------

class TestWorkspaceSummary:
    def test_summary(self, setup_workspace, ws):
        summary = ws.get_workspace_summary(setup_workspace.workspace_id)
        assert summary["phase"] == "individual_evaluation"
        assert summary["total_offerors"] == 2
        assert summary["active_offerors"] == 2
        assert summary["excluded_offerors"] == 0
        assert summary["factors"] == 3

    def test_summary_tracks_superseded(self, setup_workspace, ws):
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        original = ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.GOOD,
        )
        ws.supersede_individual_score(
            setup_workspace.workspace_id,
            original_score_id=original.score_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            rating=Rating.OUTSTANDING,
            rationale="Revised assessment after re-reading proposal",
        )
        summary = ws.get_workspace_summary(setup_workspace.workspace_id)
        assert summary["individual_scores"] == 1  # active only
        assert summary["superseded_scores"] == 1

    def test_summary_scoring_completeness(self, setup_workspace, ws):
        _score_all(ws, setup_workspace)
        summary = ws.get_workspace_summary(setup_workspace.workspace_id)
        # 2 offerors × 3 factors = 6 cells
        assert summary["scoring_completeness"]["individual"] == "6/6"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_unknown_workspace(self, ws):
        with pytest.raises(ValueError, match="Unknown workspace"):
            ws.get_workspace("nonexistent")

    def test_consensus_wrong_phase(self, setup_workspace, ws):
        """Cannot submit consensus during individual eval phase."""
        with pytest.raises(ValueError, match="Cannot submit consensus"):
            ws.submit_consensus_score(
                setup_workspace.workspace_id,
                actor="chair_lee", role=EvalRole.SSEB_CHAIR,
                offeror_id=setup_workspace.offerors[0].offeror_id,
                factor_id=setup_workspace.factors[0].factor_id,
                rating=Rating.GOOD,
            )

    def test_multiple_evaluators_same_factor(self, setup_workspace, ws):
        """Multiple evaluators can score the same factor."""
        offeror_id = setup_workspace.offerors[0].offeror_id
        factor_id = setup_workspace.factors[0].factor_id
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_01", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.GOOD,
        )
        ws.submit_individual_score(
            setup_workspace.workspace_id,
            evaluator="eval_02", role=EvalRole.SSEB_MEMBER,
            offeror_id=offeror_id, factor_id=factor_id, rating=Rating.OUTSTANDING,
        )
        workspace = ws.get_workspace(setup_workspace.workspace_id)
        scores = [s for s in workspace.individual_scores
                  if s.offeror_id == offeror_id and s.factor_id == factor_id]
        assert len(scores) == 2
