"""
Phase 27: Full Document Chain Generation — Document Engines
============================================================

Generates 10 additional document types from acquisition parameters, extending
the 5 engines in Phase 9/26 (PWS, IGCE, Section L, Section M, QASP).

New engines:
  1. JAEngine         — Justification & Approval (FAR 6.302/6.304)
  2. BCMEngine        — Business Clearance Memorandum (TSA IGPM 0103.19)
  3. DFEngine         — Determination & Findings (various FAR parts)
  4. APEngine         — Acquisition Plan (HSAM Appendix Z / TSA MD 300.25)
  5. SSPEngine        — Source Selection Plan (FAR 15.303)
  6. SBReviewEngine   — DHS Form 700-22 Small Business Review
  7. CORNomEngine     — COR Nomination Letter (TSA MD 300.9)
  8. EvalWorksheetEngine — Evaluation Worksheets (FAR 15.305)
  9. AwardNoticeEngine   — Award Notification (FAR 5.301 / DHS 2140-01)
 10. SecurityReqEngine   — Security Requirements Document (HSAR 3052.204-71)

All engines follow the Propose/Redline/Explain model from Phase 9:
  - Every section has content + authority + confidence + rationale
  - Output is list[DraftSection] compatible with DraftingWorkspace
  - Tier 2: AI proposes; CO accepts/modifies/overrides
  - Tier 3 boundaries enforced where applicable

Author: Centurion Acquisitor / FedProcure
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Shared data structures (mirrors DraftSection from drafting_workspace.py)
# ---------------------------------------------------------------------------

@dataclass
class DraftSection:
    """One section of a drafted document."""
    section_id: str
    heading: str
    content: str
    authority: str = ""
    rationale: str = ""
    confidence: float = 85.0


@dataclass
class DocumentDraft:
    """Complete draft of a document with metadata."""
    doc_type: str
    sections: list[DraftSection]
    warnings: list[str] = field(default_factory=list)
    source_provenance: list[str] = field(default_factory=list)
    requires_acceptance: bool = True
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "sections": [
                {
                    "section_id": s.section_id,
                    "heading": s.heading,
                    "content": s.content,
                    "authority": s.authority,
                    "rationale": s.rationale,
                    "confidence": s.confidence,
                }
                for s in self.sections
            ],
            "warnings": self.warnings,
            "source_provenance": self.source_provenance,
            "requires_acceptance": self.requires_acceptance,
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Constants — TSA C&P Thresholds (Feb 2026)
# ---------------------------------------------------------------------------

# BCM Approval Chains
BCM_APPROVAL_CHAINS = {
    500_000: ("CS → CO", "CO"),
    5_000_000: ("CS → CO → BC", "BC"),
    20_000_000: ("CS → CO → BC → DD", "DD"),
    50_000_000: ("CS → CO → BC → DD → DAA", "DAA"),
    float("inf"): ("CS → CO → BC → DD → DAA → HCA", "HCA"),
}

# SSA Appointment
SSA_APPOINTMENT = {
    2_500_000: "CO",
    5_000_000: "BC",
    20_000_000: "DD",
    50_000_000: "DAA",
    float("inf"): "HCA",
}

# J&A Approval Ladders (TSA Feb 2026 thresholds)
JA_APPROVAL_LADDERS = {
    250_000: ("CO", "FAR 6.304(a)(1)"),
    900_000: ("CA (Competition Advocate)", "FAR 6.304(a)(2)"),
    20_000_000: ("HCA", "FAR 6.304(a)(3)"),
    float("inf"): ("DHS CPO", "FAR 6.304(a)(4)"),
}

# D&F Approval by type
DF_APPROVAL = {
    "contract_type_tm_lh_commercial_short": "CO",
    "contract_type_tm_lh_3plus": "HCA",
    "incentive_award_fee": "DHS CPO",
    "single_award_idiq_150m": "CA",
    "urgency": "HCA",
    "public_interest": "DHS CPO",
}

# AP Thresholds (TSA Feb 2026 — OTFFP only; FFP under $50M exempt)
AP_APPROVAL = {
    2_500_000: ("CO + PM → BC", "BC"),
    10_000_000: ("CO + PM + SB → BC", "BC"),
    15_000_000: ("CO + PM + SB → BC → DD", "DD"),
    50_000_000: ("CO + PM + SB → BC → DD → CA → DAA", "DAA"),
    500_000_000: ("CO + PM + SB → BC → DD → CA → DAA → HCA", "HCA"),
    float("inf"): ("CO + PM + SB → BC → DD → CA → DAA → HCA → DHS CPO", "DHS CPO"),
}

# FAR 6.302 Authorities
FAR_6302_AUTHORITIES = {
    "sole_source": ("FAR 6.302-1", "Only One Responsible Source"),
    "urgency": ("FAR 6.302-2", "Unusual and Compelling Urgency"),
    "industrial_mobilization": ("FAR 6.302-3", "Industrial Mobilization / Engineering"),
    "international_agreement": ("FAR 6.302-4", "International Agreement"),
    "national_security": ("FAR 6.302-5", "Authorized or Required by Statute"),
    "public_interest": ("FAR 6.302-7", "Public Interest"),
}

# Section G Compliance Checklist (27 items from BCM template)
SECTION_G_CHECKLIST = [
    ("G-01", "Inherently governmental analysis", "FAR 7.503"),
    ("G-02", "Acquisition Plan required/approved", "FAR 7.102, HSAM 3007.1"),
    ("G-03", "Market research conducted", "FAR 10.001"),
    ("G-04", "J&A required/approved", "FAR 6.303/6.304"),
    ("G-05", "Competition requirements met", "FAR Part 6"),
    ("G-06", "Small business review completed", "FAR 19, DHS Form 700-22"),
    ("G-07", "Subcontracting plan required/reviewed", "FAR 19.702"),
    ("G-08", "ITAR completed", "HSAM 3039.1"),
    ("G-09", "Service Contract Labor Standards applicable", "FAR 22.10"),
    ("G-10", "Wage determination obtained", "FAR 22.10"),
    ("G-11", "Non-personal services determination", "FAR 37.104"),
    ("G-12", "Performance-based requirements", "FAR 37.102, HSAM 3037.1"),
    ("G-13", "Section 508 accessibility compliance", "FAR 39.2"),
    ("G-14", "Cost/pricing data required", "FAR 15.403"),
    ("G-15", "Cost/pricing data exception applies", "FAR 15.403-1"),
    ("G-16", "Price analysis method documented", "FAR 15.404"),
    ("G-17", "IGCE prepared and compared", "HSAM"),
    ("G-18", "Organizational Conflict of Interest reviewed", "FAR 9.5"),
    ("G-19", "Responsibility determination made", "FAR 9.1"),
    ("G-20", "FAPIIS checked", "FAR 9.104-6"),
    ("G-21", "SAM.gov registration verified", "FAR 4.1102"),
    ("G-22", "Security requirements identified", "HSAR 3052.204-71"),
    ("G-23", "Government property addressed", "FAR 45"),
    ("G-24", "Option periods justified", "FAR 17.207"),
    ("G-25", "COR nomination received", "FAR 1.604"),
    ("G-26", "QASP prepared", "FAR 46.4"),
    ("G-27", "Debriefing requirements identified", "FAR 15.506"),
]

# DHS Form 700-22 Items (23 items, 3 sections)
FORM_700_22_ITEMS = [
    # Section 1: Request (Items 1-8)
    ("1", "Requisitioner Name/Office"),
    ("2", "Program Office"),
    ("3", "PR Number"),
    ("4", "Contract Specialist"),
    ("5", "Contracting Officer"),
    ("6", "Description of Requirement"),
    ("7", "Estimated Total Value"),
    ("8", "Period of Performance"),
    # Section 2: Strategy (Items 9-19)
    ("9", "Acquisition Strategy"),
    ("10", "Method of Procurement"),
    ("11", "NAICS Code"),
    ("12", "Small Business Size Standard"),
    ("13", "First Consideration (Set-Aside Type)"),
    ("14", "Second Consideration (if set-aside ruled out)"),
    ("15", "Justification for Full & Open (if applicable)"),
    ("16", "Pre-existing Contract Vehicle"),
    ("17", "Substantial Bundling Review ($2M+ open market)"),
    ("18", "Pre-existing Contracts ($2M+)"),
    ("19", "Set-Aside Recommendation"),
    # Section 3: Signatures (Items 20-23)
    ("20", "CO Concurrence"),
    ("21", "SB Specialist Concurrence"),
    ("22", "CO Response to SBS Non-Concurrence"),
    ("23", "SBA PCR Concurrence ($2M+ unrestricted)"),
]

# PIL benchmark rates (from Phase 23a)
PIL_RATES = {
    "Program Manager": {"min": 145, "max": 225, "avg": 185},
    "Project Manager": {"min": 130, "max": 200, "avg": 165},
    "Senior Systems Engineer": {"min": 140, "max": 210, "avg": 175},
    "Systems Engineer": {"min": 110, "max": 170, "avg": 140},
    "Senior Software Developer": {"min": 135, "max": 205, "avg": 170},
    "Software Developer": {"min": 100, "max": 160, "avg": 130},
    "Business Analyst": {"min": 95, "max": 155, "avg": 125},
    "Technical Writer": {"min": 75, "max": 125, "avg": 100},
    "Help Desk Specialist": {"min": 55, "max": 95, "avg": 75},
    "Data Analyst": {"min": 100, "max": 160, "avg": 130},
    "Cybersecurity Analyst": {"min": 120, "max": 185, "avg": 152},
    "Cloud Engineer": {"min": 130, "max": 195, "avg": 162},
    "Database Administrator": {"min": 105, "max": 165, "avg": 135},
    "Quality Assurance Specialist": {"min": 90, "max": 145, "avg": 117},
    "Network Engineer": {"min": 110, "max": 170, "avg": 140},
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_bcm_approval(value: float) -> tuple[str, str]:
    """Return (chain, approver) for BCM based on value."""
    for threshold, (chain, approver) in sorted(BCM_APPROVAL_CHAINS.items()):
        if value < threshold:
            return chain, approver
    return "CS → CO → BC → DD → DAA → HCA", "HCA"


def _get_ssa_appointment(value: float) -> str:
    """Return SSA appointment level for value."""
    for threshold, role in sorted(SSA_APPOINTMENT.items()):
        if value < threshold:
            return role
    return "HCA"


def _get_ja_approval(value: float) -> tuple[str, str]:
    """Return (approver, authority) for J&A based on value."""
    for threshold, (approver, authority) in sorted(JA_APPROVAL_LADDERS.items()):
        if value < threshold:
            return approver, authority
    return "DHS CPO", "FAR 6.304(a)(4)"


def _get_ap_approval(value: float) -> tuple[str, str]:
    """Return (chain, approver) for Acquisition Plan based on value."""
    for threshold, (chain, approver) in sorted(AP_APPROVAL.items()):
        if value < threshold:
            return chain, approver
    return AP_APPROVAL[float("inf")]


def _format_value(value: float) -> str:
    """Format dollar value for display."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _estimate_fte(value: float, duration_months: int = 12) -> int:
    """Estimate FTE count from value and duration."""
    avg_rate = 140  # Average across all PIL categories
    annual_hours = 1920  # Billable hours per year
    annual_cost = avg_rate * annual_hours
    years = max(duration_months / 12, 1)
    return max(1, round(value / (annual_cost * years)))


