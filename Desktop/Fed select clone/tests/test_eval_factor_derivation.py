"""Tests for Evaluation Factor Derivation Engine (Phase 23b).

Coverage:
- PWS requirement parsing and classification (Step 1-2)
- Factor candidate generation (Step 3)
- Subfactor mapping (Step 4)
- Weight suggestion (Step 5)
- Adjectival definition drafting (Step 6)
- Protest-proofing checks (Step 7, 6 validations)
- Full pipeline orchestration
- Canonical $20M TSA IT scenario
- Edge cases (empty PWS, LPTA, micro-purchase, single-section)
- Serialization
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.eval_factor_derivation import (
    EvalFactorDerivationEngine,
    RequirementCategory,
    EvalMethodology,
    AdjectivalRating,
    ProtestCheckStatus,
    CATEGORY_KEYWORDS,
    STANDARD_FACTORS,
    ADJECTIVAL_TEMPLATES,
    parse_pws_requirements,
    classify_requirement,
    extract_keywords,
    generate_factor_candidates,
    map_subfactors,
    suggest_weights,
    draft_adjectival_definitions,
    run_protest_proofing,
    derivation_to_dict,
)


# ─── Sample Data ────────────────────────────────────────────────────────────

CANONICAL_PWS = {
    "3.1 System Administration": (
        "The contractor shall provide system administration services for TSA's "
        "IT infrastructure including cloud platform management, database administration, "
        "and network operations. System uptime shall be 99.5% measured monthly."
    ),
    "3.2 Software Development": (
        "The contractor shall design, develop, and implement software applications "
        "using modern DevOps practices with CI/CD pipelines. Application releases "
        "shall occur within 15 days of approval."
    ),
    "3.3 Cybersecurity": (
        "The contractor shall maintain FISMA compliance per NIST 800-53 Moderate "
        "baseline. Security incidents shall be reported within 1 hour. "
        "All systems shall have current ATO. CUI and SSI handling required."
    ),
    "3.4 Program Management": (
        "The contractor shall provide program management including risk management, "
        "schedule tracking, status reporting, and resource coordination. Monthly "
        "status reports within 5 days of period end."
    ),
    "3.5 Transition": (
        "The contractor shall execute a transition-in plan within 60 days of award, "
        "including knowledge transfer, onboarding, and incumbent handoff procedures."
    ),
    "3.6 Quality Assurance": (
        "The contractor shall maintain an internal quality control program with "
        "SLA tracking, KPI dashboards, and monthly performance metrics reporting."
    ),
}

CANONICAL_L_SECTIONS = {
    "L.3": "Technical approach instructions",
    "L.4": "Management approach instructions",
    "L.5": "Past performance references",
    "L.6": "Price/cost volume",
}

TSA_20M_PARAMS = {
    "estimated_value": 20_000_000,
    "services": True,
    "is_it": True,
    "sub_agency": "TSA",
    "evaluation_type": "tradeoff",
}


# ─── Test Step 1-2: PWS Parsing and Classification ─────────────────────────

class TestPWSParsing:
    def test_parses_all_sections(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        assert len(reqs) == 6

    def test_section_refs_preserved(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        refs = [r.section_ref for r in reqs]
        assert "3.1 System Administration" in refs
        assert "3.5 Transition" in refs

    def test_technical_classification(self):
        cat = classify_requirement(
            "Design, develop, and implement software using CI/CD pipelines."
        )
        assert cat == RequirementCategory.TECHNICAL

    def test_management_classification(self):
        cat = classify_requirement(
            "Provide program management including risk management, schedule tracking."
        )
        assert cat == RequirementCategory.MANAGEMENT

    def test_security_classification(self):
        cat = classify_requirement(
            "Security clearance requirements, background suitability, CUI handling, "
            "SSI procedures, TWIC badge credentialing."
        )
        assert cat == RequirementCategory.SECURITY

    def test_transition_classification(self):
        cat = classify_requirement(
            "Execute transition-in plan, knowledge transfer, incumbent handoff."
        )
        assert cat == RequirementCategory.TRANSITION

    def test_quality_classification(self):
        cat = classify_requirement(
            "Quality control program with SLA tracking and KPI reporting."
        )
        assert cat == RequirementCategory.QUALITY

    def test_keyword_extraction(self):
        kw = extract_keywords("system administration, cloud, database, NIST 800-53, FISMA")
        assert len(kw) > 0
        assert any("system" in k.lower() for k in kw)

    def test_measurable_criteria_detected(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        sys_admin = next(r for r in reqs if "System" in r.section_ref)
        assert sys_admin.is_measurable is True

    def test_sla_target_extracted(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        sys_admin = next(r for r in reqs if "System" in r.section_ref)
        assert sys_admin.sla_target is not None
        assert "99.5" in sys_admin.sla_target

    def test_empty_pws(self):
        reqs = parse_pws_requirements({})
        assert len(reqs) == 0

    def test_empty_section_skipped(self):
        reqs = parse_pws_requirements({"3.1": "", "3.2": "Some real content"})
        assert len(reqs) == 1


# ─── Test Step 3: Factor Candidate Generation ──────────────────────────────

class TestFactorGeneration:
    def test_generates_standard_factors(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        names = [f.name for f in factors]
        assert "Technical Approach" in names
        assert "Management Approach" in names
        assert "Past Performance" in names
        assert "Price/Cost" in names

    def test_price_always_included(self):
        reqs = parse_pws_requirements({"3.1": "Simple requirement"})
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        assert any(f.name == "Price/Cost" for f in factors)

    def test_factor_ids_sequential(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        ids = [f.factor_id for f in factors]
        assert ids == sorted(ids)

    def test_pws_traceability_populated(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        tech = next(f for f in factors if f.name == "Technical Approach")
        assert len(tech.pws_traceability) > 0

    def test_far_authority_present(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        for f in factors:
            assert "FAR" in f.far_authority


# ─── Test Step 4: Subfactor Mapping ─────────────────────────────────────────

class TestSubfactorMapping:
    def test_technical_has_subfactors(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        tech = next(f for f in factors if f.name == "Technical Approach")
        assert len(tech.subfactors) > 0

    def test_past_perf_has_relevance_and_quality(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        pp = next(f for f in factors if f.name == "Past Performance")
        sf_names = [sf.name for sf in pp.subfactors]
        assert "Relevance" in sf_names
        assert "Quality of Performance" in sf_names

    def test_price_has_total_evaluated_price(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        price = next(f for f in factors if f.name == "Price/Cost")
        assert price.subfactors[0].name == "Total Evaluated Price"

    def test_subfactor_ids_follow_factor(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        for f in factors:
            for sf in f.subfactors:
                assert sf.subfactor_id.startswith(f.factor_id)

    def test_subfactor_weights_sum_to_one(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        for f in factors:
            if f.subfactors:
                total = sum(sf.weight_within_factor for sf in f.subfactors)
                assert abs(total - 1.0) < 0.05, f"{f.name} subfactor weights sum to {total}"


# ─── Test Step 5: Weight Suggestion ─────────────────────────────────────────

class TestWeightSuggestion:
    def test_tradeoff_tech_gt_price(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        tech = next(f for f in factors if f.name == "Technical Approach")
        price = next(f for f in factors if f.name == "Price/Cost")
        assert tech.suggested_weight > price.suggested_weight

    def test_20m_significantly_more_important(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        tech = next(f for f in factors if f.name == "Technical Approach")
        assert "significantly more important" in tech.relative_importance

    def test_lpta_price_dominates(self):
        lpta_params = {**TSA_20M_PARAMS, "evaluation_type": "lpta"}
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, lpta_params)
        factors = suggest_weights(factors, lpta_params)
        price = next(f for f in factors if f.name == "Price/Cost")
        tech = next(f for f in factors if f.name == "Technical Approach")
        assert price.suggested_weight > tech.suggested_weight

    def test_weights_sum_to_one(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        total = sum(f.suggested_weight for f in factors)
        assert abs(total - 1.0) < 0.05

    def test_50m_higher_tech_emphasis(self):
        params_50m = {**TSA_20M_PARAMS, "estimated_value": 50_000_000}
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors_20 = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors_20 = suggest_weights(factors_20, TSA_20M_PARAMS)
        factors_50 = generate_factor_candidates(reqs, params_50m)
        factors_50 = suggest_weights(factors_50, params_50m)
        tech_20 = next(f for f in factors_20 if f.name == "Technical Approach")
        tech_50 = next(f for f in factors_50 if f.name == "Technical Approach")
        assert tech_50.suggested_weight >= tech_20.suggested_weight


# ─── Test Step 6: Adjectival Definitions ────────────────────────────────────

class TestAdjectivalDefinitions:
    def test_tech_has_five_ratings(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        tech = next(f for f in factors if f.name == "Technical Approach")
        assert len(tech.adjectival_definitions) == 5

    def test_price_has_no_adjectival(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        price = next(f for f in factors if f.name == "Price/Cost")
        assert len(price.adjectival_definitions) == 0

    def test_ratings_in_order(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        tech = next(f for f in factors if f.name == "Technical Approach")
        ratings = [d.rating for d in tech.adjectival_definitions]
        expected = [AdjectivalRating.OUTSTANDING, AdjectivalRating.GOOD,
                    AdjectivalRating.ACCEPTABLE, AdjectivalRating.MARGINAL,
                    AdjectivalRating.UNACCEPTABLE]
        assert ratings == expected

    def test_discriminators_present(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        tech = next(f for f in factors if f.name == "Technical Approach")
        for d in tech.adjectival_definitions:
            assert len(d.discriminators) > 0

    def test_adjacent_ratings_differ(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        tech = next(f for f in factors if f.name == "Technical Approach")
        for i in range(len(tech.adjectival_definitions) - 1):
            upper = tech.adjectival_definitions[i]
            lower = tech.adjectival_definitions[i + 1]
            assert set(upper.discriminators) != set(lower.discriminators)

    def test_past_perf_has_unique_template(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        pp = next(f for f in factors if f.name == "Past Performance")
        assert len(pp.adjectival_definitions) == 5
        assert "expectation" in pp.adjectival_definitions[0].definition


# ─── Test Step 7: Protest-Proofing ──────────────────────────────────────────

class TestProtestProofing:
    def test_six_checks(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        checks = run_protest_proofing(factors, reqs, CANONICAL_L_SECTIONS, TSA_20M_PARAMS)
        assert len(checks) == 6

    def test_check_ids_pp01_to_pp06(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        checks = run_protest_proofing(factors, reqs, CANONICAL_L_SECTIONS, TSA_20M_PARAMS)
        ids = [c.check_id for c in checks]
        assert ids == ["PP-01", "PP-02", "PP-03", "PP-04", "PP-05", "PP-06"]

    def test_l_to_m_traceability_pass(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        checks = run_protest_proofing(factors, reqs, CANONICAL_L_SECTIONS)
        pp01 = next(c for c in checks if c.check_id == "PP-01")
        assert pp01.status == ProtestCheckStatus.PASS

    def test_l_to_m_no_l_sections_warns(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        checks = run_protest_proofing(factors, reqs)
        pp01 = next(c for c in checks if c.check_id == "PP-01")
        assert pp01.status == ProtestCheckStatus.WARN

    def test_m_to_pws_pass(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        checks = run_protest_proofing(factors, reqs)
        pp02 = next(c for c in checks if c.check_id == "PP-02")
        assert pp02.status == ProtestCheckStatus.PASS

    def test_adjectival_distinguishability_pass(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        checks = run_protest_proofing(factors, reqs)
        pp04 = next(c for c in checks if c.check_id == "PP-04")
        assert pp04.status == ProtestCheckStatus.PASS

    def test_weight_consistency_pass(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        checks = run_protest_proofing(factors, reqs, params=TSA_20M_PARAMS)
        pp05 = next(c for c in checks if c.check_id == "PP-05")
        assert pp05.status == ProtestCheckStatus.PASS

    def test_past_perf_alignment_pass(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        checks = run_protest_proofing(factors, reqs)
        pp06 = next(c for c in checks if c.check_id == "PP-06")
        assert pp06.status == ProtestCheckStatus.PASS

    def test_all_checks_have_far_authority(self):
        reqs = parse_pws_requirements(CANONICAL_PWS)
        factors = generate_factor_candidates(reqs, TSA_20M_PARAMS)
        factors = map_subfactors(factors, reqs)
        factors = suggest_weights(factors, TSA_20M_PARAMS)
        factors = draft_adjectival_definitions(factors)
        checks = run_protest_proofing(factors, reqs, CANONICAL_L_SECTIONS, TSA_20M_PARAMS)
        for c in checks:
            assert c.far_authority, f"{c.check_id} has no FAR authority"


# ─── Test Full Pipeline ─────────────────────────────────────────────────────

class TestFullPipeline:
    def test_canonical_20m(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, TSA_20M_PARAMS, CANONICAL_L_SECTIONS)
        assert len(result.requirements) == 6
        assert len(result.factors) >= 3  # tech, mgmt, pp, price at minimum
        assert result.methodology == EvalMethodology.TRADEOFF
        assert len(result.protest_checks) == 6
        assert result.requires_acceptance is True

    def test_overall_protest_score(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, TSA_20M_PARAMS, CANONICAL_L_SECTIONS)
        assert 0 <= result.overall_protest_score <= 100
        # With good data, should score well
        assert result.overall_protest_score >= 50

    def test_warnings_for_lpta_high_value(self):
        lpta_params = {**TSA_20M_PARAMS, "evaluation_type": "lpta"}
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, lpta_params)
        assert any("LPTA" in w for w in result.warnings)

    def test_source_provenance(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, TSA_20M_PARAMS)
        assert len(result.source_provenance) > 0
        assert any("FAR 15.304" in p for p in result.source_provenance)

    def test_empty_pws(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive({}, TSA_20M_PARAMS)
        assert len(result.requirements) == 0
        # Should still produce price factor
        assert any(f.name == "Price/Cost" for f in result.factors)


# ─── Test Serialization ────────────────────────────────────────────────────

class TestSerialization:
    def test_serializes_to_dict(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, TSA_20M_PARAMS, CANONICAL_L_SECTIONS)
        d = derivation_to_dict(result)
        assert "requirements" in d
        assert "factors" in d
        assert "protest_checks" in d
        assert "overall_protest_score" in d
        assert "methodology" in d

    def test_factors_have_all_fields(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, TSA_20M_PARAMS)
        d = derivation_to_dict(result)
        for f in d["factors"]:
            assert "factor_id" in f
            assert "name" in f
            assert "subfactors" in f
            assert "adjectival_definitions" in f
            assert "suggested_weight" in f

    def test_protest_checks_serialized(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(CANONICAL_PWS, TSA_20M_PARAMS)
        d = derivation_to_dict(result)
        assert len(d["protest_checks"]) == 6
        for c in d["protest_checks"]:
            assert "check_id" in c
            assert "status" in c
            assert c["status"] in ("pass", "warn", "fail")


# ─── Test Edge Cases ────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_section_pws(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(
            {"3.1": "Design and implement a software system."},
            TSA_20M_PARAMS,
        )
        assert len(result.requirements) == 1
        assert len(result.factors) >= 2  # At least tech + price

    def test_micro_purchase(self):
        engine = EvalFactorDerivationEngine()
        result = engine.derive(
            CANONICAL_PWS,
            {"estimated_value": 5_000, "evaluation_type": "tradeoff"},
        )
        assert len(result.factors) >= 2

    def test_default_category_for_ambiguous(self):
        cat = classify_requirement("Do something unrelated to any keyword.")
        assert cat == RequirementCategory.TECHNICAL  # Default fallback

    def test_category_keywords_complete(self):
        assert len(CATEGORY_KEYWORDS) == 7
        for cat in RequirementCategory:
            assert cat in CATEGORY_KEYWORDS

    def test_adjectival_templates_complete(self):
        assert "technical_approach" in ADJECTIVAL_TEMPLATES
        assert "management_approach" in ADJECTIVAL_TEMPLATES
        assert "past_performance" in ADJECTIVAL_TEMPLATES
        for key, templates in ADJECTIVAL_TEMPLATES.items():
            assert len(templates) == 5, f"{key} has {len(templates)} ratings, expected 5"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
