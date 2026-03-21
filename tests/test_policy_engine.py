"""Policy-as-Code Engine Tests
==============================
Unit tests for the deterministic policy engine. No DB required.
Tests Q-code DAG traversal, D-code registry, posting deadlines,
J&A approval ladder, clause selection, and the PolicyService orchestrator.
"""
from __future__ import annotations

from datetime import date

import pytest

from backend.phase2.policy_engine import (
    PolicyService,
    QCodeEngine,
    classify_value_tier,
    get_dcode_registry,
    get_threshold,
    resolve_ja_approver,
    resolve_posting_deadline,
    select_clauses,
)


# ── D-Code Registry ──────────────────────────────────────────────────────────

class TestDCodeRegistry:
    def test_registry_loads(self):
        registry = get_dcode_registry()
        assert len(registry) >= 17
        assert "D102" in registry

    def test_d102_is_pws_not_cor(self):
        """Critical correction: D102 = PWS (not COR Nomination)."""
        registry = get_dcode_registry()
        assert "Performance Work Statement" in registry["D102"].name

    def test_d115_is_cor_nomination(self):
        """COR Nomination moved to D115."""
        registry = get_dcode_registry()
        assert "COR" in registry["D115"].name

    def test_d109_is_special_reqs(self):
        """D109 = Special Contract Requirements (not PWS/SOW/SOO)."""
        registry = get_dcode_registry()
        assert "Special" in registry["D109"].name

    def test_d104_is_igce(self):
        """D104 = IGCE (internal doc, no UCF section)."""
        registry = get_dcode_registry()
        assert "IGCE" in registry["D104"].name
        assert registry["D104"].ucf_section is None

    def test_d103_is_clin_structure(self):
        """D103 = CLIN Structure (UCF Section B). New code from split."""
        registry = get_dcode_registry()
        assert "CLIN" in registry["D103"].name
        assert registry["D103"].ucf_section == "B"

    def test_effective_date_filtering(self):
        """D-codes before effective date should not appear."""
        registry = get_dcode_registry(as_of=date(2020, 1, 1))
        assert len(registry) == 0  # All FY2026 codes, none active in 2020


# ── Threshold Registry ────────────────────────────────────────────────────────

class TestThresholds:
    def test_sat_value(self):
        assert get_threshold("sat") == 350000

    def test_micro_purchase(self):
        assert get_threshold("micro_purchase") == 15000

    def test_new_thresholds_exist(self):
        """Validate newly added thresholds from findings doc."""
        assert get_threshold("gao_protest_civilian_task_order") == 10_000_000
        assert get_threshold("debriefing_task_order") == 7_500_000
        assert get_threshold("esar_threshold") == 750_000
        assert get_threshold("cas_threshold") == 2_000_000

    def test_unknown_threshold_raises(self):
        with pytest.raises(ValueError):
            get_threshold("nonexistent")


# ── Q-Code DAG Engine ─────────────────────────────────────────────────────────

class TestQCodeEngine:
    def setup_method(self):
        self.engine = QCodeEngine()

    def test_micro_purchase_short_path(self):
        """$10K should traverse: Q001→Q002→Q003→Q017 (short circuit)."""
        result = self.engine.traverse({"value": 10000, "services": False, "it_related": False, "sole_source": False})
        codes = [e.code for e in result.trace]
        assert "Q001" in codes
        assert "Q003" in codes
        assert result.terminal_node == "Q047"
        assert len(result.triggered_dcodes) == 0  # Micro: no docs

    def test_20m_full_path(self):
        """$20M IT services should traverse all major nodes."""
        result = self.engine.traverse({
            "value": 20_000_000, "services": True, "it_related": True,
            "sole_source": False, "commercial_item": False, "emergency": False,
            "acquisition_plan_threshold": 5_500_000, "subcontracting_plan_threshold": 900_000,
        })
        assert result.nodes_evaluated >= 10
        assert "D102" in result.triggered_dcodes  # Services → PWS
        assert "D114" in result.triggered_dcodes  # IT
        assert "D106" in result.triggered_dcodes  # AP ≥$5.5M
        assert "D110" in result.triggered_dcodes  # Subcon ≥$900K
        assert result.terminal_node == "Q047"

    def test_sole_source_triggers_ja(self):
        result = self.engine.traverse({
            "value": 5_000_000, "services": True, "it_related": False,
            "sole_source": True, "commercial_item": False,
            "acquisition_plan_threshold": 5_500_000, "subcontracting_plan_threshold": 900_000,
        })
        assert "D108" in result.triggered_dcodes  # J&A

    def test_trace_has_authorities(self):
        """Every trace entry must cite its authority."""
        result = self.engine.traverse({"value": 1_000_000, "services": True, "it_related": True, "sole_source": False})
        for entry in result.trace:
            assert entry.authority, f"Node {entry.code} missing authority"

    def test_no_infinite_loop(self):
        """DAG traversal should terminate even with bad params."""
        result = self.engine.traverse({})
        assert result.nodes_evaluated <= 50


# ── Posting Deadline Resolution ───────────────────────────────────────────────

class TestPostingDeadlines:
    def test_micro_no_posting(self):
        days, rule, _ = resolve_posting_deadline({"value": 10000, "sole_source": False})
        assert days == 0

    def test_below_sat_no_posting(self):
        days, rule, _ = resolve_posting_deadline({"value": 200000, "sole_source": False})
        # Below SAT, combined synopsis = 15 days is the most restrictive match
        assert days == 15  # FAR 12.603 combined synopsis/solicitation

    def test_competitive_above_sat_30_days(self):
        days, rule, auth = resolve_posting_deadline({"value": 5_000_000, "sole_source": False})
        assert days == 30
        assert "5.203" in auth

    def test_sole_source_above_sat_15_days(self):
        days, rule, _ = resolve_posting_deadline({"value": 5_000_000, "sole_source": True})
        assert days == 15

    def test_emergency_overrides(self):
        days, rule, _ = resolve_posting_deadline({"value": 20_000_000, "sole_source": False, "emergency": True})
        assert days == 0
        assert "emergency" in rule


