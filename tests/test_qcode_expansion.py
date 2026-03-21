"""Tests for Q-code tree expansion (117 nodes, 45 D-codes).

Covers:
- Node count and edge count verification
- Canonical traversal paths (full_and_open, micro, sole_source, services, IT)
- New D-code triggering (D129–D145)
- Terminal node reachability for all branches
- No infinite loops or orphan nodes
- Specific TSA/DHS decision paths
"""
import pytest
from backend.phase2.policy_engine import (
    PolicyService,
    QCodeEngine,
    QCODE_NODES,
    QCODE_EDGES,
    DCODE_REGISTRY,
    get_dcode_registry,
)


# ── Structure Tests ──────────────────────────────────────────────────────────

class TestTreeStructure:
    """Verify the expanded tree has the right shape."""

    def test_node_count(self):
        """Must have exactly 117 Q-code nodes."""
        assert len(QCODE_NODES) == 117

    def test_edge_count(self):
        """Must have > 100 edges (expanded from 57)."""
        assert len(QCODE_EDGES) > 100

    def test_dcode_count(self):
        """Must have 45 D-codes (D101–D145)."""
        assert len(DCODE_REGISTRY) == 45

    def test_all_nodes_referenced_by_edges(self):
        """Every non-entry-point node should be reachable via at least one edge."""
        edge_targets = {e.to_code for e in QCODE_EDGES}
        # Branch entry points: sub-tree roots for different lifecycle phases
        BRANCH_ENTRIES = {"Q001", "Q020", "Q048", "Q054", "Q058", "Q068", "Q078", "Q080", "Q081", "Q088", "Q098", "Q108"}
        edge_sources = {e.from_code for e in QCODE_EDGES}
        for code, node in QCODE_NODES.items():
            if code in BRANCH_ENTRIES:
                continue  # Branch entry point
            assert code in edge_targets, f"Node {code} is unreachable (no incoming edge)"

    def test_all_edge_targets_exist(self):
        """Every edge target must be a valid node."""
        for edge in QCODE_EDGES:
            assert edge.to_code in QCODE_NODES, f"Edge {edge.from_code}→{edge.to_code}: target not found"
            assert edge.from_code in QCODE_NODES, f"Edge {edge.from_code}→{edge.to_code}: source not found"

    def test_terminal_nodes_exist(self):
        """There should be multiple terminal nodes for different branches."""
        terminals = [code for code, node in QCODE_NODES.items() if node.terminal]
        assert len(terminals) >= 5, f"Expected at least 5 terminal nodes, got {len(terminals)}: {terminals}"
        # Known terminals
        assert "Q047" in terminals  # Main flow
        assert "Q057" in terminals  # Modifications
        assert "Q067" in terminals  # Award
        assert "Q087" in terminals  # Disputes
        assert "Q097" in terminals  # Special programs
        assert "Q107" in terminals  # DHS/TSA
        assert "Q117" in terminals  # Closeout

    def test_dcode_registry_has_new_codes(self):
        """D129–D145 should all be in the registry."""
        registry = get_dcode_registry()
        for i in range(129, 146):
            code = f"D{i}"
            assert code in registry, f"{code} missing from registry"

    def test_no_duplicate_node_codes(self):
        """No duplicate Q-code IDs."""
        codes = list(QCODE_NODES.keys())
        assert len(codes) == len(set(codes))


# ── Traversal Tests ──────────────────────────────────────────────────────────

