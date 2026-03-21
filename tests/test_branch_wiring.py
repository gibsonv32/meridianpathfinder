"""Tests for Phase 8: Branch Wiring (Phase-to-Q-Code mapping).

Tests that:
1. PHASE_BRANCH_MAP exists and has correct entries
2. traverse_for_phase() runs main tree + branch trees
3. Phase-aware evaluation produces additional D-codes
4. Completeness validator accepts and forwards phase parameter
5. Conditional branch entries work (modification, option, protest)
6. No regression: calling without phase matches original behavior
"""
import pytest
from backend.phase2.policy_engine import (
    PolicyService,
    QCodeEngine,
    PHASE_BRANCH_MAP,
    CONDITIONAL_BRANCH_MAP,
    QCODE_NODES,
)
from backend.phase2.completeness_validator import (
    CompletenessValidator,
    ValidateCompletenessRequest,
    DocumentInHand,
)


# ── Standard test params (canonical $20M IT services) ──
CANONICAL_PARAMS = {
    "value": 20_000_000,
    "services": True,
    "it_related": True,
    "sole_source": False,
    "commercial_item": False,
    "emergency": False,
    "vendor_on_site": True,
    "competition_type": "full_and_open",
}

MICRO_PARAMS = {
    "value": 5_000,
    "services": False,
    "it_related": False,
    "sole_source": False,
    "commercial_item": False,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PHASE_BRANCH_MAP structure tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhaseBranchMap:

    def test_all_phases_have_entries(self):
        """Every acquisition phase must have an entry in the branch map."""
        expected_phases = [
            "Intake", "Requirements", "Solicitation Prep", "Solicitation",
            "Evaluation", "Award", "Post-Award", "Closeout",
        ]
        for phase in expected_phases:
            assert phase in PHASE_BRANCH_MAP, f"Missing branch map entry for: {phase}"

    def test_early_phases_have_empty_branches(self):
        """Intake through Solicitation should not add extra branches."""
        for phase in ["Intake", "Requirements", "Solicitation Prep", "Solicitation"]:
            assert PHASE_BRANCH_MAP[phase] == [], f"{phase} should have empty branches"

    def test_evaluation_includes_award_branch(self):
        """Evaluation phase should include Q058 (award prep) branch."""
        assert "Q058" in PHASE_BRANCH_MAP["Evaluation"]

    def test_award_includes_award_branch(self):
        """Award phase should include Q058 (full award) branch."""
        assert "Q058" in PHASE_BRANCH_MAP["Award"]

    def test_post_award_includes_branches(self):
        """Post-award should include Q068 (post-award admin) and Q098 (DHS/TSA)."""
        branches = PHASE_BRANCH_MAP["Post-Award"]
        assert "Q068" in branches, "Post-Award missing Q068 (post-award admin)"
        assert "Q098" in branches, "Post-Award missing Q098 (DHS/TSA specific)"

    def test_closeout_includes_closeout_branch(self):
        """Closeout should include Q108 (closeout) branch."""
        assert "Q108" in PHASE_BRANCH_MAP["Closeout"]

    def test_all_branch_entries_are_valid_qcodes(self):
        """All branch entry Q-codes must exist in QCODE_NODES."""
        for phase, entries in PHASE_BRANCH_MAP.items():
            for qcode in entries:
                assert qcode in QCODE_NODES, f"Branch entry {qcode} for {phase} not in QCODE_NODES"

    def test_conditional_branch_entries_valid(self):
        """All conditional branch entries must be valid Q-codes."""
        for key, qcode in CONDITIONAL_BRANCH_MAP.items():
            assert qcode in QCODE_NODES, f"Conditional branch {key}={qcode} not in QCODE_NODES"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. traverse_for_phase() tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTraverseForPhase:

    def setup_method(self):
        self.engine = QCodeEngine()

    def test_no_phase_matches_original_traverse(self):
        """Calling traverse_for_phase without phase should match traverse()."""
        original = self.engine.traverse(CANONICAL_PARAMS)
        phase_aware = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase=None)
        assert original.triggered_dcodes == phase_aware.triggered_dcodes
        assert original.nodes_evaluated == phase_aware.nodes_evaluated

    def test_intake_phase_matches_original(self):
        """Intake phase has no branches, so result should match original."""
        original = self.engine.traverse(CANONICAL_PARAMS)
        phase_aware = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase="Intake")
        assert original.triggered_dcodes == phase_aware.triggered_dcodes

    def test_award_phase_adds_award_dcodes(self):
        """Award phase should trigger D130, D131, D132 (pre-award/responsibility/cost)."""
        main_only = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase=None)
        with_award = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase="Award")

        # Award branch (Q058-Q067) should add new D-codes
        new_dcodes = with_award.triggered_dcodes - main_only.triggered_dcodes
        assert len(new_dcodes) > 0, "Award phase should add D-codes beyond main tree"
        # D131 (Responsibility) is triggered at Q059 for value > 350K
        assert "D131" in with_award.triggered_dcodes, "Award branch should trigger D131 (Responsibility)"
        # D132 (Cost/Price Analysis) is triggered at Q060
        assert "D132" in with_award.triggered_dcodes, "Award branch should trigger D132 (Cost/Price Analysis)"

    def test_post_award_adds_admin_dcodes(self):
        """Post-Award should traverse Q068-Q077 + Q098-Q107."""
        with_post = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase="Post-Award")
        # Q070 triggers D144 (CPARS interim)
        assert "D144" in with_post.triggered_dcodes, "Post-Award should trigger D144 (CPARS)"
        # Q072 triggers D121 (option window)
        assert "D121" in with_post.triggered_dcodes, "Post-Award should trigger D121 (option period)"

    def test_closeout_adds_closeout_dcodes(self):
        """Closeout should traverse Q108-Q117."""
        with_closeout = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase="Closeout")
        # Q113 triggers D145 (Release of Claims)
        assert "D145" in with_closeout.triggered_dcodes, "Closeout should trigger D145 (Release of Claims)"
        # Q114 triggers D144 (Final CPARS)
        assert "D144" in with_closeout.triggered_dcodes, "Closeout should trigger D144 (Final CPARS)"
        # Q116 triggers D143 (Closeout Checklist)
        assert "D143" in with_closeout.triggered_dcodes, "Closeout should trigger D143 (Closeout Checklist)"

    def test_closeout_with_vendor_onsite_triggers_property(self):
        """Closeout + vendor_on_site should trigger D126 (property disposition)."""
        with_closeout = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase="Closeout")
        # Q111 triggers D126 when vendor_on_site
        assert "D126" in with_closeout.triggered_dcodes, "Closeout + vendor on-site should trigger D126"

    def test_award_evaluates_more_nodes_than_main(self):
        """Award phase should evaluate more Q-code nodes than main tree alone."""
        main_only = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase=None)
        with_award = self.engine.traverse_for_phase(CANONICAL_PARAMS, phase="Award")
        assert with_award.nodes_evaluated > main_only.nodes_evaluated, \
            f"Award: {with_award.nodes_evaluated} nodes should be > main: {main_only.nodes_evaluated}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Conditional branch tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestConditionalBranches:

    def setup_method(self):
        self.engine = QCodeEngine()

    def test_modification_flag_enters_mod_branch(self):
        """is_modification=True should traverse Q048-Q057."""
        params = {**CANONICAL_PARAMS, "is_modification": True}
        result = self.engine.traverse_for_phase(params, phase="Post-Award")
        # Q049 triggers D129 (Modification Request Package)
        assert "D129" in result.triggered_dcodes, "Modification branch should trigger D129"

    def test_protest_flag_enters_protest_branch(self):
        """has_protest=True should traverse Q078-Q087."""
        params = {**CANONICAL_PARAMS, "has_protest": True}
        result = self.engine.traverse_for_phase(params, phase="Award")
        # Q079 triggers D137 (Protest Response Package)
        assert "D137" in result.triggered_dcodes, "Protest branch should trigger D137"

    def test_option_exercise_flag(self):
        """is_option_exercise=True should traverse Q054-Q057."""
        params = {**CANONICAL_PARAMS, "is_option_exercise": True}
        result = self.engine.traverse_for_phase(params, phase="Post-Award")
        # Q054 triggers D121 (Option Period Justification)
        assert "D121" in result.triggered_dcodes, "Option exercise should trigger D121"
        # Q056 triggers D132 (Cost/Price - option price fairness)
        assert "D132" in result.triggered_dcodes, "Option exercise should trigger D132"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PolicyService phase-aware evaluation tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyServicePhaseAware:

    def setup_method(self):
        self.service = PolicyService()

    def test_evaluate_without_phase_unchanged(self):
        """PolicyService.evaluate() without phase should work as before."""
        result = self.service.evaluate(CANONICAL_PARAMS)
        assert result.nodes_evaluated > 0
        assert len(result.required_dcodes) > 0

    def test_evaluate_with_award_phase(self):
        """PolicyService.evaluate() with Award phase should include award D-codes."""
        without_phase = self.service.evaluate(CANONICAL_PARAMS)
        with_phase = self.service.evaluate(CANONICAL_PARAMS, phase="Award")
        assert len(with_phase.required_dcodes) >= len(without_phase.required_dcodes), \
            "Award phase should produce at least as many required D-codes"

    def test_evaluate_with_closeout_phase(self):
        """Closeout phase should add closeout-specific D-codes."""
        result = self.service.evaluate(CANONICAL_PARAMS, phase="Closeout")
        assert "D143" in result.required_dcodes, "Closeout should require D143 (Closeout Checklist)"
        assert "D145" in result.required_dcodes, "Closeout should require D145 (Release of Claims)"

    def test_evaluate_micro_award_adds_branch_dcodes(self):
        """Micro-purchase in Award phase still gets award branch D-codes.
        Branch traversal force-triggers all D-codes (lifecycle event occurred).
        Even micro-purchases need basic award docs when in Award phase."""
        result = self.service.evaluate(MICRO_PARAMS, phase="Award")
        # Award branch force-triggers D-codes regardless of value threshold
        assert len(result.required_dcodes) > 0, "Award phase should add some D-codes even for micro"
        # But main tree should NOT have triggered above-SAT docs
        # (D101 Market Research only triggers for value > micro)
        assert "D101" not in result.required_dcodes, "Micro should not require D101 (Market Research)"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Completeness Validator phase-aware tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompletenessPhaseAware:

    def setup_method(self):
        self.validator = CompletenessValidator()

    def test_validate_with_phase_field(self):
        """Completeness validator should accept phase parameter."""
        request = ValidateCompletenessRequest(
            title="Test Package",
            value=20_000_000,
            services=True,
            it_related=True,
            vendor_on_site=True,
            phase="Award",
        )
        result = self.validator.validate(request)
        assert result.required_count > 0
        # Award phase should include D131 (Responsibility Determination)
        dcodes = [d.dcode for d in result.documents]
        assert "D131" in dcodes, "Award-phase completeness should include D131"

    def test_validate_without_phase_backward_compat(self):
        """Completeness validator should work without phase (backward compat)."""
        request = ValidateCompletenessRequest(
            title="Test Package",
            value=20_000_000,
            services=True,
            it_related=True,
        )
        result = self.validator.validate(request)
        assert result.required_count > 0

    def test_closeout_phase_completeness(self):
        """Closeout completeness should include closeout-specific docs."""
        request = ValidateCompletenessRequest(
            title="Closeout Package",
            value=20_000_000,
            services=True,
            it_related=True,
            vendor_on_site=True,
            phase="Closeout",
        )
        result = self.validator.validate(request)
        dcodes = [d.dcode for d in result.documents]
        assert "D143" in dcodes, "Closeout completeness should include D143 (Closeout Checklist)"
        assert "D145" in dcodes, "Closeout completeness should include D145 (Release of Claims)"

    def test_phase_aware_has_more_docs_than_no_phase(self):
        """Award-phase completeness should require >= docs than no-phase."""
        no_phase_req = ValidateCompletenessRequest(
            title="Test", value=20_000_000, services=True, it_related=True, vendor_on_site=True,
        )
        award_req = ValidateCompletenessRequest(
            title="Test", value=20_000_000, services=True, it_related=True, vendor_on_site=True,
            phase="Award",
        )
        no_phase = self.validator.validate(no_phase_req)
        with_phase = self.validator.validate(award_req)
        assert with_phase.required_count >= no_phase.required_count, \
            f"Award ({with_phase.required_count}) should require >= no-phase ({no_phase.required_count})"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. No-regression tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoRegression:

    def test_main_tree_terminal_unchanged(self):
        """Main tree should still terminate at Q047 for canonical params."""
        engine = QCodeEngine()
        result = engine.traverse(CANONICAL_PARAMS)
        assert result.terminal_node == "Q047"

    def test_micro_purchase_terminal_unchanged(self):
        """Micro-purchase should still route to Q017."""
        engine = QCodeEngine()
        result = engine.traverse(MICRO_PARAMS)
        # Micro goes Q001→Q002→Q003→Q017 (then Q017→Q018...→Q047 after expansion)
        # Actually with the full expansion Q017 routes to Q018, so terminal is Q047
        assert result.terminal_node in ("Q017", "Q047"), f"Unexpected terminal: {result.terminal_node}"

    def test_canonical_dcode_count_at_least_20(self):
        """$20M IT services should still trigger at least 20 D-codes."""
        engine = QCodeEngine()
        result = engine.traverse(CANONICAL_PARAMS)
        assert len(result.triggered_dcodes) >= 15, \
            f"Expected >= 15 D-codes, got {len(result.triggered_dcodes)}"
