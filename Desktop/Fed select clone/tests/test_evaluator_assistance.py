"""
Tests for Evaluator Assistance Model (Phase 23c)

Coverage:
- TestTier3HardStops: 3 tests — assign_rating, determine_swd, recommend_awardee
- TestRequirementsPanel: 5 tests — build, fields, subfactors, methodology, page_limit
- TestExcerptRegistration: 4 tests — register, multiple, dedup key, uploaded_by
- TestSubmissionPanel: 5 tests — basic, addressed/unaddressed subfactors, page compliance, empty
- TestObservationGeneration: 8 tests — strengths, weaknesses, deficiencies, info gaps, discussion Qs, combined, empty, confidence
- TestThreePanelPresentation: 5 tests — assembly, all panels present, tier boundary, serialization, generated_at
- TestSSDDEnhancement: 7 tests — basic generation, factor comparisons, discriminators, tradeoff narrative, LPTA mode, excluded offerors, tier3 notice
- TestOverallTradeoff: 3 tests — tradeoff, LPTA, single offeror
- TestPriceTechnical: 2 tests — tradeoff, LPTA
- TestRatingRank: 3 tests — known ratings, unknown, full ordering
- TestSerialization: 3 tests — presentation dict, ssdd dict, round-trip fields
- TestEdgeCases: 4 tests — no excerpts, single offeror SSDD, all deficient, empty workspace

Total: 52 tests
"""
import sys
import os
import unittest
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.evaluator_assistance import (
    EvaluatorAssistanceEngine,
    Tier3EvalAssistanceError,
    ObservationType,
    PanelType,
    SWDCategory,
    ThreePanelPresentation,
    SSDDEnhancement,
    FactorComparison,
    SubmissionExcerpt,
    PreliminaryObservation,
    _rating_rank,
    _identify_discriminators,
    _draft_tradeoff_narrative,
    _draft_overall_tradeoff,
    _document_price_technical_relationship,
    STRENGTH_INDICATORS,
    WEAKNESS_INDICATORS,
    DEFICIENCY_INDICATORS,
)


# ─── Test Fixtures ───────────────────────────────────────────────────────────

def _make_subfactors():
    return [
        {"id": "SF-T-01", "name": "System Architecture", "description": "Cloud-native design"},
        {"id": "SF-T-02", "name": "Data Migration", "description": "Legacy data migration plan"},
        {"id": "SF-T-03", "name": "Cybersecurity", "description": "FISMA/FedRAMP compliance"},
    ]


def _make_adjectival_defs():
    return [
        {"rating": "Outstanding", "definition": "Exceeds all requirements with innovative approach",
         "discriminators": ["exceeds requirements", "innovative methodology"]},
        {"rating": "Good", "definition": "Exceeds some requirements with no weaknesses",
         "discriminators": ["above minimum", "minor enhancements"]},
        {"rating": "Acceptable", "definition": "Meets all minimum requirements",
         "discriminators": ["meets requirements", "no deficiencies"]},
        {"rating": "Marginal", "definition": "Fails to meet some requirements",
         "discriminators": ["below minimum in some areas", "weaknesses present"]},
        {"rating": "Unacceptable", "definition": "Fails to meet material requirements",
         "discriminators": ["material deficiencies", "non-responsive"]},
    ]


def _make_engine_with_excerpts():
    engine = EvaluatorAssistanceEngine()
    # Register excerpts with varying signals
    engine.register_excerpt("F-01", "OFF-A", "Our proven cloud architecture exceeds the agency's requirements with automated deployment.",
                           source_page=5, subfactor_mapping="SF-T-01", uploaded_by="eval-1")
    engine.register_excerpt("F-01", "OFF-A", "We will develop a data migration tool during the transition phase.",
                           source_page=12, subfactor_mapping="SF-T-02", uploaded_by="eval-1")
    engine.register_excerpt("F-01", "OFF-A", "Our team has demonstrated FISMA compliance on 15 prior engagements.",
                           source_page=18, subfactor_mapping="SF-T-03", uploaded_by="eval-1")
    return engine