# ========================================================================
# Engine 1: J&A Engine (FAR 6.302 / 6.304)
# ========================================================================

class JAEngine:
    """Generates Justification & Approval documents per FAR 6.302/6.304.

    Supports FAR 6.302-1 through 6.302-7 justification types.
    Approval ladder derived from TSA C&P Feb 2026 thresholds.
    """

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate J&A sections.

        Required params: estimated_value, justification_type (sole_source, urgency, etc.)
        Optional: contractor_name, requirement_description, market_research_summary,
                  duration_months, services
        """
        value = params.get("estimated_value", 0)
        just_type = params.get("justification_type", "sole_source")
        contractor = params.get("contractor_name", "[Contractor Name]")
        description = params.get("requirement_description", "[Requirement description]")
        market_research = params.get("market_research_summary", "")
        services = params.get("services", True)

        authority_code, authority_name = FAR_6302_AUTHORITIES.get(
            just_type, ("FAR 6.302-1", "Only One Responsible Source")
        )
        approver, approval_far = _get_ja_approval(value)

        sections = []

        # Section 1: Contracting Activity
        sections.append(DraftSection(
            section_id="JA-01",
            heading="1. Contracting Activity",
            content=(
                "Transportation Security Administration (TSA)\n"
                "Department of Homeland Security\n"
                "Contracting and Procurement Division"
            ),
            authority="FAR 6.303-2(a)(1)",
            rationale="Identifies the responsible contracting activity.",
            confidence=95.0,
        ))

        # Section 2: Description of Action
        sections.append(DraftSection(
            section_id="JA-02",
            heading="2. Nature and/or Description of the Action",
            content=(
                f"This justification supports the award of a contract to {contractor} "
                f"for {description}.\n\n"
                f"Estimated Value: {_format_value(value)}\n"
                f"Contract Type: {'Services' if services else 'Supplies'}\n"
                f"NAICS: {params.get('naics_code', '[NAICS]')}"
            ),
            authority="FAR 6.303-2(a)(2)",
            rationale="Describes the supplies or services required and the estimated value.",
            confidence=85.0,
        ))

        # Section 3: Authority
        sections.append(DraftSection(
            section_id="JA-03",
            heading="3. Authority",
            content=(
                f"This action is justified under {authority_code}, {authority_name}.\n\n"
                f"{self._get_authority_narrative(just_type, contractor, description)}"
            ),
            authority=authority_code,
            rationale=f"Cites the specific statutory authority for other than full and open competition.",
            confidence=90.0,
        ))

        # Section 4: Reason for Authority
        sections.append(DraftSection(
            section_id="JA-04",
            heading="4. Demonstration that the Contractor's Unique Qualifications or the Nature "
                    "of the Acquisition Requires Use of the Authority Cited",
            content=self._get_reason_narrative(just_type, contractor, description, params),
            authority="FAR 6.303-2(a)(4)",
            rationale="Provides factual basis for the cited authority.",
            confidence=75.0,
        ))

        # Section 5: Market Research
        sections.append(DraftSection(
            section_id="JA-05",
            heading="5. Description of Market Research",
            content=(
                market_research if market_research else
                f"Market research was conducted in accordance with FAR Part 10 to determine "
                f"whether the Government's needs can be met through competitive means. "
                f"Research included review of SAM.gov, GSA Advantage, and available DHS "
                f"contract vehicles. [CO: Insert specific market research findings and why "
                f"competitive procurement is not feasible.]"
            ),
            authority="FAR 6.303-2(a)(7), FAR 10.002",
            rationale="Documents market research supporting the justification.",
            confidence=65.0 if not market_research else 80.0,
        ))

        # Section 6: Actions to Increase Competition
        sections.append(DraftSection(
            section_id="JA-06",
            heading="6. Actions to Remove or Overcome Barriers to Competition",
            content=(
                "The following actions will be taken to increase competition for "
                "future acquisitions of this requirement:\n\n"
                "a. The Government will conduct ongoing market research to identify "
                "potential alternative sources.\n"
                "b. A competitive follow-on procurement will be planned with sufficient "
                "lead time to ensure full and open competition.\n"
                "c. Requirements will be reviewed to eliminate any unnecessarily "
                "restrictive specifications."
            ),
            authority="FAR 6.303-2(a)(5)",
            rationale="Required plan to increase future competition.",
            confidence=85.0,
        ))

        # Section 7: Determination of Fair and Reasonable Price
        sections.append(DraftSection(
            section_id="JA-07",
            heading="7. Determination of Fair and Reasonable Price",
            content=(
                "The Contracting Officer will determine price reasonableness using "
                "one or more of the following methods per FAR 15.404-1:\n\n"
                "a. Comparison with IGCE\n"
                "b. Comparison with prior contract prices\n"
                "c. Analysis of DHS PIL benchmark rates\n"
                f"d. {'Cost analysis per FAR 15.404-1(c)' if value >= 2_500_000 else 'Price analysis per FAR 15.404-1(b)'}"
            ),
            authority="FAR 6.303-2(a)(8)",
            rationale="Documents method for determining price reasonableness.",
            confidence=85.0,
        ))

        # Section 8: Approval
        sections.append(DraftSection(
            section_id="JA-08",
            heading="8. Approval",
            content=(
                f"Approval Authority: {approver}\n"
                f"Authority: {approval_far}\n"
                f"Value: {_format_value(value)}\n\n"
                "Signature: ____________________________\n"
                "Date: ____________________________\n\n"
                f"{'NOTE: HSAM 3004.7003 requires legal sufficiency review for justifications exceeding $500,000.' if value > 500_000 else ''}"
            ),
            authority=approval_far,
            rationale=f"Approval per TSA C&P thresholds (Feb 2026). Value {_format_value(value)} → {approver}.",
            confidence=95.0,
        ))

        return sections

    def _get_authority_narrative(self, just_type: str, contractor: str, description: str) -> str:
        narratives = {
            "sole_source": (
                f"{contractor} is the only responsible source that can provide "
                f"the required services/supplies. No other source possesses the "
                f"unique capabilities, proprietary data, or specialized expertise "
                f"required to fulfill this requirement."
            ),
            "urgency": (
                "An unusual and compelling urgency exists that does not permit "
                "the delay associated with competitive solicitation. The Government "
                "would be seriously injured unless the agency is permitted to limit "
                "the number of sources from which it solicits."
            ),
            "industrial_mobilization": (
                "This acquisition is necessary to maintain a facility, producer, "
                "manufacturer, or other supplier available for furnishing supplies "
                "or services in case of a national emergency."
            ),
            "international_agreement": (
                "This acquisition is required by the terms of an international "
                "agreement or treaty with a foreign government or international "
                "organization."
            ),
            "national_security": (
                "This acquisition is authorized or required by statute, specifically "
                "pertaining to national security considerations."
            ),
            "public_interest": (
                "The agency head has determined that it is not in the public interest "
                "to use competitive procedures for this acquisition."
            ),
        }
        return narratives.get(just_type, narratives["sole_source"])

    def _get_reason_narrative(self, just_type: str, contractor: str,
                              description: str, params: dict) -> str:
        if just_type == "sole_source":
            return (
                f"{contractor} is uniquely qualified to perform this requirement because:\n\n"
                f"a. [CO: Describe contractor's unique qualifications, proprietary "
                f"data, or specialized expertise]\n"
                f"b. [CO: Explain why no other source can satisfy the requirement]\n"
                f"c. [CO: Reference any relevant past performance or existing "
                f"system integration requirements]\n\n"
                f"NOTE: FAR 6.302-1 for civilian agencies does NOT authorize "
                f"follow-on contracts based solely on prior performance. Each "
                f"sole source justification must stand on its own merits."
            )
        elif just_type == "urgency":
            return (
                "The urgency of this requirement is based on the following:\n\n"
                "a. [CO: Describe the specific circumstances creating urgency]\n"
                "b. [CO: Explain why competitive procurement timeline is insufficient]\n"
                "c. [CO: Document that the urgency is NOT due to lack of advance planning]\n\n"
                "NOTE: Per FAR 6.302-2, urgency caused by delayed recompete from "
                "poor planning does NOT qualify as unusual and compelling."
            )
        else:
            return (
                f"[CO: Provide detailed factual basis supporting the use of "
                f"{FAR_6302_AUTHORITIES.get(just_type, ('', ''))[1]} authority. "
                f"Include specific circumstances, evidence, and rationale.]"
            )


# ========================================================================
# Engine 2: BCM Engine (TSA IGPM 0103.19)
# ========================================================================

class BCMEngine:
    """Generates Business Clearance Memorandum per TSA IGPM 0103.19.

    Supports: Streamlined, Pre-Competitive, Pre/Post Sole Source,
    Pre/Post Competitive, OTA Streamlined.
    """

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate BCM sections A through H.

        Required params: estimated_value, bcm_type
        Optional: contractor_name, contract_number, solicitation_number,
                  naics_code, psc_code, contract_type, pop_months,
                  competition_type, requirement_description
        """
        value = params.get("estimated_value", 0)
        bcm_type = params.get("bcm_type", "pre_competitive")
        contractor = params.get("contractor_name", "[Contractor Name]")
        contract_num = params.get("contract_number", "[Contract Number]")
        sol_num = params.get("solicitation_number", "[Solicitation Number]")
        naics = params.get("naics_code", "[NAICS]")
        psc = params.get("psc_code", "[PSC]")
        contract_type_str = params.get("contract_type", "FFP")
        pop = params.get("pop_months", 12)
        description = params.get("requirement_description", "[Description]")
        competition = params.get("competition_type", "full_and_open")

        chain, approver = _get_bcm_approval(value)

        sections = []

        # Section A: Acquisition Information
        sections.append(DraftSection(
            section_id="BCM-A",
            heading="Section A — Acquisition Information",
            content=(
                f"Contract Number: {contract_num}\n"
                f"Solicitation Number: {sol_num}\n"
                f"NAICS Code: {naics}\n"
                f"PSC Code: {psc}\n"
                f"Contract Type: {contract_type_str}\n"
                f"Period of Performance: {pop} months (Base + Options)\n"
                f"Estimated Total Value: {_format_value(value)}\n"
                f"Contractor: {contractor}\n"
                f"Description: {description}"
            ),
            authority="IGPM 0103.19",
            rationale="Standard acquisition identification block.",
            confidence=90.0,
        ))

        # Section B: Business Clearance Information
        b_content = self._generate_section_b(bcm_type, value, competition, params)
        sections.append(DraftSection(
            section_id="BCM-B",
            heading="Section B — Business Clearance Information",
            content=b_content,
            authority="IGPM 0103.19, FAR 15.406-3",
            rationale=f"BCM type: {bcm_type}. Contains pre/post-negotiation objectives.",
            confidence=75.0,
        ))

        # Section C: Recommendation Summary
        sections.append(DraftSection(
            section_id="BCM-C",
            heading="Section C — Recommendation Summary",
            content=(
                f"BCM Type: {bcm_type.replace('_', ' ').title()}\n\n"
                f"[ ] Unconditional Approval — No further action required\n"
                f"[ ] Conditional Approval — Resubmit after disposition of conditions\n\n"
                f"Approval Authority: {approver}\n"
                f"Approval Chain: {chain}"
            ),
            authority="IGPM 0103.19",
            rationale=f"Value {_format_value(value)} → {approver} approval per TSA C&P thresholds.",
            confidence=95.0,
        ))

        # Section D: Review and Approvals
        sections.append(DraftSection(
            section_id="BCM-D",
            heading="Section D — Review and Approvals",
            content=self._generate_signature_block(chain, approver),
            authority="IGPM 0103.19, TSA C&P Thresholds (Feb 2026)",
            rationale=f"Signature chain for {_format_value(value)} acquisition.",
            confidence=95.0,
        ))

        # Section E: Analysis / Key Highlights
        sections.append(DraftSection(
            section_id="BCM-E",
            heading="Section E — Analysis (Key Highlights Timeline)",
            content=self._generate_timeline(bcm_type),
            authority="IGPM 0103.19",
            rationale="Tracks acquisition lifecycle milestones from PSR through award.",
            confidence=70.0,
        ))

        # Section F: Proposal Summary
        if bcm_type in ("pre_competitive", "pre_post_competitive"):
            sections.append(DraftSection(
                section_id="BCM-F",
                heading="Section F — Proposal Summary",
                content=(
                    "Evaluation Factor Ratings by Offeror:\n\n"
                    "[CO: Insert evaluation summary table with:\n"
                    "  - Offeror names\n"
                    "  - Factor ratings (adjectival)\n"
                    "  - Strengths/Weaknesses/Deficiencies per factor\n"
                    "  - Price comparison]\n\n"
                    "Total Proposals Received: [Number]\n"
                    "Technically Acceptable: [Number]\n"
                    "In Competitive Range: [Number]"
                ),
                authority="FAR 15.305, FAR 15.306",
                rationale="Summarizes evaluation results for approval authority review.",
                confidence=60.0,
            ))

        # Section G: Compliance Checklist (27 items)
        g_items = []
        for item_id, item_name, item_auth in SECTION_G_CHECKLIST:
            applicable = self._check_g_applicability(item_id, params)
            g_items.append(
                f"  {item_id}. {item_name}\n"
                f"    Authority: {item_auth}\n"
                f"    Status: {'[ ] Yes  [ ] No  [ ] N/A' if applicable else '[ ] N/A (not applicable)'}"
            )
        sections.append(DraftSection(
            section_id="BCM-G",
            heading="Section G — Pre/Post-Negotiation Compliance/Determinations",
            content="27-Item Compliance Checklist:\n\n" + "\n\n".join(g_items),
            authority="IGPM 0103.19",
            rationale="Each item verified against FAR/HSAM/TSA policy requirements.",
            confidence=85.0,
        ))

        # Section H: Pricing Analysis
        sections.append(DraftSection(
            section_id="BCM-H",
            heading="Section H — Pre/Post-Negotiation Analysis",
            content=self._generate_pricing_section(value, params),
            authority="FAR 15.404-1, FAR 15.406-3",
            rationale="Detailed pricing analysis supporting fair and reasonable determination.",
            confidence=70.0,
        ))

        return sections

    def _generate_section_b(self, bcm_type: str, value: float,
                            competition: str, params: dict) -> str:
        if bcm_type == "pre_competitive":
            return (
                "PRE-NEGOTIATION OBJECTIVES (Competitive)\n\n"
                "Purpose: Request authority to enter discussions per FAR 15.306.\n\n"
                "Procurement History:\n"
                "[CO: Summarize from PSR through proposal receipt and evaluation]\n\n"
                "Need for Discussions:\n"
                "[CO: Explain why award on initial proposals is not possible "
                "and why discussions are necessary]\n\n"
                "Discussion Topics:\n"
                "[CO: Identify areas requiring clarification or negotiation]"
            )
        elif bcm_type == "pre_post_sole_source":
            return (
                "PRE/POST-NEGOTIATION (Sole Source)\n\n"
                "Pre-Negotiation Position:\n"
                f"  Government Objective: {_format_value(value * 0.95)}\n"
                f"  Contractor Proposal: [CO: Insert proposed amount]\n"
                f"  IGCE: {_format_value(value)}\n\n"
                "Post-Negotiation Summary:\n"
                "  Negotiated Amount: [CO: Insert final amount]\n"
                "  Savings: [CO: Calculate delta]\n\n"
                "Determination of Fair and Reasonable:\n"
                "[CO: Document price analysis method per FAR 15.404-1]"
            )
        elif bcm_type == "pre_post_competitive":
            return (
                "PRE/POST-NEGOTIATION (Competitive)\n\n"
                "This Pre/Post BCM documents the complete evaluation and "
                "negotiation for award on initial offers (no discussions required).\n\n"
                "Evaluation Summary:\n"
                "[CO: Insert offeror rankings with adjectival ratings]\n\n"
                "Post-Negotiation Summary:\n"
                "[CO: Document final evaluated prices and selection rationale]\n\n"
                "Determination of Fair and Reasonable:\n"
                "[CO: Document adequate price competition per FAR 15.403-1(c)(1)]"
            )
        elif bcm_type == "streamlined":
            return (
                "STREAMLINED ACQUISITION (Task Order under Existing Vehicle)\n\n"
                "Vehicle: [CO: OASIS, EAGLE, PACTS III, etc.]\n"
                "Task Order Number: [CO: Insert]\n\n"
                "Fair Opportunity Provided: Yes / Exception Applied\n"
                "[CO: Document fair opportunity process per FAR 16.505]"
            )
        else:  # ota_streamlined
            return (
                "OTA STREAMLINED\n\n"
                "Other Transaction Authority: TSA MD 300.23\n"
                "[CO: Document OTA justification and pricing basis]"
            )

    def _generate_signature_block(self, chain: str, approver: str) -> str:
        roles = chain.split(" → ")
        lines = []
        for role in roles:
            action = "Approves" if role == approver else "Reviews"
            lines.append(
                f"{role} — {action}\n"
                f"  Name: ____________________________\n"
                f"  Signature: ____________________________\n"
                f"  Date: ____________________________"
            )
        return "\n\n".join(lines)

    def _generate_timeline(self, bcm_type: str) -> str:
        milestones = [
            "PSR (Procurement Strategy Review)",
            "Inherently Governmental Analysis",
            "PSR Finding Disposition",
            "ITAR Review",
            "SRB (Solicitation Review Board)",
            "SRB Finding Disposition",
            "Solicitation Review (Chief Counsel)",
            "Appendix G Approval",
            "Solicitation Release",
        ]
        if bcm_type in ("pre_competitive", "pre_post_competitive"):
            milestones.extend([
                "Amendment(s)",
                "Proposal Receipt",
                "Oral Presentations (if applicable)",
                "Technical/Price Evaluation",
                "Chief Counsel Review",
                "Award Recommendation Memo",
                "SSA Decision Memo",
            ])
        return "\n".join(
            f"  {i+1}. {m} — Date: [______]"
            for i, m in enumerate(milestones)
        )

    def _check_g_applicability(self, item_id: str, params: dict) -> bool:
        """Determine if a G-checklist item is applicable based on params."""
        services = params.get("services", True)
        value = params.get("estimated_value", 0)
        sole_source = params.get("sole_source", False) or params.get("competition_type") == "sole_source"

        # Items always applicable
        always = {"G-01", "G-03", "G-05", "G-18", "G-19", "G-20", "G-21"}
        if item_id in always:
            return True
        # J&A only for sole source
        if item_id == "G-04":
            return sole_source
        # AP — only OTFFP above SAT or any above $50M
        if item_id == "G-02":
            ct = params.get("contract_type", "FFP")
            if ct == "FFP" and value < 50_000_000:
                return False
            return value > 350_000
        # Services-only items
        if item_id in ("G-09", "G-10", "G-11", "G-12", "G-26"):
            return services
        # Cost data
        if item_id in ("G-14", "G-15"):
            return value >= 2_500_000
        # Subcontracting plan
        if item_id == "G-07":
            return value >= 900_000
        # Options
        if item_id == "G-24":
            return params.get("has_options", True)
        # Debriefing
        if item_id == "G-27":
            return value > 350_000 and not sole_source
        return True

    def _generate_pricing_section(self, value: float, params: dict) -> str:
        method = "cost analysis per FAR 15.404-1(c)" if value >= 2_500_000 else "price analysis per FAR 15.404-1(b)"
        return (
            f"Price Analysis Method: {method}\n\n"
            "CLIN-by-CLIN Comparison:\n"
            "[CO: Insert CLIN structure with proposed vs IGCE vs negotiated amounts]\n\n"
            "Labor Rate Analysis:\n"
            "[CO: Compare proposed rates against DHS PIL benchmarks and prior contract rates]\n\n"
            f"IGCE Total: {_format_value(value)}\n"
            "Proposed Total: [CO: Insert]\n"
            "Negotiated Total: [CO: Insert]\n\n"
            "Determination: The Contracting Officer determines the final negotiated "
            "price to be fair and reasonable based on the above analysis."
        )


