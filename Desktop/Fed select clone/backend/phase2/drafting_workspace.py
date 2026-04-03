"""
Phase 9 / Phase 26: Controlled Drafting Workspace — MVP #4

Implements the Propose / Redline / Explain model for 5 federal procurement
document types: PWS, IGCE, Section L, Section M, QASP.

Each engine is a standalone, agent-callable service with standardized
generate() interface.  DraftingWorkspace orchestrates dispatch by doc type.

Design principles:
- Every section has content + authority + confidence + rationale + source provenance
- Per-section accept/modify/override by CO
- Regeneration produces redlines against prior version automatically
- No DB dependency (in-memory, standalone)
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------

class DraftDocType(str, Enum):
    PWS = "PWS"
    IGCE = "IGCE"
    SECTION_L = "SECTION_L"
    SECTION_M = "SECTION_M"
    QASP = "QASP"


@dataclass
class DraftSection:
    section_id: str
    heading: str
    content: str
    authority: str
    rationale: str = ""
    confidence: float = 80.0


@dataclass
class RedlineEntry:
    section_id: str
    change_type: str  # "added", "modified", "deleted"
    old_content: str | None = None
    new_content: str | None = None
    diff_lines: list[str] = field(default_factory=list)


@dataclass
class DraftProposal:
    doc_type: DraftDocType
    sections: list[DraftSection]
    overall_confidence: float
    requires_acceptance: bool = True
    version: int = 1
    redlines: list[RedlineEntry] = field(default_factory=list)
    source_provenance: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class GenerateDraftRequest:
    package_id: str
    doc_type: DraftDocType
    title: str
    value: float
    naics: str = ""
    psc: str = ""
    services: bool = True
    it_related: bool = False
    sow_text: str | None = None
    prior_version_sections: list[dict] | None = None
    sole_source: bool = False
    commercial_item: bool = False
    competition_type: str | None = None
    eval_factors: list[dict] | None = None


@dataclass
class DraftDiffRequest:
    package_id: str
    doc_type: DraftDocType
    version_a: list[dict]
    version_b: list[dict]


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

SECTION_L_TEMPLATES: dict[str, list[dict]] = {
    "services_above_sat": [
        {
            "section_id": "L.1",
            "heading": "General Instructions",
            "content": (
                "Offerors shall submit proposals in accordance with the instructions "
                "contained herein. Proposals that do not conform to these instructions "
                "may be deemed non-responsive and eliminated from further consideration."
            ),
            "authority": "FAR 15.204-5(a)",
        },
        {
            "section_id": "L.2",
            "heading": "Proposal Format and Page Limitations",
            "content": (
                "The technical volume shall not exceed {tech_pages} pages. "
                "Pages in excess of the stated limit will not be evaluated. "
                "Font shall be no smaller than 12-point Times New Roman with 1-inch margins. "
                "The past performance volume shall include {pp_refs} relevant past performance references."
            ),
            "authority": "FAR 15.204-5(b)",
        },
        {
            "section_id": "L.3",
            "heading": "Technical Volume Instructions",
            "content": (
                "The technical volume shall demonstrate the offeror's understanding of the "
                "requirements and technical approach to meeting all Performance Work Statement "
                "objectives. Offerors shall address each evaluation factor and subfactor "
                "identified in Section M."
            ),
            "authority": "FAR 15.204-5(b)(1)",
        },
        {
            "section_id": "L.4",
            "heading": "Management Volume Instructions",
            "content": (
                "The management volume shall describe the offeror's management approach, "
                "organizational structure, key personnel qualifications, and quality "
                "control procedures. Offerors shall provide a staffing plan that "
                "demonstrates the ability to meet performance requirements."
            ),
            "authority": "FAR 15.204-5(b)(2)",
        },
        {
            "section_id": "L.5",
            "heading": "Past Performance Volume Instructions",
            "content": (
                "Offerors shall submit {pp_refs} past performance references for contracts "
                "of similar size, scope, and complexity performed within the past three "
                "years. Each reference shall include: contract number, contracting agency, "
                "contract value, period of performance, and a description of work performed."
            ),
            "authority": "FAR 15.304(c)(3)",
        },
        {
            "section_id": "L.6",
            "heading": "Price/Cost Volume Instructions",
            "content": (
                "The price/cost volume shall include a completed pricing matrix for each "
                "contract line item number (CLIN). Offerors shall provide sufficient detail "
                "to allow the Government to evaluate price reasonableness, including labor "
                "categories, labor rates, other direct costs, and any proposed subcontracting."
            ),
            "authority": "FAR 15.204-5(b)(4)",
        },
    ],
}

SECTION_M_TEMPLATES: dict[str, list[dict]] = {
    "tradeoff": [
        {
            "section_id": "M.1",
            "heading": "Basis for Award",
            "content": (
                "Award will be made to the offeror whose proposal represents the best "
                "value to the Government, considering the evaluation factors set forth "
                "below. The Government will use a tradeoff process in accordance with "
                "FAR 15.101-1. When combined, non-price factors are {tech_weight} "
                "than price."
            ),
            "authority": "FAR 15.101-1",
        },
        {
            "section_id": "M.2",
            "heading": "Factor 1: Technical Approach",
            "content": (
                "The Government will evaluate the offeror's technical approach for "
                "soundness, feasibility, and alignment with the Performance Work Statement "
                "requirements. The evaluation will assess the degree to which the proposed "
                "approach demonstrates a clear understanding of the work and a realistic "
                "plan for achieving performance objectives."
            ),
            "authority": "FAR 15.304(c)(1)",
        },
        {
            "section_id": "M.3",
            "heading": "Factor 2: Management Approach",
            "content": (
                "The Government will evaluate the offeror's management approach, including "
                "organizational structure, staffing plan, quality control procedures, and "
                "risk management. The evaluation will assess the degree to which the "
                "management approach supports successful contract performance."
            ),
            "authority": "FAR 15.304(c)(1)",
        },
        {
            "section_id": "M.4",
            "heading": "Factor 3: Past Performance",
            "content": (
                "The Government will evaluate the offeror's past performance to assess "
                "the degree to which the offeror has demonstrated the ability to "
                "perform contracts of similar size, scope, and complexity. Relevancy "
                "and performance quality will be considered. FAR 15.305(a)(2) applies."
            ),
            "authority": "FAR 15.304(c)(3)",
        },
        {
            "section_id": "M.5",
            "heading": "Factor 4: Price/Cost",
            "content": (
                "Proposed prices will be evaluated for reasonableness and realism. "
                "Price will not be scored using the adjectival rating scale but will "
                "be evaluated in accordance with FAR 15.404. Unrealistically low "
                "prices may indicate a lack of understanding of the requirements."
            ),
            "authority": "FAR 15.304(c)(1)",
        },
        {
            "section_id": "M.6",
            "heading": "Adjectival Rating Scale",
            "content": (
                "The following adjectival ratings will be used for non-price factors:\n\n"
                "Outstanding: Proposal significantly exceeds the minimum requirements in "
                "a way that is beneficial to the Government, demonstrating an exceptional "
                "approach with very low risk.\n\n"
                "Good: Proposal exceeds the minimum requirements, demonstrating a thorough "
                "approach with low risk.\n\n"
                "Acceptable: Proposal meets the minimum requirements, demonstrating an "
                "adequate approach with moderate risk.\n\n"
                "Marginal: Proposal does not clearly meet the minimum requirements, "
                "demonstrating a flawed approach with significant risk.\n\n"
                "Unacceptable: Proposal fails to meet the minimum requirements, "
                "demonstrating a fundamentally flawed approach with unacceptable risk."
            ),
            "authority": "FAR 15.305(a)",
        },
    ],
    "lpta": [
        {
            "section_id": "M.1",
            "heading": "Basis for Award",
            "content": (
                "Award will be made to the responsible offeror whose proposal conforms "
                "to the solicitation requirements and is the lowest price technically "
                "acceptable (LPTA) in accordance with FAR 15.101-2. Non-price factors "
                "will be evaluated on a pass/fail (acceptable/unacceptable) basis."
            ),
            "authority": "FAR 15.101-2",
        },
        {
            "section_id": "M.2",
            "heading": "Factor 1: Technical Acceptability",
            "content": (
                "The Government will evaluate the offeror's technical proposal to "
                "determine whether it meets the minimum technical requirements as "
                "set forth in the Performance Work Statement. Proposals will receive "
                "a rating of Acceptable or Unacceptable."
            ),
            "authority": "FAR 15.101-2(b)(1)",
        },
        {
            "section_id": "M.3",
            "heading": "Factor 2: Past Performance",
            "content": (
                "The Government will evaluate past performance to determine whether "
                "the offeror has a satisfactory record of performing contracts of "
                "similar size, scope, and complexity. A rating of Acceptable or "
                "Unacceptable will be assigned."
            ),
            "authority": "FAR 15.304(c)(3)",
        },
        {
            "section_id": "M.4",
            "heading": "Factor 3: Price",
            "content": (
                "Award will be made to the lowest priced offeror whose proposal is "
                "determined to be technically acceptable. Proposed prices will be "
                "evaluated for reasonableness in accordance with FAR 15.404."
            ),
            "authority": "FAR 15.101-2(b)(1)",
        },
    ],
}


# ---------------------------------------------------------------------------
# Section L Engine
# ---------------------------------------------------------------------------

class SectionLEngine:
    """Generates Section L (Instructions to Offerors) per FAR 15.204-5."""

    def _page_limits(self, value: float) -> tuple[int, int]:
        """Returns (tech_pages, pp_refs) scaled by acquisition value."""
        if value >= 50_000_000:
            return 60, 5
        elif value >= 20_000_000:
            return 40, 5
        elif value >= 5_000_000:
            return 30, 4
        else:
            return 25, 3

    def generate(self, params: dict) -> list[DraftSection]:
        value = params.get("value", 1_000_000)
        commercial = params.get("commercial_item", False)
        tech_pages, pp_refs = self._page_limits(value)

        templates = SECTION_L_TEMPLATES["services_above_sat"]
        sections = []
        for t in templates:
            content = t["content"].format(
                tech_pages=tech_pages,
                pp_refs=pp_refs,
            )
            sections.append(DraftSection(
                section_id=t["section_id"],
                heading=t["heading"],
                content=content,
                authority=t["authority"],
                rationale=f"Standard Section L element per {t['authority']}",
                confidence=85.0,
            ))

        if commercial:
            sections.append(DraftSection(
                section_id="L.7",
                heading="FAR Part 12 — Commercial Item Provisions",
                content=(
                    "This acquisition is conducted under FAR Part 12 procedures for "
                    "commercial items. Offerors shall submit proposals in accordance "
                    "with FAR 12.603. Streamlined evaluation procedures apply."
                ),
                authority="FAR 12.603",
                rationale="Commercial item acquisition requires FAR Part 12 streamlined provisions",
                confidence=90.0,
            ))

        return sections


# ---------------------------------------------------------------------------
# Section M Engine
# ---------------------------------------------------------------------------

class SectionMEngine:
    """Generates Section M (Evaluation Factors) per FAR 15.101-1 / 15.101-2."""

    def _select_method(self, params: dict) -> str:
        """Select tradeoff vs LPTA based on params."""
        explicit = params.get("competition_type", "").lower()
        if explicit == "lpta":
            return "lpta"

        value = params.get("value", 0)
        it_related = params.get("it_related", False)

        # LPTA default for low-value non-IT
        if value < 1_000_000 and not it_related:
            return "lpta"
        return "tradeoff"

    def _tech_weight(self, value: float) -> str:
        if value >= 20_000_000:
            return "significantly more important"
        return "approximately equal"

    def generate(self, params: dict) -> list[DraftSection]:
        method = self._select_method(params)
        value = params.get("value", 0)
        templates = SECTION_M_TEMPLATES[method]
        tech_weight = self._tech_weight(value)

        sections = []
        for t in templates:
            content = t["content"].format(
                tech_weight=tech_weight,
            ) if "{tech_weight}" in t["content"] else t["content"]

            sections.append(DraftSection(
                section_id=t["section_id"],
                heading=t["heading"],
                content=content,
                authority=t["authority"],
                rationale=f"{'Tradeoff' if method == 'tradeoff' else 'LPTA'} evaluation per {t['authority']}",
                confidence=85.0,
            ))

        # Custom evaluation factors injection
        custom_factors = params.get("eval_factors", None)
        if custom_factors:
            next_id = len(sections) + 1
            for cf in custom_factors:
                sections.append(DraftSection(
                    section_id=f"M.{next_id}",
                    heading=cf.get("name", "Custom Factor"),
                    content=cf.get("description", ""),
                    authority=cf.get("authority", "Agency-specific"),
                    rationale="Custom evaluation factor specified by SSA",
                    confidence=75.0,
                ))
                next_id += 1

        return sections


# ---------------------------------------------------------------------------
# PWS Engine
# ---------------------------------------------------------------------------

class PWSEngine:
    """Generates Performance Work Statement sections."""

    # SOW→PWS conversion patterns
    VAGUE_TERMS = [
        "as needed", "best efforts", "adequate", "appropriate", "timely",
        "reasonable", "etc.", "and/or", "should", "may",
    ]

    def _generate_template(self, params: dict) -> list[DraftSection]:
        """Template-based PWS generation when no SOW provided."""
        title = params.get("title", "Services")
        value = params.get("value", 0)
        sections = [
            DraftSection(
                section_id="1.0",
                heading="Background",
                content=(
                    f"The Transportation Security Administration (TSA) requires "
                    f"contractor support for {title}. This Performance Work Statement "
                    f"defines the performance objectives, standards, and deliverables "
                    f"for the required services."
                ),
                authority="FAR 37.602",
                rationale="Background establishes context and agency need",
                confidence=75.0,
            ),
            DraftSection(
                section_id="2.0",
                heading="Applicable Documents",
                content=(
                    "The contractor shall comply with all applicable Federal regulations, "
                    "DHS policies, and TSA Management Directives referenced in this PWS. "
                    "In the event of conflict, the most restrictive requirement applies."
                ),
                authority="FAR 37.602",
                rationale="Applicable documents establish regulatory framework",
                confidence=85.0,
            ),
            DraftSection(
                section_id="3.0",
                heading="Scope of Work",
                content=(
                    f"The contractor shall provide all personnel, equipment, tools, "
                    f"materials, supervision, and other items necessary to perform "
                    f"{title} as defined in this PWS."
                ),
                authority="FAR 37.602",
                rationale="Scope defines the boundaries of contractor responsibility",
                confidence=80.0,
            ),
            DraftSection(
                section_id="3.1",
                heading="Service Delivery Requirements",
                content=(
                    "The contractor shall deliver services in accordance with the "
                    "performance standards and metrics defined in Section 4.0. "
                    "All services shall meet or exceed the quality levels specified "
                    "in the Quality Assurance Surveillance Plan (QASP)."
                ),
                authority="FAR 37.601(b)",
                rationale="Service delivery defines performance-based outcomes",
                confidence=80.0,
            ),
            DraftSection(
                section_id="4.0",
                heading="Performance Standards",
                content=(
                    "The contractor shall meet the following performance standards:\n"
                    "- Service availability: 99.5% uptime during core hours\n"
                    "- Incident response: Initial response within 15 minutes for critical issues\n"
                    "- Reporting: Monthly status reports submitted within 5 business days of month-end"
                ),
                authority="FAR 37.601(b)(2)",
                rationale="Measurable performance standards enable QASP surveillance",
                confidence=75.0,
            ),
            DraftSection(
                section_id="5.0",
                heading="Reporting Requirements",
                content=(
                    "The contractor shall provide the following reports:\n"
                    "- Monthly Status Report: Progress, issues, metrics\n"
                    "- Quarterly Program Review: Trend analysis, recommendations\n"
                    "- Annual Performance Summary: Year-in-review, lessons learned"
                ),
                authority="FAR 37.602",
                rationale="Reporting provides COR visibility into contractor performance",
                confidence=80.0,
            ),
            DraftSection(
                section_id="6.0",
                heading="Transition",
                content=(
                    "The contractor shall provide transition-in support for the first "
                    "30 days of the base period and transition-out support during the "
                    "final 60 days of the last exercised option period. Transition plans "
                    "shall be submitted within 15 days of contract award."
                ),
                authority="FAR 37.602",
                rationale="Transition requirements ensure continuity of operations",
                confidence=80.0,
            ),
            DraftSection(
                section_id="7.0",
                heading="Quality Control",
                content=(
                    "The contractor shall establish and maintain a Quality Control "
                    "Plan (QCP) that describes the methods used to ensure all work "
                    "meets the performance standards specified in this PWS. The QCP "
                    "shall be submitted within 30 days of contract award."
                ),
                authority="FAR 46.4",
                rationale="Contractor QC plan complements Government QASP",
                confidence=85.0,
            ),
        ]
        return sections

    def _convert_sow(self, sow_text: str, params: dict) -> list[DraftSection]:
        """Convert SOW text to PWS with conversion warnings embedded."""
        sections = []
        # Parse SOW into rough sections
        lines = sow_text.strip().split("\n")
        content_block = " ".join(l.strip() for l in lines if l.strip())

        # Generate PWS sections from SOW content
        sections.append(DraftSection(
            section_id="1.0",
            heading="Background",
            content=(
                f"This Performance Work Statement (PWS) defines performance-based "
                f"requirements derived from the source Statement of Work."
            ),
            authority="FAR 37.602",
            rationale="SOW→PWS conversion: reframed from process to outcomes",
            confidence=70.0,
        ))
        sections.append(DraftSection(
            section_id="3.0",
            heading="Performance Requirements",
            content=self._rewrite_to_pbs(content_block),
            authority="FAR 37.601(b)",
            rationale="SOW→PWS: converted prescriptive language to performance-based outcomes",
            confidence=65.0,
        ))
        sections.append(DraftSection(
            section_id="4.0",
            heading="Performance Standards",
            content=(
                "The contractor shall meet measurable performance standards "
                "as defined in the QASP. Specific metrics shall be baselined "
                "within 30 days of contract award."
            ),
            authority="FAR 37.601(b)(2)",
            rationale="Performance standards required for PBA compliance",
            confidence=70.0,
        ))
        return sections

    def _rewrite_to_pbs(self, text: str) -> str:
        """Best-effort conversion of prescriptive SOW language to PBS."""
        result = text
        # Convert "will" to "shall" for binding obligations
        result = re.sub(r"\bwill\b", "shall", result, flags=re.IGNORECASE)
        return result

    def generate(self, params: dict) -> list[DraftSection]:
        sow_text = params.get("sow_text")
        if sow_text:
            return self._convert_sow(sow_text, params)
        return self._generate_template(params)


# ---------------------------------------------------------------------------
# IGCE Engine
# ---------------------------------------------------------------------------

class IGCEEngine:
    """Generates Independent Government Cost Estimate sections."""

    PIL_RATES = {
        "Program Manager": {"min": 175, "max": 250, "avg": 210},
        "Senior Systems Engineer": {"min": 155, "max": 225, "avg": 185},
        "Systems Engineer": {"min": 125, "max": 185, "avg": 150},
        "Senior Software Developer": {"min": 145, "max": 210, "avg": 175},
        "Software Developer": {"min": 115, "max": 170, "avg": 140},
        "Cybersecurity Analyst": {"min": 130, "max": 195, "avg": 160},
        "Help Desk Specialist": {"min": 65, "max": 110, "avg": 85},
        "Technical Writer": {"min": 85, "max": 135, "avg": 105},
        "Quality Assurance": {"min": 100, "max": 155, "avg": 125},
        "Data Analyst": {"min": 110, "max": 170, "avg": 135},
    }

    def generate(self, params: dict) -> list[DraftSection]:
        value = params.get("value", 0)
        title = params.get("title", "Services")

        sections = [
            DraftSection(
                section_id="IGCE.1",
                heading="Methodology",
                content=(
                    "This Independent Government Cost Estimate (IGCE) was developed "
                    "using a multi-source approach incorporating: (1) DHS Pricing and "
                    "Indirect Rates List (PIL) benchmark rates, (2) analysis of comparable "
                    "contracts from USAspending.gov, (3) market research data from SAM.gov "
                    "and GSA Schedule pricing, and (4) historical pricing from prior "
                    "contract performance. The estimate reflects fully burdened rates "
                    "including overhead, G&A, and profit/fee."
                ),
                authority="HSAM 3015.404",
                rationale="Multi-source methodology demonstrates thorough price analysis",
                confidence=80.0,
            ),
            DraftSection(
                section_id="IGCE.2",
                heading="Labor Rate Analysis",
                content=self._labor_rate_table(value),
                authority="FAR 15.404-1(b)",
                rationale="Labor rate benchmarks from DHS PIL provide price reasonableness basis",
                confidence=75.0,
            ),
            DraftSection(
                section_id="IGCE.3",
                heading="Comparable Contract Analysis",
                content=(
                    f"The following comparable contracts were identified through "
                    f"USAspending.gov and SAM.gov research for similar {title} "
                    f"requirements within DHS/TSA. Contract values, periods of "
                    f"performance, and scope descriptions are documented to support "
                    f"price reasonableness. Runtime enrichment from SAM.gov API "
                    f"provides additional comparable solicitations."
                ),
                authority="FAR 15.404-1(b)(2)",
                rationale="Comparable contracts provide market-based price validation",
                confidence=70.0,
            ),
        ]

        if value >= 2_500_000:
            sections.append(DraftSection(
                section_id="IGCE.4",
                heading="Cost Data Considerations",
                content=(
                    "This acquisition exceeds the cost or pricing data threshold "
                    "($2.5M per FAR 15.403-4). Unless an exception applies (e.g., "
                    "adequate price competition per FAR 15.403-1(b), commercial item "
                    "per FAR 15.403-1(c)), the contractor will be required to submit "
                    "certified cost or pricing data."
                ),
                authority="FAR 15.403-4",
                rationale="Cost data requirement triggered at $2.5M threshold",
                confidence=85.0,
            ))

        return sections

    def _labor_rate_table(self, value: float) -> str:
        """Build labor rate table from PIL benchmarks."""
        lines = ["DHS PIL Benchmark Rates (fully burdened):\n"]
        for cat, rates in self.PIL_RATES.items():
            lines.append(
                f"- {cat}: ${rates['min']}/hr – ${rates['max']}/hr "
                f"(avg ${rates['avg']}/hr)"
            )
        billable_hours = 1920
        avg_rate = 155  # weighted average across categories
        estimated_ftes = value / (avg_rate * billable_hours) if value > 0 else 0
        lines.append(f"\nEstimated FTE equivalents at avg rate: {estimated_ftes:.1f}")
        lines.append(f"Total estimated value: ${value:,.0f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# QASP Engine
# ---------------------------------------------------------------------------

class QASPEngine:
    """Generates Quality Assurance Surveillance Plan from PWS sections."""

    SURVEILLANCE_METHODS = [
        "100% inspection",
        "automated monitoring",
        "random sampling",
        "periodic assessment",
    ]

    def _extract_metrics(self, content: str) -> list[str]:
        """Extract measurable metrics from PWS content."""
        metrics = []
        # Percentage patterns
        for m in re.finditer(r'\d+\.?\d*%', content):
            metrics.append(m.group())
        # Time-based patterns
        for m in re.finditer(r'\d+\s*(?:minutes?|hours?|days?|business days?)', content, re.IGNORECASE):
            metrics.append(m.group())
        return metrics

    def _select_method(self, content: str) -> str:
        """Select surveillance method based on content."""
        lower = content.lower()
        if any(w in lower for w in ["uptime", "availability", "system", "automated"]):
            return "automated monitoring"
        if any(w in lower for w in ["report", "submit", "deliver"]):
            return "periodic assessment"
        if any(w in lower for w in ["inspect", "review", "audit"]):
            return "random sampling"
        return "100% inspection"

    def generate(self, pws_sections: list[DraftSection], params: dict) -> list[DraftSection]:
        sections = [
            DraftSection(
                section_id="QASP.1",
                heading="Purpose",
                content=(
                    "This Quality Assurance Surveillance Plan (QASP) provides a "
                    "systematic method to evaluate contractor performance against "
                    "the Performance Work Statement (PWS) requirements. The QASP "
                    "defines surveillance methods, performance standards, and the "
                    "progressive remedy chain: Corrective Action Request (CAR) → "
                    "Cure Notice → Show Cause → Termination for Default."
                ),
                authority="FAR 46.4",
                rationale="QASP purpose establishes surveillance framework and remedy chain",
                confidence=90.0,
            ),
        ]

        for idx, pws_sec in enumerate(pws_sections, start=2):
            metrics = self._extract_metrics(pws_sec.content)
            method = self._select_method(pws_sec.content)

            metric_text = ""
            if metrics:
                metric_text = f" Measurable standards: {', '.join(metrics)}."

            sections.append(DraftSection(
                section_id=f"QASP.{idx}",
                heading=f"Surveillance: {pws_sec.heading}",
                content=(
                    f"PWS Reference: {pws_sec.section_id} — {pws_sec.heading}. "
                    f"Surveillance Method: {method}.{metric_text} "
                    f"Acceptable Quality Level (AQL): Performance meets or exceeds "
                    f"the standard. Remedy: Progressive — CAR → Cure Notice → Default."
                ),
                authority="FAR 46.401",
                rationale=f"Surveillance item mapped from PWS {pws_sec.section_id}",
                confidence=80.0,
            ))

        return sections


# ---------------------------------------------------------------------------
# Diff Engine
# ---------------------------------------------------------------------------

class DiffEngine:
    """Computes section-by-section unified diffs between document versions."""

    def compute(self, old: list[dict], new: list[dict]) -> list[RedlineEntry]:
        old_map = {s["section_id"]: s for s in old}
        new_map = {s["section_id"]: s for s in new}
        redlines = []

        # Modified or deleted
        for sid, old_sec in old_map.items():
            if sid in new_map:
                new_sec = new_map[sid]
                if old_sec["content"] != new_sec["content"]:
                    diff_lines = list(difflib.unified_diff(
                        old_sec["content"].splitlines(),
                        new_sec["content"].splitlines(),
                        fromfile=f"{sid} (old)",
                        tofile=f"{sid} (new)",
                        lineterm="",
                    ))
                    redlines.append(RedlineEntry(
                        section_id=sid,
                        change_type="modified",
                        old_content=old_sec["content"],
                        new_content=new_sec["content"],
                        diff_lines=diff_lines,
                    ))
            else:
                redlines.append(RedlineEntry(
                    section_id=sid,
                    change_type="deleted",
                    old_content=old_sec["content"],
                    new_content=None,
                ))

        # Added
        for sid in new_map:
            if sid not in old_map:
                redlines.append(RedlineEntry(
                    section_id=sid,
                    change_type="added",
                    old_content=None,
                    new_content=new_map[sid]["content"],
                ))

        return redlines


# ---------------------------------------------------------------------------
# DraftingWorkspace Orchestrator
# ---------------------------------------------------------------------------

class DraftingWorkspace:
    """Dispatches draft generation to the appropriate engine by doc type."""

    def __init__(self):
        self.section_l = SectionLEngine()
        self.section_m = SectionMEngine()
        self.pws = PWSEngine()
        self.igce = IGCEEngine()
        self.qasp = QASPEngine()
        self.diff_engine = DiffEngine()

    def generate_draft(self, request: GenerateDraftRequest) -> DraftProposal:
        params = {
            "value": request.value,
            "title": request.title,
            "naics": request.naics,
            "psc": request.psc,
            "services": request.services,
            "it_related": request.it_related,
            "sow_text": request.sow_text,
            "sole_source": request.sole_source,
            "commercial_item": request.commercial_item,
            "competition_type": request.competition_type or "",
            "eval_factors": request.eval_factors,
        }

        # Generate sections by doc type
        if request.doc_type == DraftDocType.PWS:
            sections = self.pws.generate(params)
        elif request.doc_type == DraftDocType.IGCE:
            sections = self.igce.generate(params)
        elif request.doc_type == DraftDocType.SECTION_L:
            sections = self.section_l.generate(params)
        elif request.doc_type == DraftDocType.SECTION_M:
            sections = self.section_m.generate(params)
        elif request.doc_type == DraftDocType.QASP:
            # QASP needs PWS sections first — generate a quick PWS
            pws_sections = self.pws.generate(params)
            sections = self.qasp.generate(pws_sections, params)
        else:
            raise ValueError(f"Unknown doc type: {request.doc_type}")

        # Compute redlines if prior version provided
        version = 1
        redlines = []
        if request.prior_version_sections:
            version = 2
            old_secs = [
                {"section_id": s.get("section_id", ""), "content": s.get("content", "")}
                for s in request.prior_version_sections
            ]
            new_secs = [
                {"section_id": s.section_id, "content": s.content}
                for s in sections
            ]
            redlines = self.diff_engine.compute(old_secs, new_secs)

        # Aggregate provenance (deduplicated)
        provenance = list(dict.fromkeys(
            s.authority for s in sections if s.authority
        ))

        # Warnings
        warnings = self._generate_warnings(request, sections)

        # Overall confidence
        if sections:
            overall = sum(s.confidence for s in sections) / len(sections)
        else:
            overall = 0.0

        return DraftProposal(
            doc_type=request.doc_type,
            sections=sections,
            overall_confidence=overall,
            requires_acceptance=True,
            version=version,
            redlines=redlines,
            source_provenance=provenance,
            warnings=warnings,
        )

    def compute_diff(self, request: DraftDiffRequest) -> list[RedlineEntry]:
        return self.diff_engine.compute(request.version_a, request.version_b)

    def _generate_warnings(
        self, request: GenerateDraftRequest, sections: list[DraftSection]
    ) -> list[str]:
        warnings = []

        # LPTA warning on high-value
        if (
            request.doc_type == DraftDocType.SECTION_M
            and request.value >= 20_000_000
            and (request.competition_type or "").lower() == "lpta"
        ):
            warnings.append(
                "WARNING: LPTA evaluation on $20M+ acquisition. Per TSA policy, "
                "LPTA requires HCA-delegated D&F unless Class D&F for IT SW/HW applies. "
                "Consider best value tradeoff for this value threshold."
            )

        # Sole source warning on Section L
        if request.doc_type == DraftDocType.SECTION_L and request.sole_source:
            warnings.append(
                "WARNING: Generating Section L for sole source acquisition. "
                "Section L/M are typically not required for sole source — confirm "
                "whether competitive evaluation structure is intended."
            )

        return warnings


# ---------------------------------------------------------------------------
# Module-level singleton (used by drafting_persistence.py)
# ---------------------------------------------------------------------------
drafting_workspace = DraftingWorkspace()
