"""
Legacy SOW Analyzer — Phase 25
================================
Analyzes existing Statements of Work (SOW) to identify quality issues,
regulatory gaps, and protest vulnerabilities BEFORE conversion to PWS.

Three analysis layers:
1. Quality Analysis — language, structure, measurability
2. Gap Analysis — FAR 37.102 PBA compliance, QASP linkage, acceptance criteria
3. Protest Vulnerability Scan — ambiguous evaluation language, unstated criteria

Input: Raw SOW text (string or section-parsed dict)
Output: AnalysisReport with findings, severity, recommended fixes, and
        a structured requirements matrix ready for Phase 24 consumption.

Tier 2 — AI analyzes, CO reviews findings. No Tier 3 actions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Finding severity — drives fix priority ordering."""
    CRITICAL = "critical"    # Blocks solicitation release
    HIGH = "high"            # Protest risk if not fixed
    MEDIUM = "medium"        # Best practice violation
    LOW = "low"              # Style/readability improvement
    INFO = "info"            # Informational observation


class FindingCategory(str, Enum):
    """Top-level finding categories."""
    LANGUAGE = "language"
    STRUCTURE = "structure"
    MEASURABILITY = "measurability"
    PBA_COMPLIANCE = "pba_compliance"
    QASP_LINKAGE = "qasp_linkage"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    PROTEST_VULNERABILITY = "protest_vulnerability"
    SECURITY = "security"
    DELIVERABLES = "deliverables"


class PBAElement(str, Enum):
    """FAR 37.102 Performance-Based Acquisition required elements."""
    PERFORMANCE_STANDARDS = "performance_standards"
    MEASURABLE_OUTCOMES = "measurable_outcomes"
    QUALITY_ASSURANCE = "quality_assurance"
    PERFORMANCE_INCENTIVES = "performance_incentives"
    WORK_REQUIREMENTS = "work_requirements"
    GOVERNMENT_FURNISHED = "government_furnished"
    DELIVERABLES = "deliverables"
    PERIOD_OF_PERFORMANCE = "period_of_performance"


# ---------------------------------------------------------------------------
# Language detection patterns
# ---------------------------------------------------------------------------

# Passive voice markers (be + past participle patterns)
PASSIVE_INDICATORS = [
    r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b",
    r"\b(?:is|are|was|were|be|been|being)\s+\w+en\b",
    r"\bshall be\s+\w+ed\b",
    r"\bwill be\s+\w+ed\b",
]

# Vague / unmeasurable language
VAGUE_TERMS = {
    "as needed": "Define specific trigger conditions and response times",
    "as required": "Specify the conditions under which the requirement applies",
    "as appropriate": "Define criteria for what constitutes 'appropriate'",
    "as necessary": "Define specific conditions that trigger this requirement",
    "best effort": "Replace with measurable performance standard (e.g., 99.5% uptime)",
    "reasonable": "Define quantitative threshold or acceptance criteria",
    "adequate": "Replace with measurable standard (e.g., 'within 4 business hours')",
    "sufficient": "Specify quantity, quality, or performance metric",
    "timely": "Replace with specific timeframe (e.g., 'within 24 hours')",
    "promptly": "Replace with specific timeframe (e.g., 'within 2 business hours')",
    "approximately": "Specify acceptable range (e.g., '40-50 FTEs')",
    "various": "List the specific items or categories",
    "etc": "Enumerate all items — 'etc.' is unenforceable",
    "and/or": "Use 'and' or 'or' — 'and/or' creates ambiguity in obligation",
    "may": "'May' is permissive, not mandatory — use 'shall' for requirements",
    "should": "'Should' is non-binding — use 'shall' for requirements",
    "could": "'Could' implies possibility, not obligation — use 'shall'",
    "might": "'Might' implies uncertainty — define the requirement clearly",
    "try to": "Remove 'try to' — the contractor shall perform, not try",
    "best practices": "Define the specific practices required",
    "industry standard": "Cite the specific standard (ISO, NIST, etc.)",
    "state of the art": "Define the specific technical requirements",
    "minimize": "Define the acceptable threshold or target metric",
    "maximize": "Define the measurable target or performance level",
    "significant": "Define quantitative threshold",
    "substantial": "Define quantitative threshold or criteria",
}

# Will vs shall inconsistency
WILL_SHALL_PATTERN = re.compile(
    r"\b(the\s+contractor|contractor)\s+(will|shall)\b", re.IGNORECASE
)

# Staffing spec patterns (prescriptive — anti-PBA)
STAFFING_PATTERNS = [
    r"\b\d+\s+(?:FTEs?|full[- ]time\s+equivalents?|employees?|staff|personnel|workers)\b",
    r"\b(?:provide|maintain|employ|assign|dedicate)\s+\d+\s+",
    r"\bstaffing\s+level\s+of\s+\d+",
    r"\bminimum\s+of\s+\d+\s+(?:FTEs?|staff|personnel)",
    r"\b(?:team|workforce)\s+(?:of|consisting\s+of)\s+\d+",
]

# Deliverable detection patterns
DELIVERABLE_PATTERNS = [
    r"(?:deliver|submit|provide|furnish)\s+(?:a|an|the)\s+(\w[\w\s]{3,40}?)(?:\s+(?:to|within|by|no later))",
    r"(?:monthly|weekly|quarterly|annual|daily)\s+(\w[\w\s]{2,30}?report\w*)",
    r"(?:final|draft|interim)\s+(\w[\w\s]{2,30})",
]

# SLA / metric patterns
METRIC_PATTERNS = [
    r"\b(\d+(?:\.\d+)?)\s*%",                          # percentage
    r"\bwithin\s+(\d+)\s+(?:hours?|days?|minutes?)\b",  # time SLA
    r"\b(\d+)\s+(?:business|calendar|working)\s+days?\b", # business days
    r"\b(?:99|98|97|95|90)(?:\.\d+)?\s*%\s*(?:uptime|availability|SLA)", # uptime
    r"\bno\s+(?:more|fewer)\s+than\s+(\d+)",            # threshold
]