# ========================================================================
# Engine 3: D&F Engine (Various FAR Parts)
# ========================================================================

class DFEngine:
    """Generates Determination & Findings documents per various FAR parts.

    Supports: contract_type (T&M/LH), incentive/award fee, urgency,
    single_award_idiq, option_exercise, public_interest.
    """

    DF_TYPES = {
        "contract_type_tm_lh": {
            "title": "Contract Type — Time & Materials / Labor Hour",
            "authority": "FAR 16.601(d)",
            "determination": (
                "No other contract type is suitable because the work cannot be "
                "defined with sufficient precision to permit a firm-fixed-price "
                "contract, and the level of effort is unknown."
            ),
        },
        "incentive_award_fee": {
            "title": "Incentive / Award Fee Contract",
            "authority": "FAR 16.401",
            "determination": (
                "An incentive/award fee arrangement is in the Government's best "
                "interest to motivate contractor performance above minimum standards."
            ),
        },
        "urgency": {
            "title": "Unusual and Compelling Urgency",
            "authority": "FAR 6.302-2",
            "determination": (
                "An unusual and compelling urgency exists that precludes full and "
                "open competition. The Government would be seriously injured unless "
                "the agency limits the sources solicited."
            ),
        },
        "single_award_idiq": {
            "title": "Single Award Indefinite-Delivery/Indefinite-Quantity",
            "authority": "FAR 16.504(c)",
            "determination": (
                "A single-award IDIQ contract is justified because the expected "
                "orders are so integrally related that only a single source can "
                "reasonably perform the work."
            ),
        },
        "option_exercise": {
            "title": "Option Exercise",
            "authority": "FAR 17.207",
            "determination": (
                "Exercise of the option is the most advantageous method of "
                "fulfilling the Government's need, price and other factors "
                "considered."
            ),
        },
        "public_interest": {
            "title": "Public Interest Determination",
            "authority": "FAR 6.302-7",
            "determination": (
                "The agency head has determined that it is not in the public "
                "interest to use competitive procedures in this case."
            ),
        },
    }

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate D&F sections.

        Required params: estimated_value, df_type
        Optional: contractor_name, requirement_description, contract_type,
                  duration_months
        """
        value = params.get("estimated_value", 0)
        df_type = params.get("df_type", "contract_type_tm_lh")
        contractor = params.get("contractor_name", "[Contractor Name]")
        description = params.get("requirement_description", "[Requirement description]")

        df_info = self.DF_TYPES.get(df_type, self.DF_TYPES["contract_type_tm_lh"])
        approver = self._get_df_approver(df_type, value)

        sections = []

        # Header
        sections.append(DraftSection(
            section_id="DF-01",
            heading="Determination and Findings",
            content=(
                f"Subject: {df_info['title']}\n"
                f"Authority: {df_info['authority']}\n"
                f"Estimated Value: {_format_value(value)}\n"
                f"Contractor: {contractor}"
            ),
            authority=df_info["authority"],
            rationale="Standard D&F header identifying the subject and authority.",
            confidence=95.0,
        ))

        # Findings
        sections.append(DraftSection(
            section_id="DF-02",
            heading="Findings",
            content=(
                f"1. The {description} is required to support TSA mission operations.\n\n"
                f"2. The estimated value of this requirement is {_format_value(value)}.\n\n"
                f"3. {self._get_findings_narrative(df_type, contractor, params)}\n\n"
                f"4. [CO: Insert additional findings specific to this action]"
            ),
            authority=df_info["authority"],
            rationale="Factual basis supporting the determination.",
            confidence=75.0,
        ))

        # Determination
        sections.append(DraftSection(
            section_id="DF-03",
            heading="Determination",
            content=(
                f"Based on the above findings, I hereby determine that:\n\n"
                f"{df_info['determination']}\n\n"
                f"This determination is made in accordance with {df_info['authority']}."
            ),
            authority=df_info["authority"],
            rationale="The formal determination statement.",
            confidence=85.0,
        ))

        # Approval
        sections.append(DraftSection(
            section_id="DF-04",
            heading="Approval",
            content=(
                f"Approval Authority: {approver}\n\n"
                f"Signature: ____________________________\n"
                f"Name: ____________________________\n"
                f"Title: {approver}\n"
                f"Date: ____________________________"
            ),
            authority=df_info["authority"],
            rationale=f"Approval per TSA C&P thresholds. D&F type '{df_type}' → {approver}.",
            confidence=95.0,
        ))

        return sections

    def _get_df_approver(self, df_type: str, value: float) -> str:
        """Determine D&F approval authority based on type and value."""
        if df_type == "contract_type_tm_lh":
            # Commercial T&M/LH <3 years = CO; 3+ years = HCA
            duration = 36  # Default assumption
            return "CO" if duration < 36 else "HCA"
        elif df_type == "incentive_award_fee":
            return "DHS CPO"
        elif df_type == "single_award_idiq":
            return "CA" if value >= 150_000_000 else "CO"
        elif df_type == "urgency":
            return "HCA"
        elif df_type == "public_interest":
            return "DHS CPO"
        elif df_type == "option_exercise":
            return "CO"
        return "CO"

    def _get_findings_narrative(self, df_type: str, contractor: str, params: dict) -> str:
        if df_type == "contract_type_tm_lh":
            return (
                "The nature of this requirement involves [CO: describe variable scope]. "
                "The Government cannot reasonably estimate the level of effort required. "
                "A ceiling price will be established per FAR 16.601(c), and the contractor "
                "will not exceed the ceiling without prior CO authorization."
            )
        elif df_type == "option_exercise":
            return (
                f"Exercise of this option with {contractor} is the most advantageous "
                f"method because: (a) the contractor's performance has been satisfactory; "
                f"(b) the option price is fair and reasonable; (c) the option was "
                f"evaluated as part of the initial competition; (d) funds are available."
            )
        elif df_type == "urgency":
            return (
                "The urgency is based on [CO: specific circumstances]. "
                "This urgency is NOT the result of a failure to plan in advance. "
                "Per FAR 6.302-2, delayed recompete from poor planning does not "
                "constitute unusual and compelling urgency."
            )
        return f"[CO: Insert specific findings for {df_type} determination.]"


# ========================================================================
# Engine 4: Acquisition Plan Engine (HSAM Appendix Z / TSA MD 300.25)
# ========================================================================

class APEngine:
    """Generates Acquisition Plan per HSAM Appendix Z and TSA MD 300.25.

    NOTE: Per HSAM 3007.103(e), FFP acquisitions under $50M do NOT require
    a written Acquisition Plan. Only OTFFP triggers AP below $50M.
    """

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate AP sections per HSAM Appendix Z.

        Required params: estimated_value, contract_type
        Optional: requirement_description, naics_code, services, is_it,
                  competition_type, pop_months, has_options, sub_agency
        """
        value = params.get("estimated_value", 0)
        contract_type = params.get("contract_type", "FFP")
        description = params.get("requirement_description", "[Requirement description]")
        naics = params.get("naics_code", "[NAICS]")
        services = params.get("services", True)
        is_it = params.get("is_it", params.get("it_related", False))
        competition = params.get("competition_type", "full_and_open")
        pop = params.get("pop_months", 12)

        chain, approver = _get_ap_approval(value)

        sections = []
        warnings = []

        # Check AP applicability
        if contract_type == "FFP" and value < 50_000_000:
            warnings.append(
                "HSAM 3007.103(e): FFP under $50M does not require a written AP. "
                "This AP is generated for planning purposes only."
            )

        # 1. Acquisition Background and Objectives
        sections.append(DraftSection(
            section_id="AP-01",
            heading="1. Acquisition Background and Objectives",
            content=(
                f"1.1 Statement of Need\n"
                f"{description}\n\n"
                f"1.2 Applicable Conditions\n"
                f"  NAICS: {naics}\n"
                f"  Estimated Value: {_format_value(value)}\n"
                f"  Contract Type: {contract_type}\n"
                f"  Period of Performance: {pop} months\n"
                f"  {'IT Acquisition — FITARA review required per HSAM 3007.103(j)' if is_it else 'Non-IT Acquisition'}\n\n"
                f"1.3 Delivery or Performance Period Requirements\n"
                f"[CO: Specify desired performance start date and any phasing requirements]"
            ),
            authority="FAR 7.105(a)(1), HSAM Appendix Z",
            rationale="Establishes the business case and key parameters.",
            confidence=80.0,
        ))

        # 2. Plan of Action
        sections.append(DraftSection(
            section_id="AP-02",
            heading="2. Plan of Action",
            content=(
                f"2.1 Sources\n"
                f"Competition: {competition.replace('_', ' ').title()}\n"
                f"[CO: Identify known potential sources and basis for competition strategy]\n\n"
                f"2.2 Competition\n"
                f"{'Full and open competition per FAR Part 6.' if competition == 'full_and_open' else 'Other than full and open competition — J&A required per FAR 6.303.'}\n\n"
                f"2.3 Contract Type Selection\n"
                f"{contract_type} — {self._get_contract_type_rationale(contract_type, value)}\n\n"
                f"2.4 Source Selection Procedures\n"
                f"{'Best Value Tradeoff per FAR 15.101-1' if value >= 5_000_000 else 'Simplified evaluation procedures'}\n"
                f"SSA: {_get_ssa_appointment(value)}"
            ),
            authority="FAR 7.105(a)(2)-(6), HSAM Appendix Z",
            rationale="Documents the competition and contract type strategy.",
            confidence=80.0,
        ))

        # 3. Small Business Considerations
        sections.append(DraftSection(
            section_id="AP-03",
            heading="3. Small Business Considerations",
            content=(
                "Small business set-aside analysis per FAR Part 19:\n\n"
                "[CO: Document Rule of Two analysis]\n"
                "[CO: Document coordination with SB Specialist]\n"
                f"{'DHS Form 700-22 required (value exceeds $100K)' if value > 100_000 else 'DHS Form 700-22 not required (under $100K)'}\n\n"
                f"Subcontracting Plan: {'Required per FAR 19.702 (value exceeds $900K)' if value >= 900_000 else 'Not required (under $900K threshold)'}"
            ),
            authority="FAR 7.105(b)(4), FAR 19",
            rationale="Addresses small business participation requirements.",
            confidence=80.0,
        ))

        # 4. Security Considerations
        sections.append(DraftSection(
            section_id="AP-04",
            heading="4. Security Considerations",
            content=(
                "Security requirements for this acquisition:\n\n"
                f"{'Personnel security clearance requirements apply.' if params.get('classified') or params.get('clearance_required') else 'No classified access required.'}\n"
                f"{'SSI handling requirements per TSA MD 2810.' if params.get('handles_ssi') else ''}\n"
                f"{'FISMA/FedRAMP requirements apply for IT systems.' if is_it else ''}\n"
                f"HSAR 3052.204-71/72 clauses {'will' if services else 'may'} be included."
            ),
            authority="HSAR 3052.204-71, FAR 7.105(b)(6)",
            rationale="Documents security requirements and applicable clauses.",
            confidence=80.0,
        ))

        # 5. Milestones
        sections.append(DraftSection(
            section_id="AP-05",
            heading="5. Milestones for the Acquisition Cycle",
            content=self._generate_milestones(value, competition),
            authority="FAR 7.105(b)(21)",
            rationale="Key dates for the acquisition lifecycle.",
            confidence=70.0,
        ))

        # 6. Approvals
        if is_it:
            sections.append(DraftSection(
                section_id="AP-06a",
                heading="6. TSA CIO Review (FITARA)",
                content=(
                    "Per HSAM 3007.103(j), the TSA CIO must review and sign any "
                    "Acquisition Plan that includes IT prior to C&P submission.\n\n"
                    "CIO Signature: ____________________________\n"
                    "Date: ____________________________"
                ),
                authority="HSAM 3007.103(j), FITARA",
                rationale="IT acquisitions require CIO sign-off on AP before C&P submission.",
                confidence=95.0,
            ))

        sections.append(DraftSection(
            section_id="AP-06",
            heading=f"{'7' if is_it else '6'}. Approval",
            content=(
                f"Approval Authority: {approver}\n"
                f"Approval Chain: {chain}\n\n"
                "Signature: ____________________________\n"
                f"Name: ____________________________\n"
                f"Title: {approver}\n"
                "Date: ____________________________"
            ),
            authority="TSA C&P Thresholds (Feb 2026), TSA MD 300.25",
            rationale=f"AP approval for {_format_value(value)} OTFFP → {approver}.",
            confidence=95.0,
        ))

        return sections

    def _get_contract_type_rationale(self, ct: str, value: float) -> str:
        rationales = {
            "FFP": "Firm-Fixed-Price is appropriate when the requirement is well-defined and risk is manageable.",
            "T&M": "Time-and-Materials is justified because the scope cannot be defined with sufficient precision. D&F required per FAR 16.601(d).",
            "LH": "Labor-Hour is justified because the scope cannot be defined with sufficient precision. D&F required per FAR 16.601(d).",
            "CPAF": "Cost-Plus-Award-Fee provides incentive for superior performance. Award fee plan required.",
            "CPFF": "Cost-Plus-Fixed-Fee is appropriate for research/development where effort is uncertain.",
            "CPIF": "Cost-Plus-Incentive-Fee provides balanced motivation for cost control and performance.",
            "IDIQ": "Indefinite-Delivery/Indefinite-Quantity provides flexibility for variable demand.",
        }
        return rationales.get(ct, f"Contract type {ct} selected based on requirement analysis.")

    def _generate_milestones(self, value: float, competition: str) -> str:
        milestones = [
            ("Market Research Complete", "[Date]"),
            ("Requirements Package Submitted", "[Date]"),
            ("Acquisition Plan Approved", "[Date]"),
            ("Small Business Review Complete", "[Date]"),
            ("ITAR Complete", "[Date]"),
            ("Solicitation Review Board", "[Date]"),
        ]
        if competition == "full_and_open":
            milestones.extend([
                ("Solicitation Release", "[Date]"),
                ("Proposal Receipt", "[Date]"),
                ("Evaluation Complete", "[Date]"),
                ("BCM Approved", "[Date]"),
                ("Award", "[Date]"),
            ])
        else:
            milestones.extend([
                ("J&A Approved", "[Date]"),
                ("Negotiations Complete", "[Date]"),
                ("BCM Approved", "[Date]"),
                ("Award", "[Date]"),
            ])
        return "\n".join(f"  {i+1}. {name}: {date}" for i, (name, date) in enumerate(milestones))


