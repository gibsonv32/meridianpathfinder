"""
Requirements Elicitation Agent — Phase 24
==========================================
Guided intake wizard that walks program offices through structured Q&A
to extract and validate acquisition requirements.

Two entry points:
1. Greenfield: blank-slate guided intake with staged question groups
2. Legacy: import Phase 25 SOW Analyzer output to pre-populate requirements

Integrations:
- PolicyService (Phase 4): 117 Q-code decision tree drives document requirements
- CompletionValidator (Phase 4): gap analysis from derived D-codes
- LegacySOWAnalyzer (Phase 25): pre-populates from existing SOW
- EvalFactorDerivationEngine (Phase 23b): factors derived from requirements
- MarketResearchAgent (Phase 23a): market context informs requirements

Output: RequirementsPackage — structured requirements matrix ready for
        downstream document generation (PWS, IGCE, Section L/M, QASP).

Tier 2 — AI proposes requirements structure; CO/PM accepts/modifies/overrides.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class RequirementCategory(str, Enum):
    """Requirement classification per FAR structure."""
    TECHNICAL = "technical"
    MANAGEMENT = "management"
    REPORTING = "reporting"
    SECURITY = "security"
    TRANSITION = "transition"
    QUALITY = "quality"
    PERSONNEL = "personnel"
    GENERAL = "general"


class RequirementPriority(str, Enum):
    """MoSCoW-style priority for requirements."""
    MUST = "must"           # Hard requirement — proposal fails without it
    SHOULD = "should"       # Important — evaluated but not disqualifying
    COULD = "could"         # Desirable — evaluated if present
    WONT = "wont"           # Out of scope for this procurement


class VerificationMethod(str, Enum):
    """Methods for verifying requirement compliance (FAR 46)."""
    INSPECTION = "inspection"       # Visual/physical check
    ANALYSIS = "analysis"           # Data/document review
    DEMONSTRATION = "demonstration" # Observed execution
    TEST = "test"                   # Formal test procedure


class QuestionGroupID(str, Enum):
    """Staged question groups for guided intake."""
    BASIC_INFO = "basic_info"
    SCOPE_DEFINITION = "scope_definition"
    TECHNICAL_REQUIREMENTS = "technical_requirements"
    MANAGEMENT_REQUIREMENTS = "management_requirements"
    SECURITY_REQUIREMENTS = "security_requirements"
    PERSONNEL_REQUIREMENTS = "personnel_requirements"
    DELIVERABLES = "deliverables"
    PERFORMANCE_STANDARDS = "performance_standards"
    TRANSITION = "transition"
    CONSTRAINTS = "constraints"


class IntakeStatus(str, Enum):
    """Status of the intake process."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    VALIDATED = "validated"


# ---------------------------------------------------------------------------
# Intake Questions
# ---------------------------------------------------------------------------

@dataclass
class IntakeQuestion:
    """Single intake question."""
    question_id: str
    group: QuestionGroupID
    text: str
    help_text: str = ""
    required: bool = True
    field_type: str = "text"       # text, number, boolean, select, multi_select
    options: list[str] = field(default_factory=list)  # For select/multi_select
    default: Any = None
    validation_rule: str = ""      # Regex or callable name
    far_reference: str = ""        # FAR citation for why we ask this
    drives_qcode: str = ""         # Which Q-code node this answer drives