def _make_offeror_scores():
    return {
        "OFF-A": {
            "F-01": {"rating": "Outstanding", "strengths": 3, "weaknesses": 0, "deficiencies": 0,
                     "narrative": "Exceptional technical approach"},
            "F-02": {"rating": "Good", "strengths": 2, "weaknesses": 1, "deficiencies": 0,
                     "narrative": "Solid management plan with minor weakness"},
        },
        "OFF-B": {
            "F-01": {"rating": "Acceptable", "strengths": 1, "weaknesses": 2, "deficiencies": 0,
                     "narrative": "Meets minimum requirements"},
            "F-02": {"rating": "Outstanding", "strengths": 4, "weaknesses": 0, "deficiencies": 0,
                     "narrative": "Innovative management approach"},
        },
        "OFF-C": {
            "F-01": {"rating": "Marginal", "strengths": 0, "weaknesses": 3, "deficiencies": 1,
                     "narrative": "Significant weaknesses in approach"},
            "F-02": {"rating": "Acceptable", "strengths": 1, "weaknesses": 1, "deficiencies": 0,
                     "narrative": "Adequate management plan"},
        },
    }


def _make_factors():
    return [
        {"factor_id": "F-01", "factor_name": "Technical Approach",
         "relative_importance": "significantly more important than price",
         "far_authority": "FAR 15.304(c)(3)"},
        {"factor_id": "F-02", "factor_name": "Management Approach",
         "relative_importance": "approximately equal to price",
         "far_authority": "FAR 15.304(c)(3)"},
    ]


# ─── Test Classes ────────────────────────────────────────────────────────────

class TestTier3HardStops(unittest.TestCase):
    """Tier 3: AI NEVER assigns ratings, determines S/W/D, or recommends awardees."""

    def setUp(self):
        self.engine = EvaluatorAssistanceEngine()

    def test_assign_rating_always_refuses(self):
        with self.assertRaises(Tier3EvalAssistanceError) as ctx:
            self.engine.assign_rating(factor_id="F-01", offeror_id="OFF-A", rating="Outstanding")
        self.assertIn("FAR 15.305", str(ctx.exception))
        self.assertIn("FAR 7.503", str(ctx.exception))

    def test_determine_swd_always_refuses(self):
        with self.assertRaises(Tier3EvalAssistanceError) as ctx:
            self.engine.determine_swd(factor_id="F-01", category="Strength")
        self.assertIn("FAR 15.305", str(ctx.exception))

    def test_recommend_awardee_always_refuses(self):
        with self.assertRaises(Tier3EvalAssistanceError) as ctx:
            self.engine.recommend_awardee(workspace_id="WS-001")
        self.assertIn("FAR 15.308", str(ctx.exception))
        self.assertIn("FAR 7.503", str(ctx.exception))


class TestRequirementsPanel(unittest.TestCase):
    """Panel 1: Solicitation requirements presentation."""

    def setUp(self):
        self.engine = EvaluatorAssistanceEngine()

    def test_build_basic(self):
        panel = self.engine.build_requirements_panel(
            factor_id="F-01", factor_name="Technical Approach",
            section_l_instruction="Describe your technical approach...",
            section_l_ref="L.3",
            section_m_factor="Technical Approach shall be evaluated...",
            section_m_ref="M.2",
            subfactors=_make_subfactors(),
            adjectival_definitions=_make_adjectival_defs(),
            pws_sections=["3.1", "3.2", "3.3"],
        )
        self.assertEqual(panel.factor_id, "F-01")
        self.assertEqual(panel.factor_name, "Technical Approach")
        self.assertEqual(panel.far_authority, "FAR 15.305")

    def test_has_all_fields(self):
        panel = self.engine.build_requirements_panel(
            factor_id="F-01", factor_name="Technical",
            section_l_instruction="Describe...", section_l_ref="L.3",
            section_m_factor="Evaluated...", section_m_ref="M.2",
            subfactors=_make_subfactors(), adjectival_definitions=_make_adjectival_defs(),
            pws_sections=["3.1"],
        )
        self.assertEqual(len(panel.subfactors), 3)
        self.assertEqual(len(panel.adjectival_definitions), 5)

    def test_subfactors_present(self):
        panel = self.engine.build_requirements_panel(
            factor_id="F-01", factor_name="Technical",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=_make_subfactors(), adjectival_definitions=[],
            pws_sections=[],
        )
        self.assertEqual(panel.subfactors[0]["name"], "System Architecture")

    def test_methodology_tradeoff(self):
        panel = self.engine.build_requirements_panel(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=[], adjectival_definitions=[],
            pws_sections=[], evaluation_methodology="tradeoff",
        )
        self.assertEqual(panel.evaluation_methodology, "tradeoff")

    def test_page_limit(self):
        panel = self.engine.build_requirements_panel(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=[], adjectival_definitions=[],
            pws_sections=[], page_limit=40,
        )
        self.assertEqual(panel.page_limit, 40)


