"""
Phase 27: Full Document Chain Generation — Tests
=================================================

Comprehensive tests for all 10 document engines plus the full chain orchestrator.

Canonical fixture: $20M TSA IT Services, FFP, Full & Open, NAICS 541512,
                   recompete, secret clearance.

Author: Centurion Acquisitor / FedProcure
"""
import sys
import os
import unittest
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.document_engines import (
    JAEngine, BCMEngine, DFEngine, APEngine, SSPEngine,
    SBReviewEngine, CORNomEngine, EvalWorksheetEngine,
    AwardNoticeEngine, SecurityReqEngine,
    DraftSection, DocumentDraft, DOCUMENT_ENGINES,
    generate_document, generate_full_chain,
    _get_bcm_approval, _get_ssa_appointment, _get_ja_approval,
    _get_ap_approval, _format_value, _estimate_fte,
    SECTION_G_CHECKLIST, FORM_700_22_ITEMS, FAR_6302_AUTHORITIES,
    BCM_APPROVAL_CHAINS, SSA_APPOINTMENT, JA_APPROVAL_LADDERS,
)


def _canonical_params() -> dict:
    """$20M TSA IT services — canonical test fixture."""
    return {
        "estimated_value": 20_000_000,
        "services": True,
        "is_it": True,
        "it_related": True,
        "contract_type": "FFP",
        "competition_type": "full_and_open",
        "naics_code": "541512",
        "psc_code": "D311",
        "sub_agency": "TSA",
        "evaluation_type": "tradeoff",
        "pop_months": 60,
        "has_options": True,
        "sole_source": False,
        "classified": True,
        "clearance_required": True,
        "vendor_on_site": True,
        "on_site": True,
        "handles_ssi": True,
        "has_cui": True,
        "requirement_description": "IT systems support services for TSA screening operations",
        "contractor_name": "Acme Federal Services",
    }


def _sole_source_params() -> dict:
    """$20M sole source variant."""
    p = _canonical_params()
    p["competition_type"] = "sole_source"
    p["sole_source"] = True
    p["justification_type"] = "sole_source"
    return p


def _micro_params() -> dict:
    """$10K micro-purchase."""
    return {
        "estimated_value": 10_000,
        "services": True,
        "is_it": False,
        "contract_type": "FFP",
        "competition_type": "full_and_open",
        "naics_code": "561210",
        "pop_months": 12,
    }


# ========================================================================
# Test Helpers
# ========================================================================

class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_bcm_approval_under_500k(self):
        chain, approver = _get_bcm_approval(400_000)
        self.assertEqual(approver, "CO")

    def test_bcm_approval_5m(self):
        chain, approver = _get_bcm_approval(3_000_000)
        self.assertEqual(approver, "BC")

    def test_bcm_approval_20m(self):
        chain, approver = _get_bcm_approval(20_000_000)
        self.assertEqual(approver, "DAA")
        self.assertIn("DD", chain)

    def test_bcm_approval_50m_plus(self):
        chain, approver = _get_bcm_approval(75_000_000)
        self.assertEqual(approver, "HCA")

    def test_ssa_appointment_levels(self):
        self.assertEqual(_get_ssa_appointment(1_000_000), "CO")
        self.assertEqual(_get_ssa_appointment(3_000_000), "BC")
        self.assertEqual(_get_ssa_appointment(10_000_000), "DD")
        self.assertEqual(_get_ssa_appointment(30_000_000), "DAA")
        self.assertEqual(_get_ssa_appointment(60_000_000), "HCA")

    def test_ja_approval_ladders(self):
        approver, _ = _get_ja_approval(100_000)
        self.assertEqual(approver, "CO")
        approver, _ = _get_ja_approval(500_000)
        self.assertEqual(approver, "CA (Competition Advocate)")
        approver, _ = _get_ja_approval(15_000_000)
        self.assertEqual(approver, "HCA")
        approver, _ = _get_ja_approval(25_000_000)
        self.assertEqual(approver, "DHS CPO")

    def test_format_value(self):
        self.assertEqual(_format_value(10_000), "$10K")
        self.assertEqual(_format_value(5_500_000), "$5.5M")
        self.assertEqual(_format_value(2_000_000_000), "$2.0B")

    def test_estimate_fte(self):
        fte = _estimate_fte(20_000_000, 60)
        self.assertGreater(fte, 0)
        self.assertLess(fte, 200)

    def test_ap_approval(self):
        chain, approver = _get_ap_approval(1_000_000)
        self.assertEqual(approver, "BC")
        chain, approver = _get_ap_approval(20_000_000)
        self.assertEqual(approver, "DAA")


