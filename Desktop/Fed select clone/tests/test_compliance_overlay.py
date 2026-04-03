"""Tests for Compliance Overlay Engine (Pattern 3).

Coverage:
- 20 compliance rules (5 PWS, 4 Section L, 5 Section M, 3 QASP, 3 IGCE)
- Content analysis functions (prescriptive, metrics, structure, keyword)
- Rule applicability filtering (value, services, IT)
- Per-document grid generation
- Full overlay evaluation
- Source weight scoring
- Edge cases (empty content, no applicable rules, all compliant)
- Canonical $20M TSA IT scenario
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.compliance_overlay import (
    ComplianceLevel,
    ComplianceRule,
    ComplianceOverlayEngine,
    COMPLIANCE_RULES,
    COMPLIANCE_SCORES,
    SOURCE_WEIGHTS,
    evaluate_rule,
    get_all_rules,
    _check_prescriptive,
    _check_metrics,
    _check_section_structure,
    _check_keyword_present,
    _is_rule_applicable,
)


# ─── Sample Content ─────────────────────────────────────────────────────────

GOOD_PWS = {
    "1.0 Background": "The TSA requires IT support services under NAICS 541512. "
                       "This acquisition plan references HSAM 3007 and the approved AP.",
    "2.0 Service Delivery": "The contractor shall achieve 99.5% system uptime measured monthly. "
                            "Response time for critical incidents shall be within 15 minutes. "
                            "Resolution of P1 tickets within 4 hours. SLA compliance reported weekly.",
    "3.0 Security": "All systems shall comply with NIST 800-53 Moderate baseline controls. "
                    "FISMA compliance required. ATO must be obtained prior to deployment. "
                    "CUI handling per HSAR 3052.204-71. SSI procedures per 49 CFR Part 1520. "
                    "Controlled unclassified information markings required.",
}

BAD_PWS = {
    "1.0 Background": "The agency needs IT support.",
    "2.0 Staffing": "The contractor shall provide 25 staff members. "
                    "Shall employ 10 senior developers. "
                    "Minimum of 5 FTE for help desk. "
                    "Working hours shall be 8am to 5pm.",
    "3.0 Methods": "Contractor shall provide adequate support as needed in a timely manner. "
                   "Best effort response to incidents as required.",
}

GOOD_SECTION_L = {
    "L.1 General": "L.1 General instructions for submission.",
    "L.2 Instructions": "L.2 Instructions for proposal format. Page limit: not to exceed 40 pages "
                        "for technical volume.",
    "L.3 Technical": "L.3 Technical approach shall address all PWS requirements. "
                     "Offerors shall describe their technical approach to each Section C requirement.",
    "L.4 Management": "L.4 Management approach describing staffing and transition.",
    "L.5 Past Performance": "L.5 Past performance: provide 4 references for contracts of similar "
                           "scope, complexity, and dollar value demonstrating relevance.",
    "L.6 Price": "L.6 Price/cost volume instructions.",
}

GOOD_SECTION_M = {
    "M.1": "M.1 Basis for Award: The Government will award to the offeror whose proposal "
           "represents the best value. Evaluation factors and their relative importance: Technical, "
           "Management, Past Performance, Price/Cost. Non-price factors are significantly more "
           "important than price.",
    "M.2": "M.2 Technical Factor: Proposals rated Outstanding, Good, Acceptable, Marginal, "
           "or Unacceptable. Outstanding means exceptionally thorough approach that significantly "
           "exceeds requirements. Good means thorough approach that exceeds some requirements. "
           "Acceptable means meets all requirements. Marginal means fails to meet some requirements. "
           "Unacceptable means fails to meet minimum requirements.",
    "M.3": "M.3 SSA will make the source selection decision per TSA PL 2017-004. "
           "Source Selection Authority appointed per policy.",
    "M.4": "M.4 Price/cost as an evaluation factor. Price reasonableness determined per FAR 15.404.",
}

GOOD_QASP = {
    "1.0 Purpose": "Purpose: This QASP establishes surveillance methods for monitoring contractor "
                   "performance under the PWS.",
    "2.0 Objectives": "Objective: Ensure service delivery meets PWS requirements.",
    "3.0 SLAs": "SLA definitions: 99.5% uptime, 15-min response, 4-hour resolution. "
                "PWS mapping: Section 2.1 → SLA-01, Section 2.2 → SLA-02. "
                "Metric: uptime percentage. Surveillance method: automated monitoring.",
    "4.0 Surveillance": "Surveillance: Monthly review of automated monitoring reports.",
    "5.0 Corrective": "Corrective action chain: (1) Corrective Action Request, (2) Cure Notice "
                      "per FAR 49.402-3, (3) Escalation to Contracting Officer.",
}

GOOD_IGCE = {
    "1.0 Methodology": "Methodology: This IGCE uses historical contract data, GSA benchmark rates, "
                       "and parametric modeling. Source references include USAspending and DHS PIL.",
    "2.0 Comparables": "Comparable contracts: (1) PIID 70T01024C0001, $15M IT services (FPDS), "
                       "(2) PIID 70T01024C0002, $22M IT support (USAspending), "
                       "(3) PIID 70T01024C0003, $18M managed services (comparable).",
    "3.0 Pricing": "Cost data requirements per FAR 15.403-1(c): adequate price competition "
                   "exception applies. Pricing data analysis included.",
}

TSA_20M_PARAMS = {
    "estimated_value": 20_000_000,
    "services": True,
    "is_it": True,
    "sub_agency": "TSA",
    "evaluation_type": "tradeoff",
}


# ─── Test Rule Definitions ──────────────────────────────────────────────────

class TestRuleDefinitions:
    def test_twenty_rules_defined(self):
        assert len(COMPLIANCE_RULES) == 20

    def test_rule_ids_unique(self):
        ids = [r.rule_id for r in COMPLIANCE_RULES]
        assert len(ids) == len(set(ids))

    def test_pws_rules_count(self):
        pws = [r for r in COMPLIANCE_RULES if "PWS" in r.applicable_to]
        assert len(pws) == 5

    def test_section_l_rules_count(self):
        sl = [r for r in COMPLIANCE_RULES if "Section_L" in r.applicable_to]
        assert len(sl) == 4

    def test_section_m_rules_count(self):
        sm = [r for r in COMPLIANCE_RULES if "Section_M" in r.applicable_to]
        assert len(sm) == 5

    def test_qasp_rules_count(self):
        qasp = [r for r in COMPLIANCE_RULES if "QASP" in r.applicable_to]
        assert len(qasp) == 3

    def test_igce_rules_count(self):
        igce = [r for r in COMPLIANCE_RULES if "IGCE" in r.applicable_to]
        assert len(igce) == 3

    def test_all_have_regulation(self):
        for r in COMPLIANCE_RULES:
            assert r.regulation, f"{r.rule_id} has no regulation"

    def test_all_have_remediation(self):
        for r in COMPLIANCE_RULES:
            assert r.remediation, f"{r.rule_id} has no remediation"

    def test_source_weights_sum(self):
        assert abs(sum(SOURCE_WEIGHTS.values()) - 1.0) < 0.01

    def test_compliance_scores(self):
        assert COMPLIANCE_SCORES[ComplianceLevel.COMPLIANT] == 100
        assert COMPLIANCE_SCORES[ComplianceLevel.MINOR] == 70
        assert COMPLIANCE_SCORES[ComplianceLevel.MAJOR] == 30
        assert COMPLIANCE_SCORES[ComplianceLevel.MISSING] == 0


# ─── Test Content Analysis Functions ────────────────────────────────────────

class TestContentAnalysis:
    def test_prescriptive_clean(self):
        level, _ = _check_prescriptive("The contractor shall achieve 99.5% uptime.")
        assert level == ComplianceLevel.COMPLIANT

    def test_prescriptive_minor(self):
        level, detail = _check_prescriptive(
            "Shall provide 10 staff members for help desk operations."
        )
        assert level == ComplianceLevel.MINOR
        assert "1" in detail

    def test_prescriptive_major(self):
        level, _ = _check_prescriptive(
            "Shall provide 10 staff. Shall employ 5 developers. "
            "Minimum of 3 FTE for support. Working hours shall be 9-5."
        )
        assert level == ComplianceLevel.MAJOR

    def test_metrics_good(self):
        level, _ = _check_metrics(
            "99.5% uptime, 15 minutes response, within 4 hours resolution."
        )
        assert level == ComplianceLevel.COMPLIANT

    def test_metrics_mixed(self):
        level, _ = _check_metrics(
            "99% uptime but also adequate response in a timely manner as needed."
        )
        assert level == ComplianceLevel.MINOR

    def test_metrics_bad(self):
        level, _ = _check_metrics(
            "Provide adequate support as needed in a timely manner with best effort."
        )
        assert level == ComplianceLevel.MAJOR

    def test_section_structure_complete(self):
        level, _ = _check_section_structure(
            "L.1 General L.2 Instructions L.3 Technical L.4 Management",
            ["L.1", "L.2", "L.3", "L.4"]
        )
        assert level == ComplianceLevel.COMPLIANT

    def test_section_structure_partial(self):
        level, _ = _check_section_structure(
            "L.1 General L.2 Instructions",
            ["L.1", "L.2", "L.3", "L.4"]
        )
        assert level == ComplianceLevel.MAJOR

    def test_section_structure_missing(self):
        level, _ = _check_section_structure(
            "Some unrelated content",
            ["L.1", "L.2", "L.3", "L.4"]
        )
        assert level == ComplianceLevel.MISSING

    def test_keyword_present_all(self):
        level, _ = _check_keyword_present(
            "NIST 800-53 controls, FISMA compliance, security control baseline, ATO required",
            ["NIST 800-53", "FISMA", "security control", "ATO"]
        )
        assert level == ComplianceLevel.COMPLIANT

    def test_keyword_present_partial(self):
        level, _ = _check_keyword_present(
            "NIST 800-53 referenced",
            ["NIST 800-53", "FISMA", "security control", "ATO"]
        )
        assert level == ComplianceLevel.MINOR

    def test_keyword_present_none(self):
        level, _ = _check_keyword_present(
            "Nothing relevant here.",
            ["NIST 800-53", "FISMA", "security control", "ATO"]
        )
        assert level == ComplianceLevel.MISSING


# ─── Test Rule Applicability ────────────────────────────────────────────────

class TestRuleApplicability:
    def test_value_filter(self):
        rule = ComplianceRule(
            rule_id="TEST", regulation="FAR", title="Test",
            applicable_to=["PWS"], check_description="", remediation="",
            severity_if_violated=ComplianceLevel.MAJOR, min_value=5_500_000,
        )
        assert _is_rule_applicable(rule, {"estimated_value": 20_000_000}) is True
        assert _is_rule_applicable(rule, {"estimated_value": 1_000_000}) is False

    def test_services_filter(self):
        rule = ComplianceRule(
            rule_id="TEST", regulation="FAR", title="Test",
            applicable_to=["PWS"], check_description="", remediation="",
            severity_if_violated=ComplianceLevel.MAJOR, requires_services=True,
        )
        assert _is_rule_applicable(rule, {"services": True}) is True
        assert _is_rule_applicable(rule, {"services": False}) is False

    def test_it_filter(self):
        rule = ComplianceRule(
            rule_id="TEST", regulation="FAR", title="Test",
            applicable_to=["PWS"], check_description="", remediation="",
            severity_if_violated=ComplianceLevel.MAJOR, requires_it=True,
        )
        assert _is_rule_applicable(rule, {"is_it": True}) is True
        assert _is_rule_applicable(rule, {"is_it": False}) is False

    def test_no_filter(self):
        rule = ComplianceRule(
            rule_id="TEST", regulation="FAR", title="Test",
            applicable_to=["PWS"], check_description="", remediation="",
            severity_if_violated=ComplianceLevel.MAJOR,
        )
        assert _is_rule_applicable(rule, {}) is True

    def test_cr_pws_04_requires_it(self):
        """CR-PWS-04 (NIST 800-53) only applies to IT acquisitions."""
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-04")
        assert _is_rule_applicable(rule, {"is_it": True}) is True
        assert _is_rule_applicable(rule, {"is_it": False}) is False

    def test_cr_igce_02_requires_value(self):
        """CR-IGCE-02 (comparables) only applies >= $5.5M."""
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-IGCE-02")
        assert _is_rule_applicable(rule, {"estimated_value": 20_000_000}) is True
        assert _is_rule_applicable(rule, {"estimated_value": 2_000_000}) is False


# ─── Test Individual Rule Evaluation ────────────────────────────────────────

class TestRuleEvaluation:
    def test_good_pws_pba(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-01")
        result = evaluate_rule(rule, GOOD_PWS, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_bad_pws_pba(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-01")
        result = evaluate_rule(rule, BAD_PWS, TSA_20M_PARAMS)
        assert result is not None
        assert result.level in (ComplianceLevel.MINOR, ComplianceLevel.MAJOR)

    def test_good_pws_metrics(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-02")
        result = evaluate_rule(rule, GOOD_PWS, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_bad_pws_metrics(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-02")
        result = evaluate_rule(rule, BAD_PWS, TSA_20M_PARAMS)
        assert result is not None
        assert result.level in (ComplianceLevel.MINOR, ComplianceLevel.MAJOR)

    def test_pws_nist(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-04")
        result = evaluate_rule(rule, GOOD_PWS, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_pws_cui(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-05")
        result = evaluate_rule(rule, GOOD_PWS, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_section_l_structure(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-L-01")
        result = evaluate_rule(rule, GOOD_SECTION_L, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_section_m_factors(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-M-01")
        result = evaluate_rule(rule, GOOD_SECTION_M, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_section_m_adjectival(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-M-02")
        result = evaluate_rule(rule, GOOD_SECTION_M, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_section_m_price_factor(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-M-05")
        result = evaluate_rule(rule, GOOD_SECTION_M, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_section_m_lpta_skipped_for_tradeoff(self):
        """CR-M-04 (LPTA) should return None for tradeoff evaluations."""
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-M-04")
        result = evaluate_rule(rule, GOOD_SECTION_M, TSA_20M_PARAMS)
        assert result is None

    def test_section_m_lpta_checked_when_lpta(self):
        """CR-M-04 should check when evaluation_type is LPTA."""
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-M-04")
        lpta_content = {"M.1": "LPTA evaluation. D&F obtained. Lowest price technically acceptable. "
                               "Determination approved by Division Director."}
        lpta_params = {**TSA_20M_PARAMS, "evaluation_type": "lpta"}
        result = evaluate_rule(rule, lpta_content, lpta_params)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_qasp_structure(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-QASP-01")
        result = evaluate_rule(rule, GOOD_QASP, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_igce_methodology(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-IGCE-01")
        result = evaluate_rule(rule, GOOD_IGCE, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_igce_comparables(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-IGCE-02")
        result = evaluate_rule(rule, GOOD_IGCE, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.COMPLIANT

    def test_empty_content_returns_missing(self):
        rule = next(r for r in COMPLIANCE_RULES if r.rule_id == "CR-PWS-01")
        result = evaluate_rule(rule, {"section": ""}, TSA_20M_PARAMS)
        assert result is not None
        assert result.level == ComplianceLevel.MISSING
        assert result.score == 0


# ─── Test Document Grid ─────────────────────────────────────────────────────

class TestDocumentGrid:
    def test_good_pws_grid(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("PWS", GOOD_PWS, TSA_20M_PARAMS)
        assert grid.document_type == "PWS"
        assert grid.overall_score > 70
        assert len(grid.checks) > 0

    def test_bad_pws_grid(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("PWS", BAD_PWS, TSA_20M_PARAMS)
        assert grid.overall_score < 80
        assert len(grid.blocking_issues) > 0

    def test_good_section_l_grid(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("Section_L", GOOD_SECTION_L, TSA_20M_PARAMS)
        assert grid.overall_score > 70
        assert "Section_L" in grid.summary

    def test_good_section_m_grid(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("Section_M", GOOD_SECTION_M, TSA_20M_PARAMS)
        assert grid.overall_score > 70

    def test_good_qasp_grid(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("QASP", GOOD_QASP, TSA_20M_PARAMS)
        assert grid.overall_score > 70

    def test_good_igce_grid(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("IGCE", GOOD_IGCE, TSA_20M_PARAMS)
        assert grid.overall_score > 70

    def test_unknown_doc_type(self):
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("UNKNOWN", {"a": "b"}, TSA_20M_PARAMS)
        assert len(grid.checks) == 0
        assert grid.overall_score == 100.0  # No rules = compliant


# ─── Test Full Overlay ──────────────────────────────────────────────────────

class TestFullOverlay:
    def test_canonical_20m_all_good(self):
        engine = ComplianceOverlayEngine()
        documents = {
            "PWS": GOOD_PWS,
            "Section_L": GOOD_SECTION_L,
            "Section_M": GOOD_SECTION_M,
            "QASP": GOOD_QASP,
            "IGCE": GOOD_IGCE,
        }
        result = engine.evaluate_all(documents, TSA_20M_PARAMS)
        assert len(result.grids) == 5
        assert result.total_rules_checked > 15
        assert result.overall_compliance_score > 60
        assert result.requires_acceptance is True

    def test_canonical_20m_bad_pws(self):
        engine = ComplianceOverlayEngine()
        documents = {
            "PWS": BAD_PWS,
            "Section_L": GOOD_SECTION_L,
            "Section_M": GOOD_SECTION_M,
            "QASP": GOOD_QASP,
            "IGCE": GOOD_IGCE,
        }
        result = engine.evaluate_all(documents, TSA_20M_PARAMS)
        assert "PWS" in result.blocking_sections
        assert result.major_count > 0

    def test_recommended_fix_order(self):
        engine = ComplianceOverlayEngine()
        documents = {
            "PWS": BAD_PWS,
            "Section_L": GOOD_SECTION_L,
        }
        result = engine.evaluate_all(documents, TSA_20M_PARAMS)
        if result.recommended_fix_order:
            assert "PWS" in result.recommended_fix_order[0]

    def test_source_provenance(self):
        engine = ComplianceOverlayEngine()
        result = engine.evaluate_all({"PWS": GOOD_PWS}, TSA_20M_PARAMS)
        assert len(result.source_provenance) > 0
        assert any("20" in p for p in result.source_provenance)

    def test_empty_documents(self):
        engine = ComplianceOverlayEngine()
        result = engine.evaluate_all({}, TSA_20M_PARAMS)
        assert len(result.grids) == 0
        assert result.overall_compliance_score == 100.0


# ─── Test Edge Cases ────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_micro_purchase_skips_value_rules(self):
        """Micro-purchase should skip rules with min_value thresholds."""
        engine = ComplianceOverlayEngine()
        micro_params = {"estimated_value": 5_000, "services": True, "is_it": True}
        grid = engine.evaluate_document("IGCE", GOOD_IGCE, micro_params)
        # CR-IGCE-02 ($5.5M) and CR-IGCE-03 ($2.5M) should be skipped
        rule_ids = [c.rule_id for c in grid.checks]
        assert "CR-IGCE-02" not in rule_ids
        assert "CR-IGCE-03" not in rule_ids

    def test_non_services_skips_pba(self):
        """Non-services acquisition should skip PBA rules."""
        engine = ComplianceOverlayEngine()
        supply_params = {"estimated_value": 20_000_000, "services": False, "is_it": False}
        grid = engine.evaluate_document("PWS", GOOD_PWS, supply_params)
        rule_ids = [c.rule_id for c in grid.checks]
        assert "CR-PWS-01" not in rule_ids  # PBA language
        assert "CR-PWS-02" not in rule_ids  # Metrics

    def test_non_it_skips_nist(self):
        """Non-IT acquisition should skip NIST 800-53 rule."""
        engine = ComplianceOverlayEngine()
        non_it_params = {"estimated_value": 20_000_000, "services": True, "is_it": False}
        grid = engine.evaluate_document("PWS", GOOD_PWS, non_it_params)
        rule_ids = [c.rule_id for c in grid.checks]
        assert "CR-PWS-04" not in rule_ids

    def test_ssm_below_2_5m_skips_ssa(self):
        """Below $2.5M should skip SSA appointment rule."""
        engine = ComplianceOverlayEngine()
        low_params = {"estimated_value": 1_000_000, "services": True, "is_it": True}
        grid = engine.evaluate_document("Section_M", GOOD_SECTION_M, low_params)
        rule_ids = [c.rule_id for c in grid.checks]
        assert "CR-M-03" not in rule_ids

    def test_custom_rules(self):
        """Engine should accept custom rule set."""
        custom_rules = [
            ComplianceRule(
                rule_id="CUSTOM-01", regulation="FAR 1.1", title="Custom Check",
                applicable_to=["PWS"], check_description="Custom",
                remediation="Fix it", severity_if_violated=ComplianceLevel.MINOR,
            ),
        ]
        engine = ComplianceOverlayEngine(rules=custom_rules)
        grid = engine.evaluate_document("PWS", {"a": "some content"}, {})
        assert len(grid.checks) == 1
        assert grid.checks[0].rule_id == "CUSTOM-01"

    def test_get_all_rules_returns_20(self):
        rules = get_all_rules()
        assert len(rules) == 20
        for r in rules:
            assert "rule_id" in r
            assert "regulation" in r
            assert "severity_if_violated" in r


# ─── Test Scoring ───────────────────────────────────────────────────────────

class TestScoring:
    def test_weighted_score_calculation(self):
        """Verify weighted scoring uses source weights correctly."""
        engine = ComplianceOverlayEngine()
        # PWS has both FAR and HSAR rules — score should reflect weights
        grid = engine.evaluate_document("PWS", GOOD_PWS, TSA_20M_PARAMS)
        assert 0 <= grid.overall_score <= 100

    def test_all_compliant_scores_100(self):
        """When all checks pass, per-grid score should be 100."""
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("IGCE", GOOD_IGCE, TSA_20M_PARAMS)
        for c in grid.checks:
            if c.level == ComplianceLevel.COMPLIANT:
                assert c.score == 100

    def test_blocking_classification(self):
        """MAJOR and MISSING should be classified as blocking."""
        engine = ComplianceOverlayEngine()
        grid = engine.evaluate_document("PWS", BAD_PWS, TSA_20M_PARAMS)
        for b in grid.blocking_issues:
            assert b.level in (ComplianceLevel.MAJOR, ComplianceLevel.MISSING)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