class TestExcerptRegistration(unittest.TestCase):
    """Excerpt registration for Panel 2."""

    def setUp(self):
        self.engine = EvaluatorAssistanceEngine()

    def test_register_basic(self):
        ex = self.engine.register_excerpt("F-01", "OFF-A", "Our approach is innovative.")
        self.assertIn("EX-F-01-OFF-A", ex.excerpt_id)
        self.assertEqual(ex.text, "Our approach is innovative.")

    def test_register_multiple(self):
        self.engine.register_excerpt("F-01", "OFF-A", "First excerpt.")
        self.engine.register_excerpt("F-01", "OFF-A", "Second excerpt.")
        key = "F-01:OFF-A"
        self.assertEqual(len(self.engine._excerpts[key]), 2)

    def test_different_offerors(self):
        self.engine.register_excerpt("F-01", "OFF-A", "Alpha approach.")
        self.engine.register_excerpt("F-01", "OFF-B", "Bravo approach.")
        self.assertEqual(len(self.engine._excerpts["F-01:OFF-A"]), 1)
        self.assertEqual(len(self.engine._excerpts["F-01:OFF-B"]), 1)

    def test_uploaded_by(self):
        ex = self.engine.register_excerpt("F-01", "OFF-A", "Text.", uploaded_by="eval-1")
        self.assertEqual(ex.uploaded_by, "eval-1")
        self.assertIsNotNone(ex.uploaded_at)


class TestSubmissionPanel(unittest.TestCase):
    """Panel 2: Offeror submission assembly."""

    def setUp(self):
        self.engine = EvaluatorAssistanceEngine()

    def test_build_basic(self):
        self.engine.register_excerpt("F-01", "OFF-A", "Text.", subfactor_mapping="SF-T-01")
        panel = self.engine.build_submission_panel(
            "F-01", "OFF-A", "Alpha Corp", ["SF-T-01", "SF-T-02"]
        )
        self.assertEqual(panel.offeror_name, "Alpha Corp")
        self.assertEqual(len(panel.excerpts), 1)

    def test_addressed_subfactors(self):
        self.engine.register_excerpt("F-01", "OFF-A", "Arch.", subfactor_mapping="SF-T-01")
        self.engine.register_excerpt("F-01", "OFF-A", "Migrate.", subfactor_mapping="SF-T-02")
        panel = self.engine.build_submission_panel(
            "F-01", "OFF-A", "Alpha", ["SF-T-01", "SF-T-02", "SF-T-03"]
        )
        self.assertIn("SF-T-01", panel.addressed_subfactors)
        self.assertIn("SF-T-02", panel.addressed_subfactors)
        self.assertEqual(panel.unaddressed_subfactors, ["SF-T-03"])

    def test_page_limit_exceeded(self):
        panel = self.engine.build_submission_panel(
            "F-01", "OFF-A", "Alpha", [], total_pages=45, page_limit=40
        )
        self.assertIn("exceeding", panel.compliance_note)
        self.assertIn("5 pages", panel.compliance_note)

    def test_page_limit_ok(self):
        panel = self.engine.build_submission_panel(
            "F-01", "OFF-A", "Alpha", [], total_pages=35, page_limit=40
        )
        self.assertEqual(panel.compliance_note, "")

    def test_no_excerpts(self):
        panel = self.engine.build_submission_panel(
            "F-01", "OFF-B", "Bravo", ["SF-T-01", "SF-T-02"]
        )
        self.assertEqual(len(panel.excerpts), 0)
        self.assertEqual(len(panel.unaddressed_subfactors), 2)