# ========================================================================
# Test J&A Engine
# ========================================================================

class TestJAEngine(unittest.TestCase):
    """Test Justification & Approval engine."""

    def setUp(self):
        self.engine = JAEngine()
        self.params = _sole_source_params()

    def test_generates_8_sections(self):
        sections = self.engine.generate(self.params)
        self.assertEqual(len(sections), 8)

    def test_section_ids_sequential(self):
        sections = self.engine.generate(self.params)
        ids = [s.section_id for s in sections]
        self.assertEqual(ids, [f"JA-0{i}" for i in range(1, 9)])

    def test_authority_cited(self):
        sections = self.engine.generate(self.params)
        # Section 3 should cite FAR 6.302-1
        sec3 = sections[2]
        self.assertIn("FAR 6.302-1", sec3.content)

    def test_approval_at_20m(self):
        sections = self.engine.generate(self.params)
        sec8 = sections[7]
        self.assertIn("DHS CPO", sec8.content)  # $20M+ → DHS CPO per TSA J&A thresholds

    def test_legal_sufficiency_note(self):
        sections = self.engine.generate(self.params)
        sec8 = sections[7]
        self.assertIn("HSAM 3004.7003", sec8.content)

    def test_urgency_type(self):
        params = {**self.params, "justification_type": "urgency"}
        sections = self.engine.generate(params)
        sec3 = sections[2]
        self.assertIn("FAR 6.302-2", sec3.content)
        # Should warn about poor planning
        sec4 = sections[3]
        self.assertIn("poor planning", sec4.content)

    def test_market_research_default(self):
        sections = self.engine.generate(self.params)
        sec5 = sections[4]
        self.assertIn("FAR Part 10", sec5.content)
        self.assertLess(sec5.confidence, 70)  # Low confidence without actual research

    def test_market_research_provided(self):
        params = {**self.params, "market_research_summary": "Research found no alternatives."}
        sections = self.engine.generate(params)
        sec5 = sections[4]
        self.assertIn("Research found no alternatives", sec5.content)
        self.assertGreaterEqual(sec5.confidence, 80)

    def test_cost_analysis_at_2_5m(self):
        sections = self.engine.generate(self.params)
        sec7 = sections[6]
        self.assertIn("Cost analysis", sec7.content)

    def test_price_analysis_below_threshold(self):
        params = {**self.params, "estimated_value": 1_000_000}
        sections = self.engine.generate(params)
        sec7 = sections[6]
        self.assertIn("Price analysis", sec7.content)

    def test_far_6302_authorities_complete(self):
        self.assertEqual(len(FAR_6302_AUTHORITIES), 6)
        for key in ["sole_source", "urgency", "public_interest"]:
            self.assertIn(key, FAR_6302_AUTHORITIES)


# ========================================================================
# Test BCM Engine
# ========================================================================