# ========================================================================
# Engine 5: Source Selection Plan Engine (FAR 15.303)
# ========================================================================

class SSPEngine:
    """Generates Source Selection Plan per FAR 15.303.

    Documents evaluation factors, procedures, and rating methodology.
    """

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate SSP sections.

        Required params: estimated_value
        Optional: evaluation_type, eval_factors, naics_code, services
        """
        value = params.get("estimated_value", 0)
        eval_type = params.get("evaluation_type", "tradeoff")
        factors = params.get("eval_factors", [])
        ssa = _get_ssa_appointment(value)

        sections = []

        # 1. Purpose and Scope
        sections.append(DraftSection(
            section_id="SSP-01",
            heading="1. Purpose and Scope",
            content=(
                "This Source Selection Plan (SSP) establishes the evaluation "
                "methodology, organizational structure, and procedures for the "
                "source selection process.\n\n"
                f"Evaluation Methodology: {'Best Value Tradeoff (FAR 15.101-1)' if eval_type == 'tradeoff' else 'Lowest Price Technically Acceptable (FAR 15.101-2)'}\n"
                f"Source Selection Authority: {ssa}\n"
                f"Estimated Value: {_format_value(value)}"
            ),
            authority="FAR 15.303(a)",
            rationale="Establishes the evaluation framework and SSA appointment.",
            confidence=90.0,
        ))

        # 2. Organization
        sections.append(DraftSection(
            section_id="SSP-02",
            heading="2. Source Selection Organization",
            content=(
                "Source Selection Authority (SSA): [Name], [Title]\n"
                "  - Makes final source selection decision per FAR 15.308\n\n"
                "SSEB Chair: [Name], [Title]\n"
                "  - Manages evaluation process, submits consensus scores\n\n"
                "SSEB Members:\n"
                "  - [Name], [Title] — Technical Evaluator\n"
                "  - [Name], [Title] — Technical Evaluator\n"
                "  - [Name], [Title] — Past Performance Evaluator\n\n"
                "Advisors:\n"
                "  - Legal Counsel (advisory, non-voting)\n"
                "  - Small Business Specialist (advisory, non-voting)\n\n"
                "Contracting Officer: [Name]\n"
                "  - Administers process, ensures FAR compliance"
            ),
            authority="FAR 15.303(b)",
            rationale="Defines roles and responsibilities for the evaluation team.",
            confidence=85.0,
        ))

        # 3. Evaluation Factors
        if factors:
            factor_text = self._format_factors(factors, eval_type)
        else:
            factor_text = self._default_factors(value, eval_type)

        sections.append(DraftSection(
            section_id="SSP-03",
            heading="3. Evaluation Factors and Subfactors",
            content=factor_text,
            authority="FAR 15.304",
            rationale="Factors listed in descending order of importance per FAR 15.304(e).",
            confidence=80.0,
        ))

        # 4. Rating Methodology
        sections.append(DraftSection(
            section_id="SSP-04",
            heading="4. Rating Methodology",
            content=self._rating_methodology(eval_type),
            authority="FAR 15.305",
            rationale="Defines adjectival rating scale and S/W/D definitions.",
            confidence=90.0,
        ))

        # 5. Evaluation Procedures
        sections.append(DraftSection(
            section_id="SSP-05",
            heading="5. Evaluation Procedures",
            content=(
                "5.1 Individual Evaluation\n"
                "Each SSEB member independently evaluates proposals assigned to "
                "their factors. Members document strengths, weaknesses, deficiencies, "
                "and risks with supporting rationale.\n\n"
                "5.2 Consensus Evaluation\n"
                "SSEB Chair facilitates consensus discussion. Final ratings reflect "
                "collective assessment with documented rationale.\n\n"
                "5.3 Competitive Range Determination\n"
                "CO determines competitive range per FAR 15.306(c). Offerors rated "
                "Unacceptable on any factor may be excluded with written rationale.\n\n"
                "5.4 Discussions (if required)\n"
                "If discussions are necessary, Pre-BCM required per IGPM 0103.19.\n\n"
                "5.5 Source Selection Decision\n"
                "SSA makes independent decision documented in SSDD per FAR 15.308. "
                "SSA is NOT bound by SSEB recommendation.\n\n"
                "NOTE: FedProcure assists with information presentation and "
                "documentation. All evaluation judgments are inherently governmental "
                "per FAR 7.503(b)(1)."
            ),
            authority="FAR 15.305, FAR 15.306, FAR 15.308",
            rationale="Step-by-step evaluation process with Tier 3 boundaries.",
            confidence=90.0,
        ))

        # 6. Documentation Requirements
        sections.append(DraftSection(
            section_id="SSP-06",
            heading="6. Documentation Requirements",
            content=(
                "The following documents will be prepared:\n\n"
                "a. Individual Evaluation Worksheets (per evaluator, per factor)\n"
                "b. Consensus Evaluation Report\n"
                "c. Competitive Range Determination Memo (if applicable)\n"
                "d. Pre-BCM (if discussions required)\n"
                "e. Pre/Post BCM\n"
                "f. Source Selection Decision Document (SSDD)\n"
                "g. Award Notification Letters (successful and unsuccessful)\n"
                "h. Debriefing Materials"
            ),
            authority="FAR 15.305, IGPM 0103.19",
            rationale="Comprehensive documentation per FAR and TSA policy.",
            confidence=90.0,
        ))

        return sections

    def _format_factors(self, factors: list, eval_type: str) -> str:
        lines = ["Evaluation factors in descending order of importance:\n"]
        for i, f in enumerate(factors):
            name = f.get("name", f.get("factor_id", f"Factor {i+1}"))
            weight = f.get("suggested_weight", 0)
            importance = f.get("relative_importance", "")
            subfactors = f.get("subfactors", [])

            lines.append(f"  {i+1}. {name}")
            if importance:
                lines.append(f"     Relative Importance: {importance}")
            if weight:
                lines.append(f"     Suggested Weight: {weight:.0%}")
            if subfactors:
                for sf in subfactors:
                    sf_name = sf.get("name", sf.get("subfactor_id", ""))
                    lines.append(f"       - {sf_name}")
            lines.append("")

        if eval_type == "tradeoff":
            lines.append("All non-price factors, when combined, are "
                        "significantly more important than price.")
        else:
            lines.append("Award will be made to the lowest-priced offeror "
                        "whose proposal meets all technical requirements.")
        return "\n".join(lines)

    def _default_factors(self, value: float, eval_type: str) -> str:
        if eval_type == "lpta":
            return (
                "Evaluation factors:\n\n"
                "  1. Technical Capability — Pass/Fail\n"
                "  2. Past Performance — Pass/Fail\n"
                "  3. Price — Lowest price of technically acceptable offerors\n\n"
                "Award to lowest-priced technically acceptable offeror per FAR 15.101-2."
            )

        weight_text = ("significantly more important than" if value >= 20_000_000
                      else "approximately equal to")
        return (
            "Evaluation factors in descending order of importance:\n\n"
            "  1. Technical Approach\n"
            "     - Understanding of Requirements\n"
            "     - Technical Solution\n"
            "     - Innovation\n\n"
            "  2. Management Approach\n"
            "     - Staffing Plan\n"
            "     - Quality Control\n"
            "     - Transition Plan\n\n"
            "  3. Past Performance\n"
            "     - Relevance\n"
            "     - Quality of Performance\n\n"
            "  4. Price/Cost\n"
            "     - Total Evaluated Price\n"
            "     - Price Realism (if CPAF/CPFF)\n\n"
            f"All non-price factors, when combined, are {weight_text} price."
        )

    def _rating_methodology(self, eval_type: str) -> str:
        if eval_type == "lpta":
            return (
                "Technical Rating Scale (Pass/Fail):\n\n"
                "  PASS — Proposal meets all minimum requirements\n"
                "  FAIL — Proposal fails to meet one or more minimum requirements\n\n"
                "Past Performance Rating Scale:\n\n"
                "  PASS — Satisfactory confidence based on relevant performance\n"
                "  FAIL — Insufficient confidence or relevant adverse past performance"
            )

        return (
            "Technical/Management Rating Scale:\n\n"
            "  OUTSTANDING — Proposal significantly exceeds requirements in ways "
            "beneficial to the Government. Strengths far outweigh any weaknesses.\n\n"
            "  GOOD — Proposal exceeds some requirements in ways beneficial to "
            "the Government. Strengths outweigh weaknesses.\n\n"
            "  ACCEPTABLE — Proposal meets requirements. Strengths and weaknesses "
            "are offsetting or there are no significant weaknesses.\n\n"
            "  MARGINAL — Proposal fails to clearly meet some requirements. "
            "Weaknesses outweigh strengths. Deficiencies may be correctable.\n\n"
            "  UNACCEPTABLE — Proposal fails to meet requirements. Contains one or "
            "more deficiencies that cannot be corrected without major revision.\n\n"
            "Strengths/Weaknesses/Deficiencies:\n\n"
            "  STRENGTH — An aspect that exceeds a requirement in a beneficial way\n"
            "  SIGNIFICANT STRENGTH — A strength that markedly exceeds the requirement\n"
            "  WEAKNESS — A flaw that increases risk of unsuccessful performance\n"
            "  SIGNIFICANT WEAKNESS — A material weakness that appreciably increases risk\n"
            "  DEFICIENCY — A material failure to meet a requirement or a "
            "combination of significant weaknesses that increases risk to unacceptable"
        )


# ========================================================================
# Engine 6: DHS Form 700-22 Small Business Review
# ========================================================================

class SBReviewEngine:
    """Generates DHS Form 700-22 Small Business Review.

    Required for all acquisitions over $100,000.
    23 items in 3 sections.
    """

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate 700-22 sections.

        Required params: estimated_value
        Optional: naics_code, requirement_description, competition_type,
                  set_aside_type, pop_months, contractor_name
        """
        value = params.get("estimated_value", 0)
        naics = params.get("naics_code", "[NAICS]")
        description = params.get("requirement_description", "[Description]")
        set_aside = params.get("set_aside_type", "")
        competition = params.get("competition_type", "full_and_open")
        pop = params.get("pop_months", 12)

        sections = []

        if value <= 100_000:
            sections.append(DraftSection(
                section_id="SB-00",
                heading="DHS Form 700-22 — Not Required",
                content=(
                    f"Estimated value {_format_value(value)} is at or below $100,000. "
                    f"DHS Form 700-22 is not required per form instructions."
                ),
                authority="DHS Form 700-22 Instructions",
                rationale="$100K threshold not met.",
                confidence=95.0,
            ))
            return sections

        # Section 1: Request Information (Items 1-8)
        sections.append(DraftSection(
            section_id="SB-01",
            heading="Section 1 — Request Information (Items 1-8)",
            content=(
                f"Item 1 — Requisitioner: [Program Office Name]\n"
                f"Item 2 — Program Office: [Office Code]\n"
                f"Item 3 — PR Number: [PR#]\n"
                f"Item 4 — Contract Specialist: [CS Name]\n"
                f"Item 5 — Contracting Officer: [CO Name]\n"
                f"Item 6 — Description: {description}\n"
                f"Item 7 — Estimated Total Value: {_format_value(value)}\n"
                f"Item 8 — Period of Performance: {pop} months"
            ),
            authority="DHS Form 700-22",
            rationale="Standard identification and requirement information.",
            confidence=85.0,
        ))

        # Section 2: Strategy (Items 9-19)
        first_consideration = self._determine_set_aside(value, set_aside, competition)
        bundling_review = value >= 2_000_000 and competition == "full_and_open"

        sections.append(DraftSection(
            section_id="SB-02",
            heading="Section 2 — Strategy & Procurement Method (Items 9-19)",
            content=(
                f"Item 9 — Acquisition Strategy: {competition.replace('_', ' ').title()}\n"
                f"Item 10 — Method of Procurement: {'Negotiated (FAR Part 15)' if value > 350_000 else 'Simplified Acquisition (FAR Part 13)'}\n"
                f"Item 11 — NAICS Code: {naics}\n"
                f"Item 12 — Small Business Size Standard: [Per SBA Table]\n"
                f"Item 13 — First Consideration: {first_consideration}\n"
                f"Item 14 — Second Consideration: {'Full & Open Competition' if first_consideration != 'Full & Open Competition' else 'N/A'}\n"
                f"Item 15 — Justification for Full & Open: {'N/A — set-aside recommended' if 'Set-Aside' in first_consideration else '[CO: Provide justification for not setting aside]'}\n"
                f"Item 16 — Pre-existing Contract Vehicle: [CO: Identify if applicable]\n"
                f"Item 17 — Substantial Bundling Review: {'Required ($2M+ open market)' if bundling_review else 'Not applicable'}\n"
                f"Item 18 — Pre-existing Contracts ($2M+): {'Review required' if value >= 2_000_000 else 'N/A'}\n"
                f"Item 19 — Set-Aside Recommendation: {first_consideration}"
            ),
            authority="DHS Form 700-22, FAR Part 19",
            rationale="Documents small business strategy and set-aside determination.",
            confidence=75.0,
        ))

        # Section 3: Signatures (Items 20-23)
        sba_required = value >= 2_000_000 and "Full & Open" in first_consideration
        sections.append(DraftSection(
            section_id="SB-03",
            heading="Section 3 — Submission and Review (Items 20-23)",
            content=(
                "Item 20 — CO Concurrence:\n"
                "  [ ] Concur  [ ] Non-Concur\n"
                "  Signature: ____________________________  Date: ________\n\n"
                "Item 21 — SB Specialist Concurrence:\n"
                "  [ ] Concur  [ ] Non-Concur\n"
                "  Signature: ____________________________  Date: ________\n"
                "  (Turnaround: 2 business days)\n\n"
                "Item 22 — CO Response to SBS Non-Concurrence:\n"
                "  [Required only if SBS non-concurs]\n\n"
                f"Item 23 — SBA PCR Concurrence: {'Required ($2M+ unrestricted acquisition)' if sba_required else 'Not required'}\n"
                f"  {'Turnaround: 2 business days' if sba_required else ''}"
            ),
            authority="DHS Form 700-22, FAR 19.202-1",
            rationale="Signature chain per form instructions.",
            confidence=90.0,
        ))

        return sections

    def _determine_set_aside(self, value: float, set_aside: str, competition: str) -> str:
        if competition in ("sole_source", "not_competed"):
            return "Not applicable (sole source)"
        if set_aside:
            type_map = {
                "8a": "8(a) Set-Aside",
                "hubzone": "HUBZone Set-Aside",
                "sdvosb": "SDVOSB Set-Aside",
                "wosb": "WOSB Set-Aside",
                "total_sb": "Total Small Business Set-Aside",
                "partial_sb": "Partial Small Business Set-Aside",
            }
            return type_map.get(set_aside, f"{set_aside} Set-Aside")
        return "Total Small Business Set-Aside (pending Rule of Two analysis)"