# ── J&A Approval Ladder ──────────────────────────────────────────────────────

class TestJAApprovalLadder:
    def test_below_800k_co(self):
        approver, _ = resolve_ja_approver(500_000)
        assert approver == "CO"

    def test_800k_to_15m_competition_advocate(self):
        approver, _ = resolve_ja_approver(5_000_000)
        assert approver == "Competition Advocate"

    def test_15m_to_100m_hca(self):
        approver, auth = resolve_ja_approver(20_000_000)
        assert approver == "HCA"
        assert "6.304(a)(3)" in auth

    def test_above_100m_spe(self):
        approver, _ = resolve_ja_approver(150_000_000)
        assert approver == "Senior Procurement Executive"

    def test_boundary_800k(self):
        """At exactly $800K: should be Competition Advocate (>= $800K)."""
        approver, _ = resolve_ja_approver(800_000)
        assert approver == "Competition Advocate"


# ── Clause Selection ──────────────────────────────────────────────────────────

class TestClauseSelection:
    def test_commercial_it_services(self):
        clauses = select_clauses({"commercial_item": True, "services": True, "it_related": True, "value": 2_000_000})
        numbers = [c["clause_number"] for c in clauses]
        assert "52.212-4" in numbers  # Commercial terms
        assert "52.222-41" in numbers  # Service contract labor
        assert "52.239-1" in numbers  # IT privacy
        assert "3052.204-71" in numbers  # DHS contractor access

    def test_non_commercial_no_part12(self):
        clauses = select_clauses({"commercial_item": False, "services": True, "it_related": False, "value": 1_000_000})
        numbers = [c["clause_number"] for c in clauses]
        assert "52.212-1" not in numbers
        assert "52.212-4" not in numbers

    def test_cost_data_clause(self):
        """Above $2.5M non-commercial → requires certified cost data clause."""
        clauses = select_clauses({"commercial_item": False, "services": True, "it_related": False, "value": 5_000_000})
        numbers = [c["clause_number"] for c in clauses]
        assert "52.215-20" in numbers


# ── Value Tier Classification ─────────────────────────────────────────────────

class TestValueTiers:
    def test_micro(self):
        assert classify_value_tier(10000).name == "micro_purchase"

    def test_sat(self):
        assert classify_value_tier(200000).name == "sat"

    def test_mid_range(self):
        assert classify_value_tier(2_000_000).name == "mid_range"

    def test_major(self):
        assert classify_value_tier(20_000_000).name == "major_acquisition"

    def test_mega(self):
        assert classify_value_tier(150_000_000).name == "mega_acquisition"

    def test_exactly_at_boundary(self):
        """$350K = sat tier (≤ boundary)."""
        tier = classify_value_tier(350000)
        assert tier.name in ("sat", "mid_range")  # At boundary


# ── PolicyService Integration ─────────────────────────────────────────────────

class TestPolicyService:
    def setup_method(self):
        self.svc = PolicyService()

    def test_canonical_20m_it_services(self):
        """The canonical FedProcure scenario: $20M IT services, full & open."""
        result = self.svc.evaluate({
            "value": 20_000_000, "services": True, "it_related": True,
            "sole_source": False, "commercial_item": False, "emergency": False,
        })
        assert result.tier.name == "major_acquisition"
        assert result.posting_deadline_days == 30
        assert result.ja_approver == "HCA"
        assert "D102" in result.required_dcodes  # PWS
        assert "D114" in result.required_dcodes  # IT
        assert "D106" in result.required_dcodes  # AP
        assert result.nodes_evaluated >= 10
        assert len(result.qcode_trace) >= 10
        assert len(result.applicable_clauses) > 0
        assert len(result.authority_chain) > 0

    def test_micro_purchase_minimal(self):
        result = self.svc.evaluate({
            "value": 10000, "services": False, "it_related": False,
            "sole_source": False, "commercial_item": False,
        })
        assert result.tier.name == "micro_purchase"
        assert result.posting_deadline_days == 0
        assert len(result.required_dcodes) == 0

    def test_sole_source_includes_ja_note(self):
        result = self.svc.evaluate({
            "value": 5_000_000, "services": True, "it_related": True,
            "sole_source": True, "commercial_item": False,
        })
        assert "D108" in result.required_dcodes
        assert result.ja_approver == "Competition Advocate"
        ja_notes = [n for n in result.notes if "J&A" in n or "Sole source" in n]
        assert len(ja_notes) > 0

    def test_qcode_trace_is_auditable(self):
        """Every PolicyService output must include a Q-code trace for audit."""
        result = self.svc.evaluate({
            "value": 2_000_000, "services": True, "it_related": False,
            "sole_source": False, "commercial_item": True,
        })
        assert len(result.qcode_trace) > 0
        for entry in result.qcode_trace:
            assert entry.code.startswith("Q")
            assert entry.authority
            assert entry.answer

    def test_thresholds_checked_includes_new_seeds(self):
        """Verify new threshold seeds appear in the output."""
        result = self.svc.evaluate({
            "value": 20_000_000, "services": True, "it_related": True,
            "sole_source": False, "commercial_item": False,
        })
        assert "gao_protest_civilian_task_order" in result.thresholds_checked
        assert "debriefing_task_order" in result.thresholds_checked
        assert result.thresholds_checked["sat"] == 350000