# Staged question groups — ordered for progressive disclosure
INTAKE_QUESTIONS: list[IntakeQuestion] = [
    # ── Group 1: Basic Information ──
    IntakeQuestion(
        "BI-01", QuestionGroupID.BASIC_INFO,
        "What is the title/name of this requirement?",
        help_text="Short descriptive name for the procurement.",
        field_type="text",
    ),
    IntakeQuestion(
        "BI-02", QuestionGroupID.BASIC_INFO,
        "What is the estimated total contract value (including all options)?",
        help_text="Include base + all option years. Drives threshold determinations.",
        field_type="number",
        far_reference="FAR 2.101 (thresholds), FAR 7.105 (AP)",
        drives_qcode="Q004",
    ),
    IntakeQuestion(
        "BI-03", QuestionGroupID.BASIC_INFO,
        "Is this a services requirement, supply/product, or mixed?",
        field_type="select",
        options=["services", "supplies", "mixed"],
        default="services",
        far_reference="FAR Part 37 (services), FAR Part 12 (commercial)",
        drives_qcode="Q006",
    ),
    IntakeQuestion(
        "BI-04", QuestionGroupID.BASIC_INFO,
        "Is this IT-related?",
        help_text="Includes software, hardware, cloud, cybersecurity, data analytics.",
        field_type="boolean",
        default=False,
        far_reference="TSA ITAR (IGPM 0403.05)",
        drives_qcode="Q007",
    ),
    IntakeQuestion(
        "BI-05", QuestionGroupID.BASIC_INFO,
        "What is the primary NAICS code?",
        help_text="6-digit NAICS code. Determines SB size standard.",
        field_type="text",
        validation_rule=r"^\d{6}$",
        far_reference="FAR 19.102",
    ),
    IntakeQuestion(
        "BI-06", QuestionGroupID.BASIC_INFO,
        "What is the anticipated contract type?",
        field_type="select",
        options=["FFP", "T&M", "LH", "CPFF", "CPAF", "CPIF", "IDIQ", "BPA"],
        default="FFP",
        far_reference="FAR Part 16",
        drives_qcode="Q018",
    ),
    IntakeQuestion(
        "BI-07", QuestionGroupID.BASIC_INFO,
        "Is this a new requirement or a recompete/follow-on?",
        field_type="select",
        options=["new", "recompete", "follow_on", "bridge"],
        default="new",
        drives_qcode="Q001",
    ),
    IntakeQuestion(
        "BI-08", QuestionGroupID.BASIC_INFO,
        "What is the intended competition strategy?",
        field_type="select",
        options=["full_and_open", "set_aside", "sole_source", "8a_direct", "gsa_schedule"],
        default="full_and_open",
        far_reference="FAR Part 6",
        drives_qcode="Q005",
    ),

    # ── Group 2: Scope Definition ──
    IntakeQuestion(
        "SD-01", QuestionGroupID.SCOPE_DEFINITION,
        "Describe the overall mission/objective this requirement supports.",
        help_text="What is the program office trying to accomplish?",
        field_type="text",
    ),
    IntakeQuestion(
        "SD-02", QuestionGroupID.SCOPE_DEFINITION,
        "What are the specific services or products required?",
        help_text="List the major functional areas or work streams.",
        field_type="text",
    ),
    IntakeQuestion(
        "SD-03", QuestionGroupID.SCOPE_DEFINITION,
        "Where will work be performed?",
        field_type="select",
        options=["government_site", "contractor_site", "remote", "mixed"],
        default="government_site",
        drives_qcode="Q029",
    ),
    IntakeQuestion(
        "SD-04", QuestionGroupID.SCOPE_DEFINITION,
        "What is the desired period of performance?",
        help_text="Base period + option years (e.g., '1 base + 4 option years').",
        field_type="text",
        far_reference="FAR 17.204",
        drives_qcode="Q023",
    ),
    IntakeQuestion(
        "SD-05", QuestionGroupID.SCOPE_DEFINITION,
        "Is there an existing SOW/PWS from a current or prior contract?",
        help_text="If yes, FedProcure can analyze it to pre-populate requirements.",
        field_type="boolean",
        default=False,
    ),

    # ── Group 3: Technical Requirements ──
    IntakeQuestion(
        "TR-01", QuestionGroupID.TECHNICAL_REQUIREMENTS,
        "What are the key technical outcomes the contractor must achieve?",
        help_text="Focus on WHAT, not HOW. Example: '99.5% system availability' not '25 FTEs'.",
        field_type="text",
    ),
    IntakeQuestion(
        "TR-02", QuestionGroupID.TECHNICAL_REQUIREMENTS,
        "Are there specific systems, technologies, or platforms involved?",
        help_text="List specific systems the contractor must support or integrate with.",
        field_type="text",
    ),
    IntakeQuestion(
        "TR-03", QuestionGroupID.TECHNICAL_REQUIREMENTS,
        "Are there integration requirements with other government systems?",
        field_type="boolean",
        default=False,
    ),
    IntakeQuestion(
        "TR-04", QuestionGroupID.TECHNICAL_REQUIREMENTS,
        "What are the availability/uptime requirements?",
        help_text="e.g., 99.5% availability, 24/7 monitoring, business hours only",
        field_type="text",
        required=False,
    ),

    # ── Group 4: Management Requirements ──
    IntakeQuestion(
        "MR-01", QuestionGroupID.MANAGEMENT_REQUIREMENTS,
        "Are there key personnel requirements?",
        help_text="Positions that require government approval of specific individuals.",
        field_type="boolean",
        default=False,
        far_reference="FAR 37.103",
        drives_qcode="Q042",
    ),
    IntakeQuestion(
        "MR-02", QuestionGroupID.MANAGEMENT_REQUIREMENTS,
        "Is a subcontracting plan required?",
        help_text="Required for contracts >$900K with large business prime.",
        field_type="boolean",
        default=False,
        far_reference="FAR 19.702",
        drives_qcode="Q009",
    ),
    IntakeQuestion(
        "MR-03", QuestionGroupID.MANAGEMENT_REQUIREMENTS,
        "What reporting cadence is required?",
        field_type="select",
        options=["weekly", "monthly", "quarterly", "as_needed"],
        default="monthly",
    ),

    # ── Group 5: Security Requirements ──
    IntakeQuestion(
        "SR-01", QuestionGroupID.SECURITY_REQUIREMENTS,
        "What is the highest clearance level required?",
        field_type="select",
        options=["none", "public_trust", "secret", "top_secret", "ts_sci"],
        default="none",
        far_reference="HSAR 3052.204-71",
        drives_qcode="Q028",
    ),
    IntakeQuestion(
        "SR-02", QuestionGroupID.SECURITY_REQUIREMENTS,
        "Will the contractor handle Sensitive Security Information (SSI)?",
        field_type="boolean",
        default=False,
        far_reference="49 CFR 1520",
        drives_qcode="Q028",
    ),
    IntakeQuestion(
        "SR-03", QuestionGroupID.SECURITY_REQUIREMENTS,
        "Will the contractor handle CUI (Controlled Unclassified Information)?",
        field_type="boolean",
        default=False,
    ),
    IntakeQuestion(
        "SR-04", QuestionGroupID.SECURITY_REQUIREMENTS,
        "Are there FedRAMP or FISMA requirements?",
        field_type="boolean",
        default=False,
        far_reference="FISMA 2014, NIST 800-53",
        drives_qcode="Q030",
    ),
    IntakeQuestion(
        "SR-05", QuestionGroupID.SECURITY_REQUIREMENTS,
        "Will contractor personnel require badge access to TSA facilities?",
        field_type="boolean",
        default=False,
        drives_qcode="Q044",
    ),

    # ── Group 6: Personnel Requirements ──
    IntakeQuestion(
        "PR-01", QuestionGroupID.PERSONNEL_REQUIREMENTS,
        "What labor categories are anticipated?",
        help_text="e.g., Program Manager, Senior Engineer, Help Desk Analyst",
        field_type="text",
        required=False,
    ),
    IntakeQuestion(
        "PR-02", QuestionGroupID.PERSONNEL_REQUIREMENTS,
        "Are there minimum experience/certification requirements?",
        help_text="e.g., PMP, CISSP, 10 years for PM, 5 years for senior",
        field_type="text",
        required=False,
    ),

    # ── Group 7: Deliverables ──
    IntakeQuestion(
        "DL-01", QuestionGroupID.DELIVERABLES,
        "What reports/deliverables are required?",
        help_text="List all expected deliverables with frequency.",
        field_type="text",
    ),
    IntakeQuestion(
        "DL-02", QuestionGroupID.DELIVERABLES,
        "What is the standard review period for deliverables?",
        field_type="select",
        options=["3_business_days", "5_business_days", "10_business_days", "15_business_days"],
        default="5_business_days",
    ),

    # ── Group 8: Performance Standards ──
    IntakeQuestion(
        "PS-01", QuestionGroupID.PERFORMANCE_STANDARDS,
        "What are the critical SLAs or KPIs?",
        help_text="Measurable performance targets. Example: 'Respond to P1 tickets within 15 min'.",
        field_type="text",
    ),
    IntakeQuestion(
        "PS-02", QuestionGroupID.PERFORMANCE_STANDARDS,
        "What are the consequences of non-performance?",
        field_type="select",
        options=["corrective_action_only", "payment_deductions", "liquidated_damages", "award_fee"],
        default="corrective_action_only",
        far_reference="FAR 46.4",
    ),

    # ── Group 9: Transition ──
    IntakeQuestion(
        "TN-01", QuestionGroupID.TRANSITION,
        "Is there an incumbent contractor?",
        field_type="boolean",
        default=False,
    ),
    IntakeQuestion(
        "TN-02", QuestionGroupID.TRANSITION,
        "What is the required transition-in period?",
        field_type="select",
        options=["30_days", "60_days", "90_days", "120_days", "not_applicable"],
        default="30_days",
        required=False,
    ),

    # ── Group 10: Constraints ──
    IntakeQuestion(
        "CN-01", QuestionGroupID.CONSTRAINTS,
        "Is this a commercial item acquisition?",
        field_type="boolean",
        default=False,
        far_reference="FAR Part 12",
        drives_qcode="Q008",
    ),
    IntakeQuestion(
        "CN-02", QuestionGroupID.CONSTRAINTS,
        "Are there organizational conflict of interest concerns?",
        field_type="boolean",
        default=False,
        far_reference="FAR 9.5",
        drives_qcode="Q036",
    ),
    IntakeQuestion(
        "CN-03", QuestionGroupID.CONSTRAINTS,
        "Are there government-furnished equipment/property requirements?",
        field_type="boolean",
        default=False,
        far_reference="FAR Part 45",
        drives_qcode="Q038",
    ),
]