class TestBCMEngine(unittest.TestCase):
    """Test Business Clearance Memorandum engine."""

    def setUp(self):
        self.engine = BCMEngine()
        self.params = {**_canonical_params(), "bcm_type": "pre_competitive"}

    def test_generates_sections_a_through_h(self):
        sections = self.engine.generate(self.params)
        ids = [s.section_id for s in sections]
        self.assertIn("BCM-A", ids)
        self.assertIn("BCM-G", ids)
        self.assertIn("BCM-H", ids)

    def test_section_g_has_27_items(self):
        sections = self.engine.generate(self.params)
        sec_g = next(s for s in sections if s.section_id == "BCM-G")
        self.assertIn("27-Item Compliance Checklist", sec_g.content)
        self.assertEqual(len(SECTION_G_CHECKLIST), 27)

    def test_approval_chain_20m(self):
        sections = self.engine.generate(self.params)
        sec_c = next(s for s in sections if s.section_id == "BCM-C")
        self.assertIn("DAA", sec_c.content)

    def test_pre_competitive_has_section_f(self):
        sections = self.engine.generate(self.params)
        ids = [s.section_id for s in sections]
        self.assertIn("BCM-F", ids)

    def test_streamlined_no_section_f(self):
        params = {**self.params, "bcm_type": "streamlined"}
        sections = self.engine.generate(params)
        ids = [s.section_id for s in sections]
        self.assertNotIn("BCM-F", ids)

    def test_sole_source_bcm(self):
        params = {**self.params, "bcm_type": "pre_post_sole_source"}
        sections = self.engine.generate(params)
        sec_b = next(s for s in sections if s.section_id == "BCM-B")
        self.assertIn("Sole Source", sec_b.content)

    def test_timeline_milestones(self):
        sections = self.engine.generate(self.params)
        sec_e = next(s for s in sections if s.section_id == "BCM-E")
        self.assertIn("PSR", sec_e.content)
        self.assertIn("ITAR", sec_e.content)

    def test_pricing_section(self):
        sections = self.engine.generate(self.params)
        sec_h = next(s for s in sections if s.section_id == "BCM-H")
        self.assertIn("cost analysis", sec_h.content)  # $20M triggers cost analysis

    def test_g_applicability_sole_source(self):
        """G-04 (J&A) should be applicable for sole source."""
        applicable = self.engine._check_g_applicability("G-04", _sole_source_params())
        self.assertTrue(applicable)

    def test_g_applicability_competitive(self):
        """G-04 (J&A) should not be applicable for competitive."""
        applicable = self.engine._check_g_applicability("G-04", _canonical_params())
        self.assertFalse(applicable)

    def test_g_ap_ffp_under_50m(self):
        """G-02 (AP) should not be applicable for FFP under $50M."""
        applicable = self.engine._check_g_applicability("G-02", _canonical_params())
        self.assertFalse(applicable)


# ========================================================================
# Test D&F Engine
# ========================================================================

class TestDFEngine(unittest.TestCase):
    """Test Determination & Findings engine."""

    def setUp(self):
        self.engine = DFEngine()

    def test_generates_4_sections(self):
        params = {**_canonical_params(), "df_type": "contract_type_tm_lh"}
        sections = self.engine.generate(params)
        self.assertEqual(len(sections), 4)

    def test_tm_lh_authority(self):
        params = {**_canonical_params(), "df_type": "contract_type_tm_lh"}
        sections = self.engine.generate(params)
        self.assertIn("FAR 16.601", sections[0].content)

    def test_option_exercise(self):
        params = {**_canonical_params(), "df_type": "option_exercise"}
        sections = self.engine.generate(params)
        sec3 = sections[2]
        self.assertIn("most advantageous", sec3.content)

    def test_urgency_warning(self):
        params = {**_canonical_params(), "df_type": "urgency"}
        sections = self.engine.generate(params)
        sec2 = sections[1]
        self.assertIn("poor planning", sec2.content)

    def test_approver_urgency(self):
        params = {**_canonical_params(), "df_type": "urgency"}
        sections = self.engine.generate(params)
        sec4 = sections[3]
        self.assertIn("HCA", sec4.content)

    def test_approver_public_interest(self):
        params = {**_canonical_params(), "df_type": "public_interest"}
        sections = self.engine.generate(params)
        sec4 = sections[3]
        self.assertIn("DHS CPO", sec4.content)

    def test_all_df_types_exist(self):
        self.assertEqual(len(DFEngine.DF_TYPES), 6)
        for dt in ["contract_type_tm_lh", "incentive_award_fee", "urgency",
                    "single_award_idiq", "option_exercise", "public_interest"]:
            self.assertIn(dt, DFEngine.DF_TYPES)