# PBA element detection keywords
PBA_KEYWORDS = {
    PBAElement.PERFORMANCE_STANDARDS: [
        "performance standard", "service level", "SLA", "KPI",
        "key performance indicator", "metric", "benchmark",
        "acceptance criteria", "performance measure",
    ],
    PBAElement.MEASURABLE_OUTCOMES: [
        "measurable", "outcome", "result", "objective",
        "deliverable", "milestone", "target", "goal",
    ],
    PBAElement.QUALITY_ASSURANCE: [
        "quality assurance", "QASP", "surveillance",
        "inspection", "quality control", "QCP", "QA",
    ],
    PBAElement.PERFORMANCE_INCENTIVES: [
        "incentive", "award fee", "award term", "penalty",
        "liquidated damages", "deduction", "disincentive",
    ],
    PBAElement.WORK_REQUIREMENTS: [
        "scope", "task", "requirement", "service",
        "shall perform", "shall provide", "shall deliver",
    ],
    PBAElement.GOVERNMENT_FURNISHED: [
        "government furnished", "GFE", "GFI", "GFP",
        "government-provided", "government property",
        "government will provide", "furnished by the government",
    ],
    PBAElement.DELIVERABLES: [
        "deliverable", "report", "document", "artifact",
        "submission", "data item", "CDRL", "DID",
    ],
    PBAElement.PERIOD_OF_PERFORMANCE: [
        "period of performance", "base period", "option period",
        "option year", "base year", "POP", "contract period",
    ],
}

# Security-related keywords
SECURITY_KEYWORDS = [
    "clearance", "classified", "CUI", "SSI", "FOUO", "secret",
    "top secret", "sensitive", "FISMA", "FedRAMP", "ATO",
    "NIST 800", "background check", "suitability", "PIV",
    "badge", "access control", "cybersecurity", "incident response",
]

# Protest vulnerability patterns
PROTEST_PATTERNS = {
    "PV-01": {
        "name": "Ambiguous evaluation language in requirements",
        "patterns": [
            r"\b(?:best|superior|excellent|outstanding)\s+(?:quality|service|performance)\b",
            r"\bdemonstrate\s+(?:ability|capability|capacity)\b",
        ],
        "detail": "Vague quality language may lead to inconsistent evaluation. "
                  "GAO sustains protests when evaluation criteria are subjective "
                  "and not tied to measurable standards.",
        "authority": "FAR 15.304, GAO B-414230 (CACI/TSA)",
        "severity": Severity.HIGH,
    },
    "PV-02": {
        "name": "Unstated evaluation criteria embedded in SOW",
        "patterns": [
            r"\bpreference\s+(?:will|shall)\s+be\s+given\b",
            r"\b(?:highly\s+)?desirable\b",
            r"\bpreferred\b",
        ],
        "detail": "Preference language in SOW creates implicit evaluation criteria "
                  "not disclosed in Section M. All evaluation factors must be stated "
                  "in the solicitation per FAR 15.304.",
        "authority": "FAR 15.304, FAR 15.305(a)",
        "severity": Severity.CRITICAL,
    },
    "PV-03": {
        "name": "Inconsistent requirements across sections",
        "patterns": [],  # Detected by cross-section analysis, not regex
        "detail": "Requirements stated differently in different SOW sections create "
                  "ambiguity that bidders can protest. Each requirement should appear "
                  "once with clear cross-references.",
        "authority": "FAR 15.204-2, GAO case law",
        "severity": Severity.HIGH,
    },
    "PV-04": {
        "name": "Missing or vague acceptance criteria for deliverables",
        "patterns": [],  # Detected by deliverable analysis
        "detail": "Deliverables without clear acceptance criteria make evaluation "
                  "subjective. Define format, content requirements, review period, "
                  "and approval authority for each deliverable.",
        "authority": "FAR 37.602, FAR 46.2",
        "severity": Severity.MEDIUM,
    },
    "PV-05": {
        "name": "Brand-name or proprietary references without justification",
        "patterns": [
            r"\b(?:brand\s+name|proprietary|specific\s+(?:product|vendor|manufacturer))\b",
            r"\b(?:Microsoft|Oracle|SAP|Salesforce|ServiceNow|Palantir|AWS|Azure)\b",
        ],
        "detail": "Brand-name references restrict competition per FAR 11.105. "
                  "Use 'brand name or equal' with salient characteristics, or "
                  "justify sole source per FAR 6.302.",
        "authority": "FAR 11.105, FAR 6.302",
        "severity": Severity.HIGH,
    },
    "PV-06": {
        "name": "Organizational conflict of interest risk",
        "patterns": [
            r"\b(?:advisory|consulting)\s+(?:and|&)\s+(?:implementation|development)\b",
            r"\b(?:evaluate|assess|review).*(?:own|their|its)\s+(?:work|performance)\b",
            r"\badvise\b.*\b(?:and|then)\b.*\bimplement\b",
        ],
        "detail": "Combining advisory and implementation roles in the same "
                  "contract creates OCI risk per FAR 9.5. Separate the functions "
                  "or include an OCI mitigation plan.",
        "authority": "FAR 9.5, HSAR 3009.5",
        "severity": Severity.HIGH,
    },
    "PV-07": {
        "name": "Prescriptive staffing undermines competition",
        "patterns": STAFFING_PATTERNS,
        "detail": "Specifying exact headcounts forces a particular solution and "
                  "limits competition. Use outcomes and SLAs instead of FTE counts. "
                  "Prescriptive staffing also conflicts with PBA principles (FAR 37.102).",
        "authority": "FAR 37.102, DAU PBA guidance",
        "severity": Severity.MEDIUM,
    },
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SOWSection:
    """Parsed section from a legacy SOW."""
    section_id: str           # e.g., "3.1", "4.2.1"
    heading: str = ""
    content: str = ""
    level: int = 1            # Nesting depth
    word_count: int = 0
    has_deliverables: bool = False
    has_metrics: bool = False
    has_security: bool = False


@dataclass
class Finding:
    """Single analysis finding."""
    finding_id: str           # e.g., "LQ-001", "GAP-003", "PV-05"
    category: FindingCategory
    severity: Severity
    title: str
    detail: str
    location: str = ""        # Section reference where found
    snippet: str = ""         # Quoted text from SOW
    recommended_fix: str = ""
    authority: str = ""       # FAR/HSAR citation
    protest_relevant: bool = False


@dataclass
class RequirementEntry:
    """Extracted requirement for Phase 24 requirements matrix."""
    requirement_id: str
    source_section: str       # SOW section where found
    text: str                 # Original requirement text
    category: str = ""        # technical, management, reporting, etc.
    priority: str = "standard"  # critical, standard, desirable
    verification_method: str = ""  # inspection, analysis, demonstration, test
    acceptance_criteria: str = ""  # Extracted or empty (gap)
    has_metric: bool = False
    metric_value: str = ""


@dataclass
class DeliverableEntry:
    """Extracted deliverable with acceptance analysis."""
    deliverable_id: str
    name: str
    source_section: str
    frequency: str = ""       # monthly, quarterly, one-time, etc.
    format_specified: bool = False
    acceptance_criteria: str = ""
    review_period: str = ""
    approval_authority: str = ""


@dataclass
class AnalysisReport:
    """Complete SOW analysis output."""
    # Metadata
    generated_at: str = ""
    sow_word_count: int = 0
    section_count: int = 0
    source_provenance: list = field(default_factory=lambda: [
        "FAR 37.102 (PBA)", "FAR 37.602 (SOW/PWS)", "FAR 15.204-2 (UCF)",
        "FAR 46.2 (Quality Assurance)", "DAU SOW-to-PWS Conversion Guide"
    ])
    requires_acceptance: bool = True

    # Parsed structure
    sections: list = field(default_factory=list)  # list[SOWSection]

    # Findings by layer
    findings: list = field(default_factory=list)  # list[Finding]

    # Extracted artifacts
    requirements: list = field(default_factory=list)  # list[RequirementEntry]
    deliverables: list = field(default_factory=list)  # list[DeliverableEntry]

    # PBA compliance
    pba_elements_found: dict = field(default_factory=dict)  # PBAElement → bool
    pba_score: float = 0.0  # 0-100

    # Summary scores
    quality_score: float = 0.0       # 0-100 language quality
    gap_score: float = 0.0           # 0-100 completeness
    protest_risk_score: float = 0.0  # 0-100 protest vulnerability
    overall_score: float = 0.0       # Weighted composite

    # Counts by severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0

    def to_dict(self) -> dict:
        """Full serialization for API response."""
        return {
            "generated_at": self.generated_at,
            "sow_word_count": self.sow_word_count,
            "section_count": self.section_count,
            "source_provenance": self.source_provenance,
            "requires_acceptance": self.requires_acceptance,
            "sections": [
                {
                    "section_id": s.section_id,
                    "heading": s.heading,
                    "content": s.content[:200] + "..." if len(s.content) > 200 else s.content,
                    "level": s.level,
                    "word_count": s.word_count,
                    "has_deliverables": s.has_deliverables,
                    "has_metrics": s.has_metrics,
                    "has_security": s.has_security,
                }
                for s in self.sections
            ],
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "detail": f.detail,
                    "location": f.location,
                    "snippet": f.snippet,
                    "recommended_fix": f.recommended_fix,
                    "authority": f.authority,
                    "protest_relevant": f.protest_relevant,
                }
                for f in self.findings
            ],
            "requirements": [
                {
                    "requirement_id": r.requirement_id,
                    "source_section": r.source_section,
                    "text": r.text,
                    "category": r.category,
                    "priority": r.priority,
                    "verification_method": r.verification_method,
                    "acceptance_criteria": r.acceptance_criteria,
                    "has_metric": r.has_metric,
                    "metric_value": r.metric_value,
                }
                for r in self.requirements
            ],
            "deliverables": [
                {
                    "deliverable_id": d.deliverable_id,
                    "name": d.name,
                    "source_section": d.source_section,
                    "frequency": d.frequency,
                    "format_specified": d.format_specified,
                    "acceptance_criteria": d.acceptance_criteria,
                    "review_period": d.review_period,
                    "approval_authority": d.approval_authority,
                }
                for d in self.deliverables
            ],
            "pba_elements": {
                k.value: v for k, v in self.pba_elements_found.items()
            },
            "pba_score": round(self.pba_score, 1),
            "scores": {
                "quality": round(self.quality_score, 1),
                "gap": round(self.gap_score, 1),
                "protest_risk": round(self.protest_risk_score, 1),
                "overall": round(self.overall_score, 1),
            },
            "severity_counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "info": self.info_count,
            },
            "fix_priority": self._fix_priority(),
        }

    def _fix_priority(self) -> list[dict]:
        """Ordered list of fixes by severity then category."""
        priority = []
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            for f in self.findings:
                if f.severity == sev:
                    priority.append({
                        "finding_id": f.finding_id,
                        "severity": f.severity.value,
                        "title": f.title,
                        "recommended_fix": f.recommended_fix,
                    })
        return priority