# Index for fast lookup
QUESTION_INDEX: dict[str, IntakeQuestion] = {q.question_id: q for q in INTAKE_QUESTIONS}

# Group ordering
GROUP_ORDER: list[QuestionGroupID] = [
    QuestionGroupID.BASIC_INFO,
    QuestionGroupID.SCOPE_DEFINITION,
    QuestionGroupID.TECHNICAL_REQUIREMENTS,
    QuestionGroupID.MANAGEMENT_REQUIREMENTS,
    QuestionGroupID.SECURITY_REQUIREMENTS,
    QuestionGroupID.PERSONNEL_REQUIREMENTS,
    QuestionGroupID.DELIVERABLES,
    QuestionGroupID.PERFORMANCE_STANDARDS,
    QuestionGroupID.TRANSITION,
    QuestionGroupID.CONSTRAINTS,
]

GROUP_NAMES: dict[QuestionGroupID, str] = {
    QuestionGroupID.BASIC_INFO: "Basic Acquisition Information",
    QuestionGroupID.SCOPE_DEFINITION: "Scope & Objectives",
    QuestionGroupID.TECHNICAL_REQUIREMENTS: "Technical Requirements",
    QuestionGroupID.MANAGEMENT_REQUIREMENTS: "Management & Oversight",
    QuestionGroupID.SECURITY_REQUIREMENTS: "Security Requirements",
    QuestionGroupID.PERSONNEL_REQUIREMENTS: "Personnel & Labor",
    QuestionGroupID.DELIVERABLES: "Deliverables & Reporting",
    QuestionGroupID.PERFORMANCE_STANDARDS: "Performance Standards & SLAs",
    QuestionGroupID.TRANSITION: "Transition Requirements",
    QuestionGroupID.CONSTRAINTS: "Constraints & Special Considerations",
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Requirement:
    """Single elicited requirement."""
    requirement_id: str
    category: RequirementCategory
    title: str
    description: str
    priority: RequirementPriority = RequirementPriority.MUST
    verification_method: VerificationMethod = VerificationMethod.ANALYSIS
    acceptance_criteria: str = ""
    performance_standard: str = ""
    source: str = ""               # Where this requirement came from (question ID, SOW section, etc.)
    far_reference: str = ""
    traceable_to: list[str] = field(default_factory=list)  # Links to PWS sections, CLINs, etc.
    pws_section: str = ""          # Suggested PWS section mapping
    qasp_method: str = ""          # Suggested QASP surveillance method


@dataclass
class DeliverableSpec:
    """Deliverable specification from elicitation."""
    deliverable_id: str
    name: str
    description: str = ""
    frequency: str = "one_time"    # monthly, quarterly, one_time, etc.
    format: str = ""               # PDF, Word, Excel, etc.
    review_period: str = ""
    approval_authority: str = "COR"
    acceptance_criteria: str = ""
    source: str = ""


@dataclass
class PolicyDerivation:
    """Policy engine results derived from intake answers."""
    required_dcodes: list[str] = field(default_factory=list)
    approval_chain: str = ""
    posting_requirement: str = ""
    contract_type_notes: str = ""
    estimated_timeline: str = ""


@dataclass
class ValidationIssue:
    """Issue found during requirements validation."""
    issue_id: str
    severity: str           # critical, high, medium, low
    title: str
    detail: str
    recommended_action: str
    question_id: str = ""   # Which intake question to revisit
    far_reference: str = ""


@dataclass
class RequirementsPackage:
    """Complete output of the elicitation process."""
    # Metadata
    package_id: str = ""
    title: str = ""
    generated_at: str = ""
    status: IntakeStatus = IntakeStatus.NOT_STARTED
    source_provenance: list[str] = field(default_factory=lambda: [
        "FAR 7.105 (Acquisition Planning)", "FAR 10.002 (Market Research)",
        "FAR 11.002 (Requirement Definition)", "FAR 37.102 (PBA)",
    ])
    requires_acceptance: bool = True

    # Intake answers
    answers: dict[str, Any] = field(default_factory=dict)  # question_id → answer

    # Derived acquisition parameters (for PolicyService)
    acquisition_params: dict[str, Any] = field(default_factory=dict)

    # Requirements matrix
    requirements: list[Requirement] = field(default_factory=list)
    deliverables: list[DeliverableSpec] = field(default_factory=list)

    # Policy derivation
    policy: PolicyDerivation = field(default_factory=PolicyDerivation)

    # Validation
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    completeness_pct: float = 0.0

    # Legacy SOW import metadata
    legacy_sow_imported: bool = False
    legacy_sow_score: float = 0.0
    legacy_findings_count: int = 0

    def to_dict(self) -> dict:
        """Full serialization for API response."""
        return {
            "package_id": self.package_id,
            "title": self.title,
            "generated_at": self.generated_at,
            "status": self.status.value,
            "source_provenance": self.source_provenance,
            "requires_acceptance": self.requires_acceptance,
            "answers": self.answers,
            "acquisition_params": self.acquisition_params,
            "requirements": [
                {
                    "requirement_id": r.requirement_id,
                    "category": r.category.value,
                    "title": r.title,
                    "description": r.description,
                    "priority": r.priority.value,
                    "verification_method": r.verification_method.value,
                    "acceptance_criteria": r.acceptance_criteria,
                    "performance_standard": r.performance_standard,
                    "source": r.source,
                    "far_reference": r.far_reference,
                    "pws_section": r.pws_section,
                    "qasp_method": r.qasp_method,
                }
                for r in self.requirements
            ],
            "deliverables": [
                {
                    "deliverable_id": d.deliverable_id,
                    "name": d.name,
                    "description": d.description,
                    "frequency": d.frequency,
                    "format": d.format,
                    "review_period": d.review_period,
                    "approval_authority": d.approval_authority,
                    "acceptance_criteria": d.acceptance_criteria,
                    "source": d.source,
                }
                for d in self.deliverables
            ],
            "policy": {
                "required_dcodes": self.policy.required_dcodes,
                "approval_chain": self.policy.approval_chain,
                "posting_requirement": self.policy.posting_requirement,
                "contract_type_notes": self.policy.contract_type_notes,
                "estimated_timeline": self.policy.estimated_timeline,
            },
            "validation_issues": [
                {
                    "issue_id": v.issue_id,
                    "severity": v.severity,
                    "title": v.title,
                    "detail": v.detail,
                    "recommended_action": v.recommended_action,
                    "question_id": v.question_id,
                    "far_reference": v.far_reference,
                }
                for v in self.validation_issues
            ],
            "completeness_pct": round(self.completeness_pct, 1),
            "legacy_sow_imported": self.legacy_sow_imported,
            "legacy_sow_score": round(self.legacy_sow_score, 1),
            "legacy_findings_count": self.legacy_findings_count,
        }


# ---------------------------------------------------------------------------
# Intake Engine
# ---------------------------------------------------------------------------

class IntakeEngine:
    """Manages the staged intake question flow."""

    def get_questions_for_group(self, group: QuestionGroupID) -> list[IntakeQuestion]:
        """Get all questions for a specific group."""
        return [q for q in INTAKE_QUESTIONS if q.group == group]

    def get_all_groups(self) -> list[dict]:
        """Get group metadata in order."""
        return [
            {
                "group_id": g.value,
                "name": GROUP_NAMES.get(g, g.value),
                "question_count": len(self.get_questions_for_group(g)),
                "order": i,
            }
            for i, g in enumerate(GROUP_ORDER)
        ]

    def get_next_group(self, completed_groups: list[str]) -> Optional[QuestionGroupID]:
        """Get the next incomplete group."""
        completed_set = set(completed_groups)
        for g in GROUP_ORDER:
            if g.value not in completed_set:
                return g
        return None

    def validate_answer(self, question_id: str, answer: Any) -> tuple[bool, str]:
        """Validate a single answer against its question rules."""
        q = QUESTION_INDEX.get(question_id)
        if not q:
            return False, f"Unknown question: {question_id}"

        # Required check
        if q.required and (answer is None or answer == ""):
            return False, f"'{q.text}' is required."

        # Type validation
        if q.field_type == "number" and answer is not None:
            try:
                float(answer)
            except (ValueError, TypeError):
                return False, f"'{q.text}' requires a numeric value."

        if q.field_type == "boolean" and answer is not None:
            if not isinstance(answer, bool):
                return False, f"'{q.text}' requires true/false."

        if q.field_type == "select" and answer is not None:
            if answer not in q.options:
                return False, f"'{q.text}' must be one of: {', '.join(q.options)}"

        # Regex validation
        if q.validation_rule and answer:
            if not re.match(q.validation_rule, str(answer)):
                return False, f"'{q.text}' does not match expected format."

        return True, ""

    def compute_group_completeness(
        self, group: QuestionGroupID, answers: dict[str, Any]
    ) -> float:
        """Compute completeness percentage for a group."""
        questions = self.get_questions_for_group(group)
        if not questions:
            return 100.0
        required = [q for q in questions if q.required]
        if not required:
            return 100.0
        answered = sum(
            1 for q in required
            if q.question_id in answers and answers[q.question_id] is not None
            and answers[q.question_id] != ""
        )
        return (answered / len(required)) * 100.0

    def compute_overall_completeness(self, answers: dict[str, Any]) -> float:
        """Compute overall completeness across all groups."""
        total_required = sum(1 for q in INTAKE_QUESTIONS if q.required)
        if total_required == 0:
            return 100.0
        answered = sum(
            1 for q in INTAKE_QUESTIONS
            if q.required and q.question_id in answers
            and answers[q.question_id] is not None
            and answers[q.question_id] != ""
        )
        return (answered / total_required) * 100.0


# ---------------------------------------------------------------------------
# Parameter Derivation
# ---------------------------------------------------------------------------

class ParameterDeriver:
    """Derives PolicyService-compatible acquisition params from intake answers."""

    def derive(self, answers: dict[str, Any]) -> dict[str, Any]:
        """Convert intake answers to acquisition parameters."""
        params = {}

        # Value
        value = answers.get("BI-02")
        if value is not None:
            try:
                params["value"] = float(value)
            except (ValueError, TypeError):
                params["value"] = 0

        # Services
        svc = answers.get("BI-03", "services")
        params["services"] = svc in ("services", "mixed")

        # IT
        params["it_related"] = bool(answers.get("BI-04", False))

        # Sole source
        competition = answers.get("BI-08", "full_and_open")
        params["sole_source"] = competition == "sole_source"

        # Commercial
        params["commercial_item"] = bool(answers.get("CN-01", False))

        # Vendor on site
        location = answers.get("SD-03", "government_site")
        params["vendor_on_site"] = location in ("government_site", "mixed")

        # NAICS
        naics = answers.get("BI-05")
        if naics:
            params["naics_code"] = str(naics)

        # Contract type
        contract_type = answers.get("BI-06", "FFP")
        params["contract_type"] = contract_type

        # Competition type
        params["competition_type"] = competition

        # Sub-agency (default TSA)
        params["sub_agency"] = "TSA"

        # Security
        clearance = answers.get("SR-01", "none")
        params["classified"] = clearance in ("secret", "top_secret", "ts_sci")
        params["on_site"] = location in ("government_site", "mixed")

        # Options
        pop = answers.get("SD-04", "")
        params["has_options"] = "option" in str(pop).lower()

        # OCI
        params["has_oci_concern"] = bool(answers.get("CN-02", False))

        # Key personnel
        params["has_key_personnel"] = bool(answers.get("MR-01", False))

        # GFE
        params["has_gfe"] = bool(answers.get("CN-03", False))

        # SSI
        params["handles_ssi"] = bool(answers.get("SR-02", False))

        # CUI
        params["has_cui"] = bool(answers.get("SR-03", False))

        # FedRAMP
        params["requires_fedramp"] = bool(answers.get("SR-04", False))

        # Badge
        params["requires_badge"] = bool(answers.get("SR-05", False))

        return params


# ---------------------------------------------------------------------------
# Requirements Generator
# ---------------------------------------------------------------------------

class RequirementsGenerator:
    """Generates structured requirements from intake answers."""

    def generate(self, answers: dict[str, Any], params: dict[str, Any]) -> list[Requirement]:
        """Generate requirements from intake answers."""
        requirements = []
        counter = 0

        # Technical requirements from TR answers
        tr_outcomes = answers.get("TR-01", "")
        if tr_outcomes:
            for outcome in self._split_outcomes(tr_outcomes):
                counter += 1
                requirements.append(Requirement(
                    requirement_id=f"REQ-{counter:03d}",
                    category=RequirementCategory.TECHNICAL,
                    title=f"Technical Outcome: {outcome[:60]}",
                    description=f"The Contractor shall {outcome}.",
                    priority=RequirementPriority.MUST,
                    verification_method=VerificationMethod.DEMONSTRATION,
                    source="TR-01",
                    pws_section="3.x",
                    qasp_method="periodic_assessment",
                ))

        # System/technology requirements
        tr_systems = answers.get("TR-02", "")
        if tr_systems:
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.TECHNICAL,
                title="System Support Requirements",
                description=f"The Contractor shall support and maintain: {tr_systems}.",
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.DEMONSTRATION,
                source="TR-02",
                pws_section="3.x",
                qasp_method="automated_monitoring",
            ))

        # Integration requirements
        if answers.get("TR-03"):
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.TECHNICAL,
                title="System Integration",
                description=(
                    "The Contractor shall integrate with existing government systems "
                    "as specified in the interface requirements."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.TEST,
                source="TR-03",
                pws_section="3.x",
                qasp_method="periodic_assessment",
            ))

        # Availability/uptime
        tr_availability = answers.get("TR-04", "")
        if tr_availability:
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.TECHNICAL,
                title="System Availability",
                description=f"The Contractor shall maintain {tr_availability}.",
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                performance_standard=tr_availability,
                source="TR-04",
                pws_section="3.x",
                qasp_method="automated_monitoring",
            ))

        # Key personnel
        if answers.get("MR-01"):
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.PERSONNEL,
                title="Key Personnel",
                description=(
                    "The Contractor shall designate key personnel subject to "
                    "Government approval. Key personnel shall not be replaced "
                    "without CO written approval."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="MR-01",
                far_reference="FAR 37.103",
                pws_section="5.x",
                qasp_method="periodic_assessment",
            ))

        # Reporting
        cadence = answers.get("MR-03", "monthly")
        counter += 1
        requirements.append(Requirement(
            requirement_id=f"REQ-{counter:03d}",
            category=RequirementCategory.REPORTING,
            title=f"{cadence.title()} Status Reporting",
            description=(
                f"The Contractor shall submit {cadence} status reports to the COR "
                f"in accordance with the deliverables schedule."
            ),
            priority=RequirementPriority.MUST,
            verification_method=VerificationMethod.ANALYSIS,
            source="MR-03",
            pws_section="4.x",
            qasp_method="100_percent_inspection",
        ))

        # Security requirements
        clearance = answers.get("SR-01", "none")
        if clearance != "none":
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.SECURITY,
                title=f"Personnel Security — {clearance.replace('_', ' ').title()}",
                description=(
                    f"All contractor personnel shall maintain a minimum "
                    f"{clearance.replace('_', ' ')} clearance level."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="SR-01",
                far_reference="HSAR 3052.204-71",
                pws_section="6.x",
                qasp_method="100_percent_inspection",
            ))

        if answers.get("SR-02"):
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.SECURITY,
                title="SSI Handling",
                description=(
                    "The Contractor shall comply with 49 CFR 1520 for all "
                    "Sensitive Security Information. SSI training shall be "
                    "completed within 30 calendar days of award."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="SR-02",
                far_reference="49 CFR 1520",
                pws_section="6.x",
                qasp_method="100_percent_inspection",
            ))

        if answers.get("SR-04"):
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.SECURITY,
                title="FISMA/FedRAMP Compliance",
                description=(
                    "The Contractor shall maintain compliance with FISMA and "
                    "FedRAMP requirements. Systems shall maintain a current ATO."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="SR-04",
                far_reference="FISMA 2014, NIST 800-53",
                pws_section="6.x",
                qasp_method="periodic_assessment",
            ))

        # Performance standards
        slas = answers.get("PS-01", "")
        if slas:
            for sla in self._split_outcomes(slas):
                counter += 1
                requirements.append(Requirement(
                    requirement_id=f"REQ-{counter:03d}",
                    category=RequirementCategory.QUALITY,
                    title=f"Performance Standard: {sla[:60]}",
                    description=f"The Contractor shall achieve: {sla}.",
                    priority=RequirementPriority.MUST,
                    verification_method=VerificationMethod.ANALYSIS,
                    performance_standard=sla,
                    source="PS-01",
                    pws_section="3.x",
                    qasp_method="automated_monitoring",
                ))

        # Transition
        if answers.get("TN-01"):
            transition_period = answers.get("TN-02", "30_days").replace("_", " ")
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.TRANSITION,
                title="Transition-In Plan",
                description=(
                    f"The Contractor shall provide a transition-in plan within "
                    f"{transition_period} of award. The plan shall address knowledge "
                    f"transfer, staffing ramp-up, and assumption of responsibilities."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="TN-01",
                pws_section="7.x",
                qasp_method="periodic_assessment",
            ))
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.TRANSITION,
                title="Transition-Out Support",
                description=(
                    "The Contractor shall support transition-out for up to 90 "
                    "calendar days at contract end, including knowledge transfer "
                    "and documentation of all processes and procedures."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="TN-01",
                pws_section="7.x",
                qasp_method="periodic_assessment",
            ))

        # Quality Control (always generated for services)
        if params.get("services"):
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.QUALITY,
                title="Quality Control Plan",
                description=(
                    "The Contractor shall maintain a Quality Control Plan (QCP) "
                    "and submit it to the COR within 15 calendar days of award."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.ANALYSIS,
                source="auto",
                far_reference="FAR 46.2",
                pws_section="5.x",
                qasp_method="periodic_assessment",
            ))

        # GFE
        if answers.get("CN-03"):
            counter += 1
            requirements.append(Requirement(
                requirement_id=f"REQ-{counter:03d}",
                category=RequirementCategory.GENERAL,
                title="Government Furnished Equipment/Property",
                description=(
                    "The Government will furnish equipment and property as "
                    "specified in Attachment [X]. The Contractor shall maintain "
                    "and account for all GFE/GFP per FAR Part 45."
                ),
                priority=RequirementPriority.MUST,
                verification_method=VerificationMethod.INSPECTION,
                source="CN-03",
                far_reference="FAR Part 45",
                pws_section="8.x",
                qasp_method="periodic_assessment",
            ))

        return requirements

    def generate_deliverables(self, answers: dict[str, Any]) -> list[DeliverableSpec]:
        """Generate deliverable specs from answers."""
        deliverables = []
        counter = 0

        review_period = answers.get("DL-02", "5_business_days").replace("_", " ")

        # Status reports
        cadence = answers.get("MR-03", "monthly")
        counter += 1
        deliverables.append(DeliverableSpec(
            deliverable_id=f"DLV-{counter:03d}",
            name=f"{cadence.title()} Status Report",
            description=f"Comprehensive {cadence} performance and activity report.",
            frequency=cadence,
            format="PDF",
            review_period=review_period,
            approval_authority="COR",
            acceptance_criteria=(
                f"Report covers all required performance metrics, activities completed, "
                f"issues/risks, and upcoming milestones for the {cadence} period."
            ),
            source="MR-03",
        ))

        # Quality Control Plan
        counter += 1
        deliverables.append(DeliverableSpec(
            deliverable_id=f"DLV-{counter:03d}",
            name="Quality Control Plan",
            description="Contractor's internal quality control methodology and procedures.",
            frequency="one_time",
            format="Word",
            review_period="15 business days",
            approval_authority="COR",
            acceptance_criteria="Plan addresses all performance areas in the PWS and QASP.",
            source="auto",
        ))

        # Transition plan (if incumbent)
        if answers.get("TN-01"):
            counter += 1
            transition_period = answers.get("TN-02", "30_days").replace("_", " ")
            deliverables.append(DeliverableSpec(
                deliverable_id=f"DLV-{counter:03d}",
                name="Transition-In Plan",
                description="Detailed plan for assuming responsibilities from incumbent.",
                frequency="one_time",
                format="Word",
                review_period=transition_period,
                approval_authority="COR",
                acceptance_criteria=(
                    "Plan addresses knowledge transfer, staffing ramp-up, "
                    "key milestones, and risk mitigation."
                ),
                source="TN-01",
            ))

        # Custom deliverables from DL-01
        dl_text = answers.get("DL-01", "")
        if dl_text:
            for name in self._parse_deliverable_names(dl_text):
                counter += 1
                deliverables.append(DeliverableSpec(
                    deliverable_id=f"DLV-{counter:03d}",
                    name=name,
                    description=f"As specified by program office: {name}",
                    frequency=self._infer_frequency(name),
                    review_period=review_period,
                    approval_authority="COR",
                    source="DL-01",
                ))

        return deliverables

    def _split_outcomes(self, text: str) -> list[str]:
        """Split comma/semicolon/newline-separated outcome text into list."""
        # Split on common delimiters
        parts = re.split(r"[;\n]|,\s+(?=[A-Z])", text)
        results = []
        for p in parts:
            p = p.strip().strip("-•*").strip()
            if p and len(p) > 5:
                # Lowercase first letter if needed for "shall" sentence
                if p[0].isupper() and not p[:3].isupper():
                    p = p[0].lower() + p[1:]
                results.append(p)
        return results

    def _parse_deliverable_names(self, text: str) -> list[str]:
        """Extract deliverable names from free-text answer."""
        parts = re.split(r"[;\n,]", text)
        names = []
        for p in parts:
            p = p.strip().strip("-•*").strip()
            if p and len(p) > 3:
                names.append(p)
        return names[:10]  # Cap at 10

    def _infer_frequency(self, name: str) -> str:
        """Infer frequency from deliverable name."""
        name_lower = name.lower()
        if "daily" in name_lower:
            return "daily"
        if "weekly" in name_lower:
            return "weekly"
        if "monthly" in name_lower:
            return "monthly"
        if "quarterly" in name_lower:
            return "quarterly"
        if "annual" in name_lower:
            return "annually"
        return "as_needed"


