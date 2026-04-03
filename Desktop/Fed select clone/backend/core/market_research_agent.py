"""
Market Research Agent — Phase 23a
Local-first + live API architecture for FAR 10.002-compliant market research.

Primary: PostgreSQL queries against existing tables (27,686 awards, 1,451 protests,
45,635 SAM.gov opps) for historical analysis and benchmarking.
Secondary: Live USAspending/SAM.gov/GSA APIs for current market activity.

Output: Structured market research report with 6 sections per FAR 10.002(b).
Tier 2: AI synthesizes findings, proposes narrative; CO accepts/modifies/overrides.

Architecture:
- MarketResearchRequest: input contract (NAICS, PSC, agency, value, etc.)
- MarketResearchAgent: orchestrator that runs all 6 report sections
- Each section is a standalone function returning structured data
- Report assembly with source provenance per finding
- No database connection required — works with in-memory data stores or
  can be wired to asyncpg on the Spark DGX deployment

References:
- FedProcure_Phase23_Spec.docx, Section 3
- FAR 10.001 (Policy), FAR 10.002 (Procedures)
- FAR 12.101 (Commercial item determination)
- CLAUDE.md Phase 23a specification
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
import math


# ─── Input Contract ──────────────────────────────────────────────────────────

class SetAsideRecommendation(str, Enum):
    TOTAL_SMALL_BUSINESS = "total_small_business"
    PARTIAL_SMALL_BUSINESS = "partial_small_business"
    EIGHT_A = "8a"
    HUBZONE = "hubzone"
    SDVOSB = "sdvosb"
    WOSB = "wosb"
    FULL_AND_OPEN = "full_and_open"
    SOLE_SOURCE = "sole_source"


@dataclass
class MarketResearchRequest:
    """Input contract for the Market Research Agent."""
    naics_code: str                          # 6-digit NAICS (e.g. "541512")
    estimated_value: float                   # Dollar value
    agency: str = "DHS"                      # Parent agency
    sub_agency: str = "TSA"                  # Sub-agency
    psc_code: str | None = None              # Product/Service Code
    geographic_scope: str = "nationwide"      # nationwide, regional, local
    contract_type: str = "FFP"               # FFP, T&M, CPFF, IDIQ
    keywords: list[str] = field(default_factory=list)
    set_aside_preference: str | None = None  # Desired set-aside type
    services: bool = True                    # Services vs supplies
    it_related: bool = True                  # IT acquisition
    on_site: bool = False                    # On-site performance


# ─── Report Section Models ───────────────────────────────────────────────────

@dataclass
class ComparableAward:
    piid: str
    recipient: str
    value: float
    agency: str
    naics: str
    psc: str | None
    start_date: str | None
    competition_type: str | None
    set_aside: str | None
    relevance_score: float  # 0-1, how closely this matches the request


@dataclass
class ActiveOpportunity:
    notice_id: str
    title: str
    agency: str
    posted_date: str | None
    response_deadline: str | None
    set_aside: str | None
    naics: str | None
    estimated_value: float | None
    status: str


@dataclass
class SmallBusinessProfile:
    category: str  # 8(a), HUBZone, SDVOSB, WOSB, total SB
    count: int
    example_vendors: list[str]
    viable: bool
    reasoning: str


@dataclass
class PricingBenchmark:
    labor_category: str
    pil_min: float
    pil_max: float
    pil_avg: float
    source: str
    vehicle: str | None


@dataclass
class ProtestContext:
    overall_protest_rate: float
    value_bracket_rate: float
    agency_rate: float
    comparable_protests: list[dict]
    risk_factors: list[str]
    mitigations: list[str]


@dataclass
class MarketResearchSection:
    """A single section of the market research report."""
    section_number: int
    title: str
    far_authority: str
    content: dict[str, Any]
    findings: list[str]
    source_provenance: list[str]
    confidence: float  # 0-1


@dataclass
class MarketResearchReport:
    """FAR 10.002-compliant market research report."""
    request: MarketResearchRequest
    sections: list[MarketResearchSection]
    executive_summary: str
    recommendation: str
    set_aside_recommendation: SetAsideRecommendation
    overall_confidence: float
    generated_at: str
    requires_acceptance: bool = True
    warnings: list[str] = field(default_factory=list)


# ─── DHS PIL Benchmark Rates ────────────────────────────────────────────────
# Source: DHS PIL Pricing Playbook (15 labor categories)

PIL_RATES: dict[str, dict[str, float]] = {
    "Program Manager": {"min": 125.00, "max": 225.00, "avg": 175.00},
    "Project Manager": {"min": 110.00, "max": 200.00, "avg": 155.00},
    "Senior Systems Engineer": {"min": 130.00, "max": 220.00, "avg": 175.00},
    "Systems Engineer": {"min": 95.00, "max": 175.00, "avg": 135.00},
    "Senior Software Developer": {"min": 120.00, "max": 210.00, "avg": 165.00},
    "Software Developer": {"min": 85.00, "max": 165.00, "avg": 125.00},
    "Junior Software Developer": {"min": 65.00, "max": 120.00, "avg": 92.50},
    "Senior Cybersecurity Analyst": {"min": 125.00, "max": 215.00, "avg": 170.00},
    "Cybersecurity Analyst": {"min": 90.00, "max": 170.00, "avg": 130.00},
    "Database Administrator": {"min": 90.00, "max": 170.00, "avg": 130.00},
    "Network Engineer": {"min": 85.00, "max": 165.00, "avg": 125.00},
    "Help Desk Specialist": {"min": 45.00, "max": 85.00, "avg": 65.00},
    "Technical Writer": {"min": 60.00, "max": 110.00, "avg": 85.00},
    "Business Analyst": {"min": 80.00, "max": 155.00, "avg": 117.50},
    "Quality Assurance Analyst": {"min": 75.00, "max": 145.00, "avg": 110.00},
}


# ─── Empirical Protest Rates (from model v2, 27,686 DHS awards) ─────────────

PROTEST_RATES_BY_VALUE: dict[str, float] = {
    "under_sat": 0.11,
    "sat_to_5.5m": 0.31,
    "5.5m_to_50m": 1.28,
    "50m_to_100m": 7.30,
    "100m_plus": 5.81,
}

PROTEST_RATES_BY_AGENCY: dict[str, float] = {
    "TSA": 0.75, "CBP": 0.41, "ICE": 1.12, "FEMA": 0.26,
    "USCG": 0.16, "USCIS": 3.21, "USSS": 0.78, "FLETC": 0.54,
    "DHS_HQ": 0.79, "OPO": 0.79,
}


# ─── Section Generators ─────────────────────────────────────────────────────

def _value_bracket(value: float) -> str:
    if value < 350_000:
        return "under_sat"
    elif value < 5_500_000:
        return "sat_to_5.5m"
    elif value < 50_000_000:
        return "5.5m_to_50m"
    elif value < 100_000_000:
        return "50m_to_100m"
    else:
        return "100m_plus"


def generate_comparable_awards(
    req: MarketResearchRequest,
    award_store: list[dict] | None = None,
) -> MarketResearchSection:
    """Section 1: Comparable Awards Analysis.

    Local DB: awards by NAICS/PSC, price benchmarks, value distribution.
    """
    awards = award_store or []

    # Filter by NAICS (first 4 digits for broader match)
    naics_prefix = req.naics_code[:4] if req.naics_code else ""
    matching = []
    for a in awards:
        a_naics = (a.get("naics_code") or "")[:4]
        a_agency = (a.get("agency") or "").upper()
        a_sub = (a.get("sub_agency") or "").upper()

        relevance = 0.0
        if a_naics == naics_prefix:
            relevance += 0.4
        if req.sub_agency.upper() in a_sub or req.agency.upper() in a_agency:
            relevance += 0.3
        if req.psc_code and a.get("psc_code", "")[:2] == req.psc_code[:2]:
            relevance += 0.2
        # Value proximity (within 2x)
        a_val = a.get("total_obligation", 0)
        if a_val > 0 and 0.5 <= req.estimated_value / a_val <= 2.0:
            relevance += 0.1

        if relevance >= 0.3:
            matching.append(ComparableAward(
                piid=a.get("piid", ""),
                recipient=a.get("recipient_name", "Unknown"),
                value=a_val,
                agency=a.get("sub_agency") or a.get("agency", ""),
                naics=a.get("naics_code", ""),
                psc=a.get("psc_code"),
                start_date=a.get("start_date"),
                competition_type=a.get("competition_type"),
                set_aside=a.get("set_aside_type"),
                relevance_score=round(relevance, 2),
            ))

    # Sort by relevance, take top 20
    matching.sort(key=lambda x: x.relevance_score, reverse=True)
    top = matching[:20]

    # Price statistics
    values = [a.value for a in top if a.value > 0]
    stats = {}
    if values:
        stats = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "median": sorted(values)[len(values) // 2],
            "mean": sum(values) / len(values),
        }

    # Competition analysis
    comp_types = {}
    for a in top:
        ct = a.competition_type or "unknown"
        comp_types[ct] = comp_types.get(ct, 0) + 1

    findings = []
    if len(top) >= 5:
        findings.append(
            f"Found {len(matching)} comparable awards in NAICS {naics_prefix}xx, "
            f"top {len(top)} analyzed."
        )
    elif len(top) > 0:
        findings.append(
            f"Limited comparable awards ({len(top)}) in NAICS {naics_prefix}xx. "
            f"Consider broadening NAICS or PSC search."
        )
    else:
        findings.append(
            f"No comparable awards found for NAICS {naics_prefix}xx in local database. "
            f"Live USAspending API search recommended."
        )

    if stats:
        findings.append(
            f"Price range: ${stats['min']:,.0f} – ${stats['max']:,.0f} "
            f"(median ${stats['median']:,.0f})."
        )

    return MarketResearchSection(
        section_number=1,
        title="Comparable Awards Analysis",
        far_authority="FAR 10.002(b)(1)",
        content={
            "comparable_awards": [
                {"piid": a.piid, "recipient": a.recipient, "value": a.value,
                 "agency": a.agency, "naics": a.naics, "relevance": a.relevance_score}
                for a in top
            ],
            "price_statistics": stats,
            "competition_distribution": comp_types,
            "total_matches": len(matching),
        },
        findings=findings,
        source_provenance=[
            "USAspending award database (27,686 DHS awards)",
            f"NAICS {naics_prefix}xx filter",
        ],
        confidence=0.9 if len(top) >= 5 else 0.6 if len(top) > 0 else 0.3,
    )


def generate_active_market_scan(
    req: MarketResearchRequest,
    opportunity_store: list[dict] | None = None,
) -> MarketResearchSection:
    """Section 2: Active Market Scan.

    SAM.gov opportunities, expiring contracts, recompete candidates.
    """
    opps = opportunity_store or []

    matching = []
    for o in opps:
        o_naics = o.get("naics_code", "")
        if req.naics_code and o_naics[:4] == req.naics_code[:4]:
            matching.append(ActiveOpportunity(
                notice_id=o.get("notice_id", ""),
                title=o.get("title", ""),
                agency=o.get("agency", ""),
                posted_date=o.get("posted_date"),
                response_deadline=o.get("response_deadline"),
                set_aside=o.get("set_aside"),
                naics=o_naics,
                estimated_value=o.get("estimated_value"),
                status=o.get("status", "active"),
            ))

    findings = []
    if matching:
        findings.append(
            f"{len(matching)} active/recent opportunities found in NAICS {req.naics_code[:4]}xx."
        )
        set_asides = [o.set_aside for o in matching if o.set_aside]
        if set_asides:
            from collections import Counter
            sa_dist = Counter(set_asides)
            top_sa = sa_dist.most_common(3)
            findings.append(
                f"Set-aside distribution: {', '.join(f'{k} ({v})' for k, v in top_sa)}."
            )
    else:
        findings.append(
            "No active opportunities found in local SAM.gov data. "
            "Live SAM.gov API search recommended for current postings."
        )

    return MarketResearchSection(
        section_number=2,
        title="Active Market Scan",
        far_authority="FAR 10.002(b)(1)",
        content={
            "active_opportunities": [
                {"notice_id": o.notice_id, "title": o.title, "agency": o.agency,
                 "set_aside": o.set_aside, "naics": o.naics}
                for o in matching[:15]
            ],
            "total_found": len(matching),
        },
        findings=findings,
        source_provenance=[
            "SAM.gov opportunity database (45,635 opportunities)",
            f"NAICS {req.naics_code[:4]}xx filter",
        ],
        confidence=0.85 if matching else 0.4,
    )


def generate_small_business_availability(
    req: MarketResearchRequest,
    award_store: list[dict] | None = None,
) -> MarketResearchSection:
    """Section 3: Small Business Availability.

    Set-aside viability analysis based on historical awards.
    """
    awards = award_store or []
    naics_prefix = req.naics_code[:4] if req.naics_code else ""

    # Count SB set-asides in comparable awards
    sb_categories: dict[str, list[str]] = {
        "total_small_business": [],
        "8a": [],
        "hubzone": [],
        "sdvosb": [],
        "wosb": [],
        "full_and_open": [],
    }

    for a in awards:
        if (a.get("naics_code") or "")[:4] != naics_prefix:
            continue
        sa = (a.get("set_aside_type") or "").lower()
        recipient = a.get("recipient_name", "Unknown")
        if "8(a)" in sa or "8a" in sa:
            sb_categories["8a"].append(recipient)
        elif "hubzone" in sa:
            sb_categories["hubzone"].append(recipient)
        elif "sdvosb" in sa or "service-disabled" in sa:
            sb_categories["sdvosb"].append(recipient)
        elif "wosb" in sa or "women" in sa:
            sb_categories["wosb"].append(recipient)
        elif "small" in sa:
            sb_categories["total_small_business"].append(recipient)
        else:
            sb_categories["full_and_open"].append(recipient)

    # Build profiles
    profiles = []
    # Rule of two: need at least 2 capable SB firms for set-aside
    for cat, vendors in sb_categories.items():
        if cat == "full_and_open":
            continue
        unique_vendors = list(set(vendors))
        viable = len(unique_vendors) >= 2
        profiles.append(SmallBusinessProfile(
            category=cat,
            count=len(unique_vendors),
            example_vendors=unique_vendors[:5],
            viable=viable,
            reasoning=f"{'Rule of two met' if viable else 'Insufficient vendors'} "
                      f"— {len(unique_vendors)} unique {'firms' if len(unique_vendors) != 1 else 'firm'} "
                      f"found with prior DHS awards in NAICS {naics_prefix}xx.",
        ))

    # Recommendation
    viable_categories = [p for p in profiles if p.viable]
    set_aside_rec = SetAsideRecommendation.FULL_AND_OPEN
    if viable_categories:
        # Prefer total SB > 8(a) > SDVOSB > HUBZone > WOSB per DHS priority
        priority = ["total_small_business", "8a", "sdvosb", "hubzone", "wosb"]
        for cat in priority:
            match = [p for p in viable_categories if p.category == cat]
            if match:
                set_aside_rec = SetAsideRecommendation(cat)
                break

    findings = []
    if viable_categories:
        findings.append(
            f"Set-aside viable for: {', '.join(p.category for p in viable_categories)}."
        )
        findings.append(f"Recommended: {set_aside_rec.value}.")
    else:
        findings.append(
            "No socioeconomic categories meet rule-of-two threshold based on "
            "historical DHS awards. Full & open competition recommended."
        )
    findings.append(
        "SBA Dynamic Small Business Search should be consulted for current registrations."
    )

    return MarketResearchSection(
        section_number=3,
        title="Small Business Availability",
        far_authority="FAR 10.002(b)(2), FAR 19.502-2",
        content={
            "profiles": [
                {"category": p.category, "count": p.count, "viable": p.viable,
                 "example_vendors": p.example_vendors, "reasoning": p.reasoning}
                for p in profiles
            ],
            "set_aside_recommendation": set_aside_rec.value,
        },
        findings=findings,
        source_provenance=[
            "USAspending award database — SB set-aside analysis",
            "FAR 19.502-2 (rule of two)",
            "DHS Form 700-22 (Small Business Review)",
        ],
        confidence=0.8 if viable_categories else 0.5,
    )


def generate_commercial_assessment(
    req: MarketResearchRequest,
) -> MarketResearchSection:
    """Section 4: Commercial Availability Assessment.

    FAR Part 12 applicability, COTS/GOTS analysis.
    """
    # Commercial item indicators
    indicators = {
        "services_contract": req.services,
        "it_related": req.it_related,
        "value_under_sap": req.estimated_value < 9_000_000,  # Commercial SAP $9M
        "standardized_naics": req.naics_code[:2] in ("54", "51", "56"),  # Professional/IT/Admin
    }

    commercial_score = sum(1 for v in indicators.values() if v) / len(indicators)
    is_commercial = commercial_score >= 0.5

    findings = []
    if is_commercial:
        findings.append(
            "Acquisition may qualify as commercial item per FAR 12.101. "
            "Streamlined procedures per FAR Part 12 may apply."
        )
        if req.estimated_value < 9_000_000:
            findings.append(
                f"Value (${req.estimated_value:,.0f}) below Commercial SAP threshold ($9M). "
                "Simplified procedures available per FAR 13.5."
            )
    else:
        findings.append(
            "Acquisition does not clearly qualify as commercial item. "
            "Standard FAR Part 15 procedures recommended."
        )

    return MarketResearchSection(
        section_number=4,
        title="Commercial Availability Assessment",
        far_authority="FAR 10.002(b)(1), FAR 12.101",
        content={
            "commercial_indicators": indicators,
            "commercial_score": round(commercial_score, 2),
            "is_commercial": is_commercial,
            "far_part_12_applicable": is_commercial,
        },
        findings=findings,
        source_provenance=[
            "FAR 12.101 (commercial item definition)",
            "FAR 13.5 (simplified procedures for commercial items)",
        ],
        confidence=0.7,
    )


def generate_pricing_intelligence(
    req: MarketResearchRequest,
) -> MarketResearchSection:
    """Section 5: Pricing Intelligence.

    DHS PIL benchmark rates, labor category analysis, burdened rate ranges.
    """
    # Select relevant labor categories based on acquisition type
    relevant_categories = []
    if req.it_related:
        relevant_categories = [
            "Program Manager", "Senior Systems Engineer", "Systems Engineer",
            "Senior Software Developer", "Software Developer",
            "Senior Cybersecurity Analyst", "Cybersecurity Analyst",
            "Database Administrator", "Network Engineer",
            "Help Desk Specialist", "Quality Assurance Analyst",
        ]
    elif req.services:
        relevant_categories = [
            "Program Manager", "Project Manager", "Business Analyst",
            "Technical Writer", "Quality Assurance Analyst",
        ]
    else:
        relevant_categories = list(PIL_RATES.keys())[:5]

    benchmarks = []
    for cat in relevant_categories:
        if cat in PIL_RATES:
            rates = PIL_RATES[cat]
            benchmarks.append(PricingBenchmark(
                labor_category=cat,
                pil_min=rates["min"],
                pil_max=rates["max"],
                pil_avg=rates["avg"],
                source="DHS PIL Pricing Playbook",
                vehicle="DHS OASIS/EAGLE/PACTS",
            ))

    # Estimate FTE count and total labor cost
    avg_rate = sum(b.pil_avg for b in benchmarks) / len(benchmarks) if benchmarks else 150.0
    annual_hours = 1920  # Standard gov billable hours
    estimated_annual_cost = avg_rate * annual_hours
    estimated_fte = req.estimated_value / estimated_annual_cost if estimated_annual_cost > 0 else 0

    findings = [
        f"{len(benchmarks)} relevant DHS PIL benchmark rates identified.",
        f"Average burdened rate: ${avg_rate:,.2f}/hr.",
        f"Estimated FTE capacity at this value: {estimated_fte:.1f} FTEs "
        f"(at ${avg_rate:,.0f}/hr avg, {annual_hours} hrs/yr).",
    ]

    return MarketResearchSection(
        section_number=5,
        title="Pricing Intelligence",
        far_authority="FAR 10.002(b)(1), FAR 15.404-1",
        content={
            "benchmarks": [
                {"category": b.labor_category, "min": b.pil_min,
                 "max": b.pil_max, "avg": b.pil_avg, "source": b.source}
                for b in benchmarks
            ],
            "average_rate": round(avg_rate, 2),
            "estimated_fte": round(estimated_fte, 1),
            "annual_billable_hours": annual_hours,
        },
        findings=findings,
        source_provenance=[
            "DHS PIL Pricing Playbook (15 labor categories)",
            "DHS contract vehicle rate analysis (OASIS, EAGLE, PACTS)",
        ],
        confidence=0.85,
    )


def generate_protest_context(
    req: MarketResearchRequest,
    protest_store: list[dict] | None = None,
) -> MarketResearchSection:
    """Section 6: Protest Risk Context.

    Historical protest rates for similar acquisitions from protest model v2.
    """
    bracket = _value_bracket(req.estimated_value)
    value_rate = PROTEST_RATES_BY_VALUE.get(bracket, 0.5)
    agency_key = req.sub_agency.upper()
    agency_rate = PROTEST_RATES_BY_AGENCY.get(agency_key, 0.5)

    # Overall weighted rate
    overall_rate = (value_rate * 0.5 + agency_rate * 0.5)

    # Find comparable protests
    protests = protest_store or []
    naics_prefix = req.naics_code[:4] if req.naics_code else ""
    comparable = []
    for p in protests:
        p_agency = (p.get("sub_agency") or "").upper()
        p_naics = (p.get("naics_code") or "")[:4]
        if (agency_key in p_agency) or (naics_prefix and p_naics == naics_prefix):
            comparable.append({
                "case": p.get("file_number", p.get("b_number", "")),
                "company": p.get("company_name", ""),
                "outcome": p.get("outcome", ""),
                "value": p.get("estimated_value", 0),
            })

    risk_factors = []
    mitigations = []

    if req.estimated_value >= 50_000_000:
        risk_factors.append("High-value acquisition ($50M+) — 7.3% historical protest rate")
        mitigations.append("Consider SSAC per FAR 15.303(b)")
    if req.estimated_value >= 100_000_000:
        risk_factors.append("$100M+ acquisition — SSAC required")

    if agency_rate > 1.0:
        risk_factors.append(f"{req.sub_agency} has above-average protest rate ({agency_rate}%)")
        mitigations.append("Strengthen J-L-M traceability to reduce protest vulnerability")

    mitigations.append("Ensure all evaluation factors are disclosed in solicitation (FAR 15.304)")
    mitigations.append("Document price analysis methodology thoroughly (FAR 15.404-1)")

    findings = [
        f"Estimated protest probability: {overall_rate:.2f}% "
        f"(value bracket: {value_rate}%, agency: {agency_rate}%).",
        f"{len(comparable)} comparable protest cases found for {req.sub_agency}.",
    ]
    if comparable:
        sustained = sum(1 for c in comparable if "sustain" in (c.get("outcome") or "").lower())
        findings.append(
            f"Of comparable protests, {sustained} sustained "
            f"({sustained/len(comparable)*100:.0f}% sustain rate)."
        )

    return MarketResearchSection(
        section_number=6,
        title="Protest Risk Context",
        far_authority="FAR 33.104, 4 C.F.R. Part 21",
        content={
            "overall_protest_rate": round(overall_rate, 2),
            "value_bracket_rate": value_rate,
            "agency_rate": agency_rate,
            "comparable_protests": comparable[:10],
            "risk_factors": risk_factors,
            "mitigations": mitigations,
        },
        findings=findings,
        source_provenance=[
            "Protest model v2.0 (27,686 DHS awards, 162 protested)",
            "GAO.gov DHS protest database (1,451 records)",
            f"Empirical rates: value bracket {bracket} ({value_rate}%), "
            f"{req.sub_agency} ({agency_rate}%)",
        ],
        confidence=0.9,
    )


# ─── Report Assembly ─────────────────────────────────────────────────────────

class MarketResearchAgent:
    """Orchestrates all 6 report sections into a FAR 10.002-compliant report.

    Tier 2: generates report for CO review. CO accepts/modifies/overrides.
    """

    def generate_report(
        self,
        req: MarketResearchRequest,
        award_store: list[dict] | None = None,
        opportunity_store: list[dict] | None = None,
        protest_store: list[dict] | None = None,
    ) -> MarketResearchReport:
        """Generate complete FAR 10.002 market research report.

        Args:
            req: MarketResearchRequest with acquisition parameters
            award_store: List of award dicts (from contract_awards table)
            opportunity_store: List of opportunity dicts (from sam_gov_opportunities)
            protest_store: List of protest dicts (from gao_protests)

        Returns:
            MarketResearchReport with 6 sections, executive summary,
            and set-aside recommendation.
        """
        # Generate all 6 sections
        sections = [
            generate_comparable_awards(req, award_store),
            generate_active_market_scan(req, opportunity_store),
            generate_small_business_availability(req, award_store),
            generate_commercial_assessment(req),
            generate_pricing_intelligence(req),
            generate_protest_context(req, protest_store),
        ]

        # Determine set-aside recommendation from Section 3
        sb_section = sections[2]
        set_aside_rec_str = sb_section.content.get(
            "set_aside_recommendation", "full_and_open"
        )
        try:
            set_aside_rec = SetAsideRecommendation(set_aside_rec_str)
        except ValueError:
            set_aside_rec = SetAsideRecommendation.FULL_AND_OPEN

        # Overall confidence (weighted average)
        total_conf = sum(s.confidence for s in sections)
        overall_conf = total_conf / len(sections) if sections else 0.5

        # Executive summary
        findings_summary = []
        for s in sections:
            if s.findings:
                findings_summary.append(s.findings[0])

        exec_summary = (
            f"Market research conducted for {req.sub_agency} "
            f"${req.estimated_value:,.0f} acquisition (NAICS {req.naics_code}). "
            + " ".join(findings_summary[:3])
        )

        # Recommendation
        rec_parts = []
        if set_aside_rec != SetAsideRecommendation.FULL_AND_OPEN:
            rec_parts.append(f"Set-aside recommended: {set_aside_rec.value}.")
        else:
            rec_parts.append("Full and open competition recommended.")

        commercial = sections[3].content.get("is_commercial", False)
        if commercial:
            rec_parts.append("FAR Part 12 commercial procedures may apply.")

        pricing = sections[4]
        fte = pricing.content.get("estimated_fte", 0)
        if fte > 0:
            rec_parts.append(f"Estimated {fte:.0f} FTEs at benchmark rates.")

        recommendation = " ".join(rec_parts)

        # Warnings
        warnings = []
        for s in sections:
            if s.confidence < 0.5:
                warnings.append(
                    f"Section {s.section_number} ({s.title}): low confidence "
                    f"({s.confidence:.0%}). Additional research recommended."
                )

        return MarketResearchReport(
            request=req,
            sections=sections,
            executive_summary=exec_summary,
            recommendation=recommendation,
            set_aside_recommendation=set_aside_rec,
            overall_confidence=round(overall_conf, 2),
            generated_at=datetime.utcnow().isoformat(),
            warnings=warnings,
        )


def report_to_dict(report: MarketResearchReport) -> dict[str, Any]:
    """Serialize a MarketResearchReport to a JSON-friendly dict."""
    return {
        "request": {
            "naics_code": report.request.naics_code,
            "estimated_value": report.request.estimated_value,
            "agency": report.request.agency,
            "sub_agency": report.request.sub_agency,
            "psc_code": report.request.psc_code,
            "contract_type": report.request.contract_type,
            "services": report.request.services,
            "it_related": report.request.it_related,
        },
        "sections": [
            {
                "section_number": s.section_number,
                "title": s.title,
                "far_authority": s.far_authority,
                "content": s.content,
                "findings": s.findings,
                "source_provenance": s.source_provenance,
                "confidence": s.confidence,
            }
            for s in report.sections
        ],
        "executive_summary": report.executive_summary,
        "recommendation": report.recommendation,
        "set_aside_recommendation": report.set_aside_recommendation.value,
        "overall_confidence": report.overall_confidence,
        "generated_at": report.generated_at,
        "requires_acceptance": report.requires_acceptance,
        "warnings": report.warnings,
    }
