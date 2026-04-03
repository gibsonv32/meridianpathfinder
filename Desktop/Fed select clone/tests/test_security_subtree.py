"""Tests for Security Sub-Tree Expansion (Pattern 2).

Coverage:
- Sub-code definitions (8 codes, properties, authorities)
- Trigger evaluation (per-subcode condition logic)
- D142 alias resolution
- Non-waivable gate enforcement
- $20M TSA IT services scenario (canonical)
- Completeness enrichment integration
- Edge cases (no IT, no on-site, classified-only, etc.)
"""
import sys
import os
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.security_subtree import (
    SECURITY_SUBCODES,
    NON_WAIVABLE_SUBCODES,
    D142_ALIAS,
    expand_security_subcodes,
    resolve_d142_alias,
    get_non_waivable_subcodes,
    get_all_subcodes,
    enrich_completeness_with_security,
    _check_trigger,
)


# ── Test Sub-Code Definitions ────────────────────────────────────────────────

class TestSubCodeDefinitions:
    def test_eight_subcodes_defined(self):
        assert len(SECURITY_SUBCODES) == 8

    def test_all_codes_follow_d120_pattern(self):
        for sc in SECURITY_SUBCODES:
            assert sc.code.startswith("D120."), f"{sc.code} doesn't follow D120.xx"

    def test_sequential_numbering(self):
        codes = [sc.code for sc in SECURITY_SUBCODES]
        expected = [f"D120.0{i}" for i in range(1, 9)]
        assert codes == expected

    def test_all_have_far_authorities(self):
        for sc in SECURITY_SUBCODES:
            assert len(sc.far_authorities) > 0, f"{sc.code} has no FAR authorities"

    def test_all_have_responsible_party(self):
        for sc in SECURITY_SUBCODES:
            assert sc.responsible_party, f"{sc.code} has no responsible party"

    def test_non_waivable_count(self):
        # D120.01, D120.02, D120.04, D120.05 are blocking
        assert len(NON_WAIVABLE_SUBCODES) == 4

    def test_non_waivable_codes(self):
        expected = {"D120.01", "D120.02", "D120.04", "D120.05"}
        assert NON_WAIVABLE_SUBCODES == expected

    def test_d142_alias(self):
        assert resolve_d142_alias() == "D120.03"


# ── Test Trigger Evaluation ──────────────────────────────────────────────────

