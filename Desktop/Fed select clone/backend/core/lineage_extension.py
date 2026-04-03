"""
Phase 28: Lineage Extension — Full Traceability
================================================

Extends the Phase 10 Evidence Lineage Ledger with:
1. Market research findings as a new chain stage (10 stages total)
2. Phase 27 document chain integration (10 supporting doc types → lineage)
3. Cross-document dependency graph (which docs depend on which)
4. Modification impact analysis (change to any node → all affected documents)
5. Full build orchestration (market research + chain + documents + policy)

Design: COMPOSITION layer — wraps EvidenceLineageLedger without modification.
All existing Phase 10/13/14 tests remain untouched.

Chain stages (extended from 8 → 10):
  market_research → requirement → CLIN → Section L → Section M →
  evaluator_score → SSDD → QASP → CPARS → closeout

Integration:
  - MarketResearchAgent (Phase 23a) → market research findings
  - DocumentChainOrchestrator (Phase 27) → supporting documents
  - PolicyService (Phase 4) → Q-code / D-code traces
  - ComplianceOverlayEngine (Phase compliance) → compliance findings
  - EvalFactorDerivationEngine (Phase 23b) → factor derivation trace
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from backend.phase2.evidence_lineage import (
    EvidenceLineageLedger,
    LineageNode,
    LineageNodeType,
    LineageLink,
    LinkType,
    LineageChain,
    LineageLedgerResponse,
    BuildLedgerRequest,
    TraceRequirementRequest,
    CHAIN_STAGES,
)


# ---------------------------------------------------------------------------
# Extended Chain Stages (10 stages, up from 8)
# ---------------------------------------------------------------------------

EXTENDED_CHAIN_STAGES = [
    "market_research",     # NEW: market research finding anchoring this requirement
    "requirement",         # PWS section / SOO objective
    "clin",                # Contract Line Item Number
    "section_l",           # Section L instruction to offerors
    "section_m",           # Section M evaluation factor
    "evaluator_score",     # SSEB rating
    "ssdd_finding",        # Source Selection Decision Document entry
    "qasp_surveillance",   # QASP surveillance item
    "cpars_rating",        # CPARS performance rating
    "closeout",            # NEW: closeout verification
]


# ---------------------------------------------------------------------------
# Document Dependency Types
# ---------------------------------------------------------------------------

class DependencyType(str, Enum):
    """How one document depends on another."""
    CONTENT_SOURCE = "content_source"       # B derives content from A
    APPROVAL_GATE = "approval_gate"         # B cannot proceed until A approved
    CROSS_REFERENCE = "cross_reference"     # B references A's content
    COMPLIANCE_CHECK = "compliance_check"   # B validates A's compliance
    EVALUATION_BASIS = "evaluation_basis"   # B evaluates based on A's criteria


# ---------------------------------------------------------------------------
# Document Dependency Graph
# ---------------------------------------------------------------------------

# Static dependency map: source_doc → [(dependent_doc, relationship, rationale)]
DOCUMENT_DEPENDENCIES: dict[str, list[tuple[str, DependencyType, str]]] = {
    # PWS is the root — everything flows from it
    "pws": [
        ("section_l", DependencyType.CONTENT_SOURCE,
         "Section L instructions derived from PWS requirements (FAR 15.204-5)"),
        ("section_m", DependencyType.CONTENT_SOURCE,
         "Section M factors evaluate PWS requirements (FAR 15.304)"),
        ("qasp", DependencyType.CONTENT_SOURCE,
         "QASP surveillance items map to PWS sections (FAR 37.604)"),
        ("igce", DependencyType.CONTENT_SOURCE,
         "IGCE cost estimates based on PWS scope (FAR 36.203)"),
        ("bcm", DependencyType.CROSS_REFERENCE,
         "BCM Section A describes requirement from PWS"),
        ("ssp", DependencyType.CROSS_REFERENCE,
         "SSP references PWS scope for evaluation strategy"),
        ("security_requirements", DependencyType.CONTENT_SOURCE,
         "Security requirements derived from PWS security sections"),
    ],
    # Section L and M are tightly coupled
    "section_l": [
        ("section_m", DependencyType.CROSS_REFERENCE,
         "Section M factors must trace to Section L instructions (J-L-M)"),
        ("eval_worksheet", DependencyType.EVALUATION_BASIS,
         "Evaluation worksheets structured per Section L instructions"),
    ],
    "section_m": [
        ("eval_worksheet", DependencyType.CONTENT_SOURCE,
         "Evaluation worksheet factors/ratings from Section M (FAR 15.305)"),
        ("ssp", DependencyType.CONTENT_SOURCE,
         "SSP evaluation methodology aligns with Section M factors"),
    ],
    # IGCE feeds pricing analysis
    "igce": [
        ("bcm", DependencyType.CROSS_REFERENCE,
         "BCM Section H pricing analysis references IGCE (IGPM 0103.19)"),
    ],
    # Market research informs multiple documents
    "market_research": [
        ("pws", DependencyType.CONTENT_SOURCE,
         "Market research findings inform PWS scope and commercial availability"),
        ("igce", DependencyType.CONTENT_SOURCE,
         "Market research pricing intelligence feeds IGCE benchmarks"),
        ("sb_review", DependencyType.CONTENT_SOURCE,
         "Market research SB availability informs 700-22 set-aside decision"),
        ("ja", DependencyType.CONTENT_SOURCE,
         "Market research substantiates J&A market survey section"),
        ("ap", DependencyType.CROSS_REFERENCE,
         "AP references market research findings (FAR 7.105(b)(3))"),
    ],
    # BCM is the approval gateway
    "bcm": [
        ("award_notice", DependencyType.APPROVAL_GATE,
         "Award notice cannot issue until BCM approved"),
    ],
    # J&A gates sole source
    "ja": [
        ("bcm", DependencyType.APPROVAL_GATE,
         "BCM cannot proceed without approved J&A for sole source"),
    ],
    # AP gates solicitation
    "ap": [
        ("bcm", DependencyType.CROSS_REFERENCE,
         "BCM Section G references AP approval status"),
    ],
    # SSP gates evaluation
    "ssp": [
        ("eval_worksheet", DependencyType.CONTENT_SOURCE,
         "Evaluation worksheets implement SSP methodology"),
    ],
    # QASP feeds CPARS
    "qasp": [
        ("cor_nomination", DependencyType.CROSS_REFERENCE,
         "COR nomination references QASP monitoring responsibilities"),
    ],
    # Security requirements gate multiple docs
    "security_requirements": [
        ("cor_nomination", DependencyType.CROSS_REFERENCE,
         "COR nomination references security oversight duties"),
        ("bcm", DependencyType.COMPLIANCE_CHECK,
         "BCM Section G item 22 checks security requirements identified"),
    ],
}


# ---------------------------------------------------------------------------
# Supporting Document → D-code mapping
# ---------------------------------------------------------------------------

SUPPORTING_DOC_DCODES: dict[str, str] = {
    "ja": "D106",              # J&A
    "bcm": "D110",             # BCM
    "df": "D111",              # D&F
    "ap": "D104",              # Acquisition Plan
    "ssp": "D114",             # Source Selection Plan
    "sb_review": "D112",       # DHS Form 700-22
    "cor_nomination": "D115",  # COR Nomination
    "eval_worksheet": "D116",  # Evaluation Worksheets
    "award_notice": "D134",    # Award Notification Letters
    "security_requirements": "D120",  # Security Requirements
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DocumentDependency:
    """A dependency link between two documents."""
    source_doc: str
    dependent_doc: str
    dependency_type: DependencyType
    rationale: str
    is_blocking: bool = False  # True if source must be complete before dependent

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_doc": self.source_doc,
            "dependent_doc": self.dependent_doc,
            "dependency_type": self.dependency_type.value,
            "rationale": self.rationale,
            "is_blocking": self.is_blocking,
        }


@dataclass
class ConsistencyFinding:
    """A cross-document consistency issue."""
    finding_id: str
    severity: str  # critical, high, medium, low
    source_doc: str
    affected_doc: str
    description: str
    recommendation: str
    authority: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "source_doc": self.source_doc,
            "affected_doc": self.affected_doc,
            "description": self.description,
            "recommendation": self.recommendation,
            "authority": self.authority,
        }


@dataclass
class ModificationImpact:
    """Impact assessment when a document or requirement changes."""
    changed_doc: str
    affected_documents: list[str]
    affected_chains: list[str]
    total_affected_nodes: int
    severity_summary: dict[str, int]
    dependency_path: list[DocumentDependency]
    recommended_actions: list[str]
    requires_re_evaluation: bool = False
    requires_re_solicitation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_doc": self.changed_doc,
            "affected_documents": self.affected_documents,
            "affected_chains": self.affected_chains,
            "total_affected_nodes": self.total_affected_nodes,
            "severity_summary": self.severity_summary,
            "dependency_path": [d.to_dict() for d in self.dependency_path],
            "recommended_actions": self.recommended_actions,
            "requires_re_evaluation": self.requires_re_evaluation,
            "requires_re_solicitation": self.requires_re_solicitation,
        }


@dataclass
class FullTraceabilityResult:
    """Complete traceability result across all layers."""
    package_id: str
    # Base lineage (Phase 10)
    base_ledger: LineageLedgerResponse
    # Extended chain coverage (10 stages)
    extended_coverage: dict[str, float]
    # Document chain (Phase 27) integration
    document_nodes_registered: int
    document_links_created: int
    supporting_docs_in_lineage: list[str]
    # Dependency graph
    dependency_graph: list[DocumentDependency]
    # Consistency findings
    consistency_findings: list[ConsistencyFinding]
    # Summary
    total_nodes: int
    total_links: int
    total_chains: int
    overall_coverage: float
    warnings: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "base_ledger": {
                "total_nodes": self.base_ledger.total_nodes,
                "total_links": self.base_ledger.total_links,
                "overall_coverage": self.base_ledger.overall_coverage,
                "fully_traced_chains": self.base_ledger.fully_traced_chains,
                "chain_count": len(self.base_ledger.chains),
                "gap_summary": self.base_ledger.gap_summary,
            },
            "extended_coverage": self.extended_coverage,
            "document_chain": {
                "nodes_registered": self.document_nodes_registered,
                "links_created": self.document_links_created,
                "docs_in_lineage": self.supporting_docs_in_lineage,
            },
            "dependency_graph": [d.to_dict() for d in self.dependency_graph],
            "consistency_findings": [f.to_dict() for f in self.consistency_findings],
            "total_nodes": self.total_nodes,
            "total_links": self.total_links,
            "total_chains": self.total_chains,
            "overall_coverage": self.overall_coverage,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Full Traceability Ledger
# ---------------------------------------------------------------------------

class FullTraceabilityLedger:
    """
    Extends EvidenceLineageLedger with full document chain integration,
    market research findings, cross-document dependencies, and modification
    impact analysis.

    Composition: wraps the base ledger without modifying it.
    """

    def __init__(self, ledger: EvidenceLineageLedger | None = None):
        self.ledger = ledger or EvidenceLineageLedger()
        self._dependency_cache: dict[str, list[DocumentDependency]] = {}

    # -------------------------------------------------------------------
    # Market Research Integration
    # -------------------------------------------------------------------

    def register_market_research(
        self,
        package_id: str,
        report: dict[str, Any],
    ) -> list[LineageNode]:
        """
        Register market research findings as lineage nodes.

        Creates a DOCUMENT node for the report and individual finding nodes
        linked to the requirements they inform.

        Args:
            package_id: Package identifier
            report: MarketResearchAgent output dict with sections

        Returns:
            List of created nodes
        """
        nodes_created = []

        # Create the market research document node
        mr_doc_node = self.ledger.add_node(LineageNode(
            node_type=LineageNodeType.DOCUMENT,
            reference_id=f"{package_id}:market_research",
            label="Market Research Report (FAR 10.002)",
            authority="FAR 10.002",
            metadata={
                "package_id": package_id,
                "doc_type": "market_research",
            },
        ))
        nodes_created.append(mr_doc_node)

        # Create finding nodes for each report section
        sections = report.get("sections", [])
        for sec in sections:
            section_id = sec.get("section_id", sec.get("section_number", ""))
            heading = sec.get("heading", sec.get("title", ""))

            finding_node = self.ledger.add_node(LineageNode(
                node_type=LineageNodeType.DOCUMENT,
                reference_id=f"{package_id}:mr_finding:{section_id}",
                label=f"MR Finding — {heading}",
                authority=sec.get("authority", sec.get("far_authority", "FAR 10.002")),
                metadata={
                    "package_id": package_id,
                    "section_id": section_id,
                    "doc_type": "market_research_finding",
                    "confidence": sec.get("confidence", 0),
                },
            ))
            nodes_created.append(finding_node)

            # Link report → finding
            try:
                self.ledger.add_link(LineageLink(
                    source_node_id=mr_doc_node.node_id,
                    target_node_id=finding_node.node_id,
                    link_type=LinkType.CONTAINS,
                    rationale=f"Market research report contains {heading}",
                    authority="FAR 10.002",
                ))
            except ValueError:
                pass

        return nodes_created

    def link_market_research_to_requirements(
        self,
        package_id: str,
    ) -> list[LineageLink]:
        """
        Link market research findings to PWS requirements they inform.

        Looks for requirement nodes in the ledger and creates TRACES_TO
        links from market research findings.
        """
        links_created = []

        # Find all market research finding nodes
        mr_nodes = [
            n for n in self.ledger.get_all_nodes()
            if n.metadata.get("doc_type") == "market_research_finding"
            and n.metadata.get("package_id") == package_id
        ]

        # Find all requirement nodes for this package
        req_nodes = [
            n for n in self.ledger.get_all_nodes()
            if n.node_type == LineageNodeType.REQUIREMENT
            and n.metadata.get("package_id") == package_id
        ]

        # Link each MR finding to all requirements (broad coverage)
        for mr_node in mr_nodes:
            for req_node in req_nodes:
                try:
                    link = self.ledger.add_link(LineageLink(
                        source_node_id=mr_node.node_id,
                        target_node_id=req_node.node_id,
                        link_type=LinkType.TRACES_TO,
                        rationale=f"Market research informs {req_node.label}",
                        authority="FAR 10.002(b)",
                    ))
                    links_created.append(link)
                except ValueError:
                    pass

        return links_created

    # -------------------------------------------------------------------
    # Document Chain Integration (Phase 27)
    # -------------------------------------------------------------------

    def register_supporting_document(
        self,
        package_id: str,
        doc_type: str,
        draft: dict[str, Any],
    ) -> LineageNode:
        """
        Register a Phase 27 supporting document as a lineage node
        and link it to the D-code it implements.

        Args:
            package_id: Package identifier
            doc_type: Engine type key (e.g. "bcm", "ja", "ssp")
            draft: DocumentDraft.to_dict() output

        Returns:
            Created document node
        """
        dcode = SUPPORTING_DOC_DCODES.get(doc_type, f"D-{doc_type}")
        sections = draft.get("sections", [])

        doc_node = self.ledger.add_node(LineageNode(
            node_type=LineageNodeType.DOCUMENT,
            reference_id=f"{package_id}:{doc_type}",
            label=f"{doc_type.upper()} — {draft.get('doc_type', doc_type)}",
            authority=sections[0].get("authority", "") if sections else "",
            metadata={
                "package_id": package_id,
                "doc_type": doc_type,
                "dcode": dcode,
                "section_count": len(sections),
                "warnings": draft.get("warnings", []),
                "requires_acceptance": draft.get("requires_acceptance", True),
            },
        ))

        # Link document → D-code it implements
        d_node = self.ledger.get_node_by_ref(LineageNodeType.DCODE, dcode)
        if not d_node:
            d_node = self.ledger.add_node(LineageNode(
                node_type=LineageNodeType.DCODE,
                reference_id=dcode,
                label=f"D-code {dcode}",
                authority="Policy Engine",
                metadata={"package_id": package_id},
            ))

        try:
            self.ledger.add_link(LineageLink(
                source_node_id=doc_node.node_id,
                target_node_id=d_node.node_id,
                link_type=LinkType.IMPLEMENTS,
                rationale=f"{doc_type.upper()} implements {dcode}",
                authority="Completeness Validator",
            ))
        except ValueError:
            pass

        # Link sections as contained nodes
        for sec in sections:
            sec_id = sec.get("section_id", "")
            sec_node = self.ledger.add_node(LineageNode(
                node_type=LineageNodeType.DOCUMENT,
                reference_id=f"{package_id}:{doc_type}:{sec_id}",
                label=f"{doc_type.upper()} {sec_id} — {sec.get('heading', '')}",
                authority=sec.get("authority", ""),
                metadata={
                    "package_id": package_id,
                    "doc_type": doc_type,
                    "parent_doc": f"{package_id}:{doc_type}",
                    "confidence": sec.get("confidence", 0),
                },
            ))

            try:
                self.ledger.add_link(LineageLink(
                    source_node_id=doc_node.node_id,
                    target_node_id=sec_node.node_id,
                    link_type=LinkType.CONTAINS,
                    rationale=f"{doc_type.upper()} contains section {sec_id}",
                    authority=sec.get("authority", ""),
                ))
            except ValueError:
                pass

        return doc_node

    def register_document_chain(
        self,
        package_id: str,
        chain_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Register all documents from a Phase 27 ChainResult into lineage.

        Args:
            package_id: Package identifier
            chain_result: ChainResult.to_dict() output

        Returns:
            Summary of registration (nodes created, links created, docs registered)
        """
        nodes_created = 0
        links_created = 0
        docs_registered = []

        # Register supporting documents
        supporting = chain_result.get("supporting_docs", {})
        for doc_type, draft in supporting.items():
            self.register_supporting_document(package_id, doc_type, draft)
            nodes_created += 1 + len(draft.get("sections", []))
            links_created += 1 + len(draft.get("sections", []))  # IMPLEMENTS + CONTAINS
            docs_registered.append(doc_type)

        # Register base pipeline documents if present
        pipeline = chain_result.get("pipeline_result", {})
        base_docs = pipeline.get("documents", {})
        for stage, output in base_docs.items():
            sections = output.get("sections", [])
            stage_doc = self.ledger.add_node(LineageNode(
                node_type=LineageNodeType.DOCUMENT,
                reference_id=f"{package_id}:pipeline:{stage}",
                label=f"Pipeline — {stage}",
                authority="",
                metadata={
                    "package_id": package_id,
                    "doc_type": f"pipeline_{stage}",
                    "section_count": len(sections),
                },
            ))
            nodes_created += 1
            docs_registered.append(f"pipeline_{stage}")

        # Add cross-document dependency links
        dep_links = self._register_dependency_links(package_id, docs_registered)
        links_created += len(dep_links)

        return {
            "nodes_created": nodes_created,
            "links_created": links_created,
            "docs_registered": docs_registered,
        }

    def _register_dependency_links(
        self,
        package_id: str,
        available_docs: list[str],
    ) -> list[LineageLink]:
        """Create lineage links based on the document dependency graph."""
        links = []

        for source_doc, deps in DOCUMENT_DEPENDENCIES.items():
            # Normalize: pipeline docs are prefixed
            source_ref = f"{package_id}:{source_doc}"
            source_node = self.ledger.get_node_by_ref(
                LineageNodeType.DOCUMENT, source_ref
            )
            if not source_node:
                # Try pipeline prefix
                source_node = self.ledger.get_node_by_ref(
                    LineageNodeType.DOCUMENT, f"{package_id}:pipeline:{source_doc}"
                )
            if not source_node:
                continue

            for dep_doc, dep_type, rationale in deps:
                dep_ref = f"{package_id}:{dep_doc}"
                dep_node = self.ledger.get_node_by_ref(
                    LineageNodeType.DOCUMENT, dep_ref
                )
                if not dep_node:
                    dep_node = self.ledger.get_node_by_ref(
                        LineageNodeType.DOCUMENT, f"{package_id}:pipeline:{dep_doc}"
                    )
                if not dep_node:
                    continue

                try:
                    link = self.ledger.add_link(LineageLink(
                        source_node_id=source_node.node_id,
                        target_node_id=dep_node.node_id,
                        link_type=LinkType.TRACES_TO,
                        rationale=rationale,
                        metadata={"dependency_type": dep_type.value},
                    ))
                    links.append(link)
                except ValueError:
                    pass

        return links

    # -------------------------------------------------------------------
    # Cross-Document Dependency Graph
    # -------------------------------------------------------------------

    def build_dependency_graph(
        self,
        params: dict[str, Any],
    ) -> list[DocumentDependency]:
        """
        Build the cross-document dependency graph for an acquisition.

        Args:
            params: Acquisition parameters (to determine applicable docs)

        Returns:
            List of DocumentDependency edges
        """
        sole_source = (
            params.get("sole_source", False) or
            params.get("competition_type") == "sole_source"
        )
        services = params.get("services", True)
        value = params.get("estimated_value", 0)

        dependencies = []

        for source_doc, dep_list in DOCUMENT_DEPENDENCIES.items():
            # Skip inapplicable source docs
            if source_doc == "ja" and not sole_source:
                continue

            for dep_doc, dep_type, rationale in dep_list:
                # Skip inapplicable dependent docs
                if dep_doc == "ja" and not sole_source:
                    continue
                if dep_doc == "cor_nomination" and not services:
                    continue
                if dep_doc == "sb_review" and value < 100_000:
                    continue

                is_blocking = dep_type == DependencyType.APPROVAL_GATE

                dependencies.append(DocumentDependency(
                    source_doc=source_doc,
                    dependent_doc=dep_doc,
                    dependency_type=dep_type,
                    rationale=rationale,
                    is_blocking=is_blocking,
                ))

        self._dependency_cache[str(params.get("package_id", ""))] = dependencies
        return dependencies

    def get_upstream_docs(self, doc_type: str) -> list[str]:
        """Get all documents that feed INTO the given document."""
        upstream = []
        for source_doc, dep_list in DOCUMENT_DEPENDENCIES.items():
            for dep_doc, _, _ in dep_list:
                if dep_doc == doc_type:
                    upstream.append(source_doc)
        return list(set(upstream))

    def get_downstream_docs(self, doc_type: str) -> list[str]:
        """Get all documents that depend ON the given document."""
        downstream = []
        deps = DOCUMENT_DEPENDENCIES.get(doc_type, [])
        for dep_doc, _, _ in deps:
            downstream.append(dep_doc)
        return list(set(downstream))

    # -------------------------------------------------------------------
    # Cross-Document Consistency Checking
    # -------------------------------------------------------------------

    def check_consistency(
        self,
        package_id: str,
        documents: dict[str, dict[str, Any]],
    ) -> list[ConsistencyFinding]:
        """
        Check cross-document consistency for a package.

        Validates that:
        1. PWS requirements are reflected in Section L, M, QASP
        2. Section L instructions trace to Section M factors
        3. BCM Section G compliance items are addressed
        4. Evaluation worksheet factors match Section M
        5. Security requirements are consistent across docs

        Args:
            package_id: Package identifier
            documents: Dict of doc_type → document content

        Returns:
            List of consistency findings
        """
        findings = []
        finding_counter = 0

        # Check 1: PWS → Section L traceability
        if "pws" in documents and "section_l" in documents:
            finding_counter = self._check_pws_l_consistency(
                documents["pws"], documents["section_l"],
                findings, finding_counter
            )

        # Check 2: Section L → Section M traceability
        if "section_l" in documents and "section_m" in documents:
            finding_counter = self._check_l_m_consistency(
                documents["section_l"], documents["section_m"],
                findings, finding_counter
            )

        # Check 3: Section M → Eval Worksheet alignment
        if "section_m" in documents and "eval_worksheet" in documents:
            finding_counter = self._check_m_worksheet_consistency(
                documents["section_m"], documents["eval_worksheet"],
                findings, finding_counter
            )

        # Check 4: PWS → QASP coverage
        if "pws" in documents and "qasp" in documents:
            finding_counter = self._check_pws_qasp_consistency(
                documents["pws"], documents["qasp"],
                findings, finding_counter
            )

        # Check 5: Security consistency
        if "security_requirements" in documents:
            finding_counter = self._check_security_consistency(
                documents, findings, finding_counter
            )

        # Check 6: BCM references
        if "bcm" in documents:
            finding_counter = self._check_bcm_references(
                documents, findings, finding_counter
            )

        return findings

    def _check_pws_l_consistency(
        self, pws: dict, section_l: dict,
        findings: list[ConsistencyFinding], counter: int,
    ) -> int:
        """PWS requirements should be addressable via Section L instructions."""
        pws_sections = self._get_sections(pws)
        l_sections = self._get_sections(section_l)

        if pws_sections and not l_sections:
            counter += 1
            findings.append(ConsistencyFinding(
                finding_id=f"CF-{counter:03d}",
                severity="high",
                source_doc="pws",
                affected_doc="section_l",
                description="PWS has requirements but Section L has no instruction sections",
                recommendation="Generate Section L instructions that address PWS requirements",
                authority="FAR 15.204-5",
            ))

        # Check if L has technical/management sections matching PWS scope
        l_ids = {s.get("section_id", "") for s in l_sections}
        has_tech = any(lid.startswith("L.3") for lid in l_ids)
        has_mgmt = any(lid.startswith("L.4") for lid in l_ids)

        if pws_sections and not has_tech:
            counter += 1
            findings.append(ConsistencyFinding(
                finding_id=f"CF-{counter:03d}",
                severity="high",
                source_doc="pws",
                affected_doc="section_l",
                description="PWS has technical requirements but Section L lacks L.3 (Technical Approach)",
                recommendation="Add Section L.3 with instructions for technical approach",
                authority="FAR 15.204-5(b)",
            ))

        return counter

    def _check_l_m_consistency(
        self, section_l: dict, section_m: dict,
        findings: list[ConsistencyFinding], counter: int,
    ) -> int:
        """Every Section L instruction should trace to a Section M factor."""
        l_sections = self._get_sections(section_l)
        m_sections = self._get_sections(section_m)

        if l_sections and not m_sections:
            counter += 1
            findings.append(ConsistencyFinding(
                finding_id=f"CF-{counter:03d}",
                severity="critical",
                source_doc="section_l",
                affected_doc="section_m",
                description="Section L has instructions but Section M has no evaluation factors",
                recommendation="Generate Section M factors that evaluate Section L instructions",
                authority="FAR 15.304 — all evaluation factors must be stated in solicitation",
            ))

        m_ids = {s.get("section_id", "") for s in m_sections}
        l_ids = {s.get("section_id", "") for s in l_sections}

        # L.3 should pair with M.2, L.4 with M.3 (standard J-L-M mapping)
        jlm_pairs = [("L.3", "M.2"), ("L.4", "M.3")]
        for l_id, m_id in jlm_pairs:
            if any(lid.startswith(l_id) for lid in l_ids):
                if not any(mid.startswith(m_id) for mid in m_ids):
                    counter += 1
                    findings.append(ConsistencyFinding(
                        finding_id=f"CF-{counter:03d}",
                        severity="high",
                        source_doc="section_l",
                        affected_doc="section_m",
                        description=f"Section {l_id} instruction exists but {m_id} factor missing",
                        recommendation=f"Add Section {m_id} evaluation factor to evaluate {l_id}",
                        authority="FAR 15.304(c)",
                    ))

        return counter

    def _check_m_worksheet_consistency(
        self, section_m: dict, eval_worksheet: dict,
        findings: list[ConsistencyFinding], counter: int,
    ) -> int:
        """Evaluation worksheet factors should match Section M."""
        m_sections = self._get_sections(section_m)
        ws_sections = self._get_sections(eval_worksheet)

        if m_sections and not ws_sections:
            counter += 1
            findings.append(ConsistencyFinding(
                finding_id=f"CF-{counter:03d}",
                severity="medium",
                source_doc="section_m",
                affected_doc="eval_worksheet",
                description="Section M has factors but evaluation worksheets are empty",
                recommendation="Generate evaluation worksheets matching Section M factors",
                authority="FAR 15.305",
            ))

        return counter

    def _check_pws_qasp_consistency(
        self, pws: dict, qasp: dict,
        findings: list[ConsistencyFinding], counter: int,
    ) -> int:
        """QASP surveillance items should cover PWS performance requirements."""
        pws_sections = self._get_sections(pws)
        qasp_sections = self._get_sections(qasp)

        if pws_sections and not qasp_sections:
            counter += 1
            findings.append(ConsistencyFinding(
                finding_id=f"CF-{counter:03d}",
                severity="high",
                source_doc="pws",
                affected_doc="qasp",
                description="PWS has performance requirements but QASP has no surveillance items",
                recommendation="Generate QASP surveillance items mapped to PWS sections",
                authority="FAR 37.604 / FAR 46.4",
            ))

        # Check ratio — QASP should have at least as many items as PWS sections
        if pws_sections and qasp_sections:
            if len(qasp_sections) < len(pws_sections) * 0.5:
                counter += 1
                findings.append(ConsistencyFinding(
                    finding_id=f"CF-{counter:03d}",
                    severity="medium",
                    source_doc="pws",
                    affected_doc="qasp",
                    description=(
                        f"QASP has {len(qasp_sections)} items for {len(pws_sections)} "
                        f"PWS sections — coverage may be insufficient"
                    ),
                    recommendation="Review QASP to ensure all key PWS requirements have surveillance items",
                    authority="FAR 37.604",
                ))

        return counter

    def _check_security_consistency(
        self, documents: dict[str, dict],
        findings: list[ConsistencyFinding], counter: int,
    ) -> int:
        """Security requirements should be reflected in BCM and COR nomination."""
        sec_doc = documents.get("security_requirements", {})
        sec_sections = self._get_sections(sec_doc)

        # If security has personnel security, BCM should reference it
        has_personnel = any(
            "personnel" in s.get("heading", "").lower() or
            "personnel" in s.get("content", "").lower()
            for s in sec_sections
        )

        if has_personnel and "cor_nomination" in documents:
            cor_sections = self._get_sections(documents["cor_nomination"])
            cor_content = " ".join(s.get("content", "") for s in cor_sections).lower()
            if "security" not in cor_content:
                counter += 1
                findings.append(ConsistencyFinding(
                    finding_id=f"CF-{counter:03d}",
                    severity="medium",
                    source_doc="security_requirements",
                    affected_doc="cor_nomination",
                    description="Security requirements include personnel security but COR nomination doesn't reference security oversight",
                    recommendation="Update COR nomination to include security monitoring responsibilities",
                    authority="HSAR 3052.204-71",
                ))

        return counter

    def _check_bcm_references(
        self, documents: dict[str, dict],
        findings: list[ConsistencyFinding], counter: int,
    ) -> int:
        """BCM should reference key documents that exist."""
        bcm = documents.get("bcm", {})
        bcm_sections = self._get_sections(bcm)
        bcm_content = " ".join(
            s.get("content", "") for s in bcm_sections
        ).lower()

        # BCM should mention AP if one exists
        if "ap" in documents and "acquisition plan" not in bcm_content:
            counter += 1
            findings.append(ConsistencyFinding(
                finding_id=f"CF-{counter:03d}",
                severity="low",
                source_doc="ap",
                affected_doc="bcm",
                description="Acquisition Plan exists but BCM doesn't reference it",
                recommendation="Update BCM Section G item 2 to reference approved AP",
                authority="IGPM 0103.19",
            ))

        return counter

    @staticmethod
    def _get_sections(doc: dict) -> list[dict]:
        """Extract sections list from various document formats."""
        if not doc:
            return []
        # Direct sections list
        if "sections" in doc:
            secs = doc["sections"]
            if isinstance(secs, list):
                return secs
        # Nested under content
        content = doc.get("content", {})
        if isinstance(content, dict) and "sections" in content:
            return content.get("sections", [])
        return []

    # -------------------------------------------------------------------
    # Modification Impact Analysis
    # -------------------------------------------------------------------

    def analyze_modification_impact(
        self,
        changed_doc: str,
        params: dict[str, Any] | None = None,
    ) -> ModificationImpact:
        """
        Analyze the impact of modifying a document.

        Traces through the dependency graph to find all affected documents
        and generates recommended actions.

        Args:
            changed_doc: The document type that changed (e.g., "pws", "section_m")
            params: Acquisition parameters (for filtering applicable docs)

        Returns:
            ModificationImpact assessment
        """
        # BFS through dependency graph
        visited = set()
        affected_docs = []
        dependency_path = []
        queue = [changed_doc]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            deps = DOCUMENT_DEPENDENCIES.get(current, [])
            for dep_doc, dep_type, rationale in deps:
                if dep_doc not in visited:
                    affected_docs.append(dep_doc)
                    dependency_path.append(DocumentDependency(
                        source_doc=current,
                        dependent_doc=dep_doc,
                        dependency_type=dep_type,
                        rationale=rationale,
                        is_blocking=dep_type == DependencyType.APPROVAL_GATE,
                    ))
                    queue.append(dep_doc)

        # Deduplicate affected docs
        affected_docs = list(dict.fromkeys(affected_docs))

        # Compute severity
        severity = self._compute_impact_severity(changed_doc, affected_docs)

        # Check if re-evaluation or re-solicitation needed
        requires_re_eval = any(
            d in ("eval_worksheet", "section_m") for d in affected_docs
        )
        requires_re_sol = changed_doc in ("pws", "section_l", "section_m")

        # Generate actions
        actions = self._generate_mod_actions(changed_doc, affected_docs, dependency_path)

        # Find affected lineage chains
        affected_chains = []
        if changed_doc in ("pws", "section_l", "section_m", "qasp"):
            # These docs are in requirement chains
            for chain_id, chain in self.ledger._chains.items():
                affected_chains.append(chain_id)

        return ModificationImpact(
            changed_doc=changed_doc,
            affected_documents=affected_docs,
            affected_chains=affected_chains,
            total_affected_nodes=len(affected_docs),
            severity_summary=severity,
            dependency_path=dependency_path,
            recommended_actions=actions,
            requires_re_evaluation=requires_re_eval,
            requires_re_solicitation=requires_re_sol,
        )

    def _compute_impact_severity(
        self, changed_doc: str, affected_docs: list[str],
    ) -> dict[str, int]:
        """Classify impact severity based on affected documents."""
        severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        CRITICAL_DOCS = {"eval_worksheet", "section_m", "ssp"}
        HIGH_DOCS = {"section_l", "bcm", "award_notice", "pws"}
        MEDIUM_DOCS = {"igce", "qasp", "security_requirements", "ja", "df", "ap"}
        LOW_DOCS = {"sb_review", "cor_nomination"}

        for doc in affected_docs:
            if doc in CRITICAL_DOCS:
                severity["critical"] += 1
            elif doc in HIGH_DOCS:
                severity["high"] += 1
            elif doc in MEDIUM_DOCS:
                severity["medium"] += 1
            elif doc in LOW_DOCS:
                severity["low"] += 1
            else:
                severity["medium"] += 1

        return severity

    def _generate_mod_actions(
        self, changed_doc: str, affected: list[str],
        dependencies: list[DocumentDependency],
    ) -> list[str]:
        """Generate recommended actions for a modification."""
        actions = []

        DOC_ACTIONS = {
            "pws": "Regenerate PWS-derived documents (Section L, M, QASP, IGCE)",
            "section_l": "Update Section L instructions and verify J-L-M traceability",
            "section_m": "CRITICAL: Evaluation factors changed — regenerate worksheets and review SSP",
            "igce": "Update IGCE and verify BCM pricing analysis references",
            "qasp": "Update QASP surveillance items and verify COR monitoring scope",
            "bcm": "Update BCM and verify award notice references",
            "ssp": "Update SSP evaluation methodology and regenerate worksheets",
            "security_requirements": "Update security requirements across all referencing documents",
            "market_research": "Market research changed — review PWS scope, IGCE benchmarks, and SB availability",
        }

        action = DOC_ACTIONS.get(changed_doc)
        if action:
            actions.append(action)

        # Blocking dependencies get special attention
        blocking = [d for d in dependencies if d.is_blocking]
        for dep in blocking:
            actions.append(
                f"BLOCKING: {dep.source_doc.upper()} must be approved before "
                f"{dep.dependent_doc.upper()} can proceed"
            )

        # J-L-M traceability check
        jlm_docs = {"pws", "section_l", "section_m"}
        if changed_doc in jlm_docs and jlm_docs & set(affected):
            actions.append("Re-verify J-L-M traceability (FAR 15.304) after changes")

        if not actions:
            actions.append(f"Review {len(affected)} affected document(s) for consistency")

        return actions

    # -------------------------------------------------------------------
    # Extended Chain Coverage
    # -------------------------------------------------------------------

    def compute_extended_coverage(
        self,
        package_id: str,
        documents: dict[str, dict[str, Any]],
    ) -> dict[str, float]:
        """
        Compute extended 10-stage coverage for a package.

        Returns coverage percentage per stage.
        """
        coverage = {stage: 0.0 for stage in EXTENDED_CHAIN_STAGES}

        # market_research: present if MR doc exists
        if any(
            n.metadata.get("doc_type") == "market_research"
            and n.metadata.get("package_id") == package_id
            for n in self.ledger.get_all_nodes()
        ):
            coverage["market_research"] = 1.0
        elif "market_research" in documents:
            coverage["market_research"] = 1.0

        # Base 8 stages from chains
        chains = self.ledger.get_package_chains(package_id)
        if chains:
            for stage in CHAIN_STAGES:
                covered = sum(
                    1 for c in chains if c.coverage.get(stage, False)
                )
                coverage[stage] = covered / len(chains) if chains else 0.0

        # closeout: check if closeout doc exists
        if any(
            n.metadata.get("doc_type") == "closeout"
            and n.metadata.get("package_id") == package_id
            for n in self.ledger.get_all_nodes()
        ):
            coverage["closeout"] = 1.0

        return coverage

    # -------------------------------------------------------------------
    # Full Build Orchestration
    # -------------------------------------------------------------------

    def build_full_traceability(
        self,
        package_id: str,
        documents: list[dict[str, Any]],
        market_research: dict[str, Any] | None = None,
        chain_result: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> FullTraceabilityResult:
        """
        Build complete traceability for a package across all layers.

        Steps:
        1. Register market research findings (if available)
        2. Build base lineage (Phase 10 chain)
        3. Register document chain (Phase 27) into lineage
        4. Build dependency graph
        5. Check cross-document consistency
        6. Compute extended coverage
        7. Link market research to requirements

        Args:
            package_id: Package identifier
            documents: List of package documents for base ledger
            market_research: Optional market research report dict
            chain_result: Optional Phase 27 ChainResult.to_dict()
            params: Acquisition parameters

        Returns:
            FullTraceabilityResult with all layers
        """
        params = params or {}
        warnings = []

        # Step 1: Market research
        mr_nodes = []
        if market_research:
            mr_nodes = self.register_market_research(package_id, market_research)

        # Step 2: Build base lineage
        base_request = BuildLedgerRequest(
            package_id=package_id,
            documents=documents,
        )
        base_ledger = self.ledger.build_ledger(base_request)
        warnings.extend(base_ledger.warnings)

        # Step 3: Link market research → requirements
        if mr_nodes:
            self.link_market_research_to_requirements(package_id)

        # Step 4: Register document chain
        doc_nodes = 0
        doc_links = 0
        docs_in_lineage = []
        if chain_result:
            reg_result = self.register_document_chain(package_id, chain_result)
            doc_nodes = reg_result["nodes_created"]
            doc_links = reg_result["links_created"]
            docs_in_lineage = reg_result["docs_registered"]

        # Step 5: Build dependency graph
        dep_graph = self.build_dependency_graph(params)

        # Step 6: Check consistency
        doc_dict = {}
        if chain_result:
            for doc_type, draft in chain_result.get("supporting_docs", {}).items():
                doc_dict[doc_type] = draft
            for stage, output in chain_result.get("pipeline_result", {}).get("documents", {}).items():
                doc_dict[stage] = output

        consistency = self.check_consistency(package_id, doc_dict)
        if consistency:
            warnings.append(
                f"{len(consistency)} cross-document consistency finding(s) detected"
            )

        # Step 7: Extended coverage
        extended = self.compute_extended_coverage(package_id, doc_dict)

        # Compute totals
        stats = self.ledger.stats()
        overall_cov = sum(extended.values()) / len(extended) if extended else 0.0

        return FullTraceabilityResult(
            package_id=package_id,
            base_ledger=base_ledger,
            extended_coverage=extended,
            document_nodes_registered=doc_nodes,
            document_links_created=doc_links,
            supporting_docs_in_lineage=docs_in_lineage,
            dependency_graph=dep_graph,
            consistency_findings=consistency,
            total_nodes=stats["total_nodes"],
            total_links=stats["total_links"],
            total_chains=stats["total_chains"],
            overall_coverage=round(overall_cov, 3),
            warnings=warnings,
            generated_at=datetime.now(timezone.utc).isoformat() + "Z",
        )
