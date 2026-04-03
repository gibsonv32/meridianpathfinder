"""
Evaluation Factor Derivation Engine (Phase 23b)
7-step pipeline: PWS analysis → requirement classification → factor candidate
generation → subfactor mapping → weight suggestion → adjectival definition
drafting → protest-proofing check.

Architecture:
- Pure deterministic (Tier 1) logic for derivation + classification
- AI-appropriate (Tier 2) for narrative generation: SSA accepts/modifies/overrides
- Tier 3: SSA makes final factor selection, relative importance, adjectival approval
  per FAR 15.308

Protest-Proofing Checks (6 automated validations):
1. Every Section L instruction traces to at least one Section M factor
2. Every Section M factor traces to at least one PWS requirement
3. No unstated evaluation criteria (FAR 15.304)
4. Adjectival definitions distinguishable between ratings (GAO case law)
5. Price/technical weight relationship consistent with stated importance
6. Past performance questionnaire aligns with evaluation subfactors

References:
- FedProcure_Phase24_26_Spec.md, Phase 23b
- FAR 15.304 (evaluation factors), FAR 15.101-1 (tradeoff), FAR 15.101-2 (LPTA)
- FAR 15.305 (evaluation), FAR 15.308 (SSA decision authority)
- TSA PL 2017-004 (SSA appointment)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Enums ──────────────────────────────────────────────────────────────────

class RequirementCategory(str, Enum):
    """PWS requirement classification for factor mapping."""
    TECHNICAL = "technical"
    MANAGEMENT = "management"
    PAST_PERFORMANCE = "past_performance"
    STAFFING = "staffing"
    TRANSITION = "transition"
    SECURITY = "security"
    QUALITY = "quality"


class EvalMethodology(str, Enum):
    TRADEOFF = "tradeoff"
    LPTA = "lpta"


class AdjectivalRating(str, Enum):
    OUTSTANDING = "Outstanding"
    GOOD = "Good"
    ACCEPTABLE = "Acceptable"
    MARGINAL = "Marginal"
    UNACCEPTABLE = "Unacceptable"


class ProtestCheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


# ─── Data Classes ───────────────────────────────────────────────────────────

@dataclass
class PWSRequirement:
    """A parsed requirement from the PWS."""
    section_ref: str           # e.g. "3.1", "4.2.1"
    text: str                  # Requirement text
    category: RequirementCategory
    keywords: list[str] = field(default_factory=list)
    is_measurable: bool = False
    sla_target: str | None = None


@dataclass
class SubFactor:
    """An evaluation subfactor under a main factor."""
    subfactor_id: str          # e.g. "SF-T-01"
    name: str
    description: str
    pws_sections: list[str]    # PWS sections this subfactor evaluates
    weight_within_factor: float = 0.0  # 0-1, suggested weight


@dataclass
class AdjectivalDefinition:
    """Definition for one rating level of one factor."""
    rating: AdjectivalRating
    definition: str            # Specific criteria distinguishing this level
    discriminators: list[str]  # What makes this different from adjacent ratings


@dataclass
class EvalFactor:
    """A derived evaluation factor with subfactors and definitions."""
    factor_id: str             # e.g. "F-01"
    name: str                  # e.g. "Technical Approach"
    far_authority: str         # FAR citation
    subfactors: list[SubFactor]
    adjectival_definitions: list[AdjectivalDefinition]
    pws_traceability: list[str]  # PWS sections covered
    l_instruction_ref: str | None = None  # Section L reference
    relative_importance: str = ""  # e.g. "significantly more important than price"
    suggested_weight: float = 0.0  # Numeric suggestion (Tier 2)


@dataclass
class ProtestProofCheck:
    """Result of one protest-proofing validation."""
    check_id: str              # PP-01 through PP-06
    check_name: str
    status: ProtestCheckStatus
    detail: str
    remediation: str
    far_authority: str


@dataclass
class DerivationResult:
    """Full output of the 7-step derivation pipeline."""
    requirements: list[PWSRequirement]
    factors: list[EvalFactor]
    methodology: EvalMethodology
    protest_checks: list[ProtestProofCheck]
    overall_protest_score: float  # 0-100, higher = more protest-resistant
    warnings: list[str]
    source_provenance: list[str]
    requires_acceptance: bool = True  # Tier 2 — SSA must accept


# ─── Classification Keywords ───────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[RequirementCategory, list[str]] = {
    RequirementCategory.TECHNICAL: [
        "system", "software", "hardware", "architecture", "design", "develop",
        "implement", "integrate", "migrate", "interface", "platform", "database",
        "network", "cloud", "cyber", "FISMA", "FedRAMP", "NIST", "ATO",
        "application", "infrastructure", "DevOps", "CI/CD", "API",
    ],
    RequirementCategory.MANAGEMENT: [
        "manage", "plan", "schedule", "coordinate", "report", "communicate",
        "oversight", "governance", "risk", "program management", "project",
        "PMO", "status", "milestone", "WBS", "resource", "budget",
    ],
    RequirementCategory.PAST_PERFORMANCE: [
        "past performance", "experience", "similar", "reference", "contract",
        "track record", "demonstrated", "CPARS", "prior",
    ],
    RequirementCategory.STAFFING: [
        "staff", "personnel", "key personnel", "FTE", "labor", "team",
        "qualification", "certification", "clearance", "resume",
    ],
    RequirementCategory.TRANSITION: [
        "transition", "phase-in", "phase-out", "knowledge transfer",
        "onboarding", "handoff", "turnover", "incumbent",
    ],
    RequirementCategory.SECURITY: [
        "security", "clearance", "SSI", "CUI", "classified", "TWIC",
        "background", "suitability", "HSPD-12", "PIV", "badge",
    ],
    RequirementCategory.QUALITY: [
        "quality", "SLA", "metric", "KPI", "performance", "standard",
        "acceptance", "inspection", "testing", "validation",
    ],
}

# Standard factors per FAR 15.304
STANDARD_FACTORS = {
    "technical_approach": {
        "name": "Technical Approach",
        "far": "FAR 15.304(c)(3)",
        "categories": [RequirementCategory.TECHNICAL, RequirementCategory.SECURITY],
        "l_section": "L.3",
    },
    "management_approach": {
        "name": "Management Approach",
        "far": "FAR 15.304(c)(3)",
        "categories": [RequirementCategory.MANAGEMENT, RequirementCategory.STAFFING,
                       RequirementCategory.TRANSITION],
        "l_section": "L.4",
    },
    "past_performance": {
        "name": "Past Performance",
        "far": "FAR 15.304(c)(2)",
        "categories": [RequirementCategory.PAST_PERFORMANCE],
        "l_section": "L.5",
    },
    "price": {
        "name": "Price/Cost",
        "far": "FAR 15.304(c)(1)",
        "categories": [],
        "l_section": "L.6",
    },
}

# Adjectival scale template per FAR 15.305
ADJECTIVAL_TEMPLATES: dict[str, dict[AdjectivalRating, dict]] = {
    "technical_approach": {
        AdjectivalRating.OUTSTANDING: {
            "template": "Proposal demonstrates an exceptional {factor_lower} that significantly "
                        "exceeds requirements, demonstrating a thorough understanding of the "
                        "objectives with multiple strengths and no weaknesses.",
            "discriminators": ["significantly exceeds", "multiple strengths", "no weaknesses"],
        },
        AdjectivalRating.GOOD: {
            "template": "Proposal demonstrates a thorough {factor_lower} that exceeds some "
                        "requirements with one or more strengths. Any weaknesses are minor.",
            "discriminators": ["exceeds some", "one or more strengths", "minor weaknesses"],
        },
        AdjectivalRating.ACCEPTABLE: {
            "template": "Proposal demonstrates an adequate {factor_lower} that meets all "
                        "minimum requirements. Strengths and weaknesses are essentially equal.",
            "discriminators": ["meets all minimum", "strengths and weaknesses equal"],
        },
        AdjectivalRating.MARGINAL: {
            "template": "Proposal demonstrates a {factor_lower} that fails to meet some "
                        "requirements. One or more weaknesses exist without offsetting strengths.",
            "discriminators": ["fails to meet some", "weaknesses without offsetting strengths"],
        },
        AdjectivalRating.UNACCEPTABLE: {
            "template": "Proposal demonstrates a {factor_lower} that fails to meet one or more "
                        "minimum requirements. One or more deficiencies exist that are not correctable.",
            "discriminators": ["fails to meet minimum", "deficiencies not correctable"],
        },
    },
}

# Default template used for management_approach and past_performance
ADJECTIVAL_TEMPLATES["management_approach"] = ADJECTIVAL_TEMPLATES["technical_approach"]
ADJECTIVAL_TEMPLATES["past_performance"] = {
    AdjectivalRating.OUTSTANDING: {
        "template": "Based on past performance information, the Government has a high expectation "
                    "that the offeror will successfully perform the required effort.",
        "discriminators": ["high expectation", "successfully perform"],
    },
    AdjectivalRating.GOOD: {
        "template": "Based on past performance information, the Government has a reasonable "
                    "expectation that the offeror will successfully perform the required effort.",
        "discriminators": ["reasonable expectation"],
    },
    AdjectivalRating.ACCEPTABLE: {
        "template": "Based on past performance information, the Government has a moderate "
                    "expectation that the offeror will successfully perform the required effort.",
        "discriminators": ["moderate expectation"],
    },
    AdjectivalRating.MARGINAL: {
        "template": "Based on past performance information, the Government has a low expectation "
                    "that the offeror will successfully perform the required effort.",
        "discriminators": ["low expectation"],
    },
    AdjectivalRating.UNACCEPTABLE: {
        "template": "Based on past performance information, the Government has no expectation "
                    "that the offeror will successfully perform the required effort.",
        "discriminators": ["no expectation"],
    },
}


# ─── Step 1: PWS Section Analysis ──────────────────────────────────────────

def parse_pws_requirements(pws_sections: dict[str, str]) -> list[PWSRequirement]:
    """Parse PWS content into structured requirements.

    Args:
        pws_sections: Dict of section_ref -> content text

    Returns:
        List of PWSRequirement with category classification
    """
    requirements = []
    for section_ref, content in pws_sections.items():
        if not content.strip():
            continue

        category = classify_requirement(content)
        keywords = extract_keywords(content)
        is_measurable = _has_measurable_criteria(content)
        sla = _extract_sla_target(content)

        requirements.append(PWSRequirement(
            section_ref=section_ref,
            text=content,
            category=category,
            keywords=keywords,
            is_measurable=is_measurable,
            sla_target=sla,
        ))

    return requirements


# ─── Step 2: Requirement Classification ────────────────────────────────────

def classify_requirement(content: str) -> RequirementCategory:
    """Classify a PWS section into a requirement category.

    Uses keyword matching against CATEGORY_KEYWORDS. Highest match wins.
    """
    scores: dict[RequirementCategory, int] = {}
    content_lower = content.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in content_lower)
        scores[category] = score

    if not any(scores.values()):
        return RequirementCategory.TECHNICAL  # Default

    return max(scores, key=scores.get)


def extract_keywords(content: str) -> list[str]:
    """Extract relevant keywords from content."""
    found = []
    content_lower = content.lower()
    for keywords in CATEGORY_KEYWORDS.values():
        for kw in keywords:
            if kw.lower() in content_lower and kw not in found:
                found.append(kw)
    return found[:10]  # Limit to top 10


def _has_measurable_criteria(content: str) -> bool:
    """Check if content contains measurable criteria."""
    import re
    patterns = [r"\d+\s*%", r"\d+\s*(hours?|days?|minutes?)", r"SLA", r"KPI"]
    return any(re.search(p, content, re.IGNORECASE) for p in patterns)


def _extract_sla_target(content: str) -> str | None:
    """Extract SLA target if present."""
    import re
    match = re.search(r"(\d+\.?\d*\s*%\s*\w+)", content)
    if match:
        return match.group(1)
    match = re.search(r"(within\s+\d+\s*\w+)", content, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


# ─── Step 3: Factor Candidate Generation ──────────────────────────────────

def generate_factor_candidates(
    requirements: list[PWSRequirement],
    params: dict[str, Any],
) -> list[EvalFactor]:
    """Generate evaluation factor candidates from classified requirements.

    Maps PWS requirement categories to standard evaluation factors per FAR 15.304.
    """
    # Group requirements by category
    by_category: dict[RequirementCategory, list[PWSRequirement]] = {}
    for req in requirements:
        by_category.setdefault(req.category, []).append(req)

    factors = []
    factor_num = 1

    for factor_key, factor_def in STANDARD_FACTORS.items():
        if factor_key == "price":
            continue  # Price handled separately

        # Collect PWS sections for this factor
        pws_refs = []
        for cat in factor_def["categories"]:
            for req in by_category.get(cat, []):
                pws_refs.append(req.section_ref)

        if not pws_refs and factor_key != "past_performance":
            continue  # Skip factors with no PWS backing (except past perf)

        factors.append(EvalFactor(
            factor_id=f"F-{factor_num:02d}",
            name=factor_def["name"],
            far_authority=factor_def["far"],
            subfactors=[],  # Populated in step 4
            adjectival_definitions=[],  # Populated in step 6
            pws_traceability=pws_refs,
            l_instruction_ref=factor_def["l_section"],
        ))
        factor_num += 1

    # Price/Cost always included per FAR 15.304(c)(1)
    factors.append(EvalFactor(
        factor_id=f"F-{factor_num:02d}",
        name="Price/Cost",
        far_authority="FAR 15.304(c)(1)",
        subfactors=[],
        adjectival_definitions=[],
        pws_traceability=[],
        l_instruction_ref="L.6",
    ))

    return factors


# ─── Step 4: Subfactor Mapping ─────────────────────────────────────────────

def map_subfactors(
    factors: list[EvalFactor],
    requirements: list[PWSRequirement],
) -> list[EvalFactor]:
    """Map PWS requirements to subfactors within each evaluation factor.

    Groups related PWS sections into coherent subfactors.
    """
    for factor in factors:
        if factor.name == "Price/Cost":
            factor.subfactors = [
                SubFactor(
                    subfactor_id=f"{factor.factor_id}-SF-01",
                    name="Total Evaluated Price",
                    description="Total price for base and all option periods.",
                    pws_sections=[],
                    weight_within_factor=1.0,
                ),
            ]
            continue

        if factor.name == "Past Performance":
            factor.subfactors = [
                SubFactor(
                    subfactor_id=f"{factor.factor_id}-SF-01",
                    name="Relevance",
                    description="Degree of similarity in scope, complexity, and dollar value "
                                "of referenced contracts to current requirement.",
                    pws_sections=[],
                    weight_within_factor=0.4,
                ),
                SubFactor(
                    subfactor_id=f"{factor.factor_id}-SF-02",
                    name="Quality of Performance",
                    description="Quality, timeliness, and customer satisfaction demonstrated "
                                "on referenced contracts.",
                    pws_sections=[],
                    weight_within_factor=0.6,
                ),
            ]
            continue

        # Group PWS sections for technical/management subfactors
        subfactor_groups: dict[str, list[str]] = {}
        sf_num = 1

        for pws_ref in factor.pws_traceability:
            # Find the requirement
            req = next((r for r in requirements if r.section_ref == pws_ref), None)
            if not req:
                continue

            # Group by sub-category
            group_name = _subfactor_group_name(req)
            subfactor_groups.setdefault(group_name, []).append(pws_ref)

        for group_name, pws_refs in subfactor_groups.items():
            factor.subfactors.append(SubFactor(
                subfactor_id=f"{factor.factor_id}-SF-{sf_num:02d}",
                name=group_name,
                description=f"Offeror's approach to {group_name.lower()} "
                            f"as described in PWS sections {', '.join(pws_refs)}.",
                pws_sections=pws_refs,
                weight_within_factor=round(1.0 / max(len(subfactor_groups), 1), 2),
            ))
            sf_num += 1

    return factors


def _subfactor_group_name(req: PWSRequirement) -> str:
    """Generate a subfactor group name from requirement keywords."""
    if req.category == RequirementCategory.SECURITY:
        return "Security Approach"
    if req.category == RequirementCategory.STAFFING:
        return "Staffing & Key Personnel"
    if req.category == RequirementCategory.TRANSITION:
        return "Transition Plan"
    if req.category == RequirementCategory.QUALITY:
        return "Quality Control"

    # Use first keyword if available
    if req.keywords:
        kw = req.keywords[0]
        return f"{kw.title()} Approach"

    return f"Section {req.section_ref} Approach"


# ─── Step 5: Weight Suggestion ─────────────────────────────────────────────

def suggest_weights(
    factors: list[EvalFactor],
    params: dict[str, Any],
) -> list[EvalFactor]:
    """Suggest relative weights for evaluation factors.

    Tier 2: SSA makes final weight determination per FAR 15.308.
    """
    value = params.get("estimated_value", 0)
    is_it = params.get("is_it", False)
    methodology = params.get("evaluation_type", "tradeoff")

    if methodology == "lpta":
        # LPTA: price dominates, tech is pass/fail
        for f in factors:
            if f.name == "Price/Cost":
                f.suggested_weight = 0.60
                f.relative_importance = "most important factor"
            elif f.name == "Technical Approach":
                f.suggested_weight = 0.20
                f.relative_importance = "pass/fail threshold"
            elif f.name == "Past Performance":
                f.suggested_weight = 0.15
                f.relative_importance = "confidence assessment"
            else:
                f.suggested_weight = 0.05
        return factors

    # Tradeoff: technical weight increases with value and complexity
    non_price = [f for f in factors if f.name != "Price/Cost"]
    price_factor = next((f for f in factors if f.name == "Price/Cost"), None)

    if value >= 50_000_000:
        tech_emphasis = 0.45
        price_weight = 0.15
    elif value >= 20_000_000:
        tech_emphasis = 0.40
        price_weight = 0.20
    elif value >= 5_500_000:
        tech_emphasis = 0.35
        price_weight = 0.25
    else:
        tech_emphasis = 0.30
        price_weight = 0.30

    remaining = 1.0 - price_weight
    for f in non_price:
        if f.name == "Technical Approach":
            f.suggested_weight = round(tech_emphasis, 2)
            if value >= 20_000_000:
                f.relative_importance = "significantly more important than price"
            else:
                f.relative_importance = "more important than price"
        elif f.name == "Past Performance":
            f.suggested_weight = round(remaining - tech_emphasis - 0.05 * max(len(non_price) - 2, 0), 2)
            f.relative_importance = "approximately equal to management approach"
        elif f.name == "Management Approach":
            f.suggested_weight = round(remaining - tech_emphasis - f.suggested_weight if f.suggested_weight else 0.15, 2)
            f.relative_importance = "approximately equal to past performance"
        else:
            f.suggested_weight = 0.05

    if price_factor:
        price_factor.suggested_weight = price_weight
        price_factor.relative_importance = "less important than non-price factors combined"

    # Normalize to ensure sum = 1.0
    total = sum(f.suggested_weight for f in factors)
    if total > 0 and abs(total - 1.0) > 0.01:
        for f in factors:
            f.suggested_weight = round(f.suggested_weight / total, 2)

    return factors


# ─── Step 6: Adjectival Definition Drafting ────────────────────────────────

def draft_adjectival_definitions(
    factors: list[EvalFactor],
) -> list[EvalFactor]:
    """Draft adjectival rating definitions for each factor.

    Uses templates with factor-specific language. Tier 2: SSA must review
    and accept definitions per FAR 15.305.
    """
    for factor in factors:
        if factor.name == "Price/Cost":
            continue  # Price is evaluated differently (not adjectival)

        # Determine which template to use
        if "technical" in factor.name.lower():
            template_key = "technical_approach"
        elif "past performance" in factor.name.lower():
            template_key = "past_performance"
        else:
            template_key = "management_approach"

        templates = ADJECTIVAL_TEMPLATES.get(template_key, ADJECTIVAL_TEMPLATES["technical_approach"])
        factor_lower = factor.name.lower()

        definitions = []
        for rating in AdjectivalRating:
            tmpl = templates.get(rating)
            if tmpl:
                definitions.append(AdjectivalDefinition(
                    rating=rating,
                    definition=tmpl["template"].format(factor_lower=factor_lower),
                    discriminators=tmpl["discriminators"],
                ))

        factor.adjectival_definitions = definitions

    return factors


# ─── Step 7: Protest-Proofing Checks ──────────────────────────────────────

def run_protest_proofing(
    factors: list[EvalFactor],
    requirements: list[PWSRequirement],
    l_sections: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> list[ProtestProofCheck]:
    """Run 6 automated protest-proofing validations.

    Args:
        factors: Derived evaluation factors
        requirements: Parsed PWS requirements
        l_sections: Section L content (optional — for L→M traceability)
        params: Acquisition parameters

    Returns:
        List of 6 ProtestProofCheck results
    """
    params = params or {}
    l_sections = l_sections or {}
    checks = []

    # PP-01: Every L instruction traces to at least one M factor
    checks.append(_check_l_to_m_traceability(factors, l_sections))

    # PP-02: Every M factor traces to at least one PWS requirement
    checks.append(_check_m_to_pws_traceability(factors, requirements))

    # PP-03: No unstated evaluation criteria (FAR 15.304)
    checks.append(_check_no_unstated_criteria(factors, requirements))

    # PP-04: Adjectival definitions distinguishable
    checks.append(_check_adjectival_distinguishability(factors))

    # PP-05: Price/technical weight consistency
    checks.append(_check_weight_consistency(factors, params))

    # PP-06: Past performance questionnaire alignment
    checks.append(_check_past_perf_alignment(factors))

    return checks


def _check_l_to_m_traceability(factors: list[EvalFactor], l_sections: dict[str, str]) -> ProtestProofCheck:
    """PP-01: Every Section L instruction traces to at least one Section M factor."""
    if not l_sections:
        return ProtestProofCheck(
            check_id="PP-01",
            check_name="L→M Traceability",
            status=ProtestCheckStatus.WARN,
            detail="No Section L content provided for traceability check.",
            remediation="Provide Section L content to enable L→M traceability validation.",
            far_authority="FAR 15.204-5",
        )

    l_refs = set()
    for factor in factors:
        if factor.l_instruction_ref:
            l_refs.add(factor.l_instruction_ref)

    # Check that each L section has a corresponding M factor
    l_keys = set(l_sections.keys())
    untraced = [k for k in l_keys if not any(ref in k for ref in l_refs)]

    if not untraced:
        return ProtestProofCheck(
            check_id="PP-01",
            check_name="L→M Traceability",
            status=ProtestCheckStatus.PASS,
            detail=f"All {len(l_keys)} Section L instructions trace to evaluation factors.",
            remediation="",
            far_authority="FAR 15.204-5",
        )

    return ProtestProofCheck(
        check_id="PP-01",
        check_name="L→M Traceability",
        status=ProtestCheckStatus.FAIL,
        detail=f"{len(untraced)} Section L instructions have no corresponding M factor: "
               f"{', '.join(untraced[:5])}",
        remediation="Add evaluation factors or subfactors covering these L instructions, "
                    "or remove the L instructions.",
        far_authority="FAR 15.204-5",
    )


def _check_m_to_pws_traceability(factors: list[EvalFactor], requirements: list[PWSRequirement]) -> ProtestProofCheck:
    """PP-02: Every M factor traces to at least one PWS requirement."""
    non_price = [f for f in factors if f.name != "Price/Cost" and f.name != "Past Performance"]
    untraced = [f.name for f in non_price if not f.pws_traceability]

    if not untraced:
        return ProtestProofCheck(
            check_id="PP-02",
            check_name="M→PWS Traceability",
            status=ProtestCheckStatus.PASS,
            detail=f"All {len(non_price)} non-price factors trace to PWS requirements.",
            remediation="",
            far_authority="FAR 15.304(c)",
        )

    return ProtestProofCheck(
        check_id="PP-02",
        check_name="M→PWS Traceability",
        status=ProtestCheckStatus.FAIL,
        detail=f"{len(untraced)} factors have no PWS traceability: {', '.join(untraced)}",
        remediation="Map each evaluation factor to specific PWS sections. "
                    "Factors without PWS backing are vulnerable to protest.",
        far_authority="FAR 15.304(c)",
    )


def _check_no_unstated_criteria(factors: list[EvalFactor], requirements: list[PWSRequirement]) -> ProtestProofCheck:
    """PP-03: No unstated evaluation criteria (FAR 15.304)."""
    # Check: every requirement category should map to at least one factor
    covered_categories = set()
    for f in factors:
        for sf in f.subfactors:
            for pws_ref in sf.pws_sections:
                req = next((r for r in requirements if r.section_ref == pws_ref), None)
                if req:
                    covered_categories.add(req.category)

    # Past performance and price don't need PWS coverage
    all_categories = {r.category for r in requirements}
    uncovered = all_categories - covered_categories - {RequirementCategory.PAST_PERFORMANCE}

    if not uncovered:
        return ProtestProofCheck(
            check_id="PP-03",
            check_name="No Unstated Criteria",
            status=ProtestCheckStatus.PASS,
            detail="All PWS requirement categories covered by evaluation factors.",
            remediation="",
            far_authority="FAR 15.304",
        )

    return ProtestProofCheck(
        check_id="PP-03",
        check_name="No Unstated Criteria",
        status=ProtestCheckStatus.WARN,
        detail=f"PWS categories not explicitly evaluated: {', '.join(c.value for c in uncovered)}. "
               f"Verify these are covered within existing factors or not evaluation-relevant.",
        remediation="Either add subfactors covering these categories or document why they "
                    "don't require separate evaluation.",
        far_authority="FAR 15.304",
    )


def _check_adjectival_distinguishability(factors: list[EvalFactor]) -> ProtestProofCheck:
    """PP-04: Adjectival definitions distinguishable between adjacent ratings."""
    issues = []
    for factor in factors:
        if not factor.adjectival_definitions:
            continue

        # Check each adjacent pair
        defs = factor.adjectival_definitions
        for i in range(len(defs) - 1):
            upper = defs[i]
            lower = defs[i + 1]
            # Check discriminators exist and differ
            if not upper.discriminators or not lower.discriminators:
                issues.append(f"{factor.name}: {upper.rating.value}/{lower.rating.value} "
                              f"lack discriminators")
            elif set(upper.discriminators) == set(lower.discriminators):
                issues.append(f"{factor.name}: {upper.rating.value}/{lower.rating.value} "
                              f"have identical discriminators")

    if not issues:
        rated_factors = [f for f in factors if f.adjectival_definitions]
        return ProtestProofCheck(
            check_id="PP-04",
            check_name="Adjectival Distinguishability",
            status=ProtestCheckStatus.PASS,
            detail=f"All {len(rated_factors)} factors have distinguishable adjectival definitions.",
            remediation="",
            far_authority="GAO case law (B-414230 et al.)",
        )

    return ProtestProofCheck(
        check_id="PP-04",
        check_name="Adjectival Distinguishability",
        status=ProtestCheckStatus.FAIL,
        detail=f"{len(issues)} distinguishability issues: {'; '.join(issues[:3])}",
        remediation="Ensure each adjacent rating level has unique discriminating language "
                    "that evaluators can consistently apply.",
        far_authority="GAO case law (B-414230 et al.)",
    )


def _check_weight_consistency(factors: list[EvalFactor], params: dict[str, Any]) -> ProtestProofCheck:
    """PP-05: Price/technical weight relationship consistent with stated importance."""
    tech = next((f for f in factors if "technical" in f.name.lower()), None)
    price = next((f for f in factors if "price" in f.name.lower()), None)

    if not tech or not price:
        return ProtestProofCheck(
            check_id="PP-05",
            check_name="Weight Consistency",
            status=ProtestCheckStatus.WARN,
            detail="Cannot verify weight consistency — missing technical or price factor.",
            remediation="Ensure both Technical Approach and Price/Cost factors are present.",
            far_authority="FAR 15.101-1",
        )

    if "significantly more important" in tech.relative_importance:
        if tech.suggested_weight <= price.suggested_weight:
            return ProtestProofCheck(
                check_id="PP-05",
                check_name="Weight Consistency",
                status=ProtestCheckStatus.FAIL,
                detail=f"Technical stated as 'significantly more important' but weight "
                       f"({tech.suggested_weight:.0%}) ≤ price ({price.suggested_weight:.0%}).",
                remediation="Increase technical weight relative to price to match stated importance.",
                far_authority="FAR 15.101-1",
            )

    if tech.suggested_weight > price.suggested_weight:
        return ProtestProofCheck(
            check_id="PP-05",
            check_name="Weight Consistency",
            status=ProtestCheckStatus.PASS,
            detail=f"Technical weight ({tech.suggested_weight:.0%}) > price ({price.suggested_weight:.0%}), "
                   f"consistent with '{tech.relative_importance}'.",
            remediation="",
            far_authority="FAR 15.101-1",
        )

    return ProtestProofCheck(
        check_id="PP-05",
        check_name="Weight Consistency",
        status=ProtestCheckStatus.WARN,
        detail=f"Technical weight ({tech.suggested_weight:.0%}) ≤ price ({price.suggested_weight:.0%}). "
               f"Verify this reflects intended relative importance.",
        remediation="Review whether stated importance matches numeric weights.",
        far_authority="FAR 15.101-1",
    )


def _check_past_perf_alignment(factors: list[EvalFactor]) -> ProtestProofCheck:
    """PP-06: Past performance questionnaire aligns with evaluation subfactors."""
    pp = next((f for f in factors if "past performance" in f.name.lower()), None)

    if not pp:
        return ProtestProofCheck(
            check_id="PP-06",
            check_name="Past Performance Alignment",
            status=ProtestCheckStatus.WARN,
            detail="No past performance factor found.",
            remediation="Add past performance as an evaluation factor per FAR 15.304(c)(2).",
            far_authority="FAR 15.304(c)(2)",
        )

    if pp.subfactors and len(pp.subfactors) >= 2:
        return ProtestProofCheck(
            check_id="PP-06",
            check_name="Past Performance Alignment",
            status=ProtestCheckStatus.PASS,
            detail=f"Past performance has {len(pp.subfactors)} subfactors "
                   f"({', '.join(sf.name for sf in pp.subfactors)}).",
            remediation="",
            far_authority="FAR 15.304(c)(2)",
        )

    return ProtestProofCheck(
        check_id="PP-06",
        check_name="Past Performance Alignment",
        status=ProtestCheckStatus.WARN,
        detail="Past performance has fewer than 2 subfactors. Consider adding "
               "Relevance and Quality of Performance.",
        remediation="Add subfactors: (1) Relevance — scope/complexity/value similarity, "
                    "(2) Quality — CPARS ratings, customer satisfaction.",
        far_authority="FAR 15.304(c)(2)",
    )


# ─── Orchestrator ──────────────────────────────────────────────────────────

class EvalFactorDerivationEngine:
    """7-step pipeline from PWS sections to protest-proofed evaluation factors."""

    def derive(
        self,
        pws_sections: dict[str, str],
        params: dict[str, Any],
        l_sections: dict[str, str] | None = None,
    ) -> DerivationResult:
        """Run the full 7-step derivation pipeline.

        Args:
            pws_sections: Dict of section_ref -> content text
            params: Acquisition parameters (estimated_value, is_it, evaluation_type, etc.)
            l_sections: Optional Section L content for traceability checks

        Returns:
            DerivationResult with factors, protest checks, and warnings
        """
        # Step 1: Parse PWS requirements
        requirements = parse_pws_requirements(pws_sections)

        # Step 2: Classification (done in step 1 via classify_requirement)

        # Step 3: Generate factor candidates
        factors = generate_factor_candidates(requirements, params)

        # Step 4: Map subfactors
        factors = map_subfactors(factors, requirements)

        # Step 5: Suggest weights
        methodology = EvalMethodology(params.get("evaluation_type", "tradeoff"))
        factors = suggest_weights(factors, params)

        # Step 6: Draft adjectival definitions
        factors = draft_adjectival_definitions(factors)

        # Step 7: Protest-proofing checks
        protest_checks = run_protest_proofing(factors, requirements, l_sections, params)

        # Calculate overall protest score
        passed = sum(1 for c in protest_checks if c.status == ProtestCheckStatus.PASS)
        warned = sum(1 for c in protest_checks if c.status == ProtestCheckStatus.WARN)
        total = len(protest_checks)
        protest_score = round((passed * 100 + warned * 50) / max(total, 1), 1)

        # Collect warnings
        warnings = []
        value = params.get("estimated_value", 0)
        if methodology == EvalMethodology.LPTA and value >= 20_000_000:
            warnings.append(
                f"LPTA on ${value/1e6:.0f}M acquisition — ensure D&F obtained or "
                f"Class D&F exception cited (HCA Aug 2022 for IT SW/HW)."
            )
        if not any(f.name == "Past Performance" for f in factors):
            warnings.append("No past performance factor — required per FAR 15.304(c)(2) "
                            "for negotiated procurements.")

        non_price = [f for f in factors if f.name != "Price/Cost"]
        for f in non_price:
            if not f.pws_traceability:
                warnings.append(f"Factor '{f.name}' has no PWS traceability — "
                                f"vulnerable to protest.")

        return DerivationResult(
            requirements=requirements,
            factors=factors,
            methodology=methodology,
            protest_checks=protest_checks,
            overall_protest_score=protest_score,
            warnings=warnings,
            source_provenance=[
                "FAR 15.304 (evaluation factors)",
                "FAR 15.101-1 (tradeoff process)",
                "FAR 15.305 (proposal evaluation)",
                "FAR 15.308 (SSA decision authority — Tier 3)",
                f"{len(requirements)} PWS requirements analyzed",
                f"{len(factors)} evaluation factors derived",
                f"{len(protest_checks)} protest-proofing checks executed",
            ],
            requires_acceptance=True,
        )


def derivation_to_dict(result: DerivationResult) -> dict[str, Any]:
    """Serialize derivation result for API response."""
    return {
        "requirements": [
            {
                "section_ref": r.section_ref,
                "category": r.category.value,
                "keywords": r.keywords,
                "is_measurable": r.is_measurable,
                "sla_target": r.sla_target,
            }
            for r in result.requirements
        ],
        "factors": [
            {
                "factor_id": f.factor_id,
                "name": f.name,
                "far_authority": f.far_authority,
                "subfactors": [
                    {
                        "subfactor_id": sf.subfactor_id,
                        "name": sf.name,
                        "description": sf.description,
                        "pws_sections": sf.pws_sections,
                        "weight": sf.weight_within_factor,
                    }
                    for sf in f.subfactors
                ],
                "adjectival_definitions": [
                    {
                        "rating": ad.rating.value,
                        "definition": ad.definition,
                        "discriminators": ad.discriminators,
                    }
                    for ad in f.adjectival_definitions
                ],
                "pws_traceability": f.pws_traceability,
                "l_instruction_ref": f.l_instruction_ref,
                "relative_importance": f.relative_importance,
                "suggested_weight": f.suggested_weight,
            }
            for f in result.factors
        ],
        "methodology": result.methodology.value,
        "protest_checks": [
            {
                "check_id": c.check_id,
                "check_name": c.check_name,
                "status": c.status.value,
                "detail": c.detail,
                "remediation": c.remediation,
                "far_authority": c.far_authority,
            }
            for c in result.protest_checks
        ],
        "overall_protest_score": result.overall_protest_score,
        "warnings": result.warnings,
        "source_provenance": result.source_provenance,
        "requires_acceptance": result.requires_acceptance,
    }
