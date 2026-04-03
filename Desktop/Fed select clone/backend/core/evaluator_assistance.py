"""
Evaluator Assistance Model (Phase 23c)

Three-panel evaluator presentation per evaluation factor per offeror:
  Panel 1: Solicitation Requirements — Section L instruction, Section M factor/subfactor,
           adjectival definitions (what each rating means for this factor)
  Panel 2: Offeror Submission — relevant proposal excerpts mapped to this factor
  Panel 3: Preliminary Observations — AI-flagged potential S/W/D and discussion questions

Architecture:
- Tier 2 (AI-Appropriate): presents structured information and flags potential S/W/D
  for evaluator consideration. All outputs carry source provenance and require acceptance.
- Tier 3 (Human-Only): SSEB member makes independent evaluation judgment — assigns
  rating, determines S/W/D, writes narrative rationale per FAR 15.305.
  The SSA makes award decision per FAR 15.308 — FedProcure NEVER recommends an awardee.

Integration:
- Extends Phase 11 SecureEvalWorkspace (RBAC, immutable scores, phase gates)
- Consumes Phase 23b EvalFactorDerivationEngine outputs (factors, subfactors, adjectival defs)
- Feeds Phase 10 EvidenceLineageLedger (evaluator_score nodes)

References:
- FAR 15.305 (proposal evaluation), FAR 15.308 (SSA authority)
- FAR 7.503(b)(1) (inherently governmental functions)
- FAR 15.101-1 (tradeoff), FAR 15.101-2 (LPTA)
- TSA PL 2017-004 (SSA appointment), BCM May 2022 (tradeoff standard)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ─── Enums ──────────────────────────────────────────────────────────────────

class PanelType(str, Enum):
    """The three evaluator assistance panels."""
    SOLICITATION_REQUIREMENTS = "solicitation_requirements"
    OFFEROR_SUBMISSION = "offeror_submission"
    PRELIMINARY_OBSERVATIONS = "preliminary_observations"


class ObservationType(str, Enum):
    """Types of AI-flagged preliminary observations."""
    POTENTIAL_STRENGTH = "potential_strength"
    POTENTIAL_WEAKNESS = "potential_weakness"
    POTENTIAL_DEFICIENCY = "potential_deficiency"
    DISCUSSION_QUESTION = "discussion_question"
    INFORMATION_GAP = "information_gap"


class SWDCategory(str, Enum):
    """Standard strength/weakness/deficiency categories per FAR 15.305."""
    STRENGTH = "Strength"
    WEAKNESS = "Weakness"
    DEFICIENCY = "Deficiency"
    SIGNIFICANT_STRENGTH = "Significant Strength"
    SIGNIFICANT_WEAKNESS = "Significant Weakness"


class ComparisonDimension(str, Enum):
    """Dimensions for SSDD factor-by-factor comparison."""
    RATING = "rating"
    STRENGTHS_COUNT = "strengths_count"
    WEAKNESSES_COUNT = "weaknesses_count"
    DEFICIENCIES_COUNT = "deficiencies_count"
    RISK_LEVEL = "risk_level"
    DISCRIMINATOR = "discriminator"


# ─── Data Classes ───────────────────────────────────────────────────────────

@dataclass
class SolicitationRequirementsPanel:
    """Panel 1: What the solicitation requires for this factor."""
    factor_id: str
    factor_name: str
    section_l_instruction: str      # Full text of the L instruction
    section_l_ref: str              # e.g. "L.3"
    section_m_factor: str           # Full text of the M factor
    section_m_ref: str              # e.g. "M.2"
    subfactors: list[dict[str, str]]  # [{id, name, description}]
    adjectival_definitions: list[dict[str, str]]  # [{rating, definition, discriminators}]
    pws_sections: list[str]         # PWS sections this factor evaluates
    relative_importance: str        # e.g. "significantly more important than price"
    evaluation_methodology: str     # "tradeoff" or "lpta"
    page_limit: int | None = None   # From Section L
    far_authority: str = "FAR 15.305"


@dataclass
class SubmissionExcerpt:
    """An excerpt from the offeror's proposal mapped to a factor."""
    excerpt_id: str
    text: str                       # The relevant proposal text
    source_page: int | None = None
    source_section: str | None = None  # Offeror's proposal section reference
    subfactor_mapping: str | None = None  # Which subfactor this excerpt addresses
    coverage: str = "full"          # "full", "partial", "none" — how well it addresses the subfactor
    uploaded_by: str | None = None  # SSEB member who mapped this excerpt
    uploaded_at: datetime | None = None