# ---------------------------------------------------------------------------
# SOW Parser
# ---------------------------------------------------------------------------

class SOWParser:
    """Parse raw SOW text into structured sections."""

    # Section numbering patterns: 1., 1.1, 1.1.1, C.1, C.1.1
    SECTION_PATTERN = re.compile(
        r"^(?:(?:Section\s+)?([A-Z]?\d+(?:\.\d+)*))\s*[.:\-—]\s*(.+?)$",
        re.MULTILINE,
    )

    def parse(self, text: str) -> list[SOWSection]:
        """Parse SOW text into sections."""
        if not text or not text.strip():
            return []

        sections = []
        matches = list(self.SECTION_PATTERN.finditer(text))

        if not matches:
            # No section headings found — treat as single block
            sections.append(SOWSection(
                section_id="1.0",
                heading="Full Document",
                content=text.strip(),
                level=1,
                word_count=len(text.split()),
            ))
            return sections

        for i, match in enumerate(matches):
            section_id = match.group(1)
            heading = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            level = section_id.count(".") + 1
            word_count = len(content.split()) if content else 0

            sec = SOWSection(
                section_id=section_id,
                heading=heading,
                content=content,
                level=level,
                word_count=word_count,
            )

            # Tag section properties
            content_lower = content.lower()
            sec.has_deliverables = any(
                kw in content_lower
                for kw in ["deliver", "submit", "report", "provide a"]
            )
            sec.has_metrics = bool(re.search(r"\d+\s*%|\bSLA\b|\bKPI\b|\bwithin\s+\d+", content, re.IGNORECASE))
            sec.has_security = any(
                kw in content_lower for kw in ["clearance", "classified", "cui", "ssi", "fisma", "fedramp"]
            )

            sections.append(sec)

        return sections


# ---------------------------------------------------------------------------
# Analysis Engines
# ---------------------------------------------------------------------------