# ========================================================================
# Engine 7: COR Nomination Letter (TSA MD 300.9)
# ========================================================================

class CORNomEngine:
    """Generates COR Nomination Letter per TSA MD 300.9."""

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate COR nomination letter sections.

        Required params: estimated_value
        Optional: requirement_description, services, pop_months
        """
        value = params.get("estimated_value", 0)
        description = params.get("requirement_description", "[Requirement description]")
        services = params.get("services", True)
        pop = params.get("pop_months", 12)

        sections = []

        # Nomination
        sections.append(DraftSection(
            section_id="COR-01",
            heading="COR Nomination",
            content=(
                "TO: Contracting Officer\n"
                "FROM: [Nominating Official]\n"
                "SUBJECT: Nomination of Contracting Officer's Representative\n\n"
                f"I hereby nominate the following individual as COR for the "
                f"{description} requirement:\n\n"
                "Name: [COR Name]\n"
                "Title: [COR Title]\n"
                "Organization: [COR Organization]\n"
                "Phone: [COR Phone]\n"
                "Email: [COR Email]\n"
                "FAC-COR Certification Level: [I / II / III]\n"
                f"Required Level: {self._required_level(value, services)}"
            ),
            authority="TSA MD 300.9, FAR 1.604",
            rationale="Identifies the nominated COR with required certification level.",
            confidence=90.0,
        ))

        # Qualifications
        sections.append(DraftSection(
            section_id="COR-02",
            heading="COR Qualifications",
            content=(
                "The nominee possesses the following qualifications:\n\n"
                "a. Current FAC-COR certification at the required level\n"
                "b. Technical expertise in the subject matter\n"
                "c. Understanding of the contracting process\n"
                "d. Completion of required ethics training\n"
                "e. No personal conflicts of interest with the contractor\n\n"
                "[CO: Verify nominee's qualifications and certification status "
                "in CSOD (COR tracking system) before delegation]"
            ),
            authority="TSA MD 300.9",
            rationale="Documents COR qualifications per TSA policy.",
            confidence=85.0,
        ))

        # Duties and Limitations
        sections.append(DraftSection(
            section_id="COR-03",
            heading="COR Duties and Limitations",
            content=(
                "The COR is delegated the following duties:\n\n"
                "a. Monitor contractor performance per PWS/QASP\n"
                "b. Review and approve contractor deliverables\n"
                "c. Maintain COR file with correspondence and documentation\n"
                "d. Prepare periodic surveillance reports\n"
                "e. Review and recommend approval of invoices\n"
                "f. Document contractor performance for CPARS input\n"
                "g. Notify CO of performance issues immediately\n\n"
                "LIMITATIONS (Tier 3 — COR Cannot):\n"
                "a. Direct the contractor to perform work outside the scope\n"
                "b. Make commitments or changes affecting price, quality, or delivery\n"
                "c. Authorize deviations from the contract terms\n"
                "d. Obligate the Government in any manner\n"
                "e. Issue change orders or contract modifications\n"
                "f. Act as CO in any capacity"
            ),
            authority="TSA MD 300.9, FAR 1.604",
            rationale="Defines COR authority boundaries — critical for preventing unauthorized commitments.",
            confidence=95.0,
        ))

        # Signatures
        sections.append(DraftSection(
            section_id="COR-04",
            heading="Signatures",
            content=(
                "Nominating Official:\n"
                "  Signature: ____________________________\n"
                "  Name: ____________________________\n"
                "  Date: ____________________________\n\n"
                "COR Acknowledgment:\n"
                "  I accept this nomination and understand my duties and limitations.\n"
                "  Signature: ____________________________\n"
                "  Name: ____________________________\n"
                "  Date: ____________________________\n\n"
                "Contracting Officer Delegation:\n"
                "  Signature: ____________________________\n"
                "  Name: ____________________________\n"
                "  Date: ____________________________"
            ),
            authority="TSA MD 300.9",
            rationale="Three-party signature requirement.",
            confidence=95.0,
        ))

        return sections

    def _required_level(self, value: float, services: bool) -> str:
        if value >= 10_000_000:
            return "Level III (Complex — exceeds $10M)"
        elif value >= 1_000_000 or services:
            return "Level II (Advanced — services or exceeds $1M)"
        return "Level I (Basic)"


# ========================================================================
# Engine 8: Evaluation Worksheet Engine (FAR 15.305)
# ========================================================================

class EvalWorksheetEngine:
    """Generates evaluation worksheet templates per FAR 15.305.

    Produces per-factor worksheet with S/W/D fields and rating guidance.
    """

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate evaluation worksheet sections.

        Required params: estimated_value
        Optional: eval_factors, evaluation_type
        """
        value = params.get("estimated_value", 0)
        eval_type = params.get("evaluation_type", "tradeoff")
        factors = params.get("eval_factors", [])

        if not factors:
            factors = self._default_factors(eval_type)

        sections = []

        # Instructions
        sections.append(DraftSection(
            section_id="EW-00",
            heading="Evaluation Worksheet Instructions",
            content=(
                "INSTRUCTIONS FOR EVALUATORS:\n\n"
                "1. Review the offeror's proposal against the evaluation criteria "
                "in Section M of the solicitation.\n"
                "2. For each factor/subfactor, identify strengths, weaknesses, "
                "deficiencies, and risks.\n"
                "3. Assign an adjectival rating based on the rating definitions "
                "in the Source Selection Plan.\n"
                "4. Provide specific rationale citing proposal pages for each finding.\n"
                "5. Do NOT discuss your individual evaluation with other evaluators "
                "until consensus.\n\n"
                "IMPORTANT: This worksheet is source selection sensitive. "
                "Access restricted to authorized evaluation team members only.\n\n"
                "Evaluator Name: ____________________________\n"
                "Date: ____________________________\n"
                "Offeror: ____________________________"
            ),
            authority="FAR 15.305, FAR 3.104 (Procurement Integrity)",
            rationale="Standard evaluation instructions with integrity safeguards.",
            confidence=95.0,
        ))

        # Per-factor worksheets
        for i, factor in enumerate(factors):
            f_name = factor.get("name", f"Factor {i+1}")
            f_id = factor.get("factor_id", f"F-{i+1:02d}")
            subfactors = factor.get("subfactors", [])

            worksheet_content = self._build_factor_worksheet(
                f_name, f_id, subfactors, eval_type
            )
            sections.append(DraftSection(
                section_id=f"EW-{i+1:02d}",
                heading=f"Factor {i+1}: {f_name}",
                content=worksheet_content,
                authority="FAR 15.305(a)",
                rationale=f"Evaluation worksheet for {f_name}.",
                confidence=85.0,
            ))

        # Summary
        sections.append(DraftSection(
            section_id="EW-SUM",
            heading="Evaluation Summary",
            content=(
                "Overall Assessment:\n\n"
                + "\n".join(
                    f"  {f.get('name', f'Factor {i+1}')}: Rating: ________  "
                    f"S: __  W: __  D: __"
                    for i, f in enumerate(factors)
                )
                + "\n\nNarrative Summary:\n"
                "[Evaluator: Provide overall assessment of the offeror's proposal]\n\n"
                "Evaluator Signature: ____________________________\n"
                "Date: ____________________________"
            ),
            authority="FAR 15.305",
            rationale="Aggregated ratings for consensus facilitation.",
            confidence=90.0,
        ))

        return sections

    def _build_factor_worksheet(self, name: str, factor_id: str,
                                 subfactors: list, eval_type: str) -> str:
        lines = []

        if eval_type == "lpta":
            lines.append(f"Assessment: [ ] PASS  [ ] FAIL\n")
            lines.append("Basis for Rating:")
            lines.append("[Evaluator: Cite specific proposal content and requirements]\n")
        else:
            lines.append(f"Rating: [ ] Outstanding  [ ] Good  [ ] Acceptable  "
                        f"[ ] Marginal  [ ] Unacceptable\n")

        if subfactors:
            lines.append("Subfactor Assessment:")
            for sf in subfactors:
                sf_name = sf.get("name", sf.get("subfactor_id", ""))
                lines.append(f"\n  {sf_name}:")
                if eval_type != "lpta":
                    lines.append(f"    Rating: ________")
                lines.append(f"    Findings: [Evaluator notes]")

        lines.append("\nStrengths:")
        lines.append("  1. ________________________________________________")
        lines.append("     Proposal Reference: Page ___  Section ___")
        lines.append("  2. ________________________________________________")
        lines.append("     Proposal Reference: Page ___  Section ___")

        lines.append("\nWeaknesses:")
        lines.append("  1. ________________________________________________")
        lines.append("     Proposal Reference: Page ___  Section ___")
        lines.append("     Risk: ___________________________________________")

        lines.append("\nDeficiencies:")
        lines.append("  1. ________________________________________________")
        lines.append("     Requirement Not Met: ____________________________")
        lines.append("     Proposal Reference: Page ___  Section ___")

        lines.append("\nRisks:")
        lines.append("  [Evaluator: Identify any performance or schedule risks]")

        return "\n".join(lines)

    def _default_factors(self, eval_type: str) -> list[dict]:
        if eval_type == "lpta":
            return [
                {"factor_id": "F-01", "name": "Technical Capability", "subfactors": []},
                {"factor_id": "F-02", "name": "Past Performance", "subfactors": []},
            ]
        return [
            {
                "factor_id": "F-01",
                "name": "Technical Approach",
                "subfactors": [
                    {"subfactor_id": "SF-T-01", "name": "Understanding of Requirements"},
                    {"subfactor_id": "SF-T-02", "name": "Technical Solution"},
                ],
            },
            {
                "factor_id": "F-02",
                "name": "Management Approach",
                "subfactors": [
                    {"subfactor_id": "SF-M-01", "name": "Staffing Plan"},
                    {"subfactor_id": "SF-M-02", "name": "Quality Control"},
                ],
            },
            {
                "factor_id": "F-03",
                "name": "Past Performance",
                "subfactors": [
                    {"subfactor_id": "SF-P-01", "name": "Relevance"},
                    {"subfactor_id": "SF-P-02", "name": "Quality of Performance"},
                ],
            },
        ]