@dataclass
class OfferorSubmissionPanel:
    """Panel 2: What the offeror submitted for this factor."""
    factor_id: str
    offeror_id: str
    offeror_name: str
    excerpts: list[SubmissionExcerpt]
    addressed_subfactors: list[str]   # Subfactor IDs that have at least one excerpt
    unaddressed_subfactors: list[str] # Subfactor IDs with no mapped excerpts
    total_pages: int | None = None    # Offeror's page count for this volume
    compliance_note: str = ""         # e.g. "Proposal exceeds page limit by 3 pages"


@dataclass
class PreliminaryObservation:
    """An AI-flagged observation for evaluator consideration."""
    observation_id: str
    observation_type: ObservationType
    factor_id: str
    description: str                # What the AI observed
    evidence: str                   # Specific text/data supporting the observation
    subfactor_id: str | None = None
    pws_reference: str | None = None  # PWS section the observation relates to
    confidence: float = 0.0         # 0-1, AI confidence in this observation
    source_provenance: str = ""     # What data/rule produced this observation
    requires_evaluator_judgment: bool = True  # Always true — Tier 2/3 boundary


@dataclass
class PreliminaryObservationsPanel:
    """Panel 3: AI-flagged preliminary observations for evaluator consideration."""
    factor_id: str
    offeror_id: str
    observations: list[PreliminaryObservation]
    potential_strengths: list[PreliminaryObservation] = field(default_factory=list)
    potential_weaknesses: list[PreliminaryObservation] = field(default_factory=list)
    potential_deficiencies: list[PreliminaryObservation] = field(default_factory=list)
    discussion_questions: list[PreliminaryObservation] = field(default_factory=list)
    information_gaps: list[PreliminaryObservation] = field(default_factory=list)
    tier_notice: str = (
        "TIER 2 NOTICE: These observations are AI-generated preliminary flags for "
        "evaluator consideration only. The evaluator makes the independent judgment "
        "on strengths, weaknesses, and deficiencies per FAR 15.305. FedProcure does "
        "NOT assign ratings or determine S/W/D."
    )
    far_authority: str = "FAR 15.305, FAR 7.503(b)(1)"


@dataclass
class ThreePanelPresentation:
    """Complete three-panel presentation for one factor × one offeror."""
    factor_id: str
    offeror_id: str
    panel_1: SolicitationRequirementsPanel
    panel_2: OfferorSubmissionPanel
    panel_3: PreliminaryObservationsPanel
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tier_boundary: str = "Tier 2 — AI Presents, Evaluator Judges"


# ─── SSDD Enhancement Data Classes ──────────────────────────────────────────

@dataclass
class FactorComparison:
    """Factor-by-factor comparison between offerors for SSDD narrative."""
    factor_id: str
    factor_name: str
    offeror_summaries: list[dict[str, Any]]  # [{offeror_id, rating, S/W/D counts, narrative}]
    discriminators: list[str]       # What distinguishes offerors on this factor
    relative_ranking: list[str]     # Offeror IDs ranked on this factor
    tradeoff_narrative: str = ""    # AI-drafted tradeoff analysis for SSA consideration
    source_provenance: str = "evaluation_workspace, consensus_scores"


@dataclass
class SSDDEnhancement:
    """Enhanced SSDD draft with factor-by-factor comparison and tradeoff analysis."""
    workspace_id: str
    factor_comparisons: list[FactorComparison]
    overall_tradeoff_narrative: str
    price_technical_relationship: str  # Documents price/technical relationship
    excluded_offerors: list[dict[str, str]]  # [{offeror_id, rationale}]
    tier3_notice: str = (
        "TIER 3 NOTICE: FedProcure provides this analysis as structured information "
        "for the SSA's independent consideration. FedProcure does NOT recommend an "
        "awardee. The source selection decision is an inherently governmental function "
        "per FAR 15.308 and FAR 7.503(b)(1). The SSA must make an independent "
        "assessment — not a 'sign-off' of the evaluation recommendation."
    )
    tradeoff_standard: str = (
        "Per GAO case law: the SSA's decision must discuss the relative qualities "
        "of proposals (not just restate adjectival ratings), identify each area of "
        "significant difference, and demonstrate that as the price differential "
        "increases, the relative technical benefits also increase proportionally. "
        "Generalized or content-free statements create protest vulnerability."
    )
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_provenance: list[str] = field(default_factory=lambda: [
        "evaluation_workspace", "consensus_scores", "section_m_factors",
        "GAO tradeoff case law", "FAR 15.101-1", "FAR 15.308",
    ])
    requires_acceptance: bool = True


# ─── Tier 3 Hard Stop ───────────────────────────────────────────────────────

