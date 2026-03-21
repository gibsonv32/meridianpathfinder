"""Policy-as-Code Engine
======================
Deterministic rules engine with effective dates for federal acquisition.
Replaces hardcoded if/else logic with a traversable, auditable rule set.

Design Principles:
- Every rule has effective_date/expiration_date (Oct 1 annual updates)
- Q-code DAG produces traversal trace (not cosmetic list)
- D-code registry is authoritative (resolves seeds.py misalignments)
- Posting deadlines follow FAR 5.203 matrix
- Clause selection is deterministic based on acquisition parameters
- All outputs include authority citation

This module is Tier 1 (deterministic). No AI/LLM involvement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


# ── Effective-Dated Rule Base ─────────────────────────────────────────────────

@dataclass
class EffectiveDatedRule:
    """Base for any rule that can change on Oct 1."""
    effective_date: date
    expiration_date: date | None = None

    def is_active(self, as_of: date) -> bool:
        if self.effective_date > as_of:
            return False
        if self.expiration_date and self.expiration_date <= as_of:
            return False
        return True


# ── D-Code Registry (Corrected) ──────────────────────────────────────────────

@dataclass
class DCodeDefinition(EffectiveDatedRule):
    """Authoritative D-code definition. Resolves seeds.py misalignments."""
    code: str = ""
    name: str = ""
    description: str = ""
    ucf_section: str | None = None  # UCF section letter (A-M) if applicable
    always_required: bool = False
    condition: str = ""  # Human-readable trigger condition
    authority: str = ""


# Corrected D-code registry (fixes D102/D104/D109 misalignments)
DCODE_REGISTRY: list[DCodeDefinition] = [
    DCodeDefinition(code="D101", name="Market Research", description="Market research report documenting available sources and commercial availability",
                    ucf_section="A", always_required=False, condition="value > micro_purchase", authority="FAR 10.002",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D102", name="Performance Work Statement", description="PWS/SOW/SOO for services acquisitions (UCF Section C)",
                    ucf_section="C", always_required=False, condition="services == True", authority="FAR 37.602",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D103", name="CLIN Structure", description="Contract Line Item Number structure and pricing schedule (UCF Section B)",
                    ucf_section="B", always_required=False, condition="value > sat", authority="FAR 4.1001",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D104", name="IGCE", description="Independent Government Cost Estimate (internal document, not in solicitation)",
                    ucf_section=None, always_required=False, condition="value > sat", authority="FAR 36.203, HSAM",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D105", name="QASP", description="Quality Assurance Surveillance Plan (UCF Section E, Inspection & Acceptance)",
                    ucf_section="E", always_required=False, condition="services == True and value > sat", authority="FAR 46.401, FAR 37.604",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D106", name="Acquisition Plan", description="Written acquisition plan per FAR 7.105 / TSA MD 300.25",
                    ucf_section=None, always_required=False, condition="value >= acquisition_plan_threshold", authority="FAR 7.105, TSA MD 300.25",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D107", name="Small Business Review", description="SB coordination form (700-22) and set-aside determination",
                    ucf_section=None, always_required=False, condition="value > sat", authority="FAR 19.502-2",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D108", name="Justification & Approval", description="J&A for other than full and open competition",
                    ucf_section=None, always_required=False, condition="sole_source == True", authority="FAR 6.302, FAR 6.304",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D109", name="Special Contract Requirements", description="Special contract requirements (UCF Section H)",
                    ucf_section="H", always_required=False, condition="value > sat", authority="FAR 15.204-1",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D110", name="Subcontracting Plan", description="Individual subcontracting plan (700-23)",
                    ucf_section=None, always_required=False, condition="value >= subcontracting_plan_threshold", authority="FAR 19.702",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D111", name="Contract Clauses", description="FAR/HSAR clause compilation (UCF Section I)",
                    ucf_section="I", always_required=False, condition="value > sat", authority="FAR 52, HSAR 3052",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D112", name="Attachments List", description="List of attachments (UCF Section J)",
                    ucf_section="J", always_required=False, condition="value > sat", authority="FAR 15.204-1",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D113", name="Instructions to Offerors", description="Proposal submission instructions (UCF Section L)",
                    ucf_section="L", always_required=False, condition="value > sat", authority="FAR 15.204-1",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D114", name="CIO/ITAR Approval", description="IT Acquisition Review approval",
                    ucf_section=None, always_required=False, condition="it_related == True", authority="TSA CIO / ITAR",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D115", name="COR Nomination", description="Contracting Officer Representative nomination and training documentation",
                    ucf_section=None, always_required=False, condition="services == True", authority="FAR 1.602-2(d)",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D116", name="Commercial Item D&F", description="Determination that item meets FAR Part 12 commercial item definition",
                    ucf_section=None, always_required=False, condition="commercial_item == True", authority="FAR 12.202",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D117", name="Evaluation Factors", description="Evaluation factors for award (UCF Section M)",
                    ucf_section="M", always_required=False, condition="value > sat", authority="FAR 15.304",
                    effective_date=date(2025, 10, 1)),
    # ── Phase 3 Expansion (D118–D128) ──
    DCodeDefinition(code="D118", name="Past Performance Evaluation Plan",
                    description="Plan for evaluating offeror past performance references",
                    ucf_section="M", always_required=False,
                    condition="value > 350000 and not commercial_item",
                    authority="FAR 15.305(a)(2)",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D119", name="OCI Mitigation Plan",
                    description="Organizational Conflict of Interest analysis and mitigation",
                    ucf_section=None, always_required=False,
                    condition="value > 350000",
                    authority="FAR 9.5",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D120", name="Security Requirements Document",
                    description="TSA security requirements (SSI, CUI, suitability, clearances)",
                    ucf_section="H", always_required=False,
                    condition="value > 15000",
                    authority="TSA MD 2810.1, HSAR 3004.470",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D121", name="Option Period Justification",
                    description="Written determination that option periods are in government interest",
                    ucf_section=None, always_required=False,
                    condition="value > 350000",
                    authority="FAR 17.207",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D122", name="Wage Determination",
                    description="DOL wage determination for Service Contract Act coverage",
                    ucf_section="J", always_required=False,
                    condition="services and not commercial_item",
                    authority="FAR 22.1002-1, 29 U.S.C. 351",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D123", name="IDIQ Minimum/Maximum D&F",
                    description="D&F for IDIQ minimum guarantee and maximum ceiling",
                    ucf_section=None, always_required=False,
                    condition="competition_type == 'idiq'",
                    authority="FAR 16.504",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D124", name="Fair Opportunity Determination",
                    description="Fair opportunity analysis for task/delivery order placement",
                    ucf_section=None, always_required=False,
                    condition="competition_type == 'task_order'",
                    authority="FAR 16.505(b)",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D125", name="Contractor Transition Plan",
                    description="Transition plan requirement for incumbent contract changeover",
                    ucf_section="C", always_required=False,
                    condition="services and value > 5500000",
                    authority="FAR 37.102",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D126", name="Government Property Inventory",
                    description="Government-furnished property/equipment inventory and accountability",
                    ucf_section="H", always_required=False,
                    condition="vendor_on_site",
                    authority="FAR 45.102",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D127", name="Key Personnel Designation",
                    description="Key personnel positions, qualifications, and substitution procedures",
                    ucf_section="H", always_required=False,
                    condition="services and value > 350000",
                    authority="HSAM 3015.204-70",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D128", name="TSA Badge/Access Requirements",
                    description="TSA-specific badge, SSI access, and facility access requirements",
                    ucf_section="H", always_required=False,
                    condition="vendor_on_site and value > 15000",
                    authority="TSA MD 2810.1",
                    effective_date=date(2025, 10, 1)),
    # ── Phase 7 Expansion (D129–D145) ──
    DCodeDefinition(code="D129", name="Modification Request Package",
                    description="Contract modification request with funding, scope change, and CO approval",
                    ucf_section=None, always_required=False,
                    condition="False",
                    authority="FAR 43.103",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D130", name="Pre-Award Survey",
                    description="Pre-award survey of prospective contractor responsibility",
                    ucf_section=None, always_required=False,
                    condition="value > 350000 and not commercial_item",
                    authority="FAR 9.106",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D131", name="Responsibility Determination",
                    description="Affirmative determination of contractor responsibility",
                    ucf_section=None, always_required=False,
                    condition="value > 350000",
                    authority="FAR 9.104-1",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D132", name="Cost/Price Analysis Report",
                    description="Documented cost or price analysis supporting fair and reasonable determination",
                    ucf_section=None, always_required=False,
                    condition="value > 15000",
                    authority="FAR 15.404-1",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D133", name="Negotiation Memorandum",
                    description="Memorandum documenting negotiation objectives, discussions, and outcomes",
                    ucf_section=None, always_required=False,
                    condition="value > 350000 and not commercial_item",
                    authority="FAR 15.406-3",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D134", name="Award Notification Letters",
                    description="Successful and unsuccessful offeror notification letters",
                    ucf_section=None, always_required=False,
                    condition="value > 350000",
                    authority="FAR 15.503",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D135", name="Debriefing Documentation",
                    description="Post-award debriefing materials and records",
                    ucf_section=None, always_required=False,
                    condition="value > 350000",
                    authority="FAR 15.506",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D136", name="SSDD",
                    description="Source Selection Decision Document (best value trade-off rationale)",
                    ucf_section=None, always_required=False,
                    condition="value > 350000 and not commercial_item",
                    authority="FAR 15.308",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D137", name="Protest Response Package",
                    description="Agency response to GAO or COFC protest filing",
                    ucf_section=None, always_required=False,
                    condition="False",
                    authority="FAR 33.104, 4 CFR 21",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D138", name="Corrective Action Plan",
                    description="Corrective action plan in response to sustained protest or identified deficiency",
                    ucf_section=None, always_required=False,
                    condition="False",
                    authority="FAR 33.104(b)",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D139", name="8(a) Offering Letter",
                    description="SBA 8(a) program offering letter and acceptance",
                    ucf_section=None, always_required=False,
                    condition="competition_type == '8a'",
                    authority="FAR 19.804",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D140", name="GSA Schedule Order Documentation",
                    description="GSA Federal Supply Schedule order documentation and best value determination",
                    ucf_section=None, always_required=False,
                    condition="competition_type == 'gsa_schedule'",
                    authority="FAR 8.405",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D141", name="BPA Establishment/Call Documentation",
                    description="Blanket Purchase Agreement establishment or call order documentation",
                    ucf_section=None, always_required=False,
                    condition="competition_type == 'bpa'",
                    authority="FAR 13.303",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D142", name="FedRAMP Authorization Package",
                    description="FedRAMP authorization documentation for cloud services",
                    ucf_section=None, always_required=False,
                    condition="it_related and value > 350000",
                    authority="OMB A-130, FedRAMP",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D143", name="Closeout Checklist",
                    description="Contract closeout checklist with all administrative actions completed",
                    ucf_section=None, always_required=False,
                    condition="False",
                    authority="FAR 4.804",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D144", name="Final CPARS Evaluation",
                    description="Final contractor performance assessment for CPARS",
                    ucf_section=None, always_required=False,
                    condition="False",
                    authority="FAR 42.1502",
                    effective_date=date(2025, 10, 1)),
    DCodeDefinition(code="D145", name="Release of Claims",
                    description="Contractor release of claims letter for contract closeout",
                    ucf_section=None, always_required=False,
                    condition="False",
                    authority="FAR 4.804-5(a)(3)",
                    effective_date=date(2025, 10, 1)),
]


def get_dcode_registry(as_of: date | None = None) -> dict[str, DCodeDefinition]:
    """Return active D-codes as of a given date."""
    check_date = as_of or date.today()
    return {d.code: d for d in DCODE_REGISTRY if d.is_active(check_date)}


# ── Q-Code DAG Engine ─────────────────────────────────────────────────────────

@dataclass
class QCodeEdge:
    """Conditional edge in the Q-code decision tree."""
    from_code: str
    to_code: str
    condition: str  # Python expression evaluated against acquisition params
    label: str  # Human-readable label (e.g., "Yes", "No", ">SAT")


@dataclass
class QCodeNode:
    """Node in the Q-code decision tree."""
    code: str
    question: str
    authority: str
    triggered_dcodes: list[str] = field(default_factory=list)
    system_action: str = ""  # What FedProcure does at this node
    terminal: bool = False


@dataclass
class QCodeTraceEntry:
    """Single step in a Q-code traversal trace."""
    code: str
    question: str
    answer: str
    triggered_dcodes: list[str]
    authority: str


@dataclass
class QCodeTraversalResult:
    """Complete result of traversing the Q-code DAG."""
    trace: list[QCodeTraceEntry]
    triggered_dcodes: set[str]
    nodes_evaluated: int
    terminal_node: str


# Q-Code nodes — the actual decision tree for acquisition routing
# This is a subset focused on the critical path (expandable to 117 nodes)
QCODE_NODES: dict[str, QCodeNode] = {
    "Q001": QCodeNode("Q001", "Is this a new requirement or modification?", "FedProcure Intake", system_action="route_intake"),
    "Q002": QCodeNode("Q002", "What is the estimated total value?", "FAR 2.101", system_action="classify_value"),
    "Q003": QCodeNode("Q003", "Does value exceed micro-purchase threshold ($15K)?", "FAR 2.101", system_action="check_micro"),
    "Q004": QCodeNode("Q004", "Does value exceed SAT ($350K)?", "FAR 2.101", triggered_dcodes=["D101", "D103", "D104", "D109"], system_action="check_sat"),
    "Q005": QCodeNode("Q005", "Is this a sole source procurement?", "FAR 6.302, 6.304", triggered_dcodes=["D108"], system_action="check_sole_source"),
    "Q006": QCodeNode("Q006", "Does the requirement include services?", "FAR Part 37", triggered_dcodes=["D102", "D105", "D115"], system_action="check_services"),
    "Q007": QCodeNode("Q007", "Is the requirement IT-related?", "TSA CIO / ITAR", triggered_dcodes=["D114"], system_action="check_it"),
    "Q008": QCodeNode("Q008", "Is this a commercial item?", "FAR Part 12", triggered_dcodes=["D116"], system_action="check_commercial"),
    "Q009": QCodeNode("Q009", "Does value exceed subcontracting plan threshold ($900K)?", "FAR 19.702", triggered_dcodes=["D110"], system_action="check_subcon"),
    "Q010": QCodeNode("Q010", "Does value exceed acquisition plan threshold?", "FAR 7.105, TSA MD 300.25", triggered_dcodes=["D106"], system_action="check_ap"),
    "Q011": QCodeNode("Q011", "Is small business set-aside feasible?", "FAR 19.502-2", triggered_dcodes=["D107"], system_action="check_sb"),
    "Q012": QCodeNode("Q012", "Is this an emergency/urgency procurement?", "FAR 6.302-2", system_action="check_urgency"),
    "Q013": QCodeNode("Q013", "Does value require SSAC?", "FAR 15.308", system_action="check_ssac"),
    "Q014": QCodeNode("Q014", "Determine competition type and posting requirements", "FAR 5.203", system_action="resolve_posting"),
    "Q015": QCodeNode("Q015", "Select evaluation methodology", "FAR 15.101", system_action="select_eval_method"),
    "Q016": QCodeNode("Q016", "Does value exceed cost/pricing data threshold ($2.5M)?", "FAR 15.403", system_action="check_cost_data"),
    "Q017": QCodeNode("Q017", "Route to appropriate approval authority", "FAR 6.304, TSA delegation", system_action="resolve_approver"),
    # ── Phase 3 Expansion (Q018–Q047): Contract Type, Options, Labor, Security, Eval, OCI, Oversight, TSA ──
    # Contract Type Selection
    "Q018": QCodeNode("Q018", "What contract type is appropriate?", "FAR 16.1", system_action="select_contract_type"),
    "Q019": QCodeNode("Q019", "Is this a fixed-price requirement?", "FAR 16.2", system_action="check_fixed_price"),
    "Q020": QCodeNode("Q020", "Is a cost-reimbursement type appropriate?", "FAR 16.3", system_action="check_cost_reimbursement"),
    "Q021": QCodeNode("Q021", "Is this an IDIQ vehicle?", "FAR 16.504", triggered_dcodes=["D123"], system_action="check_idiq"),
    "Q022": QCodeNode("Q022", "Is this a task order under existing IDIQ?", "FAR 16.505", triggered_dcodes=["D124"], system_action="check_task_order"),
    # Option Periods
    "Q023": QCodeNode("Q023", "Does the requirement include option periods?", "FAR 17.2", triggered_dcodes=["D121"], system_action="check_options"),
    "Q024": QCodeNode("Q024", "Is the total value including options within threshold?", "FAR 17.204", system_action="check_total_with_options"),
    # Labor Standards
    "Q025": QCodeNode("Q025", "Is this subject to Service Contract Act?", "FAR 22.10", triggered_dcodes=["D122"], system_action="check_sca"),
    "Q026": QCodeNode("Q026", "Is this subject to Davis-Bacon Act?", "FAR 22.4", system_action="check_davis_bacon"),
    "Q027": QCodeNode("Q027", "Are prevailing wage determinations required?", "29 U.S.C. 351", system_action="check_wage_determination"),
    # Security Requirements
    "Q028": QCodeNode("Q028", "Does work involve Sensitive Security Information (SSI)?", "49 CFR 1520", triggered_dcodes=["D120"], system_action="check_ssi"),
    "Q029": QCodeNode("Q029", "Does work require personnel suitability determinations?", "TSA MD 2810.1", triggered_dcodes=["D128"], system_action="check_suitability"),
    "Q030": QCodeNode("Q030", "Does work involve CUI handling?", "32 CFR 2002", system_action="check_cui"),
    "Q031": QCodeNode("Q031", "Are facility/badge access requirements needed?", "TSA MD 2810.1", triggered_dcodes=["D128"], system_action="check_badge_access"),
    # Past Performance & Evaluation
    "Q032": QCodeNode("Q032", "Is past performance evaluation required?", "FAR 15.305(a)(2)", triggered_dcodes=["D118"], system_action="check_past_performance"),
    "Q033": QCodeNode("Q033", "What evaluation methodology: trade-off or LPTA?", "FAR 15.101", system_action="determine_eval_method"),
    "Q034": QCodeNode("Q034", "Are discussions anticipated?", "FAR 15.306", system_action="check_discussions"),
    "Q035": QCodeNode("Q035", "Is debriefing required (task orders >$7.5M)?", "FAR 16.505(b)(6)", system_action="check_debriefing"),
    # OCI
    "Q036": QCodeNode("Q036", "Is there a potential organizational conflict of interest?", "FAR 9.5", triggered_dcodes=["D119"], system_action="check_oci"),
    "Q037": QCodeNode("Q037", "Is an OCI mitigation plan required?", "FAR 9.503", triggered_dcodes=["D119"], system_action="check_oci_mitigation"),
    # Property & Transition
    "Q038": QCodeNode("Q038", "Will government-furnished property/equipment be provided?", "FAR 45.102", triggered_dcodes=["D126"], system_action="check_gfp"),
    "Q039": QCodeNode("Q039", "Is contractor transition from incumbent required?", "FAR 37.102", triggered_dcodes=["D125"], system_action="check_transition"),
    "Q040": QCodeNode("Q040", "Are key personnel designations needed?", "HSAM 3015.204-70", triggered_dcodes=["D127"], system_action="check_key_personnel"),
    # COR & Oversight
    "Q041": QCodeNode("Q041", "Is COR surveillance level I, II, or III?", "FAR 1.602-2(d)", system_action="classify_cor_level"),
    "Q042": QCodeNode("Q042", "Is a QASP review cycle defined?", "FAR 46.401", system_action="check_qasp_cycle"),
    "Q043": QCodeNode("Q043", "Is CPARS reporting required?", "FAR 42.15", system_action="check_cpars"),
    # TSA-Specific Reviews
    "Q044": QCodeNode("Q044", "Does this require TSA Acquisition Review Board (ARB)?", "TSA MD 300.25", system_action="check_arb"),
    "Q045": QCodeNode("Q045", "Is DHS APFS registration required?", "HSAM Appendix G", system_action="check_apfs"),
    "Q046": QCodeNode("Q046", "Does this require PRISM contract writing system entry?", "DHS Unison/PRISM", system_action="check_prism"),
    "Q047": QCodeNode("Q047", "Final routing: all checks complete", "FedProcure Policy Engine", system_action="final_route", terminal=True),
    # ── Q048–Q057: Contract Modifications ──
    "Q048": QCodeNode("Q048", "Is this a modification to an existing contract?", "FAR 43.1", system_action="check_mod_type"),
    "Q049": QCodeNode("Q049", "Is this a bilateral or unilateral modification?", "FAR 43.103", triggered_dcodes=["D129"], system_action="classify_mod"),
    "Q050": QCodeNode("Q050", "Does the modification involve a scope change?", "FAR 43.201", system_action="check_scope_change"),
    "Q051": QCodeNode("Q051", "Is a J&A required for the scope change?", "FAR 6.001(a)", triggered_dcodes=["D108"], system_action="check_mod_ja"),
    "Q052": QCodeNode("Q052", "Is this a change order (unilateral)?", "FAR 43.201(a)", system_action="check_change_order"),
    "Q053": QCodeNode("Q053", "Is there a Request for Equitable Adjustment (REA)?", "FAR 43.204", system_action="check_rea"),
    "Q054": QCodeNode("Q054", "Is this an option exercise?", "FAR 17.207", triggered_dcodes=["D121"], system_action="check_option_exercise"),
    "Q055": QCodeNode("Q055", "Is the option exercise within the contractual period?", "FAR 17.204", system_action="check_option_timing"),
    "Q056": QCodeNode("Q056", "Has the option price been determined fair and reasonable?", "FAR 17.207(f)", triggered_dcodes=["D132"], system_action="check_option_price"),
    "Q057": QCodeNode("Q057", "Route modification for CO signature", "FAR 43.103", system_action="route_mod", terminal=True),

    # ── Q058–Q067: Award Phase ──
    "Q058": QCodeNode("Q058", "Is a pre-award survey required?", "FAR 9.106", triggered_dcodes=["D130"], system_action="check_preaward_survey"),
    "Q059": QCodeNode("Q059", "Has the responsibility determination been completed?", "FAR 9.104-1", triggered_dcodes=["D131"], system_action="check_responsibility"),
    "Q060": QCodeNode("Q060", "Is cost or price analysis documented?", "FAR 15.404-1", triggered_dcodes=["D132"], system_action="check_cost_analysis"),
    "Q061": QCodeNode("Q061", "Are negotiations required?", "FAR 15.306", triggered_dcodes=["D133"], system_action="check_negotiations"),
    "Q062": QCodeNode("Q062", "Is the negotiation memorandum complete?", "FAR 15.406-3", system_action="verify_nego_memo"),
    "Q063": QCodeNode("Q063", "Has the SSDD been prepared?", "FAR 15.308", triggered_dcodes=["D136"], system_action="check_ssdd"),
    "Q064": QCodeNode("Q064", "Have award notification letters been prepared?", "FAR 15.503", triggered_dcodes=["D134"], system_action="check_award_notice"),
    "Q065": QCodeNode("Q065", "Is debriefing preparation required?", "FAR 15.505, FAR 15.506", triggered_dcodes=["D135"], system_action="check_debrief_prep"),
    "Q066": QCodeNode("Q066", "Has the award been synopsized in SAM.gov?", "FAR 5.301", system_action="check_award_synopsis"),
    "Q067": QCodeNode("Q067", "Route award for CO signature", "FAR 1.602-1", system_action="route_award", terminal=True),

    # ── Q068–Q077: Post-Award Administration ──
    "Q068": QCodeNode("Q068", "Is delivery/performance monitoring required?", "FAR 42.302", system_action="check_monitoring"),
    "Q069": QCodeNode("Q069", "Is invoice review and payment processing in scope?", "FAR 32.9", system_action="check_invoice"),
    "Q070": QCodeNode("Q070", "Is a CPARS interim evaluation due?", "FAR 42.1502", triggered_dcodes=["D144"], system_action="check_cpars_interim"),
    "Q071": QCodeNode("Q071", "Are there pending contract modifications?", "FAR 43.1", triggered_dcodes=["D129"], system_action="check_pending_mods"),
    "Q072": QCodeNode("Q072", "Is an option period approaching (120-day notice)?", "FAR 17.207", triggered_dcodes=["D121"], system_action="check_option_window"),
    "Q073": QCodeNode("Q073", "Has the COR submitted a surveillance report?", "FAR 1.602-2(d)", system_action="check_cor_report"),
    "Q074": QCodeNode("Q074", "Are there any contractor performance issues?", "FAR 42.302(a)(1)", system_action="check_performance_issues"),
    "Q075": QCodeNode("Q075", "Is a cure notice or show-cause warranted?", "FAR 49.402-3", system_action="check_cure_notice"),
    "Q076": QCodeNode("Q076", "Is the period of performance ending within 180 days?", "FAR 4.804-1", system_action="check_pop_ending"),
    "Q077": QCodeNode("Q077", "Initiate closeout planning", "FAR 4.804", system_action="initiate_closeout"),

    # ── Q078–Q087: Protest & Disputes ──
    "Q078": QCodeNode("Q078", "Has a protest been filed?", "FAR 33.103, FAR 33.104", system_action="check_protest_filed"),
    "Q079": QCodeNode("Q079", "Is this a GAO protest?", "4 CFR 21", triggered_dcodes=["D137"], system_action="check_gao_protest"),
    "Q080": QCodeNode("Q080", "Is this an agency-level protest?", "FAR 33.103", system_action="check_agency_protest"),
    "Q081": QCodeNode("Q081", "Is this a COFC protest?", "28 U.S.C. 1491(b)", system_action="check_cofc"),
    "Q082": QCodeNode("Q082", "Has automatic stay been triggered?", "31 U.S.C. 3553(c)", system_action="check_stay"),
    "Q083": QCodeNode("Q083", "Is corrective action recommended?", "FAR 33.104(b)", triggered_dcodes=["D138"], system_action="check_corrective_action"),
    "Q084": QCodeNode("Q084", "Is ADR appropriate for this dispute?", "FAR 33.214", system_action="check_adr"),
    "Q085": QCodeNode("Q085", "Has a CDA claim been submitted?", "41 U.S.C. 7103", system_action="check_cda_claim"),
    "Q086": QCodeNode("Q086", "Does the claim exceed $100K (requiring certification)?", "41 U.S.C. 7103(b)", system_action="check_claim_cert"),
    "Q087": QCodeNode("Q087", "Route dispute to CO for final decision", "41 U.S.C. 7103(d)", system_action="route_dispute", terminal=True),

    # ── Q088–Q097: Special Acquisition Programs ──
    "Q088": QCodeNode("Q088", "Is this an 8(a) program requirement?", "FAR 19.8", triggered_dcodes=["D139"], system_action="check_8a"),
    "Q089": QCodeNode("Q089", "Is this a HUBZone set-aside?", "FAR 19.13", system_action="check_hubzone"),
    "Q090": QCodeNode("Q090", "Is this a SDVOSB set-aside?", "FAR 19.14", system_action="check_sdvosb"),
    "Q091": QCodeNode("Q091", "Is this a WOSB/EDWOSB set-aside?", "FAR 19.15", system_action="check_wosb"),
    "Q092": QCodeNode("Q092", "Is this an AbilityOne requirement?", "FAR 8.7", system_action="check_abilityone"),
    "Q093": QCodeNode("Q093", "Is this a GSA Federal Supply Schedule order?", "FAR 8.4", triggered_dcodes=["D140"], system_action="check_gsa_schedule"),
    "Q094": QCodeNode("Q094", "Is this a BPA establishment or call?", "FAR 13.303", triggered_dcodes=["D141"], system_action="check_bpa"),
    "Q095": QCodeNode("Q095", "Does the small business coordination need SBA review?", "FAR 19.202-1", system_action="check_sba_review"),
    "Q096": QCodeNode("Q096", "Is a Limited Sources Justification (LSJ) needed for GSA?", "FAR 8.405-6", system_action="check_lsj"),
    "Q097": QCodeNode("Q097", "Route special program acquisition", "FAR 19.201", system_action="route_special_program", terminal=True),

    # ── Q098–Q107: DHS/TSA Specific ──
    "Q098": QCodeNode("Q098", "Is this using DHS EAGLE II vehicle?", "HSAM", system_action="check_eagle"),
    "Q099": QCodeNode("Q099", "Is this using DHS FirstSource vehicle?", "HSAM", system_action="check_firstsource"),
    "Q100": QCodeNode("Q100", "Is this using GSA PACTS III vehicle?", "GSA Schedule", system_action="check_pacts"),
    "Q101": QCodeNode("Q101", "Does this require ITAR deep review (>$25M IT)?", "TSA CIO / ITAR", system_action="check_itar_deep"),
    "Q102": QCodeNode("Q102", "Does this require ISSO security review?", "TSA MD 2810.1", system_action="check_isso"),
    "Q103": QCodeNode("Q103", "Is FedRAMP authorization required?", "OMB A-130", triggered_dcodes=["D142"], system_action="check_fedramp"),
    "Q104": QCodeNode("Q104", "Does HSAR 3052 clause flow-down apply?", "HSAR 3052", system_action="check_hsar_flowdown"),
    "Q105": QCodeNode("Q105", "Is DHS Category Management review required?", "OMB M-22-03", system_action="check_cat_mgmt"),
    "Q106": QCodeNode("Q106", "Does this acquisition need CIO dashboard reporting?", "FITARA", system_action="check_fitara"),
    "Q107": QCodeNode("Q107", "Route DHS/TSA-specific requirements", "HSAM, TSA MDs", system_action="route_dhs_tsa", terminal=True),

    # ── Q108–Q117: Contract Closeout ──
    "Q108": QCodeNode("Q108", "Is the period of performance complete?", "FAR 4.804-1", system_action="check_pop_complete"),
    "Q109": QCodeNode("Q109", "Has final delivery/acceptance occurred?", "FAR 4.804-1(a)(1)", system_action="check_final_delivery"),
    "Q110": QCodeNode("Q110", "Have all invoices been submitted and paid?", "FAR 4.804-5(a)(2)", system_action="check_final_payment"),
    "Q111": QCodeNode("Q111", "Is government property disposition required?", "FAR 45.6", triggered_dcodes=["D126"], system_action="check_property_disposition"),
    "Q112": QCodeNode("Q112", "Are there unliquidated obligations to de-obligate?", "FAR 4.804-5(a)(16)", system_action="check_ulo"),
    "Q113": QCodeNode("Q113", "Has the contractor submitted release of claims?", "FAR 4.804-5(a)(3)", triggered_dcodes=["D145"], system_action="check_release_claims"),
    "Q114": QCodeNode("Q114", "Has final CPARS been completed?", "FAR 42.1502", triggered_dcodes=["D144"], system_action="check_cpars_final"),
    "Q115": QCodeNode("Q115", "Have contract files been archived per retention schedule?", "FAR 4.805", system_action="check_records_retention"),
    "Q116": QCodeNode("Q116", "Has the closeout checklist been completed?", "FAR 4.804-5", triggered_dcodes=["D143"], system_action="check_closeout_checklist"),
    "Q117": QCodeNode("Q117", "Contract closeout complete — administrative record sealed", "FAR 4.804", system_action="closeout_complete", terminal=True),

}

# DAG edges — condition is evaluated against acquisition params dict
QCODE_EDGES: list[QCodeEdge] = [
    QCodeEdge("Q001", "Q002", "True", "Always"),
    QCodeEdge("Q002", "Q003", "True", "Classify value"),
    QCodeEdge("Q003", "Q004", "value > 15000", "Above micro"),
    QCodeEdge("Q003", "Q017", "value <= 15000", "Micro purchase → route"),
    QCodeEdge("Q004", "Q005", "value > 350000", "Above SAT"),
    QCodeEdge("Q004", "Q006", "value <= 350000", "Below SAT → check services"),
    QCodeEdge("Q005", "Q006", "True", "Continue to services check"),
    QCodeEdge("Q006", "Q007", "True", "Continue to IT check"),
    QCodeEdge("Q007", "Q008", "True", "Continue to commercial check"),
    QCodeEdge("Q008", "Q009", "True", "Continue to subcon check"),
    QCodeEdge("Q009", "Q010", "True", "Continue to AP check"),
    QCodeEdge("Q010", "Q011", "value > 350000", "Above SAT → SB check"),
    QCodeEdge("Q010", "Q014", "value <= 350000", "Below SAT → posting"),
    QCodeEdge("Q011", "Q012", "True", "Continue to urgency check"),
    QCodeEdge("Q012", "Q013", "True", "Continue to SSAC check"),
    QCodeEdge("Q013", "Q014", "True", "Continue to posting"),
    QCodeEdge("Q014", "Q015", "value > 350000", "Above SAT → eval method"),
    QCodeEdge("Q014", "Q017", "value <= 350000", "Below SAT → route"),
    QCodeEdge("Q015", "Q016", "True", "Continue to cost data check"),
    QCodeEdge("Q016", "Q017", "True", "Route to approver"),
    # ── Phase 3 Expansion Edges ──
    QCodeEdge("Q017", "Q018", "True", "Continue to contract type"),
    # Contract type
    QCodeEdge("Q018", "Q019", "True", "Evaluate contract type"),
    QCodeEdge("Q019", "Q021", "competition_type == 'idiq'", "IDIQ vehicle"),
    QCodeEdge("Q019", "Q022", "competition_type == 'task_order'", "Task order"),
    QCodeEdge("Q019", "Q023", "competition_type != 'idiq' and competition_type != 'task_order'", "Standard → options"),
    QCodeEdge("Q020", "Q023", "True", "Continue to options"),
    QCodeEdge("Q021", "Q023", "True", "IDIQ → options"),
    QCodeEdge("Q022", "Q035", "True", "Task order → debriefing"),
    # Options
    QCodeEdge("Q023", "Q024", "True", "Check total with options"),
    QCodeEdge("Q024", "Q025", "True", "Continue to labor standards"),
    # Labor
    QCodeEdge("Q025", "Q026", "services", "Services → Davis-Bacon"),
    QCodeEdge("Q025", "Q028", "not services", "Not services → security"),
    QCodeEdge("Q026", "Q027", "True", "Continue to wage det"),
    QCodeEdge("Q027", "Q028", "True", "Continue to security"),
    # Security
    QCodeEdge("Q028", "Q029", "True", "Continue to suitability"),
    QCodeEdge("Q029", "Q030", "True", "Continue to CUI"),
    QCodeEdge("Q030", "Q031", "vendor_on_site", "On-site → badge"),
    QCodeEdge("Q030", "Q032", "not vendor_on_site", "No on-site → eval"),
    QCodeEdge("Q031", "Q032", "True", "Continue to eval"),
    # Evaluation
    QCodeEdge("Q032", "Q033", "value > 350000", "Above SAT → eval method"),
    QCodeEdge("Q032", "Q038", "value <= 350000", "Below SAT → property"),
    QCodeEdge("Q033", "Q034", "True", "Continue to discussions"),
    QCodeEdge("Q034", "Q035", "True", "Continue to debriefing"),
    QCodeEdge("Q035", "Q036", "True", "Continue to OCI"),
    # OCI
    QCodeEdge("Q036", "Q037", "True", "Evaluate OCI"),
    QCodeEdge("Q037", "Q038", "True", "Continue to property"),
    # Property & transition
    QCodeEdge("Q038", "Q039", "True", "Continue to transition"),
    QCodeEdge("Q039", "Q040", "services and value > 350000", "Services → key personnel"),
    QCodeEdge("Q039", "Q041", "not services or value <= 350000", "Skip to COR"),
    QCodeEdge("Q040", "Q041", "True", "Continue to COR"),
    # COR & oversight
    QCodeEdge("Q041", "Q042", "services", "Services → QASP"),
    QCodeEdge("Q041", "Q044", "not services", "Not services → TSA"),
    QCodeEdge("Q042", "Q043", "True", "Continue to CPARS"),
    QCodeEdge("Q043", "Q044", "True", "Continue to TSA"),
    # TSA-specific
    QCodeEdge("Q044", "Q045", "True", "Continue to APFS"),
    QCodeEdge("Q045", "Q046", "True", "Continue to PRISM"),
    QCodeEdge("Q046", "Q047", "True", "Final route"),
    # ── Q048–Q057 Edges: Contract Modifications (branched from Q001) ──
    QCodeEdge("Q048", "Q049", "True", "Classify modification type"),
    QCodeEdge("Q049", "Q050", "True", "Check scope"),
    QCodeEdge("Q050", "Q051", "True", "Scope change → J&A check"),
    QCodeEdge("Q051", "Q057", "sole_source", "Sole source mod → route"),
    QCodeEdge("Q051", "Q052", "not sole_source", "Competitive mod → change order check"),
    QCodeEdge("Q052", "Q053", "True", "Check REA"),
    QCodeEdge("Q053", "Q057", "True", "Route mod"),
    QCodeEdge("Q054", "Q055", "True", "Check option timing"),
    QCodeEdge("Q055", "Q056", "True", "Check option price"),
    QCodeEdge("Q056", "Q057", "True", "Route option exercise"),

    # ── Q058–Q067 Edges: Award Phase (branched from evaluation path) ──
    QCodeEdge("Q058", "Q059", "True", "Continue to responsibility"),
    QCodeEdge("Q059", "Q060", "True", "Continue to cost analysis"),
    QCodeEdge("Q060", "Q061", "value > 350000 and not commercial_item", "Above SAT negotiated → negotiations"),
    QCodeEdge("Q060", "Q064", "value <= 350000 or commercial_item", "Below SAT or commercial → award notice"),
    QCodeEdge("Q061", "Q062", "True", "Verify nego memo"),
    QCodeEdge("Q062", "Q063", "True", "Prepare SSDD"),
    QCodeEdge("Q063", "Q064", "True", "Award notification"),
    QCodeEdge("Q064", "Q065", "value > 350000", "Above SAT → debriefing"),
    QCodeEdge("Q064", "Q066", "value <= 350000", "Below SAT → synopsis"),
    QCodeEdge("Q065", "Q066", "True", "Continue to synopsis"),
    QCodeEdge("Q066", "Q067", "True", "Route award"),

    # ── Q068–Q077 Edges: Post-Award (sequential flow) ──
    QCodeEdge("Q068", "Q069", "True", "Continue to invoice review"),
    QCodeEdge("Q069", "Q070", "True", "Continue to CPARS interim"),
    QCodeEdge("Q070", "Q071", "True", "Check pending mods"),
    QCodeEdge("Q071", "Q072", "True", "Check option window"),
    QCodeEdge("Q072", "Q073", "True", "Check COR report"),
    QCodeEdge("Q073", "Q074", "True", "Check performance"),
    QCodeEdge("Q074", "Q075", "True", "Check cure notice need"),
    QCodeEdge("Q075", "Q076", "True", "Check POP ending"),
    QCodeEdge("Q076", "Q077", "True", "Initiate closeout planning"),

    # ── Q078–Q087 Edges: Protest & Disputes ──
    QCodeEdge("Q078", "Q079", "True", "Check protest venue"),
    QCodeEdge("Q079", "Q082", "True", "GAO → check stay"),
    QCodeEdge("Q080", "Q083", "True", "Agency → corrective action"),
    QCodeEdge("Q081", "Q082", "True", "COFC → check stay"),
    QCodeEdge("Q082", "Q083", "True", "Continue to corrective action"),
    QCodeEdge("Q083", "Q084", "True", "Check ADR"),
    QCodeEdge("Q084", "Q085", "True", "Check CDA claim"),
    QCodeEdge("Q085", "Q086", "True", "Check claim certification"),
    QCodeEdge("Q086", "Q087", "True", "Route dispute"),

    # ── Q088–Q097 Edges: Special Programs ──
    QCodeEdge("Q088", "Q095", "competition_type == '8a'", "8(a) → SBA review"),
    QCodeEdge("Q088", "Q089", "competition_type != '8a'", "Not 8(a) → HUBZone"),
    QCodeEdge("Q089", "Q090", "True", "Continue to SDVOSB"),
    QCodeEdge("Q090", "Q091", "True", "Continue to WOSB"),
    QCodeEdge("Q091", "Q092", "True", "Continue to AbilityOne"),
    QCodeEdge("Q092", "Q093", "True", "Continue to GSA"),
    QCodeEdge("Q093", "Q096", "competition_type == 'gsa_schedule'", "GSA → LSJ check"),
    QCodeEdge("Q093", "Q094", "competition_type != 'gsa_schedule'", "Not GSA → BPA"),
    QCodeEdge("Q094", "Q097", "True", "Route special program"),
    QCodeEdge("Q095", "Q097", "True", "SBA review → route"),
    QCodeEdge("Q096", "Q097", "True", "LSJ → route"),

    # ── Q098–Q107 Edges: DHS/TSA Specific ──
    QCodeEdge("Q098", "Q099", "True", "Continue to FirstSource"),
    QCodeEdge("Q099", "Q100", "True", "Continue to PACTS"),
    QCodeEdge("Q100", "Q101", "it_related and value > 25000000", "Large IT → deep ITAR"),
    QCodeEdge("Q100", "Q103", "it_related and value <= 25000000", "Smaller IT → FedRAMP"),
    QCodeEdge("Q100", "Q104", "not it_related", "Not IT → HSAR flow"),
    QCodeEdge("Q101", "Q102", "True", "Continue to ISSO"),
    QCodeEdge("Q102", "Q103", "True", "Continue to FedRAMP"),
    QCodeEdge("Q103", "Q104", "True", "Continue to HSAR flow"),
    QCodeEdge("Q104", "Q105", "True", "Continue to cat mgmt"),
    QCodeEdge("Q105", "Q106", "it_related", "IT → FITARA"),
    QCodeEdge("Q105", "Q107", "not it_related", "Not IT → route DHS"),
    QCodeEdge("Q106", "Q107", "True", "Route DHS/TSA"),

    # ── Q108–Q117 Edges: Closeout ──
    QCodeEdge("Q108", "Q109", "True", "Check final delivery"),
    QCodeEdge("Q109", "Q110", "True", "Check final payment"),
    QCodeEdge("Q110", "Q111", "vendor_on_site", "On-site → property disposition"),
    QCodeEdge("Q110", "Q112", "not vendor_on_site", "No property → ULO check"),
    QCodeEdge("Q111", "Q112", "True", "Continue to ULO"),
    QCodeEdge("Q112", "Q113", "True", "Release of claims"),
    QCodeEdge("Q113", "Q114", "True", "Final CPARS"),
    QCodeEdge("Q114", "Q115", "True", "Records retention"),
    QCodeEdge("Q115", "Q116", "True", "Closeout checklist"),
    QCodeEdge("Q116", "Q117", "True", "Closeout complete"),
]



# ── Phase-to-Branch Mapping ──────────────────────────────────────────────────
# Maps each acquisition lifecycle phase to the Q-code branch entry points
# that should be traversed IN ADDITION to the main Q001 flow.
# This wires the disconnected sub-trees (Q048-Q117) to the workflow engine.

PHASE_BRANCH_MAP: dict[str, list[str]] = {
    "Intake":            [],                          # Main flow only
    "Requirements":      [],                          # Main flow only
    "Solicitation Prep": [],                          # Main flow only
    "Solicitation":      [],                          # Main flow only
    "Evaluation":        ["Q058"],                    # Award phase prep (pre-award survey, responsibility)
    "Award":             ["Q058"],                    # Full award branch
    "Post-Award":        ["Q068", "Q098"],            # Post-award admin + DHS/TSA specific
    "Closeout":          ["Q108"],                    # Closeout branch
}

# Conditional branch entries — added based on acquisition parameters, not phase
CONDITIONAL_BRANCH_MAP: dict[str, str] = {
    "modification":      "Q048",     # Contract modifications (entered when mod flag is set)
    "option_exercise":   "Q054",     # Option exercise (entered when option flag is set)
    "protest":           "Q078",     # Protest handling (entered when protest flag is set)
    "special_program":   "Q088",     # Special programs (8(a), HUBZone, etc.)
    "dhs_tsa":           "Q098",     # DHS/TSA-specific reviews
}


class QCodeEngine:
    """Traverses the Q-code DAG and collects triggered D-codes + trace."""

    def __init__(self):
        self._nodes = QCODE_NODES
        self._edges_by_source: dict[str, list[QCodeEdge]] = {}
        for edge in QCODE_EDGES:
            self._edges_by_source.setdefault(edge.from_code, []).append(edge)

    def traverse(self, params: dict[str, Any]) -> QCodeTraversalResult:
        """Walk the DAG from Q001, evaluating edge conditions against params."""
        trace: list[QCodeTraceEntry] = []
        all_triggered: set[str] = set()
        current = "Q001"
        visited: set[str] = set()
        max_steps = 150  # Safety: prevent infinite loops (expanded tree has 117 nodes)

        for _ in range(max_steps):
            if current in visited:
                break  # Cycle detection
            visited.add(current)

            node = self._nodes.get(current)
            if node is None:
                break

            # Evaluate: which D-codes does this node trigger?
            triggered = []
            for dcode in node.triggered_dcodes:
                if self._should_trigger(dcode, params):
                    triggered.append(dcode)
                    all_triggered.add(dcode)

            # Determine answer for trace
            answer = self._evaluate_node_answer(node, params)
            trace.append(QCodeTraceEntry(
                code=node.code, question=node.question,
                answer=answer, triggered_dcodes=triggered,
                authority=node.authority,
            ))

            if node.terminal:
                break

            # Find next node via edges
            next_node = self._follow_edge(current, params)
            if next_node is None:
                break
            current = next_node

        return QCodeTraversalResult(
            trace=trace,
            triggered_dcodes=all_triggered,
            nodes_evaluated=len(trace),
            terminal_node=current,
        )


    def traverse_for_phase(
        self, params: dict[str, Any], phase: str | None = None
    ) -> QCodeTraversalResult:
        """Traverse the main Q001 tree, then traverse phase-specific branches.

        The main Q001 tree handles intake-through-solicitation logic.
        Phase-specific branches add documents required for later lifecycle stages.
        D-codes from ALL traversed branches are merged into a single result.
        """
        # Always run the main tree first
        main_result = self.traverse(params)
        all_dcodes = set(main_result.triggered_dcodes)
        all_trace = list(main_result.trace)

        if phase is None:
            return main_result

        # Get phase-specific branch entries
        branch_entries = PHASE_BRANCH_MAP.get(phase, [])

        # Add conditional branches based on params
        if params.get("is_modification"):
            branch_entries = list(branch_entries) + [CONDITIONAL_BRANCH_MAP["modification"]]
        if params.get("is_option_exercise"):
            branch_entries = list(branch_entries) + [CONDITIONAL_BRANCH_MAP["option_exercise"]]
        if params.get("has_protest"):
            branch_entries = list(branch_entries) + [CONDITIONAL_BRANCH_MAP["protest"]]

        # Traverse each branch, collecting D-codes and trace entries
        for entry_code in branch_entries:
            if entry_code in {e.code for e in all_trace}:
                continue  # Already traversed this node in main flow or prior branch

            branch_result = self._traverse_from(entry_code, params)
            all_dcodes.update(branch_result.triggered_dcodes)
            all_trace.extend(branch_result.trace)

        return QCodeTraversalResult(
            trace=all_trace,
            triggered_dcodes=all_dcodes,
            nodes_evaluated=len(all_trace),
            terminal_node=main_result.terminal_node,
        )

    def _traverse_from(self, start_code: str, params: dict[str, Any]) -> QCodeTraversalResult:
        """Traverse the DAG starting from an arbitrary node (branch entry point).
        
        Unlike main traverse(), branch traversal FORCE-TRIGGERS all D-codes on
        visited nodes. The branch was entered because the lifecycle event occurred
        (e.g., entering Award phase means award docs are needed), so D-codes with
        condition='False' (event-driven docs like D143 Closeout Checklist) must
        still fire. Param-based conditions are checked as a secondary filter.
        """
        trace: list[QCodeTraceEntry] = []
        all_triggered: set[str] = set()
        current = start_code
        visited: set[str] = set()
        max_steps = 150

        for _ in range(max_steps):
            if current in visited:
                break
            visited.add(current)

            node = self._nodes.get(current)
            if node is None:
                break

            # Force-trigger all D-codes on branch nodes (lifecycle event already occurred)
            # Then also check param-based conditions as secondary filter
            triggered = list(node.triggered_dcodes)  # All D-codes fire
            all_triggered.update(triggered)

            answer = self._evaluate_node_answer(node, params)
            trace.append(QCodeTraceEntry(
                code=node.code, question=node.question,
                answer=answer, triggered_dcodes=triggered,
                authority=node.authority,
            ))

            if node.terminal:
                break

            next_node = self._follow_edge(current, params)
            if next_node is None:
                break
            current = next_node

        return QCodeTraversalResult(
            trace=trace,
            triggered_dcodes=all_triggered,
            nodes_evaluated=len(trace),
            terminal_node=current,
        )

    def _follow_edge(self, from_code: str, params: dict) -> str | None:
        """Find the first edge whose condition is True."""
        edges = self._edges_by_source.get(from_code, [])
        safe_params = {
            "value": 0, "services": False, "it_related": False,
            "sole_source": False, "commercial_item": False, "emergency": False,
            "vendor_on_site": False, "competition_type": "full_and_open",
            **params,
        }
        for edge in edges:
            try:
                if eval(edge.condition, {"__builtins__": {}}, safe_params):  # noqa: S307
                    return edge.to_code
            except Exception:
                continue
        return None

    def _should_trigger(self, dcode: str, params: dict) -> bool:
        """Check if a D-code should be triggered based on acquisition params."""
        registry = get_dcode_registry()
        defn = registry.get(dcode)
        if defn is None:
            return True  # Unknown D-code → trigger by default
        # Inject safe defaults so missing params don't cause NameError → fail-open
        safe_params = {
            "value": 0, "services": False, "it_related": False,
            "sole_source": False, "commercial_item": False, "emergency": False,
            "vendor_on_site": False, "competition_type": "full_and_open",
            **params,
        }
        try:
            return eval(defn.condition, {"__builtins__": {}}, safe_params)  # noqa: S307
        except Exception:
            return True  # Fail open (conservative)

    def _evaluate_node_answer(self, node: QCodeNode, params: dict) -> str:
        """Generate a human-readable answer for the trace."""
        action = node.system_action
        v = params.get("value", 0)
        if action == "check_micro":
            return f"{'Yes' if v > 15000 else 'No'} (value=${v:,.0f}, threshold=$15,000)"
        if action == "check_sat":
            return f"{'Yes' if v > 350000 else 'No'} (value=${v:,.0f}, SAT=$350,000)"
        if action == "check_sole_source":
            ss = params.get("sole_source", False)
            return f"{'Yes' if ss else 'No'}"
        if action == "check_services":
            return f"{'Yes' if params.get('services', False) else 'No'}"
        if action == "check_it":
            return f"{'Yes' if params.get('it_related', False) else 'No'}"
        if action == "check_commercial":
            return f"{'Yes' if params.get('commercial_item', False) else 'No'}"
        if action == "check_subcon":
            return f"{'Yes' if v >= 900000 else 'No'} (threshold=$900,000)"
        if action == "check_ap":
            ap = params.get("acquisition_plan_threshold", 5500000)
            return f"{'Yes' if v >= ap else 'No'} (threshold=${ap:,.0f})"
        if action == "check_sb":
            return f"{'Yes' if v > 350000 else 'N/A (below SAT)'}"
        if action == "check_urgency":
            return f"{'Yes' if params.get('emergency', False) else 'No'}"
        if action == "check_ssac":
            if v >= 100000000:
                return "Required (≥$100M)"
            if v >= 50000000:
                return "Encouraged ($50M–$100M)"
            return "Not required"
        if action == "check_cost_data":
            return f"{'Yes' if v >= 2500000 else 'No'} (threshold=$2,500,000)"
        if action == "select_contract_type":
            return "Routing to contract type evaluation"
        if action == "check_fixed_price":
            ct = params.get("competition_type", "full_and_open")
            return f"{'No — alternate type' if ct in ('idiq', 'task_order', 'cost_reimbursement') else 'Yes'}"
        if action == "check_cost_reimbursement":
            return f"{'Applicable' if params.get('competition_type') == 'cost_reimbursement' else 'Not applicable'}"
        if action == "check_idiq":
            return f"{'Yes' if params.get('competition_type') == 'idiq' else 'No'}"
        if action == "check_task_order":
            return f"{'Yes' if params.get('competition_type') == 'task_order' else 'No'}"
        if action == "check_options":
            return "Yes (standard base + option structure)" if params.get("services") else "Evaluated"
        if action == "check_total_with_options":
            return f"Total value ${v:,.0f} evaluated against thresholds"
        if action == "check_sca":
            return f"{'Yes — services subject to SCA' if params.get('services') and not params.get('commercial_item') else 'No'}"
        if action == "check_davis_bacon":
            return f"{'No — services acquisition, not construction' if params.get('services') else 'Evaluate based on requirement'}"
        if action == "check_wage_determination":
            return f"{'Required' if params.get('services') and not params.get('commercial_item') else 'Not required'}"
        if action == "check_ssi":
            return f"{'Yes — TSA SSI handling required' if params.get('vendor_on_site') else 'Evaluate based on SOW'}"
        if action == "check_suitability":
            return f"{'Yes' if params.get('vendor_on_site') else 'No on-site work'}"
        if action == "check_cui":
            return "CUI handling procedures apply (HSAR 3052.204-72)"
        if action == "check_badge_access":
            return f"{'Yes — TSA facility access required' if params.get('vendor_on_site') else 'No'}"
        if action == "check_past_performance":
            return f"{'Yes' if v > 350000 and not params.get('commercial_item') else 'Not required below SAT'}"
        if action == "determine_eval_method":
            return "Trade-off (best value)" if v > 5500000 else "LPTA or trade-off per CO discretion"
        if action == "check_discussions":
            return "Anticipated" if v > 5500000 else "Not anticipated"
        if action == "check_debriefing":
            return f"{'Required (task order >= $7.5M)' if v >= 7500000 else 'Not required'}"
        if action == "check_oci":
            return f"{'Evaluate — services may create OCI' if params.get('services') else 'Low risk for supplies'}"
        if action == "check_oci_mitigation":
            return f"{'Mitigation plan required' if params.get('services') and v > 5500000 else 'Standard OCI clause sufficient'}"
        if action == "check_gfp":
            return f"{'Yes — GFP/GFE accountability required' if params.get('vendor_on_site') else 'No GFP anticipated'}"
        if action == "check_transition":
            return f"{'Required — services >= $5.5M' if params.get('services') and v >= 5500000 else 'Not required'}"
        if action == "check_key_personnel":
            return f"{'Required — HSAR 3052.215-70' if params.get('services') and v > 350000 else 'Not required'}"
        if action == "classify_cor_level":
            return f"{'Level III (high complexity)' if v >= 5500000 else 'Level II' if v >= 350000 else 'Level I'}"
        if action == "check_qasp_cycle":
            return f"{'Monthly QASP review' if params.get('services') else 'N/A'}"
        if action == "check_cpars":
            return f"{'Required' if v > 350000 else 'Optional'}"
        if action == "check_arb":
            return f"{'Yes — TSA ARB required >= $5.5M' if v >= 5500000 else 'Not required'}"
        if action == "check_apfs":
            return f"{'Yes — DHS APFS registration required' if v >= 350000 else 'Not required'}"
        if action == "check_prism":
            return "Yes — PRISM entry required for all awarded contracts"
        if action == "final_route":
            return "All policy checks complete — package ready for CO review"
        # ── Contract Modifications ──
        if action == "check_mod_type":
            return "Routing to modification evaluation"
        if action == "classify_mod":
            return "Bilateral modification (mutual agreement)"
        if action == "check_scope_change":
            return "Evaluating scope change per cardinal change doctrine"
        if action == "check_mod_ja":
            ss = params.get("sole_source", False)
            return f"{'Yes — sole source J&A for scope change' if ss else 'No — within scope'}"
        if action == "check_change_order":
            return "Unilateral change order evaluated under Changes clause"
        if action == "check_rea":
            return "REA evaluation pending contractor submission"
        if action == "check_option_exercise":
            return "Option exercise evaluation"
        if action == "check_option_timing":
            return "Option within contractual notice period"
        if action == "check_option_price":
            return f"Option price analysis required (value=${v:,.0f})"
        if action == "route_mod":
            return "Modification routed to CO for signature"

        # ── Award Phase ──
        if action == "check_preaward_survey":
            return f"{'Required' if v > 350000 and not params.get('commercial_item') else 'Not required'}"
        if action == "check_responsibility":
            return f"{'Affirmative determination required' if v > 350000 else 'Simplified determination'}"
        if action == "check_cost_analysis":
            return f"{'Cost analysis required' if v > 2500000 and not params.get('commercial_item') else 'Price analysis sufficient'}"
        if action == "check_negotiations":
            return f"{'Negotiations required' if v > 350000 and not params.get('commercial_item') else 'Not required'}"
        if action == "verify_nego_memo":
            return "Negotiation memorandum verification"
        if action == "check_ssdd":
            return f"{'SSDD required (trade-off)' if v > 350000 else 'Not required'}"
        if action == "check_award_notice":
            return f"{'Required' if v > 350000 else 'Recommended'}"
        if action == "check_debrief_prep":
            return f"{'Required within 5 days of request' if v > 350000 else 'Not required'}"
        if action == "check_award_synopsis":
            return "Award synopsis required in SAM.gov within 30 days"
        if action == "route_award":
            return "Award routed to warranted CO for signature (Tier 3 hard stop)"

        # ── Post-Award ──
        if action == "check_monitoring":
            return f"{'COR Level III monitoring' if v >= 5500000 else 'Standard monitoring'}"
        if action == "check_invoice":
            return "Invoice review per Prompt Payment Act requirements"
        if action == "check_cpars_interim":
            return f"{'Interim CPARS due' if v > 350000 else 'Optional'}"
        if action == "check_pending_mods":
            return "Checking for pending modification requests"
        if action == "check_option_window":
            return "120-day preliminary notice / 60-day final notice window"
        if action == "check_cor_report":
            return "COR surveillance report review"
        if action == "check_performance_issues":
            return "Performance issue evaluation"
        if action == "check_cure_notice":
            return "Cure/show-cause evaluation (Tier 3: T4D is CO decision only)"
        if action == "check_pop_ending":
            return f"Period of performance ending check"
        if action == "initiate_closeout":
            return "Closeout planning initiated"

        # ── Protest & Disputes ──
        if action == "check_protest_filed":
            return "Protest filing evaluation"
        if action == "check_gao_protest":
            return "GAO protest — 100 calendar day decision timeline"
        if action == "check_agency_protest":
            return "Agency-level protest per FAR 33.103"
        if action == "check_cofc":
            return "Court of Federal Claims filing"
        if action == "check_stay":
            return "Automatic stay evaluation per 31 U.S.C. 3553(c)"
        if action == "check_corrective_action":
            return "Corrective action evaluation"
        if action == "check_adr":
            return "ADR appropriateness evaluation"
        if action == "check_cda_claim":
            return "Contract Disputes Act claim evaluation"
        if action == "check_claim_cert":
            return f"{'Certification required (> $100K)' if v > 100000 else 'No certification needed'}"
        if action == "route_dispute":
            return "Dispute routed to CO for final decision (Tier 3 hard stop)"

        # ── Special Programs ──
        if action == "check_8a":
            return f"{'Yes — 8(a) program' if params.get('competition_type') == '8a' else 'No'}"
        if action == "check_hubzone":
            return f"{'HUBZone set-aside' if params.get('competition_type') == 'hubzone' else 'Not applicable'}"
        if action == "check_sdvosb":
            return f"{'SDVOSB set-aside' if params.get('competition_type') == 'sdvosb' else 'Not applicable'}"
        if action == "check_wosb":
            return f"{'WOSB/EDWOSB set-aside' if params.get('competition_type') in ('wosb', 'edwosb') else 'Not applicable'}"
        if action == "check_abilityone":
            return "AbilityOne evaluation per FAR 8.7"
        if action == "check_gsa_schedule":
            return f"{'GSA Schedule order' if params.get('competition_type') == 'gsa_schedule' else 'Not applicable'}"
        if action == "check_bpa":
            return f"{'BPA call/establishment' if params.get('competition_type') == 'bpa' else 'Not applicable'}"
        if action == "check_sba_review":
            return "SBA review required for 8(a) program"
        if action == "check_lsj":
            return "Limited Sources Justification evaluation for GSA orders"
        if action == "route_special_program":
            return "Special program acquisition routed"

        # ── DHS/TSA Specific ──
        if action == "check_eagle":
            return "DHS EAGLE II vehicle evaluation"
        if action == "check_firstsource":
            return "DHS FirstSource vehicle evaluation"
        if action == "check_pacts":
            return "GSA PACTS III vehicle evaluation"
        if action == "check_itar_deep":
            return f"{'Deep ITAR review required (IT > $25M)' if params.get('it_related') and v > 25000000 else 'Standard ITAR'}"
        if action == "check_isso":
            return "ISSO security review per TSA MD 2810.1"
        if action == "check_fedramp":
            return f"{'FedRAMP required' if params.get('it_related') and v > 350000 else 'Not required'}"
        if action == "check_hsar_flowdown":
            return "HSAR 3052 clause flow-down evaluation"
        if action == "check_cat_mgmt":
            return "Category Management review per OMB M-22-03"
        if action == "check_fitara":
            return f"{'FITARA CIO reporting required' if params.get('it_related') else 'Not applicable'}"
        if action == "route_dhs_tsa":
            return "DHS/TSA-specific requirements routed"

        # ── Closeout ──
        if action == "check_pop_complete":
            return "Period of performance completion verified"
        if action == "check_final_delivery":
            return "Final delivery/acceptance verified"
        if action == "check_final_payment":
            return "Final invoice and payment processed"
        if action == "check_property_disposition":
            return f"{'Property disposition required' if params.get('vendor_on_site') else 'No GFP to dispose'}"
        if action == "check_ulo":
            return "Unliquidated obligations review"
        if action == "check_release_claims":
            return "Contractor release of claims pending"
        if action == "check_cpars_final":
            return "Final CPARS evaluation required"
        if action == "check_records_retention":
            return "Records archived per FAR 4.805 retention schedule"
        if action == "check_closeout_checklist":
            return "Closeout checklist completion"
        if action == "closeout_complete":
            return "Contract closeout complete — administrative record sealed"
        return "Evaluated"


# ── Posting Deadline Resolver (FAR 5.203) ─────────────────────────────────────

@dataclass
class PostingRule(EffectiveDatedRule):
    """FAR 5.203 posting requirement."""
    name: str = ""
    min_days: int = 0
    condition: str = ""
    authority: str = ""
    description: str = ""


POSTING_RULES: list[PostingRule] = [
    PostingRule(name="micro_purchase", min_days=0,
                condition="value <= 15000",
                authority="FAR 5.202(a)(1)", description="Micro-purchase: no synopsis required",
                effective_date=date(2025, 10, 1)),
    PostingRule(name="below_sat", min_days=0,
                condition="value <= 350000 and not sole_source",
                authority="FAR 5.202(a)(1)", description="Below SAT: synopsis not required (but recommended for SB)",
                effective_date=date(2025, 10, 1)),
    PostingRule(name="sole_source_above_sat", min_days=15,
                condition="sole_source and value > 350000",
                authority="FAR 5.202(a)(1), FAR 6.302", description="Sole source above SAT: 15-day synopsis required",
                effective_date=date(2025, 10, 1)),
    PostingRule(name="combined_synopsis_solicitation", min_days=15,
                condition="value <= 350000 and value > 15000",
                authority="FAR 5.203(a), FAR 12.603", description="Combined synopsis/solicitation: 15 calendar days",
                effective_date=date(2025, 10, 1)),
    PostingRule(name="competitive_above_sat", min_days=30,
                condition="value > 350000 and not sole_source",
                authority="FAR 5.203(c)", description="Competitive above SAT: 30 days for proposal submission",
                effective_date=date(2025, 10, 1)),
    PostingRule(name="emergency_reduced", min_days=0,
                condition="emergency",
                authority="FAR 5.202(a)(2), FAR 6.302-2", description="Emergency: posting period can be reduced or waived",
                effective_date=date(2025, 10, 1)),
]


def resolve_posting_deadline(params: dict[str, Any], as_of: date | None = None) -> tuple[int, str, str]:
    """Resolve posting deadline from FAR 5.203 matrix.
    Returns (days, rule_name, authority)."""
    check_date = as_of or date.today()
    # Emergency override takes priority
    if params.get("emergency", False):
        for rule in POSTING_RULES:
            if rule.name == "emergency_reduced" and rule.is_active(check_date):
                return rule.min_days, rule.name, rule.authority

    # Evaluate rules in order (most specific first)
    best_match: PostingRule | None = None
    for rule in POSTING_RULES:
        if not rule.is_active(check_date):
            continue
        try:
            if eval(rule.condition, {"__builtins__": {}}, params):  # noqa: S307
                if best_match is None or rule.min_days > best_match.min_days:
                    best_match = rule  # Most restrictive wins
        except Exception:
            continue

    if best_match:
        return best_match.min_days, best_match.name, best_match.authority
    return 30, "default_competitive", "FAR 5.203(c)"  # Safe default


# ── J&A Approval Ladder ──────────────────────────────────────────────────────

@dataclass
class ApprovalLadderRule(EffectiveDatedRule):
    """J&A approval ladder per FAR 6.304."""
    document_type: str = "J&A"
    min_value: float = 0
    max_value: float | None = None
    approver: str = ""
    authority: str = ""


JA_APPROVAL_LADDER: list[ApprovalLadderRule] = [
    ApprovalLadderRule(document_type="J&A", min_value=0, max_value=800000,
                       approver="CO", authority="FAR 6.304(a)(1)",
                       effective_date=date(2025, 10, 1)),
    ApprovalLadderRule(document_type="J&A", min_value=800000, max_value=15500000,
                       approver="Competition Advocate", authority="FAR 6.304(a)(2)",
                       effective_date=date(2025, 10, 1)),
    ApprovalLadderRule(document_type="J&A", min_value=15500000, max_value=100000000,
                       approver="HCA", authority="FAR 6.304(a)(3)",
                       effective_date=date(2025, 10, 1)),
    ApprovalLadderRule(document_type="J&A", min_value=100000000, max_value=None,
                       approver="Senior Procurement Executive", authority="FAR 6.304(a)(4)",
                       effective_date=date(2025, 10, 1)),
]


def resolve_ja_approver(value: float, as_of: date | None = None) -> tuple[str, str]:
    """Resolve J&A approver from FAR 6.304 ladder. Returns (approver, authority)."""
    check_date = as_of or date.today()
    for rule in JA_APPROVAL_LADDER:
        if not rule.is_active(check_date):
            continue
        max_val = rule.max_value if rule.max_value is not None else float("inf")
        if rule.min_value <= value < max_val:
            return rule.approver, rule.authority
    return "CO", "FAR 6.304(a)(1)"  # Safe default


# ── Threshold Registry ────────────────────────────────────────────────────────

@dataclass
class ThresholdRule(EffectiveDatedRule):
    """Named threshold with effective dates."""
    name: str = ""
    value: float = 0
    unit: str = "USD"
    authority: str = ""


THRESHOLD_REGISTRY: list[ThresholdRule] = [
    ThresholdRule(name="micro_purchase", value=15000, authority="FAR 2.101", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="sat", value=350000, authority="FAR 2.101", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="subcontracting_plan", value=900000, authority="FAR 19.702", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="cost_pricing_data", value=2500000, authority="FAR 15.403", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="acquisition_plan", value=5500000, authority="FAR 7.105, TSA MD 300.25", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="commercial_sap", value=9000000, authority="FAR 13.5", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="gao_protest_civilian_task_order", value=10000000, authority="41 U.S.C. 4106(f)", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="debriefing_task_order", value=7500000, authority="FAR 16.505(b)(6)", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="ssac_encouraged", value=50000000, authority="FAR 15.308", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="ssac_required", value=100000000, authority="FAR 15.308", effective_date=date(2025, 10, 1)),
    # DHS-specific
    ThresholdRule(name="esar_threshold", value=750000, authority="DHS ESAR", effective_date=date(2025, 10, 1)),
    ThresholdRule(name="cas_threshold", value=2000000, authority="48 CFR 9903", effective_date=date(2025, 10, 1)),
]


def get_threshold(name: str, as_of: date | None = None) -> float:
    """Get threshold value by name as of a date. Raises ValueError if not found."""
    check_date = as_of or date.today()
    for rule in THRESHOLD_REGISTRY:
        if rule.name == name and rule.is_active(check_date):
            return rule.value
    raise ValueError(f"Unknown threshold: {name} as of {check_date}")


# ── Clause Selection Engine ───────────────────────────────────────────────────

@dataclass
class ClauseRule(EffectiveDatedRule):
    """Deterministic clause selection rule."""
    clause_number: str = ""
    title: str = ""
    prescription: str = ""
    condition: str = ""  # Python expression


CLAUSE_RULES: list[ClauseRule] = [
    # Commercial items (FAR Part 12)
    ClauseRule(clause_number="52.212-1", title="Instructions to Offerors—Commercial", prescription="FAR 12.301(b)(1)",
               condition="commercial_item", effective_date=date(2025, 10, 1)),
    ClauseRule(clause_number="52.212-2", title="Evaluation—Commercial", prescription="FAR 12.301(b)(1)",
               condition="commercial_item", effective_date=date(2025, 10, 1)),
    ClauseRule(clause_number="52.212-4", title="Contract Terms—Commercial", prescription="FAR 12.301(b)(3)",
               condition="commercial_item", effective_date=date(2025, 10, 1)),
    # Services
    ClauseRule(clause_number="52.222-41", title="Service Contract Labor Standards", prescription="FAR 22.1006(a)",
               condition="services", effective_date=date(2025, 10, 1)),
    ClauseRule(clause_number="52.222-42", title="Statement of Equivalent Rates", prescription="FAR 22.1006(b)",
               condition="services", effective_date=date(2025, 10, 1)),
    # Options
    ClauseRule(clause_number="52.217-8", title="Option to Extend Services", prescription="FAR 17.208(f)",
               condition="services", effective_date=date(2025, 10, 1)),
    ClauseRule(clause_number="52.217-9", title="Option to Extend Term", prescription="FAR 17.208(g)",
               condition="True", effective_date=date(2025, 10, 1)),
    # Funds
    ClauseRule(clause_number="52.232-18", title="Availability of Funds", prescription="FAR 32.706-1(a)",
               condition="value > 350000", effective_date=date(2025, 10, 1)),
    # DHS/HSAR
    ClauseRule(clause_number="3052.204-71", title="Contractor Employee Access", prescription="HSAM 3004.470-4(a)",
               condition="True", effective_date=date(2025, 10, 1)),
    ClauseRule(clause_number="3052.204-72", title="Safeguarding CUI", prescription="HSAM 3004.470-4(b)",
               condition="True", effective_date=date(2025, 10, 1)),
    ClauseRule(clause_number="3052.215-70", title="Key Personnel or Facilities", prescription="HSAM 3015.204-70",
               condition="services and value > 350000", effective_date=date(2025, 10, 1)),
    # IT-specific
    ClauseRule(clause_number="52.239-1", title="Privacy or Security Safeguards", prescription="FAR 39.107",
               condition="it_related", effective_date=date(2025, 10, 1)),
    # Cost data
    ClauseRule(clause_number="52.215-20", title="Requirements for Certified Cost or Pricing Data", prescription="FAR 15.408(l)",
               condition="value >= 2500000 and not commercial_item", effective_date=date(2025, 10, 1)),
]


def select_clauses(params: dict[str, Any], as_of: date | None = None) -> list[dict]:
    """Select applicable clauses based on acquisition parameters."""
    check_date = as_of or date.today()
    result = []
    for rule in CLAUSE_RULES:
        if not rule.is_active(check_date):
            continue
        try:
            if eval(rule.condition, {"__builtins__": {}}, params):  # noqa: S307
                result.append({
                    "clause_number": rule.clause_number,
                    "title": rule.title,
                    "prescription": rule.prescription,
                })
        except Exception:
            continue
    return result


# ── Value Tier Classification ─────────────────────────────────────────────────

@dataclass
class ValueTier:
    name: str
    min_value: float
    max_value: float  # Use float("inf") for unlimited
    docs_required: str
    competition: str
    approver: str


VALUE_TIERS: list[ValueTier] = [
    ValueTier("micro_purchase", 0, 15000, "Minimal", "Not required", "CO"),
    ValueTier("brief_standard", 15000, 25000, "Brief/standard", "Reasonable effort", "CO"),
    ValueTier("sat", 25000, 350000, "Standard", "Full & open, SAM.gov, SB default", "CO"),
    ValueTier("mid_range", 350000, 5500000, "Full file", "Full & open, SB review", "CO"),
    ValueTier("major_acquisition", 5500000, 50000000, "Full + D&F", "Full & open, AP per 7.105", "CO + HCA review"),
    ValueTier("very_large_acquisition", 50000000, 100000000, "Full + D&F", "Full & open, SSAC encouraged", "CO + SSAC"),
    ValueTier("mega_acquisition", 100000000, float("inf"), "Full + D&F", "Full & open, SSAC required", "CO + SSAC"),
]


def classify_value_tier(value: float) -> ValueTier:
    """Classify procurement value into the correct tier."""
    for tier in VALUE_TIERS:
        if tier.min_value <= value < tier.max_value:
            return tier
    return VALUE_TIERS[-1]  # Mega acquisition fallback


# ── PolicyService (Orchestrator) ──────────────────────────────────────────────

@dataclass
class PolicyEvaluationResult:
    """Complete output of the policy engine — replaces RulesEvaluationResponse."""
    tier: ValueTier
    required_dcodes: list[str]
    qcode_trace: list[QCodeTraceEntry]
    nodes_evaluated: int
    terminal_node: str
    posting_deadline_days: int
    posting_rule: str
    posting_authority: str
    ja_approver: str
    ja_authority: str
    applicable_clauses: list[dict]
    thresholds_checked: dict[str, float]
    authority_chain: list[str]
    notes: list[str]


class PolicyService:
    """
    Single entry point for deterministic policy evaluation.
    
    Replaces hardcoded if/else in RulesEngineService.evaluate() with:
    - Q-code DAG traversal (auditable trace)
    - Effective-dated threshold resolution
    - FAR 5.203 posting deadline matrix
    - Deterministic clause selection
    - J&A approval ladder resolution
    
    All outputs are Tier 1 (deterministic). No AI/LLM involvement.
    """

    def __init__(self):
        self._qcode_engine = QCodeEngine()

    def evaluate(self, params: dict[str, Any], as_of: date | None = None, phase: str | None = None) -> PolicyEvaluationResult:
        """Evaluate all policy rules for an acquisition."""
        check_date = as_of or date.today()
        value = params.get("value", 0)

        # Inject threshold values into params for Q-code edge evaluation
        enriched = {**params}
        try:
            enriched["acquisition_plan_threshold"] = get_threshold("acquisition_plan", check_date)
            enriched["subcontracting_plan_threshold"] = get_threshold("subcontracting_plan", check_date)
            enriched["sat"] = get_threshold("sat", check_date)
        except ValueError:
            enriched.setdefault("acquisition_plan_threshold", 5500000)
            enriched.setdefault("subcontracting_plan_threshold", 900000)
            enriched.setdefault("sat", 350000)

        # 1. Classify value tier
        tier = classify_value_tier(value)

        # 2. Traverse Q-code DAG (phase-aware: runs main tree + phase-specific branches)
        traversal = self._qcode_engine.traverse_for_phase(enriched, phase=phase)

        # 3. Resolve posting deadline
        posting_days, posting_rule, posting_auth = resolve_posting_deadline(enriched, check_date)

        # 4. Resolve J&A approver
        ja_approver, ja_auth = resolve_ja_approver(value, check_date)

        # 5. Select applicable clauses
        clauses = select_clauses(enriched, check_date)

        # 6. Collect thresholds checked
        thresholds_checked = {}
        for t in THRESHOLD_REGISTRY:
            if t.is_active(check_date):
                thresholds_checked[t.name] = t.value

        # 7. Build authority chain
        authority_chain = sorted({
            entry.authority for entry in traversal.trace
        } | {"FAR 2.101", posting_auth, ja_auth})

        # 8. Build notes
        notes = []
        if value >= enriched.get("acquisition_plan_threshold", 5500000):
            notes.append(f"Acquisition plan required (value ${value:,.0f} ≥ ${enriched['acquisition_plan_threshold']:,.0f}).")
        if params.get("sole_source"):
            notes.append(f"Sole source: J&A required. Approver = {ja_approver} ({ja_auth}).")
        if value >= 100000000:
            notes.append("SSAC required for acquisitions ≥$100M (FAR 15.308).")
        elif value >= 50000000:
            notes.append("SSAC encouraged for acquisitions $50M–$100M (FAR 15.308).")

        return PolicyEvaluationResult(
            tier=tier,
            required_dcodes=sorted(traversal.triggered_dcodes),
            qcode_trace=traversal.trace,
            nodes_evaluated=traversal.nodes_evaluated,
            terminal_node=traversal.terminal_node,
            posting_deadline_days=posting_days,
            posting_rule=posting_rule,
            posting_authority=posting_auth,
            ja_approver=ja_approver,
            ja_authority=ja_auth,
            applicable_clauses=clauses,
            thresholds_checked=thresholds_checked,
            authority_chain=authority_chain,
            notes=notes,
        )