# ---------------------------------------------------------------------------
# Requirements Validator
# ---------------------------------------------------------------------------

class RequirementsValidator:
    """Validates elicited requirements for completeness and consistency."""

    def validate(self, package: RequirementsPackage) -> list[ValidationIssue]:
        """Run all validation checks."""
        issues = []
        counter = 0

        # 1. Value-driven validations
        value = package.acquisition_params.get("value", 0)

        if value >= 20_000_000 and not package.answers.get("MR-01"):
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="medium",
                title="Key personnel not specified for $20M+ acquisition",
                detail=(
                    f"Acquisitions at ${value:,.0f} typically require designated key personnel. "
                    f"Consider requiring at minimum a Program Manager as key personnel."
                ),
                recommended_action="Revisit MR-01 and designate key personnel positions.",
                question_id="MR-01",
            ))

        if value >= 5_500_000 and package.answers.get("BI-06") in ("T&M", "LH"):
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="high",
                title="T&M/LH contract type on high-value acquisition",
                detail=(
                    "T&M and LH contract types place cost risk on the Government. "
                    "FAR 16.601(d) requires a D&F for T&M/LH above SAT."
                ),
                recommended_action="Consider FFP or CPFF instead. If T&M is justified, prepare D&F.",
                question_id="BI-06",
                far_reference="FAR 16.601(d)",
            ))

        # 2. PBA validation
        has_slas = bool(package.answers.get("PS-01"))
        if package.acquisition_params.get("services") and not has_slas:
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="high",
                title="Services requirement without performance standards",
                detail=(
                    "FAR 37.102 requires performance-based acquisition for services. "
                    "No SLAs or KPIs were specified."
                ),
                recommended_action="Define measurable performance standards in PS-01.",
                question_id="PS-01",
                far_reference="FAR 37.102",
            ))

        # 3. Security validation
        clearance = package.answers.get("SR-01", "none")
        if clearance != "none" and not package.answers.get("SR-05"):
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="low",
                title="Clearance required but badge access not specified",
                detail=(
                    "Personnel clearance is required but TSA badge access was not "
                    "specified. Cleared personnel typically need facility access."
                ),
                recommended_action="Confirm whether badge access is needed for cleared personnel.",
                question_id="SR-05",
            ))

        it_related = package.acquisition_params.get("it_related", False)
        if it_related and not package.answers.get("SR-04"):
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="high",
                title="IT requirement without FISMA/FedRAMP specification",
                detail=(
                    "IT acquisitions require FISMA compliance. FedRAMP is required "
                    "for cloud services. Neither was specified."
                ),
                recommended_action="Specify FISMA and/or FedRAMP requirements in SR-04.",
                question_id="SR-04",
                far_reference="FISMA 2014",
            ))

        # 4. Scope validation
        if not package.answers.get("SD-02"):
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="critical",
                title="No specific services/products defined",
                detail="The scope of work has not been defined. This is required for any acquisition.",
                recommended_action="Define specific services or products in SD-02.",
                question_id="SD-02",
            ))

        # 5. Competition validation
        competition = package.answers.get("BI-08", "full_and_open")
        if competition == "sole_source" and value >= 250_000:
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="high",
                title="Sole source above $250K requires J&A",
                detail=(
                    f"Sole source at ${value:,.0f} requires a Justification & Approval "
                    f"per FAR 6.303/6.304."
                ),
                recommended_action="Prepare J&A with specific FAR 6.302 authority.",
                question_id="BI-08",
                far_reference="FAR 6.303, 6.304",
            ))

        # 6. Requirement quality — no requirements generated
        if not package.requirements:
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="critical",
                title="No requirements generated",
                detail="The intake produced no requirements. Technical outcomes must be defined.",
                recommended_action="Provide technical outcomes in TR-01 and SLAs in PS-01.",
                question_id="TR-01",
            ))

        # 7. Deliverables without acceptance criteria
        missing_acceptance = [d for d in package.deliverables if not d.acceptance_criteria]
        if missing_acceptance:
            counter += 1
            names = [d.name for d in missing_acceptance[:3]]
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="medium",
                title=f"{len(missing_acceptance)} deliverables without acceptance criteria",
                detail=f"Deliverables need acceptance criteria: {', '.join(names)}.",
                recommended_action="Define acceptance criteria for all deliverables.",
                question_id="DL-01",
                far_reference="FAR 46.2",
            ))

        # 8. Transition validation
        is_recompete = package.answers.get("BI-07") in ("recompete", "follow_on")
        if is_recompete and not package.answers.get("TN-01"):
            counter += 1
            issues.append(ValidationIssue(
                issue_id=f"VAL-{counter:03d}",
                severity="medium",
                title="Recompete without incumbent transition planning",
                detail="This is a recompete but no incumbent transition was specified.",
                recommended_action="Indicate incumbent contractor in TN-01 for transition planning.",
                question_id="TN-01",
            ))

        return issues