class Tier3EvalAssistanceError(Exception):
    """Raised when an action crosses the Tier 3 boundary in evaluation assistance.

    Distinct from Tier3HardStopError (evaluation workspace) and
    Tier3PostAwardError (post-award). All are constitutional limits
    per FAR 7.503(b)(1).
    """

    def __init__(self, action: str, authority: str):
        self.action = action
        self.authority = authority
        super().__init__(
            f"TIER 3 HARD STOP: '{action}' is an inherently governmental function. "
            f"Authority: {authority}. FedProcure cannot perform this action."
        )


# ─── Evaluator Assistance Engine ────────────────────────────────────────────

# Observation generation rules — maps requirement patterns to observation types
STRENGTH_INDICATORS = [
    ("exceeds", "Proposal appears to exceed the minimum requirement"),
    ("innovative", "Proposal describes an innovative approach"),
    ("proven", "Proposal references a proven methodology or prior success"),
    ("automated", "Proposal proposes automation that may improve efficiency"),
    ("additional", "Proposal offers additional capability beyond the requirement"),
    ("experienced", "Proposal emphasizes team experience in this area"),
    ("certified", "Proposal references relevant certifications"),
    ("demonstrated", "Proposal cites demonstrated results"),
    ("best practice", "Proposal references industry best practices"),
    ("risk mitigation", "Proposal includes specific risk mitigation strategies"),
]

WEAKNESS_INDICATORS = [
    ("will develop", "Proposal indicates approach is not yet developed"),
    ("to be determined", "Proposal defers specifics to post-award"),
    ("tbd", "Proposal contains TBD placeholders"),
    ("general", "Proposal provides general statements without specifics"),
    ("vague", "Proposal language lacks specificity"),
    ("may", "Proposal uses non-committal language ('may', 'might')"),
    ("might", "Proposal uses non-committal language"),
    ("could", "Proposal uses hedging language ('could')"),
    ("intend to", "Proposal states intent without commitment"),
    ("not addressed", "Proposal does not address this subfactor"),
]

DEFICIENCY_INDICATORS = [
    ("does not comply", "Proposal appears non-compliant with the requirement"),
    ("unable to", "Proposal indicates inability to meet the requirement"),
    ("not applicable", "Proposal marks a mandatory requirement as N/A"),
    ("exception", "Proposal takes exception to a solicitation requirement"),
    ("alternate", "Proposal proposes an alternative to the stated requirement"),
    ("not included", "Required element appears missing from the proposal"),
    ("no response", "Proposal provides no response to this instruction"),
]