class LanguageQualityAnalyzer:
    """Layer 1: Language quality — passive voice, vague terms, will/shall."""

    def analyze(self, sections: list[SOWSection]) -> list[Finding]:
        findings = []
        counter = 0

        for sec in sections:
            if not sec.content:
                continue
            text = sec.content
            text_lower = text.lower()

            # 1. Passive voice detection
            for pattern in PASSIVE_INDICATORS:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                if len(matches) >= 2:  # Only flag if multiple instances
                    counter += 1
                    snippets = [m.group(0) for m in matches[:3]]
                    findings.append(Finding(
                        finding_id=f"LQ-{counter:03d}",
                        category=FindingCategory.LANGUAGE,
                        severity=Severity.MEDIUM,
                        title="Excessive passive voice",
                        detail=(
                            f"Section {sec.section_id} contains {len(matches)} passive voice "
                            f"constructions. PWS should use active voice with 'The Contractor shall...' "
                            f"for clear obligation assignment."
                        ),
                        location=f"Section {sec.section_id}",
                        snippet="; ".join(snippets),
                        recommended_fix=(
                            "Rewrite using active voice: 'The Contractor shall [verb]...' "
                            "This clarifies who is responsible for each action."
                        ),
                        authority="DAU PBA Rule 1 — use active voice",
                    ))
                    break  # One finding per section for passive voice

            # 2. Vague term detection
            for term, fix in VAGUE_TERMS.items():
                if term.lower() in text_lower:
                    # Find actual snippet context
                    idx = text_lower.find(term.lower())
                    start = max(0, idx - 30)
                    end = min(len(text), idx + len(term) + 30)
                    snippet = text[start:end].strip()

                    counter += 1
                    findings.append(Finding(
                        finding_id=f"LQ-{counter:03d}",
                        category=FindingCategory.LANGUAGE,
                        severity=Severity.HIGH if term in ("etc", "and/or", "may", "should") else Severity.MEDIUM,
                        title=f"Vague language: '{term}'",
                        detail=(
                            f"'{term}' in Section {sec.section_id} is unenforceable in a contract. "
                            f"This language creates ambiguity about contractor obligations."
                        ),
                        location=f"Section {sec.section_id}",
                        snippet=snippet,
                        recommended_fix=fix,
                        authority="DAU PBA Rule 3 — use measurable standards",
                        protest_relevant=term in ("etc", "and/or"),
                    ))

            # 3. Will vs shall inconsistency
            will_matches = re.findall(r"\bcontractor\s+will\b", text_lower)
            shall_matches = re.findall(r"\bcontractor\s+shall\b", text_lower)
            if will_matches and shall_matches:
                counter += 1
                findings.append(Finding(
                    finding_id=f"LQ-{counter:03d}",
                    category=FindingCategory.LANGUAGE,
                    severity=Severity.HIGH,
                    title="Will/shall inconsistency",
                    detail=(
                        f"Section {sec.section_id} uses both 'contractor will' ({len(will_matches)}×) "
                        f"and 'contractor shall' ({len(shall_matches)}×). 'Shall' denotes binding "
                        f"obligation; 'will' is merely predictive. Inconsistent use creates "
                        f"ambiguity about which requirements are actually binding."
                    ),
                    location=f"Section {sec.section_id}",
                    snippet="",
                    recommended_fix=(
                        "Replace all 'contractor will' with 'contractor shall' for binding "
                        "requirements. Use 'will' only for statements of fact (e.g., "
                        "'The Government will provide...')."
                    ),
                    authority="FAR 2.101 — 'shall' denotes mandatory requirement",
                    protest_relevant=True,
                ))
            elif will_matches and not shall_matches:
                counter += 1
                findings.append(Finding(
                    finding_id=f"LQ-{counter:03d}",
                    category=FindingCategory.LANGUAGE,
                    severity=Severity.HIGH,
                    title="Missing 'shall' — only 'will' used for contractor obligations",
                    detail=(
                        f"Section {sec.section_id} uses 'contractor will' ({len(will_matches)}×) "
                        f"but never 'contractor shall'. This may render requirements non-binding."
                    ),
                    location=f"Section {sec.section_id}",
                    snippet="",
                    recommended_fix="Replace 'contractor will' with 'The Contractor shall' throughout.",
                    authority="FAR 2.101",
                ))

            # 4. Prescriptive staffing
            for pattern in STAFFING_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    counter += 1
                    findings.append(Finding(
                        finding_id=f"LQ-{counter:03d}",
                        category=FindingCategory.LANGUAGE,
                        severity=Severity.MEDIUM,
                        title="Prescriptive staffing specification",
                        detail=(
                            f"Section {sec.section_id} specifies staffing levels. PBA principle: "
                            f"tell the contractor WHAT to achieve, not HOW MANY people to use."
                        ),
                        location=f"Section {sec.section_id}",
                        snippet=match.group(0),
                        recommended_fix=(
                            "Replace headcount requirements with performance outcomes and SLAs. "
                            "Let the contractor propose the staffing mix in their proposal."
                        ),
                        authority="FAR 37.102(a), DAU PBA Rule 5",
                        protest_relevant=True,
                    ))
                    break  # One finding per section

        return findings