# ---------------------------------------------------------------------------
# Legacy SOW Importer
# ---------------------------------------------------------------------------

class LegacySOWImporter:
    """Import Phase 25 SOW Analyzer output to pre-populate requirements."""

    def import_from_analysis(
        self,
        analysis_report: dict,
        existing_answers: dict[str, Any],
    ) -> tuple[dict[str, Any], list[Requirement], list[DeliverableSpec]]:
        """
        Import SOW analysis results into the elicitation flow.

        Args:
            analysis_report: Output from LegacySOWAnalyzer.to_dict()
            existing_answers: Current intake answers (preserved, not overwritten)

        Returns:
            (updated_answers, imported_requirements, imported_deliverables)
        """
        answers = dict(existing_answers)  # Don't mutate original
        requirements = []
        deliverables = []

        # Import extracted requirements
        for i, req in enumerate(analysis_report.get("requirements", [])):
            requirements.append(Requirement(
                requirement_id=f"SOW-REQ-{i+1:03d}",
                category=self._map_category(req.get("category", "general")),
                title=req.get("text", "")[:60],
                description=req.get("text", ""),
                priority=self._map_priority(req.get("priority", "standard")),
                verification_method=self._map_verification(req.get("verification_method", "")),
                acceptance_criteria=req.get("acceptance_criteria", ""),
                performance_standard=req.get("metric_value", ""),
                source=f"legacy_sow:{req.get('source_section', '')}",
            ))

        # Import extracted deliverables
        for i, dlv in enumerate(analysis_report.get("deliverables", [])):
            deliverables.append(DeliverableSpec(
                deliverable_id=f"SOW-DLV-{i+1:03d}",
                name=dlv.get("name", ""),
                frequency=dlv.get("frequency", ""),
                format="PDF" if dlv.get("format_specified") else "",
                review_period=dlv.get("review_period", ""),
                approval_authority=dlv.get("approval_authority", "COR"),
                acceptance_criteria=dlv.get("acceptance_criteria", ""),
                source=f"legacy_sow:{dlv.get('source_section', '')}",
            ))

        # Pre-populate answers from PBA elements (don't overwrite existing)
        pba = analysis_report.get("pba_elements", {})

        if "BI-03" not in answers:
            answers["BI-03"] = "services"  # SOWs are typically services

        if pba.get("period_of_performance") and "SD-04" not in answers:
            answers["SD-04"] = "See legacy SOW"

        if pba.get("quality_assurance") and "PS-01" not in answers:
            # Extract from requirements with metrics
            metrics = [r.get("metric_value", "") for r in analysis_report.get("requirements", [])
                       if r.get("has_metric")]
            if metrics:
                answers["PS-01"] = "; ".join(m for m in metrics if m)

        # Security inference
        sections = analysis_report.get("sections", [])
        has_security = any(s.get("has_security") for s in sections)
        if has_security and "SR-01" not in answers:
            answers["SR-01"] = "public_trust"  # Conservative default

        return answers, requirements, deliverables

    def _map_category(self, cat: str) -> RequirementCategory:
        mapping = {
            "technical": RequirementCategory.TECHNICAL,
            "management": RequirementCategory.MANAGEMENT,
            "reporting": RequirementCategory.REPORTING,
            "security": RequirementCategory.SECURITY,
            "transition": RequirementCategory.TRANSITION,
        }
        return mapping.get(cat, RequirementCategory.GENERAL)

    def _map_priority(self, pri: str) -> RequirementPriority:
        mapping = {
            "critical": RequirementPriority.MUST,
            "standard": RequirementPriority.SHOULD,
            "desirable": RequirementPriority.COULD,
        }
        return mapping.get(pri, RequirementPriority.SHOULD)

    def _map_verification(self, method: str) -> VerificationMethod:
        mapping = {
            "test": VerificationMethod.TEST,
            "demonstration": VerificationMethod.DEMONSTRATION,
            "analysis": VerificationMethod.ANALYSIS,
            "inspection": VerificationMethod.INSPECTION,
        }
        return mapping.get(method, VerificationMethod.ANALYSIS)