class EvaluatorAssistanceEngine:
    """Generates three-panel evaluator presentations and enhanced SSDD drafts.

    Tier 2: All outputs are preliminary, carry source provenance, and require
    evaluator/SSA acceptance. FedProcure presents; humans judge.

    Tier 3 Hard Stops:
    - assign_rating() → ALWAYS raises Tier3EvalAssistanceError
    - determine_swd() → ALWAYS raises Tier3EvalAssistanceError
    - recommend_awardee() → ALWAYS raises Tier3EvalAssistanceError
    """

    def __init__(self):
        self._presentations: dict[str, ThreePanelPresentation] = {}  # key: f"{factor_id}:{offeror_id}"
        self._excerpts: dict[str, list[SubmissionExcerpt]] = {}  # key: f"{factor_id}:{offeror_id}"
        self._ssdd_cache: dict[str, SSDDEnhancement] = {}  # key: workspace_id

    # ── Tier 3 Hard Stops (ALWAYS refuse) ────────────────────────────────

    def assign_rating(self, **kwargs) -> None:
        """TIER 3: Assigning adjectival ratings is inherently governmental."""
        raise Tier3EvalAssistanceError(
            action="assign adjectival rating to offeror proposal",
            authority="FAR 15.305(a), FAR 7.503(b)(1)"
        )

    def determine_swd(self, **kwargs) -> None:
        """TIER 3: Determining strengths/weaknesses/deficiencies is inherently governmental."""
        raise Tier3EvalAssistanceError(
            action="determine strengths, weaknesses, or deficiencies",
            authority="FAR 15.305(a), FAR 7.503(b)(1)"
        )

    def recommend_awardee(self, **kwargs) -> None:
        """TIER 3: Recommending an awardee is inherently governmental."""
        raise Tier3EvalAssistanceError(
            action="recommend an awardee for source selection",
            authority="FAR 15.308, FAR 7.503(b)(1)"
        )

    # ── Panel 1: Solicitation Requirements ───────────────────────────────

    def build_requirements_panel(
        self,
        factor_id: str,
        factor_name: str,
        section_l_instruction: str,
        section_l_ref: str,
        section_m_factor: str,
        section_m_ref: str,
        subfactors: list[dict[str, str]],
        adjectival_definitions: list[dict[str, str]],
        pws_sections: list[str],
        relative_importance: str = "",
        evaluation_methodology: str = "tradeoff",
        page_limit: int | None = None,
    ) -> SolicitationRequirementsPanel:
        """Build Panel 1: what the solicitation requires for this factor."""
        return SolicitationRequirementsPanel(
            factor_id=factor_id,
            factor_name=factor_name,
            section_l_instruction=section_l_instruction,
            section_l_ref=section_l_ref,
            section_m_factor=section_m_factor,
            section_m_ref=section_m_ref,
            subfactors=subfactors,
            adjectival_definitions=adjectival_definitions,
            pws_sections=pws_sections,
            relative_importance=relative_importance,
            evaluation_methodology=evaluation_methodology,
            page_limit=page_limit,
        )

    # ── Panel 2: Offeror Submission ──────────────────────────────────────

    def register_excerpt(
        self,
        factor_id: str,
        offeror_id: str,
        excerpt_text: str,
        source_page: int | None = None,
        source_section: str | None = None,
        subfactor_mapping: str | None = None,
        uploaded_by: str | None = None,
    ) -> SubmissionExcerpt:
        """Register a proposal excerpt mapped to a factor for an offeror.

        Manual upload initially; future: OCR/NLP extraction from proposal PDFs.
        """
        key = f"{factor_id}:{offeror_id}"
        if key not in self._excerpts:
            self._excerpts[key] = []

        excerpt = SubmissionExcerpt(
            excerpt_id=f"EX-{factor_id}-{offeror_id}-{len(self._excerpts[key]) + 1:03d}",
            text=excerpt_text,
            source_page=source_page,
            source_section=source_section,
            subfactor_mapping=subfactor_mapping,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(timezone.utc),
        )
        self._excerpts[key].append(excerpt)
        return excerpt

    def build_submission_panel(
        self,
        factor_id: str,
        offeror_id: str,
        offeror_name: str,
        all_subfactor_ids: list[str],
        total_pages: int | None = None,
        page_limit: int | None = None,
    ) -> OfferorSubmissionPanel:
        """Build Panel 2: what the offeror submitted for this factor."""
        key = f"{factor_id}:{offeror_id}"
        excerpts = self._excerpts.get(key, [])

        # Determine which subfactors have mapped excerpts
        addressed = set()
        for ex in excerpts:
            if ex.subfactor_mapping:
                addressed.add(ex.subfactor_mapping)

        unaddressed = [sf for sf in all_subfactor_ids if sf not in addressed]

        # Check page limit compliance
        compliance_note = ""
        if total_pages and page_limit:
            if total_pages > page_limit:
                compliance_note = (
                    f"NOTICE: Offeror's submission is {total_pages} pages, "
                    f"exceeding the {page_limit}-page limit by {total_pages - page_limit} pages. "
                    f"CO must determine treatment per FAR 15.305."
                )

        return OfferorSubmissionPanel(
            factor_id=factor_id,
            offeror_id=offeror_id,
            offeror_name=offeror_name,
            excerpts=excerpts,
            addressed_subfactors=list(addressed),
            unaddressed_subfactors=unaddressed,
            total_pages=total_pages,
            compliance_note=compliance_note,
        )

    # ── Panel 3: Preliminary Observations ────────────────────────────────

    def generate_observations(
        self,
        factor_id: str,
        offeror_id: str,
        excerpts: list[SubmissionExcerpt],
        subfactors: list[dict[str, str]],
        pws_sections: list[str],
    ) -> PreliminaryObservationsPanel:
        """Generate AI-flagged preliminary observations for evaluator consideration.

        Tier 2: These are flags, not determinations. The evaluator decides.
        """
        observations = []
        obs_counter = 0

        # Scan excerpts for strength/weakness/deficiency indicators
        for excerpt in excerpts:
            text_lower = excerpt.text.lower()

            # Check strength indicators
            for keyword, desc in STRENGTH_INDICATORS:
                if keyword.lower() in text_lower:
                    obs_counter += 1
                    observations.append(PreliminaryObservation(
                        observation_id=f"OBS-{factor_id}-{offeror_id}-{obs_counter:03d}",
                        observation_type=ObservationType.POTENTIAL_STRENGTH,
                        factor_id=factor_id,
                        subfactor_id=excerpt.subfactor_mapping,
                        description=desc,
                        evidence=excerpt.text[:200],
                        pws_reference=pws_sections[0] if pws_sections else None,
                        confidence=0.6,
                        source_provenance=f"keyword_match:{keyword}",
                    ))
                    break  # One observation per excerpt per category

            # Check weakness indicators
            for keyword, desc in WEAKNESS_INDICATORS:
                if keyword.lower() in text_lower:
                    obs_counter += 1
                    observations.append(PreliminaryObservation(
                        observation_id=f"OBS-{factor_id}-{offeror_id}-{obs_counter:03d}",
                        observation_type=ObservationType.POTENTIAL_WEAKNESS,
                        factor_id=factor_id,
                        subfactor_id=excerpt.subfactor_mapping,
                        description=desc,
                        evidence=excerpt.text[:200],
                        pws_reference=pws_sections[0] if pws_sections else None,
                        confidence=0.5,
                        source_provenance=f"keyword_match:{keyword}",
                    ))
                    break

            # Check deficiency indicators
            for keyword, desc in DEFICIENCY_INDICATORS:
                if keyword.lower() in text_lower:
                    obs_counter += 1
                    observations.append(PreliminaryObservation(
                        observation_id=f"OBS-{factor_id}-{offeror_id}-{obs_counter:03d}",
                        observation_type=ObservationType.POTENTIAL_DEFICIENCY,
                        factor_id=factor_id,
                        subfactor_id=excerpt.subfactor_mapping,
                        description=desc,
                        evidence=excerpt.text[:200],
                        pws_reference=pws_sections[0] if pws_sections else None,
                        confidence=0.7,
                        source_provenance=f"keyword_match:{keyword}",
                    ))
                    break

        # Flag unaddressed subfactors as information gaps
        addressed_sfs = {ex.subfactor_mapping for ex in excerpts if ex.subfactor_mapping}
        for sf in subfactors:
            sf_id = sf.get("id", sf.get("subfactor_id", ""))
            if sf_id and sf_id not in addressed_sfs:
                obs_counter += 1
                observations.append(PreliminaryObservation(
                    observation_id=f"OBS-{factor_id}-{offeror_id}-{obs_counter:03d}",
                    observation_type=ObservationType.INFORMATION_GAP,
                    factor_id=factor_id,
                    subfactor_id=sf_id,
                    description=f"Subfactor '{sf.get('name', sf_id)}' has no mapped proposal excerpts",
                    evidence="No proposal text mapped to this subfactor",
                    confidence=0.9,
                    source_provenance="subfactor_coverage_check",
                ))

        # Generate discussion questions for weak/deficient areas
        weakness_count = sum(1 for o in observations
                            if o.observation_type == ObservationType.POTENTIAL_WEAKNESS)
        deficiency_count = sum(1 for o in observations
                              if o.observation_type == ObservationType.POTENTIAL_DEFICIENCY)

        if weakness_count + deficiency_count > 0:
            obs_counter += 1
            observations.append(PreliminaryObservation(
                observation_id=f"OBS-{factor_id}-{offeror_id}-{obs_counter:03d}",
                observation_type=ObservationType.DISCUSSION_QUESTION,
                factor_id=factor_id,
                description=(
                    f"Consider discussion topics: {weakness_count} potential weakness(es) "
                    f"and {deficiency_count} potential deficiency(ies) flagged. "
                    f"If discussions are conducted per FAR 15.306, these areas "
                    f"may warrant clarification from the offeror."
                ),
                evidence=f"{weakness_count} weaknesses, {deficiency_count} deficiencies flagged",
                confidence=0.8,
                source_provenance="observation_aggregation",
            ))

        # Categorize observations
        panel = PreliminaryObservationsPanel(
            factor_id=factor_id,
            offeror_id=offeror_id,
            observations=observations,
            potential_strengths=[o for o in observations
                                if o.observation_type == ObservationType.POTENTIAL_STRENGTH],
            potential_weaknesses=[o for o in observations
                                 if o.observation_type == ObservationType.POTENTIAL_WEAKNESS],
            potential_deficiencies=[o for o in observations
                                   if o.observation_type == ObservationType.POTENTIAL_DEFICIENCY],
            discussion_questions=[o for o in observations
                                 if o.observation_type == ObservationType.DISCUSSION_QUESTION],
            information_gaps=[o for o in observations
                              if o.observation_type == ObservationType.INFORMATION_GAP],
        )
        return panel

    # ── Three-Panel Assembly ─────────────────────────────────────────────

    def build_presentation(
        self,
        # Panel 1 inputs
        factor_id: str,
        factor_name: str,
        section_l_instruction: str,
        section_l_ref: str,
        section_m_factor: str,
        section_m_ref: str,
        subfactors: list[dict[str, str]],
        adjectival_definitions: list[dict[str, str]],
        pws_sections: list[str],
        relative_importance: str,
        evaluation_methodology: str,
        # Panel 2 inputs
        offeror_id: str,
        offeror_name: str,
        page_limit: int | None = None,
        total_pages: int | None = None,
    ) -> ThreePanelPresentation:
        """Build the complete three-panel presentation for one factor × one offeror."""
        # Panel 1: Solicitation Requirements
        panel_1 = self.build_requirements_panel(
            factor_id=factor_id,
            factor_name=factor_name,
            section_l_instruction=section_l_instruction,
            section_l_ref=section_l_ref,
            section_m_factor=section_m_factor,
            section_m_ref=section_m_ref,
            subfactors=subfactors,
            adjectival_definitions=adjectival_definitions,
            pws_sections=pws_sections,
            relative_importance=relative_importance,
            evaluation_methodology=evaluation_methodology,
            page_limit=page_limit,
        )

        # Panel 2: Offeror Submission
        all_subfactor_ids = [sf.get("id", sf.get("subfactor_id", "")) for sf in subfactors]
        panel_2 = self.build_submission_panel(
            factor_id=factor_id,
            offeror_id=offeror_id,
            offeror_name=offeror_name,
            all_subfactor_ids=all_subfactor_ids,
            total_pages=total_pages,
            page_limit=page_limit,
        )

        # Panel 3: Preliminary Observations
        key = f"{factor_id}:{offeror_id}"
        excerpts = self._excerpts.get(key, [])
        panel_3 = self.generate_observations(
            factor_id=factor_id,
            offeror_id=offeror_id,
            excerpts=excerpts,
            subfactors=subfactors,
            pws_sections=pws_sections,
        )

        presentation = ThreePanelPresentation(
            factor_id=factor_id,
            offeror_id=offeror_id,
            panel_1=panel_1,
            panel_2=panel_2,
            panel_3=panel_3,
        )
        self._presentations[key] = presentation
        return presentation

    # ── SSDD Enhancement ─────────────────────────────────────────────────

    def generate_ssdd_enhancement(
        self,
        workspace_id: str,
        factors: list[dict[str, Any]],
        offeror_scores: dict[str, dict[str, Any]],
        excluded_offerors: list[dict[str, str]] | None = None,
        evaluation_methodology: str = "tradeoff",
    ) -> SSDDEnhancement:
        """Generate enhanced SSDD with factor-by-factor comparison.

        factors: [{factor_id, factor_name, relative_importance, far_authority}]
        offeror_scores: {offeror_id: {factor_id: {rating, strengths, weaknesses,
                         deficiencies, narrative}}}
        excluded_offerors: [{offeror_id, rationale}]

        Tier 2: AI drafts the comparison narrative. SSA accepts/modifies/overrides.
        Tier 3: SSA makes the award decision. FedProcure NEVER recommends.
        """
        factor_comparisons = []

        for factor in factors:
            fid = factor["factor_id"]
            fname = factor["factor_name"]

            offeror_summaries = []
            rating_ranks = []

            for oid, scores in offeror_scores.items():
                # Skip excluded offerors
                if excluded_offerors and any(
                    ex["offeror_id"] == oid for ex in excluded_offerors
                ):
                    continue

                factor_score = scores.get(fid, {})
                rating = factor_score.get("rating", "Not Evaluated")
                s_count = factor_score.get("strengths", 0)
                w_count = factor_score.get("weaknesses", 0)
                d_count = factor_score.get("deficiencies", 0)
                narrative = factor_score.get("narrative", "")

                offeror_summaries.append({
                    "offeror_id": oid,
                    "rating": rating,
                    "strengths": s_count,
                    "weaknesses": w_count,
                    "deficiencies": d_count,
                    "narrative": narrative,
                })
                rating_ranks.append((oid, _rating_rank(rating), s_count, w_count, d_count))

            # Sort by rating (desc), then strengths (desc), then weaknesses (asc)
            rating_ranks.sort(key=lambda x: (-x[1], -x[2], x[3], x[4]))
            relative_ranking = [r[0] for r in rating_ranks]

            # Identify discriminators
            discriminators = _identify_discriminators(offeror_summaries)

            # Draft tradeoff narrative
            tradeoff_narrative = _draft_tradeoff_narrative(
                fname, offeror_summaries, discriminators, evaluation_methodology
            )

            factor_comparisons.append(FactorComparison(
                factor_id=fid,
                factor_name=fname,
                offeror_summaries=offeror_summaries,
                discriminators=discriminators,
                relative_ranking=relative_ranking,
                tradeoff_narrative=tradeoff_narrative,
            ))

        # Overall tradeoff narrative
        overall = _draft_overall_tradeoff(
            factor_comparisons, offeror_scores, evaluation_methodology
        )

        # Price/technical relationship documentation
        price_tech = _document_price_technical_relationship(
            factor_comparisons, offeror_scores, evaluation_methodology
        )

        enhancement = SSDDEnhancement(
            workspace_id=workspace_id,
            factor_comparisons=factor_comparisons,
            overall_tradeoff_narrative=overall,
            price_technical_relationship=price_tech,
            excluded_offerors=excluded_offerors or [],
        )
        self._ssdd_cache[workspace_id] = enhancement
        return enhancement

    # ── Serialization ────────────────────────────────────────────────────

    def presentation_to_dict(self, p: ThreePanelPresentation) -> dict:
        """Serialize a ThreePanelPresentation for API response."""
        return {
            "factor_id": p.factor_id,
            "offeror_id": p.offeror_id,
            "tier_boundary": p.tier_boundary,
            "generated_at": p.generated_at.isoformat(),
            "panel_1_solicitation_requirements": {
                "factor_name": p.panel_1.factor_name,
                "section_l_ref": p.panel_1.section_l_ref,
                "section_l_instruction": p.panel_1.section_l_instruction,
                "section_m_ref": p.panel_1.section_m_ref,
                "section_m_factor": p.panel_1.section_m_factor,
                "subfactors": p.panel_1.subfactors,
                "adjectival_definitions": p.panel_1.adjectival_definitions,
                "pws_sections": p.panel_1.pws_sections,
                "relative_importance": p.panel_1.relative_importance,
                "evaluation_methodology": p.panel_1.evaluation_methodology,
                "page_limit": p.panel_1.page_limit,
                "far_authority": p.panel_1.far_authority,
            },
            "panel_2_offeror_submission": {
                "offeror_name": p.panel_2.offeror_name,
                "excerpts": [
                    {
                        "excerpt_id": ex.excerpt_id,
                        "text": ex.text,
                        "source_page": ex.source_page,
                        "source_section": ex.source_section,
                        "subfactor_mapping": ex.subfactor_mapping,
                        "coverage": ex.coverage,
                    }
                    for ex in p.panel_2.excerpts
                ],
                "addressed_subfactors": p.panel_2.addressed_subfactors,
                "unaddressed_subfactors": p.panel_2.unaddressed_subfactors,
                "total_pages": p.panel_2.total_pages,
                "compliance_note": p.panel_2.compliance_note,
            },
            "panel_3_preliminary_observations": {
                "tier_notice": p.panel_3.tier_notice,
                "far_authority": p.panel_3.far_authority,
                "total_observations": len(p.panel_3.observations),
                "potential_strengths": len(p.panel_3.potential_strengths),
                "potential_weaknesses": len(p.panel_3.potential_weaknesses),
                "potential_deficiencies": len(p.panel_3.potential_deficiencies),
                "discussion_questions": len(p.panel_3.discussion_questions),
                "information_gaps": len(p.panel_3.information_gaps),
                "observations": [
                    {
                        "observation_id": o.observation_id,
                        "type": o.observation_type.value,
                        "description": o.description,
                        "evidence": o.evidence,
                        "subfactor_id": o.subfactor_id,
                        "pws_reference": o.pws_reference,
                        "confidence": o.confidence,
                        "source_provenance": o.source_provenance,
                    }
                    for o in p.panel_3.observations
                ],
            },
        }

    def ssdd_to_dict(self, s: SSDDEnhancement) -> dict:
        """Serialize an SSDDEnhancement for API response."""
        return {
            "workspace_id": s.workspace_id,
            "tier3_notice": s.tier3_notice,
            "tradeoff_standard": s.tradeoff_standard,
            "generated_at": s.generated_at.isoformat(),
            "requires_acceptance": s.requires_acceptance,
            "overall_tradeoff_narrative": s.overall_tradeoff_narrative,
            "price_technical_relationship": s.price_technical_relationship,
            "excluded_offerors": s.excluded_offerors,
            "factor_comparisons": [
                {
                    "factor_id": fc.factor_id,
                    "factor_name": fc.factor_name,
                    "relative_ranking": fc.relative_ranking,
                    "discriminators": fc.discriminators,
                    "tradeoff_narrative": fc.tradeoff_narrative,
                    "offeror_summaries": fc.offeror_summaries,
                }
                for fc in s.factor_comparisons
            ],
            "source_provenance": s.source_provenance,
        }