class GapAnalyzer:
    """Layer 2: Regulatory gap analysis — PBA, QASP, acceptance criteria."""

    def analyze(
        self,
        sections: list[SOWSection],
        requirements: list[RequirementEntry],
        deliverables: list[DeliverableEntry],
    ) -> tuple[list[Finding], dict[PBAElement, bool], float]:
        """Returns findings, PBA element map, and PBA score."""
        findings = []
        counter = 0

        # Combine all content for PBA element search
        all_text = " ".join(s.content for s in sections).lower()

        # 1. PBA element coverage
        pba_found = {}
        for element, keywords in PBA_KEYWORDS.items():
            found = any(kw.lower() in all_text for kw in keywords)
            pba_found[element] = found
            if not found:
                counter += 1
                sev = Severity.CRITICAL if element in (
                    PBAElement.PERFORMANCE_STANDARDS,
                    PBAElement.MEASURABLE_OUTCOMES,
                    PBAElement.WORK_REQUIREMENTS,
                ) else Severity.HIGH if element in (
                    PBAElement.QUALITY_ASSURANCE,
                    PBAElement.DELIVERABLES,
                ) else Severity.MEDIUM

                findings.append(Finding(
                    finding_id=f"GAP-{counter:03d}",
                    category=FindingCategory.PBA_COMPLIANCE,
                    severity=sev,
                    title=f"Missing PBA element: {element.value.replace('_', ' ').title()}",
                    detail=(
                        f"FAR 37.102 requires performance-based acquisitions to include "
                        f"{element.value.replace('_', ' ')}. This element was not detected "
                        f"in the SOW."
                    ),
                    recommended_fix=_pba_fix_suggestion(element),
                    authority="FAR 37.102, FAR 37.601",
                    protest_relevant=element in (
                        PBAElement.PERFORMANCE_STANDARDS,
                        PBAElement.MEASURABLE_OUTCOMES,
                    ),
                ))

        pba_score = (sum(1 for v in pba_found.values() if v) / len(PBAElement)) * 100

        # 2. QASP linkage check
        qasp_mentioned = "qasp" in all_text or "quality assurance surveillance" in all_text
        if not qasp_mentioned:
            counter += 1
            findings.append(Finding(
                finding_id=f"GAP-{counter:03d}",
                category=FindingCategory.QASP_LINKAGE,
                severity=Severity.HIGH,
                title="No QASP reference in SOW",
                detail=(
                    "The SOW does not reference a Quality Assurance Surveillance Plan. "
                    "FAR 46.4 requires surveillance for service contracts. The QASP must "
                    "map to specific PWS requirements."
                ),
                recommended_fix=(
                    "Add QASP reference section to PWS. Each performance requirement "
                    "should have a corresponding surveillance method (100% inspection, "
                    "random sampling, periodic review, or automated monitoring)."
                ),
                authority="FAR 46.401, FAR 37.601(b)(2)",
                protest_relevant=False,
            ))

        # 3. Sections without measurable requirements
        for sec in sections:
            if sec.word_count > 50 and not sec.has_metrics:
                counter += 1
                findings.append(Finding(
                    finding_id=f"GAP-{counter:03d}",
                    category=FindingCategory.MEASURABILITY,
                    severity=Severity.MEDIUM,
                    title=f"No measurable standards in Section {sec.section_id}",
                    detail=(
                        f"Section {sec.section_id} ({sec.heading}) contains {sec.word_count} words "
                        f"but no detectable metrics, SLAs, or quantitative standards. "
                        f"PBA requires measurable performance standards for surveillance."
                    ),
                    location=f"Section {sec.section_id}",
                    recommended_fix=(
                        "Add specific performance metrics: response times, accuracy rates, "
                        "completion deadlines, or quality thresholds that can be measured "
                        "and included in the QASP."
                    ),
                    authority="FAR 37.102(a)(1)",
                ))

        # 4. Deliverables without acceptance criteria
        for dlv in deliverables:
            if not dlv.acceptance_criteria:
                counter += 1
                findings.append(Finding(
                    finding_id=f"GAP-{counter:03d}",
                    category=FindingCategory.ACCEPTANCE_CRITERIA,
                    severity=Severity.MEDIUM,
                    title=f"Deliverable '{dlv.name}' missing acceptance criteria",
                    detail=(
                        f"Deliverable '{dlv.name}' (from Section {dlv.source_section}) "
                        f"has no defined acceptance criteria. Without acceptance criteria, "
                        f"the Government cannot objectively accept or reject the deliverable."
                    ),
                    location=f"Section {dlv.source_section}",
                    recommended_fix=(
                        f"Define acceptance criteria for '{dlv.name}': required content, "
                        f"format (Word/PDF/Excel), review period (e.g., 5 business days), "
                        f"and approval authority (COR/CO)."
                    ),
                    authority="FAR 46.202-1, FAR 46.401",
                ))

        # 5. Requirements without verification method
        reqs_without_verification = [r for r in requirements if not r.verification_method]
        if reqs_without_verification and len(requirements) > 0:
            pct = len(reqs_without_verification) / len(requirements) * 100
            if pct > 30:  # Only flag if >30% lack verification
                counter += 1
                findings.append(Finding(
                    finding_id=f"GAP-{counter:03d}",
                    category=FindingCategory.MEASURABILITY,
                    severity=Severity.MEDIUM,
                    title=f"{len(reqs_without_verification)} requirements lack verification method",
                    detail=(
                        f"{pct:.0f}% of extracted requirements have no verification method "
                        f"(inspection, analysis, demonstration, or test). This makes QASP "
                        f"development difficult."
                    ),
                    recommended_fix=(
                        "For each requirement, define how compliance will be verified: "
                        "inspection (visual check), analysis (data review), demonstration "
                        "(observed execution), or test (formal test procedure)."
                    ),
                    authority="FAR 46.202",
                ))

        # 6. Security requirements completeness
        security_sections = [s for s in sections if s.has_security]
        if security_sections:
            security_text = " ".join(s.content.lower() for s in security_sections)
            missing_security = []
            if "clearance" not in security_text and "suitability" not in security_text:
                missing_security.append("personnel security/suitability requirements")
            if "incident" not in security_text:
                missing_security.append("security incident response procedures")
            if "data" not in security_text and "cui" not in security_text:
                missing_security.append("data handling/classification requirements")

            if missing_security:
                counter += 1
                findings.append(Finding(
                    finding_id=f"GAP-{counter:03d}",
                    category=FindingCategory.SECURITY,
                    severity=Severity.HIGH,
                    title="Incomplete security requirements",
                    detail=(
                        f"SOW references security but is missing: {', '.join(missing_security)}. "
                        f"TSA contracts require HSAR 3052.204-71/72 flow-down."
                    ),
                    recommended_fix=(
                        "Add complete security section covering: personnel suitability, "
                        "data classification/handling, IT security (FISMA/FedRAMP), "
                        "incident response, and physical access requirements."
                    ),
                    authority="HSAR 3052.204-71, HSAR 3052.204-72, IGPM 0403.05",
                ))

        return findings, pba_found, pba_score