# ---------------------------------------------------------------------------
# Approval Chain Deriver
# ---------------------------------------------------------------------------

# TSA C&P thresholds (Feb 2026)
APPROVAL_CHAINS = [
    (500_000, "CO approves"),
    (5_000_000, "CS → CO → BC approves"),
    (20_000_000, "CS → CO → BC → DD approves"),
    (50_000_000, "CS → CO → BC → DD → DAA approves"),
    (float("inf"), "CS → CO → BC → DD → DAA → HCA approves"),
]

SSA_APPOINTMENTS = [
    (2_500_000, "CO is SSA"),
    (5_000_000, "BC is SSA"),
    (20_000_000, "DD is SSA"),
    (50_000_000, "DAA is SSA"),
    (float("inf"), "HCA is SSA"),
]


def derive_approval_chain(value: float) -> str:
    """Derive BCM approval chain from value."""
    for threshold, chain in APPROVAL_CHAINS:
        if value < threshold:
            return chain
    return APPROVAL_CHAINS[-1][1]


def derive_ssa(value: float) -> str:
    """Derive SSA appointment from value."""
    for threshold, ssa in SSA_APPOINTMENTS:
        if value < threshold:
            return ssa
    return SSA_APPOINTMENTS[-1][1]


def derive_posting_requirement(value: float, sole_source: bool) -> str:
    """Derive FAR 5.203 posting requirement."""
    if value <= 15_000:
        return "No posting required (micro-purchase)"
    if sole_source:
        return "Award notice within 30 days of award per FAR 5.301"
    if value <= 350_000:
        return "SAM.gov, reasonable response time"
    return "SAM.gov, minimum 30-day response period per FAR 5.203(a)"


