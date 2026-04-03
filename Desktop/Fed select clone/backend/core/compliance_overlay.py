"""
Compliance Overlay Engine (Pattern 3)
Per-section compliance checking against FAR, HSAR, and TSA directives.

Evaluates each drafted document section against applicable regulations,
producing a Green/Yellow/Red/Black grid that catches problems before
legal review rather than after.

Architecture:
- 20 concrete compliance rules for $20M TSA IT services (extensible)
- Rules stored as Python dicts with effective dates (policy-as-code)
- Each rule returns COMPLIANT (100), MINOR (70), MAJOR (30), or MISSING (0)
- Per-document compliance grids aggregate to overall compliance score
- Integration with Multi-Axis Scoring (Pattern 1) via compliance axis

Tier 2: AI-assisted evaluation — CO reviews and accepts/overrides findings.

References:
- FedProcure_Phase24_26_Spec.md, Pattern 3
- FAR 37.102 (PBA), FAR 15.204-5 (Section L), FAR 15.101-1 (Tradeoff)
- HSAM 3037.1, HSAR 3052.204-71, TSA MD 300.25
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any
import re


# ─── Compliance Levels ───────────────────────────────────────────────────────

class ComplianceLevel(str, Enum):
    COMPLIANT = "GREEN"     # 100 points — fully meets requirement
    MINOR = "YELLOW"        # 70 points — minor gap, easily remediated
    MAJOR = "RED"           # 30 points — significant deficiency
    MISSING = "BLACK"       # 0 points — not addressed at all
    NOT_APPLICABLE = "N/A"  # Rule doesn't apply to this acquisition


COMPLIANCE_SCORES = {
    ComplianceLevel.COMPLIANT: 100,
    ComplianceLevel.MINOR: 70,
    ComplianceLevel.MAJOR: 30,
    ComplianceLevel.MISSING: 0,
}


# ─── Rule Definition ─────────────────────────────────────────────────────────

@dataclass
class ComplianceRule:
    """A single compliance check against a specific regulation."""
    rule_id: str                         # e.g. "CR-PWS-01"
    regulation: str                      # e.g. "FAR 37.102"
    title: str                           # Human-readable
    applicable_to: list[str]             # Document types: PWS, Section_L, Section_M, QASP, IGCE
    check_description: str               # What the rule checks
    remediation: str                     # How to fix a violation
    severity_if_violated: ComplianceLevel  # Default severity
    source_weight: str = "FAR"           # FAR (40%), HSAR (35%), TSA (25%)
    effective_date: date = field(default_factory=lambda: date(2025, 10, 1))
    expiration_date: date | None = None
    # Applicability conditions (if None, always applicable)
    min_value: float | None = None       # Only applies above this value
    requires_services: bool | None = None
    requires_it: bool | None = None


@dataclass
class ComplianceCheckResult:
    """Result of checking one rule against one document section."""
    rule_id: str
    regulation: str
    title: str
    level: ComplianceLevel
    score: int
    detail: str
    remediation: str
    section_ref: str  # Which section of the document was checked


@dataclass
class DocumentComplianceGrid:
    """Compliance results for one document type."""
    document_type: str
    checks: list[ComplianceCheckResult]
    overall_score: float
    blocking_issues: list[ComplianceCheckResult]
    summary: str


@dataclass
class ComplianceOverlayResponse:
    """Full compliance overlay across all documents."""
    grids: list[DocumentComplianceGrid]
    overall_compliance_score: float
    total_rules_checked: int
    compliant_count: int
    minor_count: int
    major_count: int
    missing_count: int
    blocking_sections: list[str]
    recommended_fix_order: list[str]
    source_provenance: list[str]
    requires_acceptance: bool = True


# ─── The 20 Compliance Rules ────────────────────────────────────────────────

COMPLIANCE_RULES: list[ComplianceRule] = [
    # ── PWS Rules (5) ──
    ComplianceRule(
        rule_id="CR-PWS-01",
        regulation="FAR 37.102",
        title="Performance-Based Language",
        applicable_to=["PWS"],
        check_description="PWS uses outcome-based language rather than prescriptive/input-based. "
                          "Checks for prescriptive indicators: staffing specs, hours, methods.",
        remediation="Convert prescriptive statements to outcome-based requirements with "
                    "measurable performance standards.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
        requires_services=True,
    ),
    ComplianceRule(
        rule_id="CR-PWS-02",
        regulation="HSAM 3037.1",
        title="Measurable Metrics",
        applicable_to=["PWS"],
        check_description="PWS sections contain quantifiable metrics (SLAs, response times, "
                          "percentages) rather than vague terms.",
        remediation="Add specific SLA targets, response time requirements, and measurable "
                    "acceptance criteria to each service area.",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="HSAR",
        requires_services=True,
    ),
    ComplianceRule(
        rule_id="CR-PWS-03",
        regulation="TSA MD 300.25",
        title="Acquisition Plan Reference",
        applicable_to=["PWS"],
        check_description="PWS references approved Acquisition Plan for acquisitions >= $5.5M "
                          "(OTFFP) or cites FFP exemption per HSAM 3007.103(e).",
        remediation="Add AP reference or cite FFP exemption from written AP requirement.",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="TSA",
        min_value=5_500_000,
    ),
    ComplianceRule(
        rule_id="CR-PWS-04",
        regulation="NIST 800-53",
        title="Cybersecurity Requirements Reference",
        applicable_to=["PWS"],
        check_description="IT PWS references applicable NIST 800-53 security control baseline "
                          "and FISMA requirements.",
        remediation="Add section referencing NIST 800-53 controls applicable to the system "
                    "impact level (Low/Moderate/High).",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
        requires_it=True,
    ),
    ComplianceRule(
        rule_id="CR-PWS-05",
        regulation="HSAR 3052.204-71",
        title="CUI/SSI Handling Procedures",
        applicable_to=["PWS"],
        check_description="PWS addresses CUI and SSI handling requirements including marking, "
                          "storage, transmission, and destruction.",
        remediation="Add CUI/SSI handling section per HSAR 3052.204-71 and 49 CFR Part 1520.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="HSAR",
    ),

    # ── Section L Rules (4) ──
    ComplianceRule(
        rule_id="CR-L-01",
        regulation="FAR 15.204-5",
        title="Standard L Structure",
        applicable_to=["Section_L"],
        check_description="Section L follows standard L.1-L.6 structure per FAR 15.204-5.",
        remediation="Restructure to include L.1 (General), L.2 (Instructions), L.3 (Technical), "
                    "L.4 (Management), L.5 (Past Performance), L.6 (Price/Cost).",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),
    ComplianceRule(
        rule_id="CR-L-02",
        regulation="FAR 15.204-5",
        title="Technical Approach Traceability",
        applicable_to=["Section_L"],
        check_description="L.3 technical approach instructions trace to specific PWS sections.",
        remediation="Map each L.3 instruction to corresponding PWS requirement section. "
                    "Every PWS section should have at least one L instruction.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),
    ComplianceRule(
        rule_id="CR-L-03",
        regulation="HSAM 3015.204-71",
        title="Past Performance References",
        applicable_to=["Section_L"],
        check_description="Past performance instructions specify number of references "
                          "and relevance criteria.",
        remediation="Specify 3-5 references (scaled to value), define relevance in terms "
                    "of scope, complexity, and dollar value.",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="HSAR",
    ),
    ComplianceRule(
        rule_id="CR-L-04",
        regulation="FAR 15.204-5",
        title="Page Limits",
        applicable_to=["Section_L"],
        check_description="Page limits are stated and scaled appropriately to acquisition value.",
        remediation="Add page limits. Guideline: 25pp ($1M), 40pp ($20M), 60pp ($50M+).",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="FAR",
    ),

    # ── Section M Rules (5) ──
    ComplianceRule(
        rule_id="CR-M-01",
        regulation="FAR 15.101-1",
        title="Evaluation Factors Structure",
        applicable_to=["Section_M"],
        check_description="Section M includes basis for award, evaluation factors, "
                          "and relative importance/traceability.",
        remediation="Add M.1 (Basis for Award), evaluation factors with subfactors, "
                    "and relative importance statement.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),
    ComplianceRule(
        rule_id="CR-M-02",
        regulation="FAR 15.101-1",
        title="Adjectival Rating Definitions",
        applicable_to=["Section_M"],
        check_description="Adjectival ratings (Outstanding/Good/Acceptable/Marginal/Unacceptable) "
                          "have specific, distinguishable definitions.",
        remediation="Define each rating level with specific criteria that distinguish "
                    "between adjacent levels. Avoid generic/vague definitions.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),
    ComplianceRule(
        rule_id="CR-M-03",
        regulation="TSA PL 2017-004",
        title="SSA Appointment Citation",
        applicable_to=["Section_M"],
        check_description="For acquisitions >= $2.5M, SSA appointment is cited per TSA policy.",
        remediation="Reference SSA appointment authority per TSA PL 2017-004 Rev.004.",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="TSA",
        min_value=2_500_000,
    ),
    ComplianceRule(
        rule_id="CR-M-04",
        regulation="FAR 15.101-2",
        title="LPTA Rationale",
        applicable_to=["Section_M"],
        check_description="If LPTA evaluation, rationale documented per FAR 15.101-2 "
                          "and D&F obtained (or Class D&F exception cited for IT SW/HW).",
        remediation="Document LPTA rationale. For IT SW/HW, cite HCA Class D&F (Aug 2022). "
                    "For other categories, obtain individual D&F from Division Director.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),
    ComplianceRule(
        rule_id="CR-M-05",
        regulation="FAR 15.101-1",
        title="Price as Evaluation Factor",
        applicable_to=["Section_M"],
        check_description="Price/cost is included as an evaluation factor.",
        remediation="Add price/cost evaluation factor. Price must always be evaluated "
                    "per FAR 15.304(c)(1).",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),

    # ── QASP Rules (3) ──
    ComplianceRule(
        rule_id="CR-QASP-01",
        regulation="FAR 37.604",
        title="QASP Structure",
        applicable_to=["QASP"],
        check_description="QASP includes 5 sections: purpose, objectives, SLAs, "
                          "surveillance method, corrective action chain.",
        remediation="Structure QASP with: (1) Purpose, (2) Objectives aligned to PWS, "
                    "(3) SLA definitions, (4) Surveillance method, (5) Corrective actions.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
        requires_services=True,
    ),
    ComplianceRule(
        rule_id="CR-QASP-02",
        regulation="HSAM 3037.604",
        title="QASP-PWS Mapping",
        applicable_to=["QASP"],
        check_description="QASP surveillance items map to specific PWS metrics/SLAs.",
        remediation="Create explicit mapping table: PWS section → QASP surveillance item "
                    "→ metric → acceptable level → surveillance method.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="HSAR",
        requires_services=True,
    ),
    ComplianceRule(
        rule_id="CR-QASP-03",
        regulation="FAR 37.604-5",
        title="Corrective Action Chain",
        applicable_to=["QASP"],
        check_description="Progressive corrective action chain defined "
                          "(CAR → Cure Notice → Show Cause → Default).",
        remediation="Define escalation: (1) Corrective Action Request, (2) Cure Notice "
                    "(10 days per FAR 49.402-3), (3) Show Cause, (4) Termination for Default.",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="FAR",
        requires_services=True,
    ),

    # ── IGCE Rules (3) ──
    ComplianceRule(
        rule_id="CR-IGCE-01",
        regulation="FAR 15.404-1(d)",
        title="Methodology Transparency",
        applicable_to=["IGCE"],
        check_description="IGCE documents methodology used (historical, benchmarks, parametric) "
                          "with source references.",
        remediation="Add methodology section documenting data sources, analysis approach, "
                    "and basis for each cost element.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="FAR",
    ),
    ComplianceRule(
        rule_id="CR-IGCE-02",
        regulation="HSAM 3034.201-70",
        title="Comparable Contracts",
        applicable_to=["IGCE"],
        check_description="For acquisitions >= $5.5M, IGCE includes >= 3 comparable contracts "
                          "with source references.",
        remediation="Add section with at least 3 comparable contracts from USAspending or "
                    "FPDS showing PIID, value, period, scope similarity.",
        severity_if_violated=ComplianceLevel.MAJOR,
        source_weight="HSAR",
        min_value=5_500_000,
    ),
    ComplianceRule(
        rule_id="CR-IGCE-03",
        regulation="FAR 15.403-1(c)",
        title="Cost/Pricing Data Threshold",
        applicable_to=["IGCE"],
        check_description="For acquisitions >= $2.5M, addresses cost/pricing data requirements "
                          "or documents exception per FAR 15.403-1.",
        remediation="Document whether cost/pricing data is required or cite applicable "
                    "exception (adequate price competition, commercial item, etc.).",
        severity_if_violated=ComplianceLevel.MINOR,
        source_weight="FAR",
        min_value=2_500_000,
    ),
]


# ─── Source Weights ──────────────────────────────────────────────────────────

SOURCE_WEIGHTS = {
    "FAR": 0.40,
    "HSAR": 0.35,
    "TSA": 0.25,
}


# ─── Content Analysis Functions ──────────────────────────────────────────────

_PRESCRIPTIVE_PATTERNS = [
    r"\bshall\s+provide\s+\d+\s+staff",
    r"\bshall\s+employ\s+\d+",
    r"\bminimum\s+of\s+\d+\s+(FTE|personnel|staff)",
    r"\bworking\s+hours?\s+(shall|must|will)\s+be",
    r"\bshall\s+use\s+(the\s+following\s+)?method",
    r"\bshall\s+follow\s+the\s+(exact|specific|prescribed)\s+process",
]

_VAGUE_PATTERNS = [
    r"\b(adequate|appropriate|reasonable|sufficient|timely)\b(?!\s+(price|competition))",
    r"\bas\s+needed\b",
    r"\bas\s+required\b",
    r"\bin\s+a\s+timely\s+manner\b",
    r"\bbest\s+effort\b",
]

_METRIC_PATTERNS = [
    r"\d+\s*%",
    r"\d+\s*(hours?|days?|minutes?|seconds?)",
    r"SLA",
    r"\d+\.\d+",
    r"within\s+\d+",
    r"no\s+(more|less)\s+than\s+\d+",
]


def _check_prescriptive(content: str) -> tuple[ComplianceLevel, str]:
    """Check for prescriptive language in PWS content."""
    matches = []
    for pattern in _PRESCRIPTIVE_PATTERNS:
        found = re.findall(pattern, content, re.IGNORECASE)
        matches.extend(found)
    if len(matches) >= 3:
        return ComplianceLevel.MAJOR, f"Found {len(matches)} prescriptive statements"
    elif matches:
        return ComplianceLevel.MINOR, f"Found {len(matches)} prescriptive statement(s)"
    return ComplianceLevel.COMPLIANT, "Performance-based language used"


def _check_metrics(content: str) -> tuple[ComplianceLevel, str]:
    """Check for measurable metrics in content."""
    metrics = []
    for pattern in _METRIC_PATTERNS:
        metrics.extend(re.findall(pattern, content, re.IGNORECASE))
    vague = []
    for pattern in _VAGUE_PATTERNS:
        vague.extend(re.findall(pattern, content, re.IGNORECASE))

    if len(metrics) >= 3 and len(vague) <= 1:
        return ComplianceLevel.COMPLIANT, f"{len(metrics)} metrics found, {len(vague)} vague terms"
    elif metrics:
        return ComplianceLevel.MINOR, f"{len(metrics)} metrics but {len(vague)} vague terms"
    return ComplianceLevel.MAJOR, f"No measurable metrics found, {len(vague)} vague terms"


def _check_section_structure(content: str, required_sections: list[str]) -> tuple[ComplianceLevel, str]:
    """Check if content contains required section headings."""
    found = sum(1 for s in required_sections if s.lower() in content.lower())
    total = len(required_sections)
    if found == total:
        return ComplianceLevel.COMPLIANT, f"All {total} required sections present"
    elif found >= total * 0.7:
        return ComplianceLevel.MINOR, f"{found}/{total} required sections present"
    elif found > 0:
        return ComplianceLevel.MAJOR, f"Only {found}/{total} required sections present"
    return ComplianceLevel.MISSING, "No required sections found"


def _check_keyword_present(content: str, keywords: list[str]) -> tuple[ComplianceLevel, str]:
    """Check if any of the required keywords are present."""
    found = [k for k in keywords if k.lower() in content.lower()]
    if len(found) >= len(keywords) * 0.7:
        return ComplianceLevel.COMPLIANT, f"Found: {', '.join(found[:5])}"
    elif found:
        return ComplianceLevel.MINOR, f"Partial: {', '.join(found[:3])}"
    return ComplianceLevel.MISSING, f"None of {', '.join(keywords[:3])} found"


# ─── Rule Evaluation Engine ─────────────────────────────────────────────────

def _is_rule_applicable(rule: ComplianceRule, params: dict[str, Any]) -> bool:
    """Check if a compliance rule applies to this acquisition."""
    if rule.min_value and params.get("estimated_value", 0) < rule.min_value:
        return False
    if rule.requires_services is not None:
        if params.get("services", True) != rule.requires_services:
            return False
    if rule.requires_it is not None:
        if params.get("is_it", False) != rule.requires_it:
            return False
    return True


def evaluate_rule(
    rule: ComplianceRule,
    document_content: dict[str, str],
    params: dict[str, Any],
) -> ComplianceCheckResult | None:
    """Evaluate a single compliance rule against document content.

    Args:
        rule: The compliance rule to check
        document_content: Dict of section_name -> content text
        params: Acquisition parameters for applicability checks

    Returns:
        ComplianceCheckResult or None if rule doesn't apply
    """
    if not _is_rule_applicable(rule, params):
        return None

    # Combine all content for this document type
    full_content = " ".join(document_content.values())
    if not full_content.strip():
        return ComplianceCheckResult(
            rule_id=rule.rule_id,
            regulation=rule.regulation,
            title=rule.title,
            level=ComplianceLevel.MISSING,
            score=0,
            detail="Document content is empty",
            remediation=rule.remediation,
            section_ref="all",
        )

    # Rule-specific checks
    level = ComplianceLevel.COMPLIANT
    detail = "Passes check"

    if rule.rule_id == "CR-PWS-01":
        level, detail = _check_prescriptive(full_content)
    elif rule.rule_id == "CR-PWS-02":
        level, detail = _check_metrics(full_content)
    elif rule.rule_id == "CR-PWS-03":
        level, detail = _check_keyword_present(
            full_content, ["acquisition plan", "HSAM 3007", "FFP exemption", "AP"]
        )
    elif rule.rule_id == "CR-PWS-04":
        level, detail = _check_keyword_present(
            full_content, ["NIST 800-53", "FISMA", "security control", "ATO"]
        )
    elif rule.rule_id == "CR-PWS-05":
        level, detail = _check_keyword_present(
            full_content, ["CUI", "SSI", "HSAR 3052", "controlled unclassified"]
        )
    elif rule.rule_id == "CR-L-01":
        level, detail = _check_section_structure(
            full_content, ["L.1", "L.2", "L.3", "L.4", "L.5", "L.6"]
        )
    elif rule.rule_id == "CR-L-02":
        level, detail = _check_keyword_present(
            full_content, ["PWS", "technical approach", "requirement", "Section C"]
        )
    elif rule.rule_id == "CR-L-03":
        level, detail = _check_keyword_present(
            full_content, ["past performance", "reference", "relevance", "contract"]
        )
    elif rule.rule_id == "CR-L-04":
        level, detail = _check_keyword_present(
            full_content, ["page limit", "pages", "not to exceed", "maximum"]
        )
    elif rule.rule_id == "CR-M-01":
        level, detail = _check_section_structure(
            full_content, ["basis for award", "evaluation factor", "importance"]
        )
    elif rule.rule_id == "CR-M-02":
        level, detail = _check_keyword_present(
            full_content, ["outstanding", "good", "acceptable", "marginal", "unacceptable"]
        )
    elif rule.rule_id == "CR-M-03":
        level, detail = _check_keyword_present(
            full_content, ["SSA", "source selection authority", "PL 2017-004"]
        )
    elif rule.rule_id == "CR-M-04":
        # Only check if LPTA
        if "lpta" in full_content.lower() or params.get("evaluation_type") == "lpta":
            level, detail = _check_keyword_present(
                full_content, ["D&F", "determination", "LPTA", "lowest price"]
            )
        else:
            return None  # Tradeoff — LPTA rule doesn't apply
    elif rule.rule_id == "CR-M-05":
        level, detail = _check_keyword_present(
            full_content, ["price", "cost", "evaluation factor"]
        )
    elif rule.rule_id == "CR-QASP-01":
        level, detail = _check_section_structure(
            full_content, ["purpose", "objective", "SLA", "surveillance", "corrective"]
        )
    elif rule.rule_id == "CR-QASP-02":
        level, detail = _check_keyword_present(
            full_content, ["PWS", "mapping", "metric", "surveillance"]
        )
    elif rule.rule_id == "CR-QASP-03":
        level, detail = _check_keyword_present(
            full_content, ["corrective action", "cure notice", "escalation"]
        )
    elif rule.rule_id == "CR-IGCE-01":
        level, detail = _check_keyword_present(
            full_content, ["methodology", "historical", "benchmark", "parametric", "source"]
        )
    elif rule.rule_id == "CR-IGCE-02":
        level, detail = _check_keyword_present(
            full_content, ["comparable", "contract", "PIID", "FPDS", "USAspending"]
        )
    elif rule.rule_id == "CR-IGCE-03":
        level, detail = _check_keyword_present(
            full_content, ["cost data", "pricing data", "FAR 15.403", "exception"]
        )

    return ComplianceCheckResult(
        rule_id=rule.rule_id,
        regulation=rule.regulation,
        title=rule.title,
        level=level,
        score=COMPLIANCE_SCORES.get(level, 0),
        detail=detail,
        remediation=rule.remediation if level != ComplianceLevel.COMPLIANT else "",
        section_ref="all",
    )


# ─── Compliance Overlay Engine ───────────────────────────────────────────────

class ComplianceOverlayEngine:
    """Evaluates documents against compliance rules, producing per-section grids."""

    def __init__(self, rules: list[ComplianceRule] | None = None):
        self.rules = rules or COMPLIANCE_RULES

    def evaluate_document(
        self,
        doc_type: str,
        content: dict[str, str],
        params: dict[str, Any],
    ) -> DocumentComplianceGrid:
        """Evaluate a single document against all applicable rules.

        Args:
            doc_type: Document type (PWS, Section_L, Section_M, QASP, IGCE)
            content: Dict of section_name -> content text
            params: Acquisition parameters

        Returns:
            DocumentComplianceGrid with per-rule results
        """
        applicable_rules = [r for r in self.rules if doc_type in r.applicable_to]
        checks = []

        for rule in applicable_rules:
            result = evaluate_rule(rule, content, params)
            if result:
                checks.append(result)

        # Calculate weighted score
        if checks:
            total_weighted = 0
            total_weight = 0
            for c in checks:
                rule = next((r for r in self.rules if r.rule_id == c.rule_id), None)
                weight = SOURCE_WEIGHTS.get(rule.source_weight if rule else "FAR", 0.4)
                total_weighted += c.score * weight
                total_weight += weight
            overall = total_weighted / total_weight if total_weight > 0 else 0
        else:
            overall = 100.0  # No applicable rules = compliant by default

        blocking = [c for c in checks if c.level in (ComplianceLevel.MAJOR, ComplianceLevel.MISSING)]

        summary_parts = []
        compliant = sum(1 for c in checks if c.level == ComplianceLevel.COMPLIANT)
        minor = sum(1 for c in checks if c.level == ComplianceLevel.MINOR)
        major = sum(1 for c in checks if c.level == ComplianceLevel.MAJOR)
        missing = sum(1 for c in checks if c.level == ComplianceLevel.MISSING)
        if compliant:
            summary_parts.append(f"{compliant} compliant")
        if minor:
            summary_parts.append(f"{minor} minor")
        if major:
            summary_parts.append(f"{major} major")
        if missing:
            summary_parts.append(f"{missing} missing")

        return DocumentComplianceGrid(
            document_type=doc_type,
            checks=checks,
            overall_score=round(overall, 1),
            blocking_issues=blocking,
            summary=f"{doc_type}: {', '.join(summary_parts)}" if summary_parts else f"{doc_type}: no rules applicable",
        )

    def evaluate_all(
        self,
        documents: dict[str, dict[str, str]],
        params: dict[str, Any],
    ) -> ComplianceOverlayResponse:
        """Evaluate all documents and produce the full compliance overlay.

        Args:
            documents: Dict of doc_type -> {section_name -> content}
                       e.g. {"PWS": {"2.1 Service Delivery": "...", "3.0 Reporting": "..."}}
            params: Acquisition parameters

        Returns:
            ComplianceOverlayResponse with grids, scores, and fix recommendations
        """
        grids = []
        for doc_type, content in documents.items():
            grid = self.evaluate_document(doc_type, content, params)
            grids.append(grid)

        # Aggregate counts
        all_checks = [c for g in grids for c in g.checks]
        compliant = sum(1 for c in all_checks if c.level == ComplianceLevel.COMPLIANT)
        minor = sum(1 for c in all_checks if c.level == ComplianceLevel.MINOR)
        major = sum(1 for c in all_checks if c.level == ComplianceLevel.MAJOR)
        missing = sum(1 for c in all_checks if c.level == ComplianceLevel.MISSING)

        # Overall compliance score
        if all_checks:
            overall = sum(c.score for c in all_checks) / len(all_checks)
        else:
            overall = 100.0

        # Blocking sections
        blocking_sections = []
        for g in grids:
            if g.blocking_issues:
                blocking_sections.append(g.document_type)

        # Recommended fix order: most blocking issues first
        fix_order = sorted(grids, key=lambda g: len(g.blocking_issues), reverse=True)
        recommended_fix_order = [
            f"{g.document_type} ({len(g.blocking_issues)} blocking)"
            for g in fix_order if g.blocking_issues
        ]

        return ComplianceOverlayResponse(
            grids=grids,
            overall_compliance_score=round(overall, 1),
            total_rules_checked=len(all_checks),
            compliant_count=compliant,
            minor_count=minor,
            major_count=major,
            missing_count=missing,
            blocking_sections=blocking_sections,
            recommended_fix_order=recommended_fix_order,
            source_provenance=[
                f"{len(COMPLIANCE_RULES)} compliance rules (FAR/HSAR/TSA)",
                "Source weights: FAR 40%, HSAR 35%, TSA 25%",
                "Effective date: Oct 1, 2025",
            ],
        )


def get_all_rules() -> list[dict[str, Any]]:
    """Return all compliance rules for display/documentation."""
    return [
        {
            "rule_id": r.rule_id,
            "regulation": r.regulation,
            "title": r.title,
            "applicable_to": r.applicable_to,
            "check_description": r.check_description,
            "remediation": r.remediation,
            "severity_if_violated": r.severity_if_violated.value,
            "source_weight": r.source_weight,
        }
        for r in COMPLIANCE_RULES
    ]