class TestTriggerEvaluation:
    """Test each sub-code's trigger conditions."""

    def test_d120_01_personnel_on_site(self):
        """D120.01 triggers when on_site=True."""
        result = expand_security_subcodes({"on_site": True})
        codes = [r["code"] for r in result]
        assert "D120.01" in codes

    def test_d120_01_personnel_classified(self):
        """D120.01 also triggers when classified=True (OR condition)."""
        result = expand_security_subcodes({"classified": True})
        codes = [r["code"] for r in result]
        assert "D120.01" in codes

    def test_d120_02_fisma_it_not_cloud(self):
        """D120.02 triggers for IT that isn't cloud-only."""
        result = expand_security_subcodes({"is_it": True, "cloud_only": False})
        codes = [r["code"] for r in result]
        assert "D120.02" in codes

    def test_d120_02_no_trigger_cloud_only(self):
        """D120.02 does NOT trigger for cloud-only IT."""
        result = expand_security_subcodes({"is_it": True, "cloud_only": True})
        codes = [r["code"] for r in result]
        assert "D120.02" not in codes

    def test_d120_03_fedramp_cloud(self):
        """D120.03 triggers for IT with cloud."""
        result = expand_security_subcodes({"is_it": True, "cloud": True})
        codes = [r["code"] for r in result]
        assert "D120.03" in codes

    def test_d120_04_twic_tsa_on_site(self):
        """D120.04 triggers when on TSA facilities."""
        result = expand_security_subcodes({
            "on_site": True, "tsa_facilities": True
        })
        codes = [r["code"] for r in result]
        assert "D120.04" in codes

    def test_d120_04_no_trigger_without_tsa(self):
        """D120.04 does NOT trigger without tsa_facilities."""
        result = expand_security_subcodes({"on_site": True, "tsa_facilities": False})
        codes = [r["code"] for r in result]
        assert "D120.04" not in codes

    def test_d120_05_ssi_tsa_with_security_info(self):
        """D120.05 triggers for TSA handling security info."""
        result = expand_security_subcodes({
            "is_tsa": True, "handles_security_info": True
        })
        codes = [r["code"] for r in result]
        assert "D120.05" in codes

    def test_d120_05_auto_infer_tsa(self):
        """D120.05 auto-infers is_tsa from sub_agency='TSA'."""
        result = expand_security_subcodes({
            "sub_agency": "TSA", "is_it": True,
        })
        codes = [r["code"] for r in result]
        # is_tsa inferred, handles_security_info inferred for TSA IT
        assert "D120.05" in codes

    def test_d120_06_incident_response_it(self):
        """D120.06 triggers for IT acquisitions."""
        result = expand_security_subcodes({"is_it": True})
        codes = [r["code"] for r in result]
        assert "D120.06" in codes

    def test_d120_06_incident_response_pii(self):
        """D120.06 also triggers for PII handling (OR condition)."""
        result = expand_security_subcodes({"handles_pii": True})
        codes = [r["code"] for r in result]
        assert "D120.06" in codes

    def test_d120_07_cui_marking(self):
        """D120.07 triggers for CUI."""
        result = expand_security_subcodes({"has_cui": True})
        codes = [r["code"] for r in result]
        assert "D120.07" in codes

    def test_d120_07_classified(self):
        """D120.07 also triggers for classified (OR condition)."""
        result = expand_security_subcodes({"classified": True})
        codes = [r["code"] for r in result]
        assert "D120.07" in codes

    def test_d120_08_cyber_posture(self):
        """D120.08 triggers for high-value IT on federal network."""
        result = expand_security_subcodes({
            "is_it": True,
            "integrates_federal_network": True,
            "estimated_value": 20_000_000,
        })
        codes = [r["code"] for r in result]
        assert "D120.08" in codes

    def test_d120_08_no_trigger_low_value(self):
        """D120.08 does NOT trigger below $5.5M."""
        result = expand_security_subcodes({
            "is_it": True,
            "integrates_federal_network": True,
            "estimated_value": 3_000_000,
        })
        codes = [r["code"] for r in result]
        assert "D120.08" not in codes


# ── Test Canonical $20M TSA IT Services Scenario ─────────────────────────────

class TestCanonicalScenario:
    """$20M TSA IT services, on-site, FISMA, TWIC, federal network."""

    TSA_20M_PARAMS = {
        "estimated_value": 20_000_000,
        "is_it": True,
        "on_site": True,
        "tsa_facilities": True,
        "sub_agency": "TSA",
        "cloud_only": False,
        "has_cui": True,
        "integrates_federal_network": True,
    }

    def test_triggers_six_subcodes(self):
        """$20M TSA IT should trigger 6 sub-codes per spec."""
        result = expand_security_subcodes(self.TSA_20M_PARAMS)
        codes = {r["code"] for r in result}
        # Per Phase 24/26 spec example:
        # D120.01 (on_site), D120.02 (IT, not cloud-only),
        # D120.04 (TSA facility), D120.05 (TSA+SSI auto-inferred),
        # D120.06 (IT), D120.07 (CUI), D120.08 (IT + fed network + $20M)
        expected = {"D120.01", "D120.02", "D120.04", "D120.05", "D120.06", "D120.07", "D120.08"}
        assert codes == expected, f"Expected {expected}, got {codes}"

    def test_blocking_subcodes_in_scenario(self):
        result = expand_security_subcodes(self.TSA_20M_PARAMS)
        blocking = [r["code"] for r in result if r["blocking"]]
        assert set(blocking) == {"D120.01", "D120.02", "D120.04", "D120.05"}

    def test_all_have_status_missing(self):
        result = expand_security_subcodes(self.TSA_20M_PARAMS)
        for r in result:
            assert r["status"] == "missing"


