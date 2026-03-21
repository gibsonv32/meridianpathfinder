"""
PIL Pricing Integration — Phase 2 Feature
==========================================
Integrates DHS Procurement Instrument Library (PIL) pricing data
for rate validation and contract type guidance.

The PIL provides pre-negotiated labor rates for common DHS service categories.
This engine cross-references IGCE rates against PIL benchmarks.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class RateStatus(str, Enum):
    WITHIN_RANGE = "within_range"
    BELOW_FLOOR = "below_floor"
    ABOVE_CEILING = "above_ceiling"
    NO_BENCHMARK = "no_benchmark"


@dataclass
class PILRate:
    """A single PIL benchmark rate."""
    labor_category: str
    sin: str  # Special Item Number (GSA schedule)
    min_rate: float
    max_rate: float
    avg_rate: float
    vehicle: str  # e.g., "PACTS-III", "EAGLE-II", "STARS-III"
    effective_date: str
    source: str


@dataclass
class RateComparison:
    """Comparison of a proposed rate against PIL benchmark."""
    labor_category: str
    proposed_rate: float
    pil_min: float
    pil_max: float
    pil_avg: float
    status: RateStatus
    variance_pct: float  # % above/below average
    vehicle: str
    recommendation: str


@dataclass
class PILAnalysis:
    """Complete PIL pricing analysis for an IGCE."""
    comparisons: list[RateComparison]
    rates_within_range: int
    rates_above_ceiling: int
    rates_below_floor: int
    rates_no_benchmark: int
    overall_assessment: str
    recommended_vehicle: str | None
    source_provenance: list[str] = field(default_factory=list)
    confidence_score: float = 0.82
    requires_acceptance: bool = True


# DHS PIL benchmark rates — representative data for common IT/cyber categories
# In production, these would come from a database table updated per PIL release
PIL_BENCHMARKS: list[PILRate] = [
    PILRate("Cybersecurity Analyst", "541512", 62.00, 95.00, 78.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Senior Cybersecurity Analyst", "541512", 85.00, 130.00, 107.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Network Operations Specialist", "541512", 52.00, 82.00, 67.00, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Senior Network Engineer", "541512", 78.00, 120.00, 99.00, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Systems Administrator", "541512", 48.00, 78.00, 63.00, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Senior Systems Administrator", "541512", 70.00, 108.00, 89.00, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Help Desk Specialist", "541512", 32.00, 55.00, 43.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Project Manager", "541611", 85.00, 145.00, 115.00, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Program Manager", "541611", 110.00, 185.00, 147.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Business Analyst", "541611", 55.00, 92.00, 73.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Cloud Engineer", "541512", 72.00, 115.00, 93.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("DevSecOps Engineer", "541512", 75.00, 120.00, 97.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Data Scientist", "541512", 80.00, 135.00, 107.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Software Developer", "541512", 65.00, 110.00, 87.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
    PILRate("Quality Assurance Analyst", "541512", 50.00, 85.00, 67.50, "PACTS-III", "2025-10-01", "DHS PIL FY2026 Release"),
]


def _normalize(name: str) -> str:
    """Normalize labor category name for fuzzy matching."""
    return name.lower().strip().replace("-", " ").replace("_", " ")


def _match_benchmark(labor_category: str) -> PILRate | None:
    """Find best matching PIL benchmark for a labor category."""
    norm = _normalize(labor_category)
    # Exact match first
    for rate in PIL_BENCHMARKS:
        if _normalize(rate.labor_category) == norm:
            return rate
    # Keyword match
    for rate in PIL_BENCHMARKS:
        rate_norm = _normalize(rate.labor_category)
        # Check if key terms overlap
        rate_words = set(rate_norm.split())
        input_words = set(norm.split())
        overlap = rate_words & input_words
        if len(overlap) >= 2 or (len(overlap) == 1 and list(overlap)[0] not in ("senior", "specialist", "analyst")):
            return rate
    return None


class PILPricingEngine:
    """
    Cross-references proposed labor rates against DHS PIL benchmarks.

    Usage:
        engine = PILPricingEngine()
        analysis = engine.analyze([
            {"title": "Cybersecurity Analyst", "proposed_rate": 75.00},
            {"title": "Network Operations Specialist", "proposed_rate": 90.00},
        ])
    """

    def analyze(self, labor_categories: list[dict]) -> PILAnalysis:
        """
        Analyze proposed rates against PIL benchmarks.

        Args:
            labor_categories: List of dicts with 'title' and 'proposed_rate' keys.
        """
        comparisons: list[RateComparison] = []
        provenance = ["DHS PIL FY2026 Release", "FAR 15.404-1(b) (Price Analysis)", "HSAM 3015.404"]

        for cat in labor_categories:
            title = cat.get("title", "Unknown")
            proposed = float(cat.get("proposed_rate", cat.get("hourly_rate", 0)))

            benchmark = _match_benchmark(title)
            if benchmark is None:
                comparisons.append(RateComparison(
                    labor_category=title,
                    proposed_rate=proposed,
                    pil_min=0, pil_max=0, pil_avg=0,
                    status=RateStatus.NO_BENCHMARK,
                    variance_pct=0,
                    vehicle="N/A",
                    recommendation=f"No PIL benchmark found for '{title}'. Use BLS/SAM.gov comparables for price analysis.",
                ))
                continue

            variance_pct = ((proposed - benchmark.avg_rate) / benchmark.avg_rate * 100) if benchmark.avg_rate > 0 else 0

            if proposed < benchmark.min_rate:
                status = RateStatus.BELOW_FLOOR
                rec = f"Proposed rate ${proposed:.2f}/hr is {abs(variance_pct):.0f}% below PIL average (${benchmark.avg_rate:.2f}). Risk of unrealistically low pricing — verify contractor can sustain quality."
            elif proposed > benchmark.max_rate:
                status = RateStatus.ABOVE_CEILING
                rec = f"Proposed rate ${proposed:.2f}/hr exceeds PIL ceiling (${benchmark.max_rate:.2f}). Requires justification or negotiation per FAR 15.404-1."
            else:
                status = RateStatus.WITHIN_RANGE
                rec = f"Rate ${proposed:.2f}/hr is within PIL range (${benchmark.min_rate:.2f}-${benchmark.max_rate:.2f}). Variance {variance_pct:+.0f}% from average."

            comparisons.append(RateComparison(
                labor_category=title,
                proposed_rate=proposed,
                pil_min=benchmark.min_rate,
                pil_max=benchmark.max_rate,
                pil_avg=benchmark.avg_rate,
                status=status,
                variance_pct=round(variance_pct, 1),
                vehicle=benchmark.vehicle,
                recommendation=rec,
            ))

        within = sum(1 for c in comparisons if c.status == RateStatus.WITHIN_RANGE)
        above = sum(1 for c in comparisons if c.status == RateStatus.ABOVE_CEILING)
        below = sum(1 for c in comparisons if c.status == RateStatus.BELOW_FLOOR)
        no_bench = sum(1 for c in comparisons if c.status == RateStatus.NO_BENCHMARK)

        vehicles = [c.vehicle for c in comparisons if c.vehicle != "N/A"]
        recommended_vehicle = max(set(vehicles), key=vehicles.count) if vehicles else None

        if above == 0 and below == 0 and no_bench == 0:
            assessment = "All proposed rates are within DHS PIL benchmarks. Pricing is defensible."
        elif above > 0:
            assessment = f"{above} rate(s) exceed PIL ceiling. Negotiate down or document justification per FAR 15.404-1."
        elif below > 0:
            assessment = f"{below} rate(s) below PIL floor. Evaluate price realism — risk of quality shortfall."
        else:
            assessment = f"{no_bench} category(ies) without PIL benchmarks. Supplement with BLS/SAM.gov data."

        return PILAnalysis(
            comparisons=comparisons,
            rates_within_range=within,
            rates_above_ceiling=above,
            rates_below_floor=below,
            rates_no_benchmark=no_bench,
            overall_assessment=assessment,
            recommended_vehicle=recommended_vehicle,
            source_provenance=provenance,
        )


pil_pricing_engine = PILPricingEngine()