class TestObservationGeneration(unittest.TestCase):
    """Panel 3: AI-flagged preliminary observations."""

    def setUp(self):
        self.engine = _make_engine_with_excerpts()
        key = "F-01:OFF-A"
        self.excerpts = self.engine._excerpts[key]
        self.subfactors = _make_subfactors()
        self.pws = ["3.1", "3.2"]

    def test_detects_strength(self):
        panel = self.engine.generate_observations("F-01", "OFF-A", self.excerpts, self.subfactors, self.pws)
        strengths = panel.potential_strengths
        self.assertGreater(len(strengths), 0)
        self.assertTrue(any("proven" in s.source_provenance or "exceeds" in s.source_provenance
                            or "demonstrated" in s.source_provenance for s in strengths))

    def test_detects_weakness(self):
        panel = self.engine.generate_observations("F-01", "OFF-A", self.excerpts, self.subfactors, self.pws)
        weaknesses = panel.potential_weaknesses
        self.assertGreater(len(weaknesses), 0)
        self.assertTrue(any("will develop" in w.source_provenance for w in weaknesses))

    def test_no_false_deficiency(self):
        # Our test excerpts don't have deficiency language
        panel = self.engine.generate_observations("F-01", "OFF-A", self.excerpts, self.subfactors, self.pws)
        self.assertEqual(len(panel.potential_deficiencies), 0)

    def test_detects_deficiency(self):
        excerpt = SubmissionExcerpt(
            excerpt_id="EX-TEST", text="This requirement is not applicable to our approach.",
            subfactor_mapping="SF-T-01",
        )
        panel = self.engine.generate_observations("F-01", "OFF-B", [excerpt], self.subfactors, self.pws)
        self.assertGreater(len(panel.potential_deficiencies), 0)

    def test_information_gaps(self):
        # Only SF-T-01/02/03 mapped — none should be unaddressed since all 3 are mapped
        panel = self.engine.generate_observations("F-01", "OFF-A", self.excerpts, self.subfactors, self.pws)
        self.assertEqual(len(panel.information_gaps), 0)

    def test_information_gaps_present(self):
        # Only map one subfactor
        excerpt = SubmissionExcerpt(
            excerpt_id="EX-1", text="Our cloud architecture is proven.",
            subfactor_mapping="SF-T-01",
        )
        panel = self.engine.generate_observations("F-01", "OFF-C", [excerpt], self.subfactors, self.pws)
        self.assertEqual(len(panel.information_gaps), 2)  # SF-T-02 and SF-T-03 unaddressed

    def test_discussion_question_generated(self):
        excerpt = SubmissionExcerpt(
            excerpt_id="EX-W", text="We will develop the migration tool post-award. Details TBD.",
            subfactor_mapping="SF-T-02",
        )
        panel = self.engine.generate_observations("F-01", "OFF-D", [excerpt], self.subfactors, self.pws)
        self.assertGreater(len(panel.discussion_questions), 0)

    def test_observation_confidence(self):
        panel = self.engine.generate_observations("F-01", "OFF-A", self.excerpts, self.subfactors, self.pws)
        for obs in panel.observations:
            self.assertGreaterEqual(obs.confidence, 0.0)
            self.assertLessEqual(obs.confidence, 1.0)


class TestThreePanelPresentation(unittest.TestCase):
    """Full three-panel assembly."""

    def setUp(self):
        self.engine = _make_engine_with_excerpts()

    def test_build_presentation(self):
        p = self.engine.build_presentation(
            factor_id="F-01", factor_name="Technical Approach",
            section_l_instruction="Describe your approach...", section_l_ref="L.3",
            section_m_factor="Technical shall be evaluated...", section_m_ref="M.2",
            subfactors=_make_subfactors(), adjectival_definitions=_make_adjectival_defs(),
            pws_sections=["3.1", "3.2"], relative_importance="significantly more important than price",
            evaluation_methodology="tradeoff",
            offeror_id="OFF-A", offeror_name="Alpha Corp",
        )
        self.assertIsInstance(p, ThreePanelPresentation)
        self.assertEqual(p.factor_id, "F-01")
        self.assertEqual(p.offeror_id, "OFF-A")

    def test_all_panels_present(self):
        p = self.engine.build_presentation(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=_make_subfactors(), adjectival_definitions=_make_adjectival_defs(),
            pws_sections=["3.1"], relative_importance="", evaluation_methodology="tradeoff",
            offeror_id="OFF-A", offeror_name="Alpha",
        )
        self.assertIsNotNone(p.panel_1)
        self.assertIsNotNone(p.panel_2)
        self.assertIsNotNone(p.panel_3)

    def test_tier_boundary(self):
        p = self.engine.build_presentation(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=[], adjectival_definitions=[], pws_sections=[],
            relative_importance="", evaluation_methodology="tradeoff",
            offeror_id="OFF-A", offeror_name="Alpha",
        )
        self.assertIn("Tier 2", p.tier_boundary)

    def test_serialization(self):
        p = self.engine.build_presentation(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=_make_subfactors(), adjectival_definitions=_make_adjectival_defs(),
            pws_sections=["3.1"], relative_importance="", evaluation_methodology="tradeoff",
            offeror_id="OFF-A", offeror_name="Alpha",
        )
        d = self.engine.presentation_to_dict(p)
        self.assertIn("panel_1_solicitation_requirements", d)
        self.assertIn("panel_2_offeror_submission", d)
        self.assertIn("panel_3_preliminary_observations", d)
        self.assertEqual(d["factor_id"], "F-01")

    def test_generated_at(self):
        p = self.engine.build_presentation(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=[], adjectival_definitions=[], pws_sections=[],
            relative_importance="", evaluation_methodology="tradeoff",
            offeror_id="OFF-A", offeror_name="Alpha",
        )
        self.assertIsInstance(p.generated_at, datetime)