def derive_estimated_timeline(value: float, sole_source: bool) -> str:
    """Rough timeline estimate based on value and competition."""
    if value <= 350_000:
        return "6-12 weeks (simplified acquisition)"
    if sole_source:
        return "8-16 weeks (sole source with J&A)"
    if value <= 5_500_000:
        return "4-6 months (competitive below AP threshold)"
    if value <= 50_000_000:
        return "6-12 months (competitive with AP)"
    return "12-18 months (major acquisition)"


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

class RequirementsElicitationAgent:
    """
    Orchestrates the full requirements elicitation process.

    Usage (greenfield):
        agent = RequirementsElicitationAgent()
        groups = agent.get_intake_groups()
        # ... user answers questions group by group ...
        package = agent.process_answers(answers)

    Usage (legacy SOW):
        agent = RequirementsElicitationAgent()
        sow_report = LegacySOWAnalyzer().analyze(sow_text).to_dict()
        package = agent.import_legacy_sow(sow_report)
        # ... user reviews/modifies imported requirements ...
        package = agent.process_answers(package.answers)
    """

    def __init__(self):
        self.intake = IntakeEngine()
        self.deriver = ParameterDeriver()
        self.generator = RequirementsGenerator()
        self.validator = RequirementsValidator()
        self.importer = LegacySOWImporter()

    def get_intake_groups(self) -> list[dict]:
        """Get all intake question groups with metadata."""
        return self.intake.get_all_groups()

    def get_questions(self, group: QuestionGroupID) -> list[dict]:
        """Get questions for a specific group."""
        questions = self.intake.get_questions_for_group(group)
        return [
            {
                "question_id": q.question_id,
                "group": q.group.value,
                "text": q.text,
                "help_text": q.help_text,
                "required": q.required,
                "field_type": q.field_type,
                "options": q.options,
                "default": q.default,
                "far_reference": q.far_reference,
            }
            for q in questions
        ]

    def get_next_group(self, completed: list[str]) -> Optional[dict]:
        """Get next incomplete group."""
        group = self.intake.get_next_group(completed)
        if group is None:
            return None
        questions = self.get_questions(group)
        return {
            "group_id": group.value,
            "name": GROUP_NAMES.get(group, group.value),
            "questions": questions,
        }

    def process_answers(self, answers: dict[str, Any]) -> RequirementsPackage:
        """
        Process all intake answers into a RequirementsPackage.

        This is the main entry point after the user has answered questions.
        """
        package = RequirementsPackage(
            generated_at=datetime.now(timezone.utc).isoformat(),
            status=IntakeStatus.IN_PROGRESS,
            answers=answers,
            title=answers.get("BI-01", "Untitled Requirement"),
        )

        # Step 1: Derive acquisition parameters
        package.acquisition_params = self.deriver.derive(answers)

        # Step 2: Generate requirements from answers
        package.requirements = self.generator.generate(answers, package.acquisition_params)

        # Step 3: Generate deliverables
        package.deliverables = self.generator.generate_deliverables(answers)

        # Step 4: Derive policy implications
        value = package.acquisition_params.get("value", 0)
        sole_source = package.acquisition_params.get("sole_source", False)

        package.policy = PolicyDerivation(
            approval_chain=derive_approval_chain(value),
            posting_requirement=derive_posting_requirement(value, sole_source),
            estimated_timeline=derive_estimated_timeline(value, sole_source),
        )

        # Contract type notes
        ct = answers.get("BI-06", "FFP")
        if ct in ("T&M", "LH"):
            package.policy.contract_type_notes = (
                "T&M/LH requires D&F per FAR 16.601(d). "
                "Hourly rate ceiling and maximum obligated amount required."
            )
        elif ct == "CPAF":
            package.policy.contract_type_notes = (
                "CPAF requires approved award fee plan with objective criteria. "
                "FAR 16.401(e)(3) — cannot use cost-plus-a-percentage-of-cost."
            )

        # Step 5: Validate
        package.validation_issues = self.validator.validate(package)

        # Step 6: Completeness
        package.completeness_pct = self.intake.compute_overall_completeness(answers)

        # Status determination
        critical_issues = [v for v in package.validation_issues if v.severity == "critical"]
        if critical_issues:
            package.status = IntakeStatus.IN_PROGRESS
        elif package.completeness_pct >= 80:
            package.status = IntakeStatus.COMPLETE
        else:
            package.status = IntakeStatus.IN_PROGRESS

        return package

    def import_legacy_sow(
        self,
        analysis_report: dict,
        existing_answers: Optional[dict] = None,
    ) -> RequirementsPackage:
        """
        Import legacy SOW analysis and process into a RequirementsPackage.

        Args:
            analysis_report: Output from LegacySOWAnalyzer().analyze().to_dict()
            existing_answers: Optional pre-existing answers (won't be overwritten)
        """
        existing = existing_answers or {}

        # Import SOW findings
        answers, sow_reqs, sow_deliverables = self.importer.import_from_analysis(
            analysis_report, existing
        )

        # Process as normal
        package = self.process_answers(answers)

        # Merge SOW-extracted requirements (prepend, they're the source truth)
        package.requirements = sow_reqs + package.requirements

        # Merge SOW-extracted deliverables (prepend)
        existing_names = {d.name.lower() for d in package.deliverables}
        for d in sow_deliverables:
            if d.name.lower() not in existing_names:
                package.deliverables.insert(0, d)
                existing_names.add(d.name.lower())

        # Mark as legacy import
        package.legacy_sow_imported = True
        package.legacy_sow_score = analysis_report.get("scores", {}).get("overall", 0)
        package.legacy_findings_count = sum(
            analysis_report.get("severity_counts", {}).values()
        )

        return package