# ─── Helper Functions ───────────────────────────────────────────────────────

RATING_ORDER = {
    "Outstanding": 5, "Good": 4, "Acceptable": 3,
    "Marginal": 2, "Unacceptable": 1, "Not Evaluated": 0,
}


def _rating_rank(rating: str) -> int:
    """Convert adjectival rating to numeric rank."""
    return RATING_ORDER.get(rating, 0)


def _identify_discriminators(offeror_summaries: list[dict]) -> list[str]:
    """Identify what distinguishes offerors on a factor."""
    discriminators = []

    if len(offeror_summaries) < 2:
        return ["Single offeror — no comparison available"]

    ratings = [s["rating"] for s in offeror_summaries]
    unique_ratings = set(ratings)
    if len(unique_ratings) > 1:
        discriminators.append(
            f"Rating spread: {', '.join(sorted(unique_ratings, key=lambda r: -_rating_rank(r)))}"
        )

    # S/W/D count differences
    max_s = max(s["strengths"] for s in offeror_summaries)
    min_s = min(s["strengths"] for s in offeror_summaries)
    if max_s > min_s:
        discriminators.append(f"Strength count range: {min_s}–{max_s}")

    max_w = max(s["weaknesses"] for s in offeror_summaries)
    if max_w > 0:
        discriminators.append(f"Weakness exposure: up to {max_w} weakness(es)")

    max_d = max(s["deficiencies"] for s in offeror_summaries)
    if max_d > 0:
        discriminators.append(f"Deficiency alert: {max_d} deficiency(ies) present")

    if not discriminators:
        discriminators.append("No significant discriminators identified between offerors")

    return discriminators