# ========================================================================
# Test AP Engine
# ========================================================================

class TestAPEngine(unittest.TestCase):
    """Test Acquisition Plan engine."""

    def setUp(self):
        self.engine = APEngine()

    def test_canonical_generates_sections(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        self.assertGreaterEqual(len(sections), 5)

    def test_fitara_for_it(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        content = " ".join(s.content for s in sections)
        self.assertIn("FITARA", content)

    def test_fitara_cio_section(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        ids = [s.section_id for s in sections]
        self.assertIn("AP-06a", ids)  # CIO review section for IT

    def test_no_fitara_non_it(self):
        params = {**_canonical_params(), "is_it": False, "it_related": False, "contract_type": "T&M"}
        sections = self.engine.generate(params)
        ids = [s.section_id for s in sections]
        self.assertNotIn("AP-06a", ids)

    def test_small_business_900k_threshold(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        sec3 = next(s for s in sections if s.section_id == "AP-03")
        self.assertIn("Required per FAR 19.702", sec3.content)

    def test_milestones_competitive(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        sec5 = next(s for s in sections if s.section_id == "AP-05")
        self.assertIn("Solicitation Release", sec5.content)

    def test_milestones_sole_source(self):
        params = {**_sole_source_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        sec5 = next(s for s in sections if s.section_id == "AP-05")
        self.assertIn("J&A Approved", sec5.content)

    def test_approval_chain_20m(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        sections = self.engine.generate(params)
        approval = [s for s in sections if "Approval" in s.heading and "CIO" not in s.heading][-1]
        self.assertIn("DAA", approval.content)


# ========================================================================
# Test SSP Engine
# ========================================================================

class TestSSPEngine(unittest.TestCase):
    """Test Source Selection Plan engine."""

    def setUp(self):
        self.engine = SSPEngine()

    def test_generates_6_sections(self):
        sections = self.engine.generate(_canonical_params())
        self.assertEqual(len(sections), 6)

    def test_tradeoff_methodology(self):
        sections = self.engine.generate(_canonical_params())
        sec1 = sections[0]
        self.assertIn("Best Value Tradeoff", sec1.content)

    def test_lpta_methodology(self):
        params = {**_canonical_params(), "evaluation_type": "lpta"}
        sections = self.engine.generate(params)
        sec1 = sections[0]
        self.assertIn("Lowest Price", sec1.content)

    def test_ssa_at_20m(self):
        sections = self.engine.generate(_canonical_params())
        sec1 = sections[0]
        self.assertIn("DAA", sec1.content)  # Exactly $20M → DAA (< $20M = DD, >= $20M = DAA)

    def test_tier3_notice(self):
        sections = self.engine.generate(_canonical_params())
        sec5 = sections[4]
        self.assertIn("inherently governmental", sec5.content)

    def test_custom_factors(self):
        params = {**_canonical_params(), "eval_factors": [
            {"name": "Custom Factor A", "suggested_weight": 0.5, "subfactors": []},
            {"name": "Custom Factor B", "suggested_weight": 0.3, "subfactors": []},
        ]}
        sections = self.engine.generate(params)
        sec3 = sections[2]
        self.assertIn("Custom Factor A", sec3.content)
        self.assertIn("Custom Factor B", sec3.content)

    def test_rating_methodology_tradeoff(self):
        sections = self.engine.generate(_canonical_params())
        sec4 = sections[3]
        self.assertIn("OUTSTANDING", sec4.content)
        self.assertIn("UNACCEPTABLE", sec4.content)

    def test_rating_methodology_lpta(self):
        params = {**_canonical_params(), "evaluation_type": "lpta"}
        sections = self.engine.generate(params)
        sec4 = sections[3]
        self.assertIn("PASS", sec4.content)
        self.assertIn("FAIL", sec4.content)


# ========================================================================
# Test SB Review Engine (DHS Form 700-22)
# ========================================================================

class TestSBReviewEngine(unittest.TestCase):
    """Test DHS Form 700-22 Small Business Review engine."""

    def setUp(self):
        self.engine = SBReviewEngine()

    def test_canonical_generates_3_sections(self):
        sections = self.engine.generate(_canonical_params())
        self.assertEqual(len(sections), 3)

    def test_not_required_under_100k(self):
        sections = self.engine.generate(_micro_params())
        self.assertEqual(len(sections), 1)
        self.assertIn("Not Required", sections[0].heading)

    def test_bundling_review_at_2m(self):
        sections = self.engine.generate(_canonical_params())
        sec2 = sections[1]
        self.assertIn("Substantial Bundling Review", sec2.content)

    def test_sba_pcr_at_2m_unrestricted(self):
        params = {**_canonical_params(), "set_aside_type": ""}
        sections = self.engine.generate(params)
        sec3 = sections[2]
        # SBA PCR required for $2M+ when set-aside pending
        self.assertIn("SBA PCR", sec3.content)

    def test_sole_source_set_aside(self):
        sections = self.engine.generate(_sole_source_params())
        sec2 = sections[1]
        self.assertIn("Not applicable (sole source)", sec2.content)

    def test_form_items_count(self):
        self.assertEqual(len(FORM_700_22_ITEMS), 23)


# ========================================================================
# Test COR Nomination Engine
# ========================================================================

class TestCORNomEngine(unittest.TestCase):
    """Test COR Nomination Letter engine."""

    def setUp(self):
        self.engine = CORNomEngine()

    def test_generates_4_sections(self):
        sections = self.engine.generate(_canonical_params())
        self.assertEqual(len(sections), 4)

    def test_certification_level_iii(self):
        sections = self.engine.generate(_canonical_params())
        sec1 = sections[0]
        self.assertIn("Level III", sec1.content)  # $20M → Level III

    def test_certification_level_ii(self):
        params = {**_canonical_params(), "estimated_value": 5_000_000}
        sections = self.engine.generate(params)
        sec1 = sections[0]
        self.assertIn("Level II", sec1.content)

    def test_certification_level_i(self):
        params = {**_canonical_params(), "estimated_value": 500_000, "services": False}
        sections = self.engine.generate(params)
        sec1 = sections[0]
        self.assertIn("Level I", sec1.content)

    def test_tier3_limitations(self):
        sections = self.engine.generate(_canonical_params())
        sec3 = sections[2]
        self.assertIn("Cannot", sec3.content)
        self.assertIn("Obligate", sec3.content)

    def test_three_signatures(self):
        sections = self.engine.generate(_canonical_params())
        sec4 = sections[3]
        self.assertIn("Nominating Official", sec4.content)
        self.assertIn("COR Acknowledgment", sec4.content)
        self.assertIn("Contracting Officer Delegation", sec4.content)


# ========================================================================
# Test Eval Worksheet Engine
# ========================================================================

class TestEvalWorksheetEngine(unittest.TestCase):
    """Test Evaluation Worksheet engine."""

    def setUp(self):
        self.engine = EvalWorksheetEngine()

    def test_generates_sections(self):
        sections = self.engine.generate(_canonical_params())
        self.assertGreaterEqual(len(sections), 3)  # Instructions + factors + summary

    def test_instructions_section(self):
        sections = self.engine.generate(_canonical_params())
        sec0 = sections[0]
        self.assertIn("INSTRUCTIONS", sec0.content)
        self.assertIn("source selection sensitive", sec0.content)

    def test_tradeoff_ratings(self):
        sections = self.engine.generate(_canonical_params())
        # Factor worksheets should have adjectival ratings
        factor_section = sections[1]
        self.assertIn("Outstanding", factor_section.content)

    def test_lpta_ratings(self):
        params = {**_canonical_params(), "evaluation_type": "lpta"}
        sections = self.engine.generate(params)
        factor_section = sections[1]
        self.assertIn("PASS", factor_section.content)
        self.assertIn("FAIL", factor_section.content)

    def test_custom_factors(self):
        params = {**_canonical_params(), "eval_factors": [
            {"factor_id": "F-01", "name": "Cybersecurity", "subfactors": [
                {"subfactor_id": "SF-1", "name": "Zero Trust Architecture"},
            ]},
        ]}
        sections = self.engine.generate(params)
        sec1 = sections[1]
        self.assertIn("Cybersecurity", sec1.heading)
        self.assertIn("Zero Trust Architecture", sec1.content)

    def test_summary_section(self):
        sections = self.engine.generate(_canonical_params())
        summary = sections[-1]
        self.assertIn("Summary", summary.heading)
        self.assertIn("Evaluator Signature", summary.content)

    def test_swd_fields(self):
        sections = self.engine.generate(_canonical_params())
        factor_section = sections[1]
        self.assertIn("Strengths", factor_section.content)
        self.assertIn("Weaknesses", factor_section.content)
        self.assertIn("Deficiencies", factor_section.content)


# ========================================================================
# Test Award Notice Engine
# ========================================================================

class TestAwardNoticeEngine(unittest.TestCase):
    """Test Award Notice engine."""

    def setUp(self):
        self.engine = AwardNoticeEngine()

    def test_competitive_generates_3_sections(self):
        sections = self.engine.generate(_canonical_params())
        self.assertEqual(len(sections), 3)

    def test_sole_source_no_unsuccessful_letter(self):
        sections = self.engine.generate(_sole_source_params())
        ids = [s.section_id for s in sections]
        self.assertNotIn("AN-03", ids)

    def test_sam_gov_posting(self):
        sections = self.engine.generate(_canonical_params())
        sec1 = sections[0]
        self.assertIn("FAR 5.301", sec1.authority)

    def test_debriefing_rights(self):
        sections = self.engine.generate(_canonical_params())
        sec3 = sections[2]
        self.assertIn("FAR 15.506", sec3.content)
        self.assertIn("3 days", sec3.content)

    def test_dhs_form_2140(self):
        sections = self.engine.generate(_canonical_params())
        sec2 = sections[1]
        self.assertIn("DHS Form 2140-01", sec2.heading)

    def test_under_sat_posting_optional(self):
        sections = self.engine.generate(_micro_params())
        sec1 = sections[0]
        self.assertIn("optional", sec1.content)


# ========================================================================
# Test Security Requirements Engine
# ========================================================================

class TestSecurityReqEngine(unittest.TestCase):
    """Test Security Requirements Document engine."""

    def setUp(self):
        self.engine = SecurityReqEngine()

    def test_canonical_generates_multiple_sections(self):
        sections = self.engine.generate(_canonical_params())
        self.assertGreaterEqual(len(sections), 5)  # Personnel + IT + SSI + CUI + Incident + Clauses

    def test_personnel_security(self):
        sections = self.engine.generate(_canonical_params())
        personnel = next(s for s in sections if "Personnel" in s.heading)
        self.assertIn("Secret", personnel.content)

    def test_it_security(self):
        sections = self.engine.generate(_canonical_params())
        it_sec = next(s for s in sections if "Information System" in s.heading)
        self.assertIn("FISMA", it_sec.content)
        self.assertIn("NIST", it_sec.content)

    def test_ssi_handling(self):
        sections = self.engine.generate(_canonical_params())
        ssi = next(s for s in sections if "SSI" in s.heading)
        self.assertIn("49 CFR Part 1520", ssi.content)

    def test_cui_handling(self):
        sections = self.engine.generate(_canonical_params())
        cui = next(s for s in sections if "CUI" in s.heading)
        self.assertIn("NIST SP 800-171", cui.content)

    def test_incident_response(self):
        sections = self.engine.generate(_canonical_params())
        incident = next(s for s in sections if "Incident" in s.heading)
        self.assertIn("1 hour", incident.content)

    def test_hsar_clauses(self):
        sections = self.engine.generate(_canonical_params())
        clause_sec = next(s for s in sections if "Clauses" in s.heading)
        self.assertIn("HSAR 3052.204-71", clause_sec.content)
        self.assertIn("HSAR 3052.204-72", clause_sec.content)  # IT → 204-72

    def test_minimal_security(self):
        """Non-IT, no clearance, no SSI, no CUI should still have incident response."""
        params = {
            "estimated_value": 1_000_000,
            "services": True,
            "is_it": False,
            "classified": False,
            "handles_ssi": False,
            "has_cui": False,
            "on_site": False,
        }
        sections = self.engine.generate(params)
        self.assertGreaterEqual(len(sections), 1)
        # Should have at least incident response + clauses
        headings = [s.heading for s in sections]
        self.assertTrue(any("Incident" in h for h in headings))


# ========================================================================
# Test Document Draft
# ========================================================================

class TestDocumentDraft(unittest.TestCase):
    """Test DocumentDraft data structure."""

    def test_to_dict(self):
        draft = DocumentDraft(
            doc_type="ja",
            sections=[DraftSection("JA-01", "Test", "Content")],
            warnings=["Warning 1"],
            source_provenance=["Source 1"],
        )
        d = draft.to_dict()
        self.assertEqual(d["doc_type"], "ja")
        self.assertEqual(len(d["sections"]), 1)
        self.assertEqual(d["warnings"], ["Warning 1"])
        self.assertTrue(d["requires_acceptance"])
        self.assertIn("Z", d["generated_at"])

    def test_generated_at_auto(self):
        draft = DocumentDraft(doc_type="test", sections=[])
        self.assertIn("Z", draft.generated_at)


# ========================================================================
# Test generate_document()
# ========================================================================

class TestGenerateDocument(unittest.TestCase):
    """Test the generate_document() factory function."""

    def test_all_doc_types(self):
        """Every registered engine should generate without error."""
        for doc_type in DOCUMENT_ENGINES:
            params = _canonical_params()
            if doc_type == "ja":
                params["justification_type"] = "sole_source"
            elif doc_type == "df":
                params["df_type"] = "contract_type_tm_lh"
            elif doc_type == "bcm":
                params["bcm_type"] = "pre_competitive"
            draft = generate_document(doc_type, params)
            self.assertIsInstance(draft, DocumentDraft)
            self.assertGreater(len(draft.sections), 0)

    def test_unknown_doc_type(self):
        with self.assertRaises(ValueError):
            generate_document("nonexistent", {})

    def test_ja_warning_when_competitive(self):
        draft = generate_document("ja", _canonical_params())
        self.assertTrue(any("not sole_source" in w for w in draft.warnings))

    def test_ap_warning_ffp_under_50m(self):
        draft = generate_document("ap", _canonical_params())
        self.assertTrue(any("FFP under $50M" in w for w in draft.warnings))

    def test_bcm_warning_over_500k(self):
        draft = generate_document("bcm", {**_canonical_params(), "bcm_type": "pre_competitive"})
        self.assertTrue(any("$500K" in w for w in draft.warnings))


# ========================================================================
# Test generate_full_chain()
# ========================================================================

class TestGenerateFullChain(unittest.TestCase):
    """Test full document chain generation."""

    def test_canonical_chain(self):
        """$20M FFP F&O should generate BCM, SSP, eval worksheets, award notice, security, COR, SB."""
        docs = generate_full_chain(_canonical_params())
        self.assertIn("bcm", docs)
        self.assertIn("ssp", docs)
        self.assertIn("eval_worksheet", docs)
        self.assertIn("award_notice", docs)
        self.assertIn("security_requirements", docs)
        self.assertIn("cor_nomination", docs)  # Services → COR
        self.assertIn("sb_review", docs)  # >$100K → SB review

    def test_canonical_no_ja(self):
        """Full & open should NOT generate J&A."""
        docs = generate_full_chain(_canonical_params())
        self.assertNotIn("ja", docs)

    def test_canonical_no_ap_ffp(self):
        """FFP under $50M should NOT generate AP."""
        docs = generate_full_chain(_canonical_params())
        self.assertNotIn("ap", docs)

    def test_canonical_no_df_ffp(self):
        """FFP should NOT generate D&F."""
        docs = generate_full_chain(_canonical_params())
        self.assertNotIn("df", docs)

    def test_sole_source_has_ja(self):
        docs = generate_full_chain(_sole_source_params())
        self.assertIn("ja", docs)

    def test_tm_has_df(self):
        params = {**_canonical_params(), "contract_type": "T&M"}
        docs = generate_full_chain(params)
        self.assertIn("df", docs)

    def test_tm_has_ap(self):
        """T&M above SAT should generate AP."""
        params = {**_canonical_params(), "contract_type": "T&M"}
        docs = generate_full_chain(params)
        self.assertIn("ap", docs)

    def test_over_50m_has_ap(self):
        """Any contract over $50M should generate AP."""
        params = {**_canonical_params(), "estimated_value": 60_000_000}
        docs = generate_full_chain(params)
        self.assertIn("ap", docs)

    def test_micro_minimal_chain(self):
        docs = generate_full_chain(_micro_params())
        # Should still have BCM, SSP, eval_worksheet, award_notice, security
        self.assertIn("bcm", docs)
        # Should NOT have SB review (under $100K)
        self.assertNotIn("sb_review", docs)

    def test_all_drafts_are_document_drafts(self):
        docs = generate_full_chain(_canonical_params())
        for doc_type, draft in docs.items():
            self.assertIsInstance(draft, DocumentDraft, f"{doc_type} is not DocumentDraft")

    def test_chain_count_canonical(self):
        docs = generate_full_chain(_canonical_params())
        self.assertEqual(len(docs), 7)  # bcm, ssp, eval_worksheet, award_notice, security, cor, sb_review


# ========================================================================
# Test Edge Cases
# ========================================================================

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_zero_value(self):
        params = {"estimated_value": 0}
        draft = generate_document("bcm", {**params, "bcm_type": "streamlined"})
        self.assertGreater(len(draft.sections), 0)

    def test_very_high_value(self):
        params = {**_canonical_params(), "estimated_value": 500_000_000}
        chain, approver = _get_bcm_approval(500_000_000)
        self.assertEqual(approver, "HCA")
        docs = generate_full_chain(params)
        self.assertIn("ap", docs)  # $500M → AP required

    def test_missing_params_graceful(self):
        """Engines should handle missing optional params gracefully."""
        for doc_type in DOCUMENT_ENGINES:
            params = {"estimated_value": 5_000_000}
            if doc_type == "ja":
                params["justification_type"] = "sole_source"
            elif doc_type == "df":
                params["df_type"] = "contract_type_tm_lh"
            elif doc_type == "bcm":
                params["bcm_type"] = "pre_competitive"
            try:
                draft = generate_document(doc_type, params)
                self.assertGreater(len(draft.sections), 0)
            except Exception as e:
                self.fail(f"Engine {doc_type} failed with minimal params: {e}")

    def test_document_engines_registry(self):
        self.assertEqual(len(DOCUMENT_ENGINES), 10)

    def test_all_sections_have_authority(self):
        """Every section across all engines should have an authority citation."""
        for doc_type in DOCUMENT_ENGINES:
            params = _canonical_params()
            if doc_type == "ja":
                params["justification_type"] = "sole_source"
            elif doc_type == "df":
                params["df_type"] = "contract_type_tm_lh"
            elif doc_type == "bcm":
                params["bcm_type"] = "pre_competitive"
            draft = generate_document(doc_type, params)
            for section in draft.sections:
                self.assertTrue(
                    section.authority,
                    f"{doc_type}/{section.section_id} missing authority"
                )


if __name__ == "__main__":
    unittest.main()