# ========================================================================
# Engine 9: Award Notice Engine (FAR 5.301 / DHS 2140-01)
# ========================================================================

class AwardNoticeEngine:
    """Generates award notification documents per FAR 5.301 and DHS Form 2140-01."""

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate award notice sections.

        Required params: estimated_value
        Optional: contractor_name, contract_number, solicitation_number,
                  naics_code, award_date, competition_type
        """
        value = params.get("estimated_value", 0)
        contractor = params.get("contractor_name", "[Contractor Name]")
        contract_num = params.get("contract_number", "[Contract Number]")
        sol_num = params.get("solicitation_number", "[Solicitation Number]")
        naics = params.get("naics_code", "[NAICS]")
        competition = params.get("competition_type", "full_and_open")

        sections = []

        # SAM.gov Synopsis (FAR 5.301)
        sections.append(DraftSection(
            section_id="AN-01",
            heading="Award Notice — SAM.gov Synopsis",
            content=(
                f"Contract Award Notice per FAR 5.301\n\n"
                f"Solicitation Number: {sol_num}\n"
                f"Contract Number: {contract_num}\n"
                f"Contractor: {contractor}\n"
                f"Award Amount: {_format_value(value)}\n"
                f"NAICS: {naics}\n"
                f"Competition: {competition.replace('_', ' ').title()}\n"
                f"Award Date: [Date]\n"
                f"Number of Offers Received: [Number]\n\n"
                f"{'Post within 30 days of award per FAR 5.301(a).' if value > 350_000 else 'Award notice posting optional (under SAT).'}"
            ),
            authority="FAR 5.301",
            rationale="Public notification of contract award.",
            confidence=90.0,
        ))

        # DHS Form 2140-01 (Contract Award Notification)
        sections.append(DraftSection(
            section_id="AN-02",
            heading="DHS Form 2140-01 — Contract Award Notification",
            content=(
                "DHS Contract Award Notification\n\n"
                f"Date of Award: [Date]\n"
                f"Contract Number: {contract_num}\n"
                f"Contractor Name: {contractor}\n"
                f"Contractor Address: [Address]\n"
                f"UEI: [Unique Entity ID]\n"
                f"CAGE Code: [CAGE]\n"
                f"Total Award Value: {_format_value(value)}\n"
                f"Funded Amount: [Funded Amount]\n"
                f"Period of Performance: [Start Date] through [End Date]\n"
                f"Contracting Officer: [CO Name]\n"
                f"COR: [COR Name]"
            ),
            authority="DHS Form 2140-01",
            rationale="Internal DHS award notification for distribution.",
            confidence=85.0,
        ))

        # Unsuccessful Offeror Notification
        if competition == "full_and_open":
            sections.append(DraftSection(
                section_id="AN-03",
                heading="Notification to Unsuccessful Offerors",
                content=(
                    "TO: [Unsuccessful Offeror]\n"
                    "FROM: Contracting Officer\n"
                    f"SUBJECT: Notification of Award — {sol_num}\n\n"
                    "This letter is to notify you that the above-referenced "
                    f"solicitation has been awarded to {contractor}.\n\n"
                    "You may request a debriefing per FAR 15.506. "
                    "Pre-award debriefings are available for offerors excluded "
                    "from the competitive range. Post-award debriefings must be "
                    "requested within 3 days of notification.\n\n"
                    "The debriefing will include:\n"
                    "a. The Government's evaluation of significant elements in your proposal\n"
                    "b. Summary of the rationale for eliminating your proposal (if applicable)\n"
                    "c. Reasonable responses to relevant questions about evaluation procedures\n"
                    "d. Number of offerors and name/address of the awardee\n\n"
                    "NOTE: The debriefing shall NOT include point-by-point comparison "
                    "with other proposals, trade secrets, or privileged information."
                ),
                authority="FAR 15.503, FAR 15.506",
                rationale="Required notification per FAR with debriefing rights.",
                confidence=90.0,
            ))

        return sections


# ========================================================================
# Engine 10: Security Requirements Document (HSAR 3052.204-71)
# ========================================================================

class SecurityReqEngine:
    """Generates Security Requirements Document per HSAR 3052.204-71/72."""

    def generate(self, params: dict[str, Any]) -> list[DraftSection]:
        """Generate security requirements sections.

        Required params: estimated_value
        Optional: classified, handles_ssi, is_it, services,
                  clearance_required, on_site, has_cui
        """
        classified = params.get("classified", False)
        handles_ssi = params.get("handles_ssi", False)
        is_it = params.get("is_it", params.get("it_related", False))
        services = params.get("services", True)
        on_site = params.get("on_site", params.get("vendor_on_site", False))
        has_cui = params.get("has_cui", False)
        clearance_required = params.get("clearance_required", False)

        sections = []

        # 1. Personnel Security
        if on_site or classified or clearance_required:
            level = "Secret" if classified else "Public Trust (Moderate Risk)"
            sections.append(DraftSection(
                section_id="SEC-01",
                heading="1. Personnel Security Requirements",
                content=(
                    f"Security Clearance Level: {level}\n\n"
                    "All contractor personnel requiring access to TSA facilities "
                    "or systems must:\n"
                    "a. Successfully complete background investigation per HSAR 3052.204-71\n"
                    "b. Obtain TSA-approved identification/access credentials\n"
                    "c. Complete TSA security awareness training annually\n"
                    "d. Report any security incidents immediately to the COR and ISSO\n\n"
                    f"{'TSA badge/escort requirements apply for all on-site personnel.' if on_site else ''}\n"
                    "Personnel who fail to obtain or maintain required clearance "
                    "shall be removed from the contract."
                ),
                authority="HSAR 3052.204-71",
                rationale="Personnel security requirements based on access level.",
                confidence=90.0,
            ))

        # 2. Information Security
        if is_it:
            sections.append(DraftSection(
                section_id="SEC-02",
                heading="2. Information System Security",
                content=(
                    "All IT systems used in performance of this contract must:\n\n"
                    "a. Comply with FISMA 2014 requirements\n"
                    "b. Obtain Authority to Operate (ATO) per NIST SP 800-37\n"
                    "c. Implement security controls per NIST SP 800-53 Rev 5\n"
                    "d. Undergo continuous monitoring per DHS CDM program\n\n"
                    f"{'FedRAMP authorization required for cloud services.' if is_it else ''}\n\n"
                    "ISSO designation: [ISSO Name] will serve as Information System "
                    "Security Officer for contractor-operated systems."
                ),
                authority="FISMA 2014, NIST 800-53, HSAR 3052.204-72",
                rationale="IT security controls required for system access.",
                confidence=90.0,
            ))

        # 3. SSI Handling
        if handles_ssi:
            sections.append(DraftSection(
                section_id="SEC-03",
                heading="3. Sensitive Security Information (SSI)",
                content=(
                    "This contract involves access to Sensitive Security Information "
                    "as defined in 49 CFR Part 1520.\n\n"
                    "Requirements:\n"
                    "a. All personnel handling SSI must complete SSI awareness training\n"
                    "b. SSI must be marked, stored, and transmitted per TSA MD 2810\n"
                    "c. SSI shall not be disclosed to unauthorized persons\n"
                    "d. Destruction of SSI media per TSA-approved methods\n"
                    "e. SSI incidents reported within 1 hour to TSA ISSO\n\n"
                    "NOTE: SSI is unique to TSA/DHS transportation security. "
                    "It is NOT the same as CUI or classified information."
                ),
                authority="49 CFR Part 1520, TSA MD 2810",
                rationale="SSI handling requirements specific to TSA.",
                confidence=90.0,
            ))

        # 4. CUI Handling
        if has_cui:
            sections.append(DraftSection(
                section_id="SEC-04",
                heading="4. Controlled Unclassified Information (CUI)",
                content=(
                    "This contract involves CUI as defined in 32 CFR Part 2002.\n\n"
                    "Requirements:\n"
                    "a. CUI marking per NIST SP 800-171 and CUI Registry\n"
                    "b. Storage and transmission per NIST SP 800-171\n"
                    "c. Access limited to personnel with need-to-know\n"
                    "d. Destruction per agency-approved methods\n"
                    "e. Incident reporting within 1 hour"
                ),
                authority="32 CFR Part 2002, NIST SP 800-171",
                rationale="CUI handling requirements per federal standards.",
                confidence=90.0,
            ))

        # 5. Incident Response
        sections.append(DraftSection(
            section_id="SEC-05",
            heading=f"{'5' if sections else '1'}. Security Incident Response",
            content=(
                "The contractor shall:\n\n"
                "a. Report all security incidents to the COR and ISSO within 1 hour\n"
                "b. Preserve all evidence related to the incident\n"
                "c. Cooperate fully with TSA/DHS investigation\n"
                "d. Implement corrective actions within timeframes directed by TSA\n"
                "e. Submit post-incident report within 5 business days\n\n"
                "Security incidents include: unauthorized access, data breaches, "
                "lost/stolen credentials, malware, and social engineering attempts."
            ),
            authority="HSAR 3052.204-72, TSA IGPM 0420.08",
            rationale="Incident response requirements per DHS policy.",
            confidence=90.0,
        ))

        # 6. HSAR Clauses
        clauses = ["HSAR 3052.204-71 (Safeguarding Sensitive Information)"]
        if is_it:
            clauses.append("HSAR 3052.204-72 (Safeguarding of IT Resources)")
        if handles_ssi:
            clauses.append("TSA Clause — SSI Handling Requirements")
        if has_cui:
            clauses.append("DFARS 252.204-7012 (Safeguarding Covered Defense Information) or equivalent")

        sections.append(DraftSection(
            section_id="SEC-06",
            heading=f"{'6' if len(sections) >= 5 else str(len(sections) + 1)}. Applicable Security Clauses",
            content=(
                "The following security clauses are incorporated:\n\n"
                + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(clauses))
            ),
            authority="HSAR 3052.204-71/72",
            rationale="Clause selection based on security requirement analysis.",
            confidence=90.0,
        ))

        return sections


# ========================================================================
# Document Chain — Orchestration Helper
# ========================================================================

# Maps document type string to engine class
DOCUMENT_ENGINES = {
    "ja": JAEngine,
    "bcm": BCMEngine,
    "df": DFEngine,
    "ap": APEngine,
    "ssp": SSPEngine,
    "sb_review": SBReviewEngine,
    "cor_nomination": CORNomEngine,
    "eval_worksheet": EvalWorksheetEngine,
    "award_notice": AwardNoticeEngine,
    "security_requirements": SecurityReqEngine,
}


def generate_document(doc_type: str, params: dict[str, Any]) -> DocumentDraft:
    """Generate a document by type.

    Args:
        doc_type: Key from DOCUMENT_ENGINES
        params: Acquisition parameters

    Returns:
        DocumentDraft with sections, warnings, and provenance
    """
    engine_cls = DOCUMENT_ENGINES.get(doc_type)
    if not engine_cls:
        raise ValueError(f"Unknown document type: {doc_type}. "
                        f"Available: {list(DOCUMENT_ENGINES.keys())}")

    engine = engine_cls()
    sections = engine.generate(params)

    # Collect warnings
    warnings = []
    value = params.get("estimated_value", 0)

    if doc_type == "ja" and not params.get("sole_source", False) and params.get("competition_type") != "sole_source":
        warnings.append("J&A generated but competition_type is not sole_source. Verify justification need.")
    if doc_type == "ap" and params.get("contract_type") == "FFP" and value < 50_000_000:
        warnings.append("HSAM 3007.103(e): FFP under $50M does not require a written AP.")
    if doc_type == "df" and params.get("df_type") == "contract_type_tm_lh" and value >= 50_000_000:
        warnings.append("T&M/LH D&F at $50M+ requires HCA approval and strong justification.")
    if doc_type == "bcm" and value >= 500_000:
        warnings.append(f"BCM over $500K must be reviewed and approved at one level above the CO, at a minimum.")

    return DocumentDraft(
        doc_type=doc_type,
        sections=sections,
        warnings=warnings,
        source_provenance=[
            f"Engine: {engine_cls.__name__}",
            "TSA C&P Review and Approval Thresholds (February 2026)",
            "FAR/HSAR/HSAM regulatory stack",
        ],
    )


def generate_full_chain(params: dict[str, Any]) -> dict[str, DocumentDraft]:
    """Generate all applicable documents for an acquisition.

    Determines which documents are needed based on params and generates them all.

    Returns:
        Dict mapping doc_type → DocumentDraft
    """
    value = params.get("estimated_value", 0)
    services = params.get("services", True)
    sole_source = params.get("sole_source", False) or params.get("competition_type") == "sole_source"
    contract_type = params.get("contract_type", "FFP")
    competition = params.get("competition_type", "full_and_open")

    docs = {}

    # Always generate
    docs["bcm"] = generate_document("bcm", params)
    docs["ssp"] = generate_document("ssp", params)
    docs["eval_worksheet"] = generate_document("eval_worksheet", params)
    docs["award_notice"] = generate_document("award_notice", params)
    docs["security_requirements"] = generate_document("security_requirements", params)

    # COR nomination for services
    if services:
        docs["cor_nomination"] = generate_document("cor_nomination", params)

    # Small business review if over $100K
    if value > 100_000:
        docs["sb_review"] = generate_document("sb_review", params)

    # J&A only for sole source / other than full and open
    if sole_source or competition not in ("full_and_open", ""):
        docs["ja"] = generate_document("ja", params)

    # D&F for T&M/LH contracts
    if contract_type in ("T&M", "LH"):
        df_params = {**params, "df_type": "contract_type_tm_lh"}
        docs["df"] = generate_document("df", df_params)

    # AP for OTFFP above SAT or any above $50M
    if contract_type != "FFP" and value > 350_000:
        docs["ap"] = generate_document("ap", params)
    elif value >= 50_000_000:
        docs["ap"] = generate_document("ap", params)

    return docs