def _draft_tradeoff_narrative(
    factor_name: str,
    summaries: list[dict],
    discriminators: list[str],
    methodology: str,
) -> str:
    """Draft a factor-level tradeoff narrative for SSA consideration."""
    if methodology == "lpta":
        return (
            f"Under LPTA evaluation per FAR 15.101-2, {factor_name} is evaluated "
            f"on a pass/fail basis. All offerors rated Acceptable or above are "
            f"technically acceptable; the lowest-priced acceptable offeror represents "
            f"the best value to the Government."
        )

    if len(summaries) < 2:
        return f"Single offeror evaluation — tradeoff analysis not applicable for {factor_name}."

    # Build narrative from discriminators
    disc_text = "; ".join(discriminators) if discriminators else "minimal differentiation"

    top = max(summaries, key=lambda s: (_rating_rank(s["rating"]), s["strengths"], -s["weaknesses"]))
    bottom = min(summaries, key=lambda s: (_rating_rank(s["rating"]), s["strengths"], -s["weaknesses"]))

    narrative = (
        f"For {factor_name}, the evaluation reveals the following discriminators: "
        f"{disc_text}. "
        f"Offeror {top['offeror_id']} received the highest rating of {top['rating']} "
        f"with {top['strengths']} strength(s) and {top['weaknesses']} weakness(es). "
    )

    if top["offeror_id"] != bottom["offeror_id"]:
        narrative += (
            f"Offeror {bottom['offeror_id']} received {bottom['rating']} "
            f"with {bottom['strengths']} strength(s) and {bottom['weaknesses']} weakness(es). "
        )

    narrative += (
        "The SSA must independently assess whether the technical differences "
        "between proposals warrant any price premium, considering the relative "
        "importance of this factor as stated in the solicitation."
    )
    return narrative