# ── Test Edge Cases ──────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_no_params_returns_empty(self):
        """No params = no sub-codes triggered."""
        result = expand_security_subcodes({})
        assert len(result) == 0

    def test_non_it_non_onsite(self):
        """Non-IT, off-site acquisition triggers nothing."""
        result = expand_security_subcodes({
            "estimated_value": 5_000_000,
            "is_it": False,
            "on_site": False,
        })
        assert len(result) == 0

    def test_classified_only(self):
        """Classified flag triggers D120.01 + D120.07."""
        result = expand_security_subcodes({"classified": True})
        codes = {r["code"] for r in result}
        assert "D120.01" in codes  # Personnel security
        assert "D120.07" in codes  # Data classification

    def test_pii_only(self):
        """PII flag triggers only D120.06."""
        result = expand_security_subcodes({"handles_pii": True})
        codes = {r["code"] for r in result}
        assert codes == {"D120.06"}

    def test_micro_purchase_it(self):
        """$10K IT on federal network — D120.08 doesn't trigger (below $5.5M)."""
        result = expand_security_subcodes({
            "is_it": True,
            "integrates_federal_network": True,
            "estimated_value": 10_000,
        })
        codes = {r["code"] for r in result}
        assert "D120.08" not in codes
        # But D120.02, D120.06 still trigger (IT-related)
        assert "D120.06" in codes


# ── Test Completeness Enrichment ─────────────────────────────────────────────

class TestCompletenessEnrichment:
    def test_enrichment_with_d120(self):
        """When D120 is in completeness result, sub-codes are injected."""
        completeness = {
            "documents": [
                {"dcode": "D102", "status": "satisfied"},
                {"dcode": "D120", "status": "missing"},
            ],
            "package_ready": True,
            "completeness_pct": 50.0,
        }
        params = {"is_it": True, "on_site": True, "sub_agency": "TSA",
                  "tsa_facilities": True, "cloud_only": False,
                  "has_cui": True, "integrates_federal_network": True,
                  "estimated_value": 20_000_000}

        result = enrich_completeness_with_security(completeness, params)

        assert "security_subcodes" in result
        assert len(result["security_subcodes"]) > 0
        assert "security_summary" in result
        assert result["security_summary"]["total_subcodes"] > 0

    def test_enrichment_blocks_package(self):
        """Blocking sub-codes set package_ready=False."""
        completeness = {
            "documents": [
                {"dcode": "D120", "status": "missing"},
            ],
            "package_ready": True,
        }
        params = {"on_site": True}  # Triggers D120.01 (blocking)

        result = enrich_completeness_with_security(completeness, params)
        assert result["package_ready"] is False
        assert result["security_summary"]["blocking_missing"] > 0

    def test_enrichment_without_d120(self):
        """No D120 in completeness = no sub-code expansion."""
        completeness = {
            "documents": [{"dcode": "D102", "status": "satisfied"}],
            "package_ready": True,
        }
        result = enrich_completeness_with_security(completeness, {"is_it": True})
        assert result["security_subcodes"] == []

    def test_satisfied_subcodes_dont_block(self):
        """Sub-codes marked satisfied don't count as blocking."""
        completeness = {
            "documents": [
                {"dcode": "D120", "status": "pending"},
                {"dcode": "D120.01", "status": "satisfied"},
            ],
            "package_ready": True,
        }
        params = {"on_site": True, "is_it": False}
        # Only D120.01 triggers, and it's satisfied
        result = enrich_completeness_with_security(completeness, params)
        assert result["security_summary"]["blocking_missing"] == 0


# ── Test get_all_subcodes ────────────────────────────────────────────────────

class TestMetadata:
    def test_get_all_subcodes_returns_8(self):
        all_sc = get_all_subcodes()
        assert len(all_sc) == 8

    def test_get_all_subcodes_has_required_fields(self):
        for sc in get_all_subcodes():
            assert "code" in sc
            assert "name" in sc
            assert "trigger_conditions" in sc
            assert "far_authorities" in sc
            assert "blocking" in sc

    def test_get_non_waivable(self):
        nw = get_non_waivable_subcodes()
        assert isinstance(nw, frozenset)
        assert len(nw) == 4


# ── Run Tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