class ProtestVulnerabilityScanner:
    """Layer 3: Protest vulnerability scan."""

    def scan(self, sections: list[SOWSection], deliverables: list[DeliverableEntry]) -> list[Finding]:
        findings = []
        counter = 0

        all_text = " ".join(s.content for s in sections)

        # 1. Pattern-based vulnerability detection
        for pv_id, pv_def in PROTEST_PATTERNS.items():
            if not pv_def["patterns"]:
                continue  # Skip cross-section checks (handled separately)

            for pattern in pv_def["patterns"]:
                matches = list(re.finditer(pattern, all_text, re.IGNORECASE))
                if matches:
                    counter += 1
                    snippet = matches[0].group(0)
                    # Find which section
                    location = self._find_section(sections, matches[0].start(), all_text)
                    findings.append(Finding(
                        finding_id=f"PV-{counter:03d}",
                        category=FindingCategory.PROTEST_VULNERABILITY,
                        severity=pv_def["severity"],
                        title=pv_def["name"],
                        detail=pv_def["detail"],
                        location=location,
                        snippet=snippet,
                        recommended_fix=self._pv_fix(pv_id),
                        authority=pv_def["authority"],
                        protest_relevant=True,
                    ))
                    break  # One finding per pattern group

        # 2. Cross-section inconsistency (PV-03)
        inconsistencies = self._detect_inconsistencies(sections)
        for inc in inconsistencies:
            counter += 1
            findings.append(Finding(
                finding_id=f"PV-{counter:03d}",
                category=FindingCategory.PROTEST_VULNERABILITY,
                severity=Severity.HIGH,
                title="Potential cross-section inconsistency",
                detail=inc["detail"],
                location=inc["location"],
                snippet="",
                recommended_fix=(
                    "Consolidate duplicate requirements into a single section with "
                    "cross-references. Ensure consistent language across all references."
                ),
                authority="FAR 15.204-2, GAO case law",
                protest_relevant=True,
            ))

        # 3. Deliverables without acceptance criteria (PV-04)
        missing_acceptance = [d for d in deliverables if not d.acceptance_criteria]
        if missing_acceptance:
            counter += 1
            names = [d.name for d in missing_acceptance[:5]]
            findings.append(Finding(
                finding_id=f"PV-{counter:03d}",
                category=FindingCategory.PROTEST_VULNERABILITY,
                severity=Severity.MEDIUM,
                title=f"{len(missing_acceptance)} deliverables without acceptance criteria",
                detail=(
                    f"Deliverables without clear acceptance criteria: {', '.join(names)}. "
                    f"Undefined acceptance criteria create evaluation subjectivity."
                ),
                recommended_fix=(
                    "For each deliverable, define: required content, format, "
                    "review period, and approval authority."
                ),
                authority="FAR 37.602, FAR 46.2",
                protest_relevant=True,
            ))

        return findings

    def _find_section(self, sections: list[SOWSection], char_pos: int, all_text: str) -> str:
        """Map character position back to section ID."""
        offset = 0
        for sec in sections:
            sec_len = len(sec.content) + 1  # +1 for join space
            if offset + sec_len > char_pos:
                return f"Section {sec.section_id}"
            offset += sec_len
        return "Unknown section"

    def _detect_inconsistencies(self, sections: list[SOWSection]) -> list[dict]:
        """Detect requirements stated differently across sections."""
        inconsistencies = []

        # Extract "shall" requirements per section
        section_reqs = {}
        for sec in sections:
            shall_stmts = re.findall(
                r"(?:contractor|vendor|provider)\s+shall\s+(.{10,60}?)(?:\.|,|;)",
                sec.content,
                re.IGNORECASE,
            )
            section_reqs[sec.section_id] = [s.lower().strip() for s in shall_stmts]

        # Look for similar requirements in different sections (Jaccard on words)
        section_ids = list(section_reqs.keys())
        for i in range(len(section_ids)):
            for j in range(i + 1, len(section_ids)):
                reqs_a = section_reqs[section_ids[i]]
                reqs_b = section_reqs[section_ids[j]]
                for ra in reqs_a:
                    words_a = set(ra.split())
                    if len(words_a) < 4:
                        continue
                    for rb in reqs_b:
                        words_b = set(rb.split())
                        if len(words_b) < 4:
                            continue
                        overlap = words_a & words_b
                        union = words_a | words_b
                        jaccard = len(overlap) / len(union) if union else 0
                        if 0.4 <= jaccard < 0.9:  # Similar but not identical
                            inconsistencies.append({
                                "detail": (
                                    f"Similar requirement in Section {section_ids[i]} and "
                                    f"Section {section_ids[j]} with different wording: "
                                    f"'{ra[:60]}...' vs '{rb[:60]}...'. "
                                    f"Word overlap: {jaccard:.0%}"
                                ),
                                "location": f"Sections {section_ids[i]} and {section_ids[j]}",
                            })
        return inconsistencies[:5]  # Cap at 5

    def _pv_fix(self, pv_id: str) -> str:
        """Recommended fix per protest vulnerability type."""
        fixes = {
            "PV-01": "Replace subjective quality language with measurable criteria tied to QASP.",
            "PV-02": "Remove preference language from SOW. Evaluation preferences belong in Section M only.",
            "PV-03": "Consolidate duplicative requirements with cross-references.",
            "PV-04": "Define format, content, review period, and approval authority for each deliverable.",
            "PV-05": "Use 'brand name or equal' with salient characteristics, or remove proprietary references.",
            "PV-06": "Separate advisory and implementation functions, or add OCI mitigation plan per FAR 9.5.",
            "PV-07": "Replace FTE counts with outcome-based performance standards and SLAs.",
        }
        return fixes.get(pv_id, "Review and revise per applicable FAR citation.")


# ---------------------------------------------------------------------------
# Requirement & Deliverable Extractors
# ---------------------------------------------------------------------------

class RequirementExtractor:
    """Extract structured requirements from SOW sections."""

    CATEGORY_MAP = {
        "technical": ["system", "software", "hardware", "network", "develop", "maintain",
                      "operate", "monitor", "support", "deploy", "configure", "implement"],
        "management": ["manage", "supervise", "coordinate", "plan", "schedule", "organize",
                       "direct", "lead", "staff", "train", "quality"],
        "reporting": ["report", "submit", "document", "brief", "notify", "inform",
                      "communicate", "present", "update"],
        "security": ["security", "clearance", "classified", "CUI", "SSI", "FISMA",
                     "cyber", "access control", "badge", "background"],
        "transition": ["transition", "phase-in", "phase-out", "knowledge transfer",
                       "turnover", "handoff", "incoming", "outgoing"],
    }

    def extract(self, sections: list[SOWSection]) -> list[RequirementEntry]:
        """Extract requirements from parsed SOW sections."""
        requirements = []
        counter = 0

        for sec in sections:
            if not sec.content:
                continue

            # Find "shall" statements — these are binding requirements
            shall_stmts = re.findall(
                r"(?:The\s+)?(?:Contractor|Vendor|Provider)\s+shall\s+(.+?)(?:\.\s|\.$|\n)",
                sec.content,
                re.IGNORECASE,
            )

            for stmt in shall_stmts:
                counter += 1
                stmt = stmt.strip().rstrip(".")

                # Classify category
                category = self._classify(stmt)

                # Check for metric
                metric_match = None
                for mp in METRIC_PATTERNS:
                    metric_match = re.search(mp, stmt, re.IGNORECASE)
                    if metric_match:
                        break

                # Infer verification method
                verification = self._infer_verification(stmt, category)

                # Extract acceptance criteria if present
                acceptance = ""
                acc_match = re.search(
                    r"(?:acceptance|completion|satisfaction)\s+(?:criteria|standard|requirement)[:\s]+(.{10,100})",
                    stmt, re.IGNORECASE
                )
                if acc_match:
                    acceptance = acc_match.group(1).strip()

                requirements.append(RequirementEntry(
                    requirement_id=f"REQ-{counter:03d}",
                    source_section=sec.section_id,
                    text=f"The Contractor shall {stmt}",
                    category=category,
                    priority=self._infer_priority(stmt, sec),
                    verification_method=verification,
                    acceptance_criteria=acceptance,
                    has_metric=metric_match is not None,
                    metric_value=metric_match.group(0) if metric_match else "",
                ))

        return requirements

    def _classify(self, text: str) -> str:
        """Classify requirement by category."""
        text_lower = text.lower()
        scores = {}
        for category, keywords in self.CATEGORY_MAP.items():
            scores[category] = sum(1 for kw in keywords if kw.lower() in text_lower)
        if not any(scores.values()):
            return "general"
        return max(scores, key=scores.get)

    def _infer_verification(self, text: str, category: str) -> str:
        """Infer verification method from requirement content."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["test", "validate", "verify", "certif"]):
            return "test"
        if any(kw in text_lower for kw in ["demonstrate", "show", "present", "brief"]):
            return "demonstration"
        if any(kw in text_lower for kw in ["report", "document", "submit", "review", "data"]):
            return "analysis"
        if category in ("reporting", "management"):
            return "analysis"
        return ""

    def _infer_priority(self, text: str, section: SOWSection) -> str:
        """Infer requirement priority."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["critical", "essential", "mandatory", "must"]):
            return "critical"
        if any(kw in text_lower for kw in ["desirable", "preferred", "optional"]):
            return "desirable"
        return "standard"