def _draft_overall_tradeoff(
    factor_comparisons: list[FactorComparison],
    offeror_scores: dict[str, dict[str, Any]],
    methodology: str,
) -> str:
    """Draft overall tradeoff narrative for SSDD."""
    if methodology == "lpta":
        return (
            "Under LPTA evaluation per FAR 15.101-2, award shall be made to the "
            "lowest-priced offeror whose proposal meets all technical acceptability "
            "standards. No tradeoff analysis is required."
        )

    num_factors = len(factor_comparisons)
    num_offerors = len(offeror_scores)

    narrative = (
        f"This source selection involved the evaluation of {num_offerors} offeror(s) "
        f"across {num_factors} evaluation factor(s) using a best value tradeoff "
        f"process per FAR 15.101-1. "
    )

    # Summarize factor-level results
    for fc in factor_comparisons:
        if fc.relative_ranking:
            narrative += (
                f"For {fc.factor_name}, {fc.relative_ranking[0]} was highest-ranked. "
            )

    narrative += (
        "The SSA must make an independent integrated assessment of proposals, "
        "considering the relative merits of each offeror's technical approach "
        "against the evaluated price, consistent with the stated evaluation "
        "criteria. Per GAO case law, this assessment must discuss the relative "
        "qualities of proposals — not just restate adjectival ratings — and "
        "demonstrate that as the price differential increases, the relative "
        "technical benefits also increase proportionally."
    )
    return narrative


def _document_price_technical_relationship(
    factor_comparisons: list[FactorComparison],
    offeror_scores: dict[str, dict[str, Any]],
    methodology: str,
) -> str:
    """Document the price/technical relationship for SSDD."""
    if methodology == "lpta":
        return (
            "Under LPTA, price is the determining factor for technically acceptable "
            "proposals. No price/technical tradeoff relationship exists."
        )

    return (
        "The solicitation stated that non-price factors, when combined, are "
        "significantly more important than price. As the evaluation progresses "
        "and price proposals are opened, the SSA must document how the technical "
        "differences between proposals justify (or do not justify) any price "
        "premium. If the highest technically rated offeror is also the lowest "
        "priced, no tradeoff analysis is required — this should be stated explicitly. "
        "Source: FAR 15.101-1, TSA Best Value Decisions Aug 2023."
    )