class TestSSDDEnhancement(unittest.TestCase):
    """SSDD factor-by-factor comparison and tradeoff narrative."""

    def setUp(self):
        self.engine = EvaluatorAssistanceEngine()

    def test_basic_generation(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            workspace_id="WS-001",
            factors=_make_factors(),
            offeror_scores=_make_offeror_scores(),
        )
        self.assertIsInstance(ssdd, SSDDEnhancement)
        self.assertEqual(ssdd.workspace_id, "WS-001")
        self.assertTrue(ssdd.requires_acceptance)

    def test_factor_comparisons(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        self.assertEqual(len(ssdd.factor_comparisons), 2)
        self.assertEqual(ssdd.factor_comparisons[0].factor_id, "F-01")

    def test_discriminators(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        f01 = ssdd.factor_comparisons[0]
        self.assertGreater(len(f01.discriminators), 0)
        # Should detect rating spread (Outstanding, Acceptable, Marginal)
        self.assertTrue(any("Rating spread" in d for d in f01.discriminators))

    def test_relative_ranking(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        f01 = ssdd.factor_comparisons[0]
        # OFF-A (Outstanding) should be ranked first
        self.assertEqual(f01.relative_ranking[0], "OFF-A")

    def test_tradeoff_narrative(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        f01 = ssdd.factor_comparisons[0]
        self.assertIn("SSA", f01.tradeoff_narrative)
        self.assertIn("OFF-A", f01.tradeoff_narrative)

    def test_lpta_mode(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores(),
            evaluation_methodology="lpta",
        )
        f01 = ssdd.factor_comparisons[0]
        self.assertIn("LPTA", f01.tradeoff_narrative)
        self.assertIn("pass/fail", f01.tradeoff_narrative)

    def test_excluded_offerors(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores(),
            excluded_offerors=[{"offeror_id": "OFF-C", "rationale": "Non-responsive per FAR 15.306(c)"}],
        )
        f01 = ssdd.factor_comparisons[0]
        # OFF-C should not appear in ranking
        self.assertNotIn("OFF-C", f01.relative_ranking)
        self.assertEqual(len(ssdd.excluded_offerors), 1)

    def test_tier3_notice(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        self.assertIn("FedProcure does NOT recommend", ssdd.tier3_notice)
        self.assertIn("FAR 15.308", ssdd.tier3_notice)
        self.assertIn("FAR 7.503", ssdd.tier3_notice)


class TestOverallTradeoff(unittest.TestCase):
    """Overall tradeoff narrative generation."""

    def test_tradeoff_narrative(self):
        comparisons = [
            FactorComparison("F-01", "Technical", [], [], ["OFF-A", "OFF-B"]),
        ]
        narrative = _draft_overall_tradeoff(comparisons, _make_offeror_scores(), "tradeoff")
        self.assertIn("best value tradeoff", narrative)
        self.assertIn("GAO case law", narrative)

    def test_lpta_narrative(self):
        narrative = _draft_overall_tradeoff([], {}, "lpta")
        self.assertIn("LPTA", narrative)
        self.assertIn("lowest-priced", narrative)

    def test_single_offeror(self):
        scores = {"OFF-A": {"F-01": {"rating": "Acceptable"}}}
        comparisons = [FactorComparison("F-01", "Tech", [], [], ["OFF-A"])]
        narrative = _draft_overall_tradeoff(comparisons, scores, "tradeoff")
        self.assertIn("1 offeror", narrative)


class TestPriceTechnical(unittest.TestCase):
    """Price/technical relationship documentation."""

    def test_tradeoff(self):
        result = _document_price_technical_relationship([], {}, "tradeoff")
        self.assertIn("significantly more important than price", result)
        self.assertIn("FAR 15.101-1", result)

    def test_lpta(self):
        result = _document_price_technical_relationship([], {}, "lpta")
        self.assertIn("price is the determining factor", result)


class TestRatingRank(unittest.TestCase):
    """Rating rank ordering."""

    def test_known_ratings(self):
        self.assertEqual(_rating_rank("Outstanding"), 5)
        self.assertEqual(_rating_rank("Unacceptable"), 1)

    def test_unknown_rating(self):
        self.assertEqual(_rating_rank("Nonexistent"), 0)

    def test_full_ordering(self):
        ratings = ["Unacceptable", "Marginal", "Acceptable", "Good", "Outstanding"]
        ranks = [_rating_rank(r) for r in ratings]
        self.assertEqual(ranks, sorted(ranks))


class TestSerialization(unittest.TestCase):
    """Serialization to dict."""

    def setUp(self):
        self.engine = _make_engine_with_excerpts()

    def test_presentation_dict(self):
        p = self.engine.build_presentation(
            factor_id="F-01", factor_name="Tech",
            section_l_instruction="X", section_l_ref="L.3",
            section_m_factor="Y", section_m_ref="M.2",
            subfactors=_make_subfactors(), adjectival_definitions=_make_adjectival_defs(),
            pws_sections=["3.1"], relative_importance="", evaluation_methodology="tradeoff",
            offeror_id="OFF-A", offeror_name="Alpha",
        )
        d = self.engine.presentation_to_dict(p)
        self.assertIn("generated_at", d)
        self.assertIn("tier_boundary", d)
        self.assertIsInstance(d["panel_3_preliminary_observations"]["observations"], list)

    def test_ssdd_dict(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        d = self.engine.ssdd_to_dict(ssdd)
        self.assertIn("tier3_notice", d)
        self.assertIn("tradeoff_standard", d)
        self.assertIn("factor_comparisons", d)
        self.assertEqual(len(d["factor_comparisons"]), 2)

    def test_round_trip_fields(self):
        ssdd = self.engine.generate_ssdd_enhancement(
            "WS-001", _make_factors(), _make_offeror_scores()
        )
        d = self.engine.ssdd_to_dict(ssdd)
        self.assertEqual(d["workspace_id"], "WS-001")
        self.assertTrue(d["requires_acceptance"])
        self.assertIn("evaluation_workspace", d["source_provenance"])


class TestEdgeCases(unittest.TestCase):
    """Edge cases."""

    def test_no_excerpts(self):
        engine = EvaluatorAssistanceEngine()
        panel = engine.build_submission_panel("F-01", "OFF-X", "Unknown Corp", ["SF-01", "SF-02"])
        self.assertEqual(len(panel.excerpts), 0)
        self.assertEqual(len(panel.unaddressed_subfactors), 2)

    def test_single_offeror_ssdd(self):
        engine = EvaluatorAssistanceEngine()
        scores = {"OFF-A": {"F-01": {"rating": "Acceptable", "strengths": 1,
                                      "weaknesses": 0, "deficiencies": 0, "narrative": "OK"}}}
        ssdd = engine.generate_ssdd_enhancement("WS-002",
            [{"factor_id": "F-01", "factor_name": "Tech"}], scores)
        self.assertEqual(len(ssdd.factor_comparisons), 1)
        self.assertIn("Single offeror", ssdd.factor_comparisons[0].tradeoff_narrative)

    def test_all_deficient_excerpts(self):
        engine = EvaluatorAssistanceEngine()
        engine.register_excerpt("F-01", "OFF-Z", "This does not comply with any requirement.",
                               subfactor_mapping="SF-01")
        engine.register_excerpt("F-01", "OFF-Z", "We are unable to meet the schedule.",
                               subfactor_mapping="SF-02")
        excerpts = engine._excerpts["F-01:OFF-Z"]
        panel = engine.generate_observations(
            "F-01", "OFF-Z", excerpts,
            [{"id": "SF-01", "name": "Architecture"}, {"id": "SF-02", "name": "Schedule"}],
            ["3.1"],
        )
        self.assertGreater(len(panel.potential_deficiencies), 0)
        self.assertGreater(len(panel.discussion_questions), 0)

    def test_empty_workspace_ssdd(self):
        engine = EvaluatorAssistanceEngine()
        ssdd = engine.generate_ssdd_enhancement("WS-EMPTY", [], {})
        self.assertEqual(len(ssdd.factor_comparisons), 0)
        self.assertIn("tradeoff", ssdd.overall_tradeoff_narrative)  # defaults to tradeoff methodology


if __name__ == "__main__":
    unittest.main()