class DeliverableExtractor:
    """Extract deliverables with acceptance analysis."""

    FREQUENCY_PATTERNS = {
        "daily": r"\bdail(?:y|ies)\b",
        "weekly": r"\bweekl(?:y|ies)\b",
        "monthly": r"\bmonth(?:ly|lies)\b",
        "quarterly": r"\bquarterl(?:y|ies)\b",
        "annually": r"\bannual(?:ly)?\b",
        "one-time": r"\b(?:one[- ]time|initial|final)\b",
    }

    def extract(self, sections: list[SOWSection]) -> list[DeliverableEntry]:
        """Extract deliverables from parsed sections."""
        deliverables = []
        counter = 0
        seen_names = set()

        for sec in sections:
            if not sec.content:
                continue

            # Pattern 1: "submit/deliver/provide a [name]"
            for pattern in DELIVERABLE_PATTERNS:
                matches = re.finditer(pattern, sec.content, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    name = re.sub(r"\s+", " ", name).strip()

                    # Dedup
                    name_key = name.lower()
                    if name_key in seen_names or len(name) < 5:
                        continue
                    seen_names.add(name_key)

                    counter += 1
                    dlv = DeliverableEntry(
                        deliverable_id=f"DLV-{counter:03d}",
                        name=name,
                        source_section=sec.section_id,
                    )

                    # Detect frequency
                    context = sec.content[max(0, match.start() - 100):match.end() + 100]
                    for freq, fp in self.FREQUENCY_PATTERNS.items():
                        if re.search(fp, context, re.IGNORECASE):
                            dlv.frequency = freq
                            break

                    # Check format specification
                    dlv.format_specified = bool(re.search(
                        r"\b(?:PDF|Word|Excel|PowerPoint|format|template)\b",
                        context, re.IGNORECASE
                    ))

                    # Check for review period
                    review_match = re.search(
                        r"(\d+)\s+(?:business|calendar|working)\s+days?\s+(?:for\s+)?review",
                        context, re.IGNORECASE
                    )
                    if review_match:
                        dlv.review_period = f"{review_match.group(1)} days"

                    # Check for approval authority
                    if re.search(r"\bCOR\b", context):
                        dlv.approval_authority = "COR"
                    elif re.search(r"\bCO\b|contracting\s+officer", context, re.IGNORECASE):
                        dlv.approval_authority = "CO"

                    # Acceptance criteria
                    acc_match = re.search(
                        r"(?:accept|approv|review)\w*\s+(?:criteria|standard|requirement|within)",
                        context, re.IGNORECASE
                    )
                    if acc_match:
                        dlv.acceptance_criteria = context[acc_match.start():acc_match.end() + 60].strip()

                    deliverables.append(dlv)

        return deliverables


# ---------------------------------------------------------------------------
# Scoring Engine
# ---------------------------------------------------------------------------

class SOWScorer:
    """Compute quality, gap, and protest risk scores from findings."""

    # Severity weights for scoring (penalty per finding)
    SEVERITY_PENALTY = {
        Severity.CRITICAL: 15,
        Severity.HIGH: 8,
        Severity.MEDIUM: 3,
        Severity.LOW: 1,
        Severity.INFO: 0,
    }

    def score(self, report: AnalysisReport) -> None:
        """Compute and set all scores on the report. Mutates in place."""
        # Count severities
        for f in report.findings:
            if f.severity == Severity.CRITICAL:
                report.critical_count += 1
            elif f.severity == Severity.HIGH:
                report.high_count += 1
            elif f.severity == Severity.MEDIUM:
                report.medium_count += 1
            elif f.severity == Severity.LOW:
                report.low_count += 1
            else:
                report.info_count += 1

        # Quality score: start at 100, deduct per language finding
        lang_findings = [f for f in report.findings if f.category == FindingCategory.LANGUAGE]
        quality_penalty = sum(self.SEVERITY_PENALTY.get(f.severity, 0) for f in lang_findings)
        report.quality_score = max(0.0, min(100.0, 100.0 - quality_penalty))

        # Gap score: based on PBA coverage + gap findings
        gap_findings = [f for f in report.findings if f.category in (
            FindingCategory.PBA_COMPLIANCE, FindingCategory.QASP_LINKAGE,
            FindingCategory.ACCEPTANCE_CRITERIA, FindingCategory.MEASURABILITY,
            FindingCategory.SECURITY,
        )]
        gap_penalty = sum(self.SEVERITY_PENALTY.get(f.severity, 0) for f in gap_findings)
        # PBA score contributes 50%, gap findings contribute 50%
        report.gap_score = max(0.0, min(100.0,
            report.pba_score * 0.5 + max(0, 100 - gap_penalty) * 0.5
        ))

        # Protest risk score: based on protest-relevant findings
        protest_findings = [f for f in report.findings if f.protest_relevant]
        protest_penalty = sum(self.SEVERITY_PENALTY.get(f.severity, 0) for f in protest_findings)
        report.protest_risk_score = min(100.0, protest_penalty)  # Higher = more risk

        # Overall: weighted composite (higher is better)
        # Quality 30%, Gap 40%, (100 - Protest Risk) 30%
        report.overall_score = (
            report.quality_score * 0.30 +
            report.gap_score * 0.40 +
            (100.0 - report.protest_risk_score) * 0.30
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _pba_fix_suggestion(element: PBAElement) -> str:
    """Specific fix suggestion per missing PBA element."""
    suggestions = {
        PBAElement.PERFORMANCE_STANDARDS: (
            "Add performance standards section with specific SLAs, response times, "
            "accuracy rates, and availability requirements. Example: "
            "'99.5% system availability measured monthly.'"
        ),
        PBAElement.MEASURABLE_OUTCOMES: (
            "Define expected outcomes, not just activities. For each service area, "
            "state what 'success' looks like in measurable terms."
        ),
        PBAElement.QUALITY_ASSURANCE: (
            "Add QASP reference: 'Performance will be assessed in accordance with "
            "the Quality Assurance Surveillance Plan (QASP) at Attachment [X].'"
        ),
        PBAElement.PERFORMANCE_INCENTIVES: (
            "Consider adding positive/negative incentives tied to KPIs. "
            "At minimum, define the consequence of non-performance "
            "(e.g., corrective action report, cure notice progression)."
        ),
        PBAElement.WORK_REQUIREMENTS: (
            "Ensure all required tasks/services are stated as binding 'shall' "
            "requirements with clear scope boundaries."
        ),
        PBAElement.GOVERNMENT_FURNISHED: (
            "Add section listing all government-furnished equipment, information, "
            "facilities, and access that the contractor will receive."
        ),
        PBAElement.DELIVERABLES: (
            "Add deliverables table with: name, description, format, frequency, "
            "due date/trigger, review period, and approval authority."
        ),
        PBAElement.PERIOD_OF_PERFORMANCE: (
            "Add POP section: base period dates, option periods, and total "
            "potential contract duration including all options."
        ),
    }
    return suggestions.get(element, "Add this element per FAR 37.102.")


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

class LegacySOWAnalyzer:
    """
    Orchestrates full SOW analysis pipeline.

    Usage:
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(sow_text)
        result = report.to_dict()
    """

    def __init__(self):
        self.parser = SOWParser()
        self.language_analyzer = LanguageQualityAnalyzer()
        self.gap_analyzer = GapAnalyzer()
        self.protest_scanner = ProtestVulnerabilityScanner()
        self.requirement_extractor = RequirementExtractor()
        self.deliverable_extractor = DeliverableExtractor()
        self.scorer = SOWScorer()

    def analyze(self, sow_text: str) -> AnalysisReport:
        """
        Run full 3-layer analysis on SOW text.

        Args:
            sow_text: Raw SOW text (plain text, may include section headings)

        Returns:
            AnalysisReport with all findings, extracted artifacts, and scores
        """
        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            sow_word_count=len(sow_text.split()) if sow_text else 0,
        )

        if not sow_text or not sow_text.strip():
            report.findings.append(Finding(
                finding_id="ERR-001",
                category=FindingCategory.STRUCTURE,
                severity=Severity.CRITICAL,
                title="Empty SOW text",
                detail="No SOW text provided for analysis.",
                recommended_fix="Provide the full SOW text for analysis.",
            ))
            self.scorer.score(report)
            return report

        # Step 1: Parse into sections
        sections = self.parser.parse(sow_text)
        report.sections = sections
        report.section_count = len(sections)

        # Step 2: Extract requirements and deliverables
        requirements = self.requirement_extractor.extract(sections)
        deliverables = self.deliverable_extractor.extract(sections)
        report.requirements = requirements
        report.deliverables = deliverables

        # Step 3: Layer 1 — Language quality
        language_findings = self.language_analyzer.analyze(sections)
        report.findings.extend(language_findings)

        # Step 4: Layer 2 — Gap analysis (PBA, QASP, acceptance)
        gap_findings, pba_found, pba_score = self.gap_analyzer.analyze(
            sections, requirements, deliverables
        )
        report.findings.extend(gap_findings)
        report.pba_elements_found = pba_found
        report.pba_score = pba_score

        # Step 5: Layer 3 — Protest vulnerability scan
        protest_findings = self.protest_scanner.scan(sections, deliverables)
        report.findings.extend(protest_findings)

        # Step 6: Score everything
        self.scorer.score(report)

        return report

    def analyze_sections(self, sections_dict: list[dict]) -> AnalysisReport:
        """
        Analyze pre-parsed sections (e.g., from a document parser).

        Args:
            sections_dict: List of dicts with keys: section_id, heading, content
        """
        # Convert to SOWSection objects
        sections = []
        for sd in sections_dict:
            sec = SOWSection(
                section_id=sd.get("section_id", ""),
                heading=sd.get("heading", ""),
                content=sd.get("content", ""),
                level=sd.get("section_id", "").count(".") + 1,
                word_count=len(sd.get("content", "").split()),
            )
            content_lower = sec.content.lower()
            sec.has_deliverables = any(kw in content_lower for kw in ["deliver", "submit", "report"])
            sec.has_metrics = bool(re.search(r"\d+\s*%|\bSLA\b|\bKPI\b|\bwithin\s+\d+", sec.content, re.IGNORECASE))
            sec.has_security = any(kw in content_lower for kw in ["clearance", "classified", "cui", "ssi", "fisma"])
            sections.append(sec)

        # Reconstruct text for word count
        full_text = " ".join(s.content for s in sections)

        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            sow_word_count=len(full_text.split()),
            sections=sections,
            section_count=len(sections),
        )

        requirements = self.requirement_extractor.extract(sections)
        deliverables = self.deliverable_extractor.extract(sections)
        report.requirements = requirements
        report.deliverables = deliverables

        language_findings = self.language_analyzer.analyze(sections)
        report.findings.extend(language_findings)

        gap_findings, pba_found, pba_score = self.gap_analyzer.analyze(
            sections, requirements, deliverables
        )
        report.findings.extend(gap_findings)
        report.pba_elements_found = pba_found
        report.pba_score = pba_score

        protest_findings = self.protest_scanner.scan(sections, deliverables)
        report.findings.extend(protest_findings)

        self.scorer.score(report)

        return report
