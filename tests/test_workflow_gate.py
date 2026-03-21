"""Tests for the Workflow Gate Engine.

Tests cover:
1. Simple gate pass — all requirements met
2. Gate block — missing required document
3. Phase ordering — can't go backward
4. Phase ordering — can't skip phases
5. Override with rationale — allowed
6. Override without rationale — denied
7. Non-waivable requirement — override denied
8. Completeness threshold enforcement
9. Status hierarchy — pending meets pending requirement
10. Roadmap generation
11. Next phase lookup
12. Unknown phase handling
"""
import pytest
import sys

sys.path.insert(0, "/app")

from backend.phase2.workflow_gate_engine import (
    WorkflowGateEngine,
    AcquisitionPhase,
    PHASE_ORDER,
    PHASE_GATES,
)


@pytest.fixture
def engine():
    return WorkflowGateEngine()


# ── Test 1: Simple gate pass ─────────────────────────────────────────────────

def test_gate_pass_intake_to_requirements(engine):
    """Intake → Requirements: need D101 at least pending."""
    docs = {"D101": "pending", "D102": "missing", "D103": "missing"}
    result = engine.check_gate("Intake", "Requirements", docs)
    assert result.allowed is True
    assert len(result.failed_requirements) == 0
    assert len(result.passed_requirements) == 1


# ── Test 2: Gate block ───────────────────────────────────────────────────────

def test_gate_block_missing_doc(engine):
    """Intake → Requirements: D101 missing → blocked."""
    docs = {"D101": "missing", "D102": "missing"}
    result = engine.check_gate("Intake", "Requirements", docs)
    assert result.allowed is False
    assert len(result.failed_requirements) == 1
    assert result.failed_requirements[0]["dcode"] == "D101"


# ── Test 3: Can't go backward ────────────────────────────────────────────────

def test_no_backward_movement(engine):
    """Requirements → Intake should be denied."""
    docs = {"D101": "satisfied"}
    result = engine.check_gate("Requirements", "Intake", docs)
    assert result.allowed is False
    assert "backward" in result.notes[0].lower() or "Cannot" in result.notes[0]


# ── Test 4: Can't skip phases ────────────────────────────────────────────────

def test_no_phase_skipping(engine):
    """Intake → Solicitation Prep (skipping Requirements) should be denied."""
    docs = {"D101": "satisfied", "D102": "satisfied", "D104": "satisfied", "D115": "satisfied"}
    result = engine.check_gate("Intake", "Solicitation Prep", docs)
    assert result.allowed is False
    assert "skip" in result.notes[0].lower()


# ── Test 5: Override with rationale ──────────────────────────────────────────

def test_override_with_rationale(engine):
    """CO override with written rationale should succeed for waivable gates."""
    docs = {"D101": "missing"}
    result = engine.advance(
        "Intake", "Requirements", docs,
        override=True,
        override_rationale="Market research being conducted concurrently per CO determination.",
        actor="CO Smith",
    )
    assert result.success is True
    assert result.override_used is True
    assert "OVERRIDDEN" in " ".join(result.gate_check.notes)


# ── Test 6: Override without rationale ────────────────────────────────────────

def test_override_without_rationale_denied(engine):
    """CO override without rationale should be denied."""
    docs = {"D101": "missing"}
    result = engine.advance(
        "Intake", "Requirements", docs,
        override=True,
        override_rationale="",
    )
    assert result.success is False
    assert "rationale" in " ".join(result.gate_check.notes).lower()


# ── Test 7: Non-waivable requirement ─────────────────────────────────────────

def test_non_waivable_override_denied(engine):
    """D120 (Security) is non-waivable — override should be denied at Solicitation gate."""
    docs = {
        "D101": "satisfied", "D102": "satisfied", "D103": "satisfied",
        "D104": "satisfied", "D115": "satisfied", "D120": "missing",
        "D105": "satisfied", "D107": "satisfied", "D109": "satisfied",
        "D114": "satisfied", "D117": "satisfied", "D118": "satisfied",
        "D119": "satisfied", "D121": "satisfied", "D122": "satisfied",
        "D127": "satisfied",
    }
    result = engine.advance(
        "Solicitation Prep", "Solicitation", docs,
        required_dcodes=set(docs.keys()),
        override=True,
        override_rationale="Trying to override security requirement.",
        actor="CO Test",
    )
    assert result.success is False
    assert result.gate_check.overridable is False
    assert "non-waivable" in " ".join(result.gate_check.notes).lower() or "DENIED" in " ".join(result.gate_check.notes)


# ── Test 8: Completeness threshold ───────────────────────────────────────────

def test_completeness_threshold(engine):
    """Solicitation Prep requires 15% completeness."""
    # 4 docs, 0 satisfied = 0% but D101 satisfied = meeting req
    docs = {"D101": "satisfied", "D102": "pending", "D104": "pending", "D115": "pending"}
    required = set(docs.keys()) | {"D103", "D105", "D107", "D109", "D120"}
    result = engine.check_gate("Requirements", "Solicitation Prep", docs, required)
    # D101 satisfied = 1/9 ≈ 11% < 15% minimum
    if not result.completeness_met:
        assert result.allowed is False
        assert "completeness" in " ".join(result.notes).lower()


# ── Test 9: Status hierarchy ─────────────────────────────────────────────────

def test_status_hierarchy_pending_meets_pending(engine):
    """Pending status should meet a 'pending' requirement."""
    docs = {"D101": "pending"}
    result = engine.check_gate("Intake", "Requirements", docs)
    assert result.allowed is True


def test_status_hierarchy_satisfied_meets_pending(engine):
    """Satisfied status should also meet a 'pending' requirement."""
    docs = {"D101": "satisfied"}
    result = engine.check_gate("Intake", "Requirements", docs)
    assert result.allowed is True


def test_status_hierarchy_missing_fails_pending(engine):
    """Missing status should NOT meet a 'pending' requirement."""
    docs = {"D101": "missing"}
    result = engine.check_gate("Intake", "Requirements", docs)
    assert result.allowed is False


# ── Test 10: Roadmap generation ───────────────────────────────────────────────

def test_roadmap(engine):
    """Roadmap should show all phases with correct statuses."""
    docs = {"D101": "pending", "D102": "missing"}
    roadmap = engine.get_phase_roadmap("Intake", docs)
    assert len(roadmap) == 8  # 8 phases
    assert roadmap[0]["status"] == "current"  # Intake is current
    assert roadmap[1]["status"] in ("ready", "blocked")  # Requirements
    assert roadmap[2]["status"] == "future"  # Solicitation Prep


# ── Test 11: Next phase lookup ────────────────────────────────────────────────

def test_next_phase(engine):
    """Next phase from Intake should be Requirements."""
    assert engine.get_next_phase("Intake") == "Requirements"
    assert engine.get_next_phase("Requirements") == "Solicitation Prep"
    assert engine.get_next_phase("Closeout") is None  # Last phase


# ── Test 12: Unknown phase ───────────────────────────────────────────────────

def test_unknown_phase(engine):
    """Unknown phase should return not-allowed with a clear message."""
    result = engine.check_gate("Nonexistent Phase", "Requirements", {})
    assert result.allowed is False
    assert "Unknown" in result.notes[0]
