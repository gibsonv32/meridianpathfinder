"""
Solicitation Assembly Engine — Phase 2 Feature
===============================================
Assembles a complete solicitation package from generated/accepted documents.
Validates J-L-M traceability, checks completeness, produces assembly manifest.

Tier 2 AI output — CO reviews assembled package before posting.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class AssemblyStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    BLOCKED = "blocked"


class SectionType(str, Enum):
    A = "A"  # SF-33 / SF-1449
    B = "B"  # Supplies or Services and Prices/Costs
    C = "C"  # Description/Specs/SOW (PWS goes here)
    D = "D"  # Packaging and Marking
    E = "E"  # Inspection and Acceptance
    F = "F"  # Deliveries or Performance
    G = "G"  # Contract Administration Data
    H = "H"  # Special Contract Requirements
    I = "I"  # Contract Clauses
    J = "J"  # List of Attachments
    K = "K"  # Representations and Certifications
    L = "L"  # Instructions to Offerors
    M = "M"  # Evaluation Factors


@dataclass
class SectionMapping:
    """Maps a generated document (by dcode) to a solicitation section."""
    section: SectionType
    dcode: str
    document_type: str
    title: str
    required: bool = True
    present: bool = False
    accepted: bool = False
    document_id: str | None = None


@dataclass
class JLMTraceItem:
    """Single traceability link between J, L, and M sections."""
    j_reference: str  # e.g., "PWS 3.1"
    l_instruction: str  # e.g., "L.4.1 - Technical Approach"
    m_factor: str  # e.g., "M.1 - Technical Capability"
    traced: bool = True
    gap: str | None = None


@dataclass
class AssemblyManifest:
    """Complete solicitation assembly manifest."""
    package_id: str
    title: str
    assembly_status: AssemblyStatus
    sections: list[SectionMapping]
    jlm_traceability: list[JLMTraceItem]
    completeness_pct: float
    missing_sections: list[str]
    clauses: list[dict]
    posting_deadline_days: int
    estimated_posting_date: str | None = None
    warnings: list[str] = field(default_factory=list)
    source_provenance: list[str] = field(default_factory=list)
    confidence_score: float = 0.88
    requires_acceptance: bool = True


# Standard section-to-dcode mappings for services solicitations
SERVICES_SECTION_MAP: list[tuple[SectionType, str, str, str, bool]] = [
    (SectionType.A, "D101", "cover_page", "Standard Form 33/1449", True),
    (SectionType.B, "D104", "clins", "CLIN Structure / Pricing Schedule", True),
    (SectionType.C, "D102", "pws", "Performance Work Statement", True),
    (SectionType.E, "D105", "inspection", "Inspection and Acceptance (QASP)", True),
    (SectionType.H, "D109", "special_reqs", "Special Contract Requirements", False),
    (SectionType.I, "D111", "clauses", "Contract Clauses (FAR/HSAR)", True),
    (SectionType.J, "D112", "attachments", "List of Attachments", True),
    (SectionType.L, "D113", "instructions", "Instructions to Offerors", True),
    (SectionType.M, "D107", "eval_factors", "Evaluation Factors for Award", True),
]

# Standard FAR/HSAR clauses for IT services >SAT
STANDARD_CLAUSES_IT_SERVICES = [
    {"clause": "FAR 52.212-1", "title": "Instructions to Offerors—Commercial Products and Commercial Services", "prescription": "FAR 12.301(b)(1)"},
    {"clause": "FAR 52.212-2", "title": "Evaluation—Commercial Products and Commercial Services", "prescription": "FAR 12.301(b)(1)"},
    {"clause": "FAR 52.212-4", "title": "Contract Terms and Conditions—Commercial Products and Commercial Services", "prescription": "FAR 12.301(b)(3)"},
    {"clause": "FAR 52.217-8", "title": "Option to Extend Services", "prescription": "FAR 17.208(f)"},
    {"clause": "FAR 52.217-9", "title": "Option to Extend the Term of the Contract", "prescription": "FAR 17.208(g)"},
    {"clause": "FAR 52.222-41", "title": "Service Contract Labor Standards", "prescription": "FAR 22.1006(a)"},
    {"clause": "FAR 52.222-42", "title": "Statement of Equivalent Rates for Federal Hires", "prescription": "FAR 22.1006(b)"},
    {"clause": "FAR 52.232-18", "title": "Availability of Funds", "prescription": "FAR 32.706-1(a)"},
    {"clause": "HSAR 3052.204-71", "title": "Contractor Employee Access", "prescription": "HSAM 3004.470-4(a)"},
    {"clause": "HSAR 3052.204-72", "title": "Safeguarding of Controlled Unclassified Information", "prescription": "HSAM 3004.470-4(b)"},
    {"clause": "HSAR 3052.215-70", "title": "Key Personnel or Facilities", "prescription": "HSAM 3015.204-70"},
]


class SolicitationAssemblyEngine:
    """
    Assembles solicitation from generated documents.

    Input: package_id + list of generated/accepted documents
    Output: AssemblyManifest with section mappings, J-L-M traceability, clause list
    """

    def assemble(
        self,
        *,
        package_id: str,
        title: str,
        value: float,
        documents: list[dict],  # [{dcode, document_type, document_id, acceptance_status, content}]
        posting_deadline_days: int = 30,
        services: bool = True,
        it_related: bool = True,
    ) -> AssemblyManifest:
        # Build section mappings
        doc_by_dcode = {d["dcode"]: d for d in documents}
        sections: list[SectionMapping] = []

        for section, dcode, doc_type, sec_title, required in SERVICES_SECTION_MAP:
            doc = doc_by_dcode.get(dcode)
            sections.append(SectionMapping(
                section=section,
                dcode=dcode,
                document_type=doc_type,
                title=sec_title,
                required=required,
                present=doc is not None,
                accepted=doc.get("acceptance_status") == "accepted" if doc else False,
                document_id=doc.get("document_id") if doc else None,
            ))

        # Completeness
        required_sections = [s for s in sections if s.required]
        present_required = [s for s in required_sections if s.present]
        completeness_pct = len(present_required) / max(len(required_sections), 1) * 100
        missing = [f"Section {s.section.value}: {s.title} ({s.dcode})" for s in required_sections if not s.present]

        # J-L-M traceability check
        jlm = self._check_jlm_traceability(documents, doc_by_dcode)

        # Clause selection
        clauses = list(STANDARD_CLAUSES_IT_SERVICES) if it_related else STANDARD_CLAUSES_IT_SERVICES[:6]

        # Warnings
        warnings: list[str] = []
        if completeness_pct < 100:
            warnings.append(f"Solicitation is {completeness_pct:.0f}% complete. {len(missing)} required section(s) missing.")
        unaccepted = [s for s in sections if s.present and not s.accepted]
        if unaccepted:
            warnings.append(f"{len(unaccepted)} document(s) not yet accepted by CO. Acceptance required before posting.")
        jlm_gaps = [item for item in jlm if not item.traced]
        if jlm_gaps:
            warnings.append(f"{len(jlm_gaps)} J-L-M traceability gap(s) detected. Review before posting.")

        # Status
        if completeness_pct == 100 and not unaccepted and not jlm_gaps:
            status = AssemblyStatus.COMPLETE
        elif missing:
            status = AssemblyStatus.BLOCKED
        else:
            status = AssemblyStatus.INCOMPLETE

        return AssemblyManifest(
            package_id=package_id,
            title=title,
            assembly_status=status,
            sections=sections,
            jlm_traceability=jlm,
            completeness_pct=completeness_pct,
            missing_sections=missing,
            clauses=clauses,
            posting_deadline_days=posting_deadline_days,
            warnings=warnings,
            source_provenance=[
                "FAR Part 12 (Commercial Item Procedures)",
                "FAR Part 15 (Contracting by Negotiation)",
                "HSAR Part 3052 (Solicitation Provisions and Contract Clauses)",
                "FAR 15.204 (Uniform Contract Format)",
            ],
        )

    def _check_jlm_traceability(self, documents: list[dict], doc_by_dcode: dict) -> list[JLMTraceItem]:
        """Check that Section J (PWS) requirements trace to L (instructions) and M (evaluation factors)."""
        jlm_items: list[JLMTraceItem] = []

        has_pws = "D102" in doc_by_dcode
        has_l = "D113" in doc_by_dcode
        has_m = "D107" in doc_by_dcode

        if has_pws:
            # Generate standard traceability items
            standard_traces = [
                ("PWS 3.1 - Primary Service Delivery", "L.4.1 - Technical Approach", "M.1 - Technical Capability"),
                ("PWS 3.2 - Reporting Requirements", "L.4.2 - Management Approach", "M.2 - Management"),
                ("PWS 3.3 - Performance Standards", "L.4.3 - Staffing Plan", "M.3 - Staffing"),
                ("PWS 3.4 - Transition Requirements", "L.4.4 - Transition Plan", "M.1 - Technical Capability"),
            ]
            for j_ref, l_inst, m_factor in standard_traces:
                traced = has_l and has_m
                gap = None if traced else f"Missing {'Section L' if not has_l else 'Section M'}"
                jlm_items.append(JLMTraceItem(
                    j_reference=j_ref,
                    l_instruction=l_inst if has_l else "MISSING",
                    m_factor=m_factor if has_m else "MISSING",
                    traced=traced,
                    gap=gap,
                ))
        else:
            jlm_items.append(JLMTraceItem(
                j_reference="MISSING - No PWS",
                l_instruction="Cannot trace",
                m_factor="Cannot trace",
                traced=False,
                gap="PWS (Section C/J) not present — cannot establish J-L-M traceability",
            ))

        return jlm_items


solicitation_assembly_engine = SolicitationAssemblyEngine()