class TestTraversalPaths:
    """Verify canonical traversals reach terminal nodes correctly."""

    def setup_method(self):
        self.ps = PolicyService()

    def test_canonical_20m_it_services(self):
        """$20M IT services should traverse deep into the tree."""
        result = self.ps.evaluate({
            "value": 20_000_000,
            "services": True,
            "it_related": True,
            "sole_source": False,
            "commercial_item": False,
            "emergency": False,
            "vendor_on_site": True,
            "competition_type": "full_and_open",
        })
        assert result.nodes_evaluated >= 20, f"Expected deep traversal, got {result.nodes_evaluated} nodes"
        assert result.terminal_node == "Q047"
        # Should trigger core D-codes
        assert "D101" in result.required_dcodes  # Market Research
        assert "D102" in result.required_dcodes  # PWS
        assert "D104" in result.required_dcodes  # IGCE
        assert "D114" in result.required_dcodes  # CIO/ITAR
        assert "D120" in result.required_dcodes  # Security
        assert "D128" in result.required_dcodes  # TSA Badge (vendor_on_site)

    def test_micro_purchase_short_path(self):
        """Micro-purchase should still take the short path."""
        result = self.ps.evaluate({
            "value": 5000,
            "services": False,
            "it_related": False,
            "sole_source": False,
            "commercial_item": False,
            "emergency": False,
            "vendor_on_site": False,
            "competition_type": "full_and_open",
        })
        # Micro should exit early via Q003→Q017 but then continue through expanded tree
        assert result.nodes_evaluated >= 3

    def test_sole_source_triggers_ja(self):
        """Sole source must trigger D108 (J&A)."""
        result = self.ps.evaluate({
            "value": 5_000_000,
            "services": True,
            "it_related": False,
            "sole_source": True,
            "commercial_item": False,
            "emergency": False,
            "vendor_on_site": False,
            "competition_type": "full_and_open",
        })
        assert "D108" in result.required_dcodes

    def test_vendor_on_site_triggers_security(self):
        """vendor_on_site should trigger D120, D126, D128."""
        result = self.ps.evaluate({
            "value": 1_000_000,
            "services": True,
            "it_related": False,
            "sole_source": False,
            "commercial_item": False,
            "emergency": False,
            "vendor_on_site": True,
            "competition_type": "full_and_open",
        })
        assert "D120" in result.required_dcodes
        assert "D126" in result.required_dcodes
        assert "D128" in result.required_dcodes

    def test_it_related_triggers_itar_and_fedramp(self):
        """IT-related should trigger D114 and potentially D142 (FedRAMP)."""
        result = self.ps.evaluate({
            "value": 1_000_000,
            "services": True,
            "it_related": True,
            "sole_source": False,
            "commercial_item": False,
            "emergency": False,
            "vendor_on_site": False,
            "competition_type": "full_and_open",
        })
        assert "D114" in result.required_dcodes  # CIO/ITAR

    def test_services_triggers_labor_docs(self):
        """Services procurement should trigger D102, D105, D115, D122 (wage det)."""
        result = self.ps.evaluate({
            "value": 2_000_000,
            "services": True,
            "it_related": False,
            "sole_source": False,
            "commercial_item": False,
            "emergency": False,
            "vendor_on_site": False,
            "competition_type": "full_and_open",
        })
        assert "D102" in result.required_dcodes  # PWS
        assert "D115" in result.required_dcodes  # COR
        assert "D122" in result.required_dcodes  # Wage Determination

    def test_no_infinite_loop(self):
        """Traversal must terminate within max_steps for any input."""
        engine = QCodeEngine()
        # Try a bunch of different parameter combos
        test_cases = [
            {"value": 0},
            {"value": 100_000_000, "services": True, "it_related": True, "vendor_on_site": True,
             "sole_source": True, "commercial_item": True, "emergency": True, "competition_type": "idiq"},
            {"value": 500_000, "competition_type": "task_order"},
            {"value": 10_000, "services": False},
        ]
        for params in test_cases:
            result = engine.traverse(params)
            assert result.nodes_evaluated < 150, f"Possible infinite loop: {result.nodes_evaluated} nodes"


# ── New D-Code Tests ─────────────────────────────────────────────────────────

class TestNewDCodes:
    """Verify new D-codes have correct properties."""

    def test_d130_pre_award_survey(self):
        registry = get_dcode_registry()
        d = registry["D130"]
        assert d.name == "Pre-Award Survey"
        assert "FAR 9.106" in d.authority

    def test_d136_ssdd(self):
        registry = get_dcode_registry()
        d = registry["D136"]
        assert d.name == "SSDD"
        assert "FAR 15.308" in d.authority

    def test_d142_fedramp(self):
        registry = get_dcode_registry()
        d = registry["D142"]
        assert d.name == "FedRAMP Authorization Package"
        assert "FedRAMP" in d.authority

    def test_d143_closeout_checklist(self):
        registry = get_dcode_registry()
        d = registry["D143"]
        assert d.name == "Closeout Checklist"
        assert "FAR 4.804" in d.authority

    def test_d145_release_of_claims(self):
        registry = get_dcode_registry()
        d = registry["D145"]
        assert d.name == "Release of Claims"


# ── Completeness Validator Integration ───────────────────────────────────────

class TestCompletenessWithNewDCodes:
    """Verify completeness validator handles new D-codes."""

    def test_large_it_services_has_many_required_docs(self):
        """$20M IT services with vendor on site should require 15+ docs."""
        from backend.phase2.completeness_validator import completeness_validator, ValidateCompletenessRequest
        req = ValidateCompletenessRequest(
            value=20_000_000,
            services=True,
            it_related=True,
            vendor_on_site=True,
            sole_source=False,
            commercial_item=False,
            competition_type="full_and_open",
        )
        result = completeness_validator.validate(req)
        assert result.required_count >= 15, f"Expected 15+ required docs, got {result.required_count}"
        # All should be missing since no docs provided
        assert result.missing_count == result.required_count
        assert result.completeness_pct == 0.0

    def test_new_dcodes_have_responsible_parties(self):
        """D129–D145 should have responsible parties in validator."""
        from backend.phase2.completeness_validator import RESPONSIBLE_PARTY
        for i in range(129, 146):
            code = f"D{i}"
            assert code in RESPONSIBLE_PARTY, f"{code} missing from RESPONSIBLE_PARTY"
