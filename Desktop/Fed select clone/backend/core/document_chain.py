"""
Phase 27: Full Document Chain Integration
==========================================

Integrates the 10 new document engines (document_engines.py) with the
Phase 26 Drafting Orchestrator pipeline. Adds new PipelineStages and
engine adapters for supporting documents (J&A, BCM, D&F, AP, SSP, etc.).

The document chain extends the base pipeline by:
1. Running the base 10-stage pipeline (market research → UCF assembly)
2. Generating all applicable supporting documents via generate_full_chain()
3. Mapping supporting docs to UCF sections
4. Aggregating into a unified ChainResult

Design: This is a COMPOSITION layer — it does NOT modify the base
orchestrator. Existing 89 orchestrator tests remain untouched.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.core.document_engines import (
    generate_full_chain, generate_document,
    DocumentDraft, DraftSection, DOCUMENT_ENGINES,
    _get_bcm_approval, _get_ssa_appointment, _get_ja_approval,
)
from backend.core.drafting_orchestrator import (
    DraftingOrchestrator, PipelineResult, PipelineStage,
    EngineOutput, UCFSection, UCFMapping, VersionStore,
)


# ─── UCF Mapping for Supporting Documents ──────────────────────────────────

# Maps document engine type → UCF section
SUPPORT_DOC_UCF_MAP: dict[str, tuple[UCFSection, str]] = {
    "bcm": (UCFSection.G, "IGPM 0103.19"),
    "ja": (UCFSection.J, "FAR 6.303/6.304"),
    "df": (UCFSection.J, "Various FAR parts"),
    "ap": (UCFSection.J, "FAR 7.105, HSAM Appendix Z"),
    "ssp": (UCFSection.J, "FAR 15.303"),
    "sb_review": (UCFSection.K, "DHS Form 700-22"),
    "cor_nomination": (UCFSection.G, "TSA MD 300.9"),
    "eval_worksheet": (UCFSection.J, "FAR 15.305"),
    "award_notice": (UCFSection.G, "FAR 5.301, DHS 2140-01"),
    "security_requirements": (UCFSection.H, "HSAR 3052.204-71/72"),
}


# ─── Chain Result ──────────────────────────────────────────────────────────

@dataclass
class ChainResult:
    """Full output of the document chain — base pipeline + supporting docs."""
    package_id: str
    # Base pipeline output (PWS, IGCE, L, M, QASP)
    pipeline_result: PipelineResult
    # Supporting documents (J&A, BCM, D&F, AP, SSP, etc.)
    supporting_docs: dict[str, DocumentDraft]
    # Combined UCF assembly (base + supporting)
    full_ucf_assembly: list[UCFMapping]
    # Aggregated metadata
    total_documents: int
    total_sections: int
    warnings: list[str]
    generated_at: str
    # Approval chain summary
    approval_summary: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "pipeline_result": self.pipeline_result.to_dict(),
            "supporting_docs": {
                k: v.to_dict() for k, v in self.supporting_docs.items()
            },
            "full_ucf_assembly": [
                {
                    "ucf_section": m.ucf_section.value,
                    "doc_type": m.doc_type,
                    "section_count": len(m.sections),
                    "authority": m.authority,
                }
                for m in self.full_ucf_assembly
            ],
            "total_documents": self.total_documents,
            "total_sections": self.total_sections,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
            "approval_summary": self.approval_summary,
        }


# ─── Document Chain Orchestrator ───────────────────────────────────────────

class DocumentChainOrchestrator:
    """Orchestrates full document chain generation.

    Composes the Phase 26 DraftingOrchestrator (base pipeline) with
    Phase 27 document engines (supporting documents).

    Usage:
        chain = DocumentChainOrchestrator()
        result = chain.generate("pkg-001", params)
    """

    def __init__(self, version_store: VersionStore | None = None):
        self.version_store = version_store or VersionStore()
        self.base_orchestrator = DraftingOrchestrator(self.version_store)

    def generate(
        self,
        package_id: str,
        params: dict[str, Any],
        requirements: list[dict] | None = None,
        eval_factors: list[dict] | None = None,
        skip_base_pipeline: bool = False,
        skip_supporting: bool = False,
        doc_types: list[str] | None = None,
    ) -> ChainResult:
        """Generate full document chain.

        Args:
            package_id: Unique package identifier
            params: Acquisition parameters
            requirements: Optional pre-built requirements list
            eval_factors: Optional pre-built evaluation factors
            skip_base_pipeline: Skip PWS/IGCE/L/M/QASP generation
            skip_supporting: Skip J&A/BCM/D&F/AP/SSP generation
            doc_types: If provided, only generate these supporting doc types

        Returns:
            ChainResult with base pipeline + supporting documents
        """
        all_warnings = []

        # Step 1: Run base pipeline (unless skipped)
        if skip_base_pipeline:
            pipeline_result = PipelineResult(
                package_id=package_id,
                stages_completed=[],
                documents={},
                compliance_results={},
                ucf_assembly=[],
                warnings=["Base pipeline skipped"],
                overall_confidence=0.0,
                generated_at=datetime.now(timezone.utc).isoformat(),
                source_provenance=[],
            )
        else:
            pipeline_result = self.base_orchestrator.run(
                package_id=package_id,
                params=params,
                requirements=requirements,
                eval_factors=eval_factors,
            )
            all_warnings.extend(pipeline_result.warnings)

        # Step 2: Generate supporting documents
        supporting_docs: dict[str, DocumentDraft] = {}
        if not skip_supporting:
            if doc_types:
                # Generate only specified types
                for dt in doc_types:
                    if dt in DOCUMENT_ENGINES:
                        try:
                            supporting_docs[dt] = generate_document(dt, params)
                        except Exception as e:
                            all_warnings.append(f"Failed to generate {dt}: {str(e)}")
            else:
                # Generate all applicable
                supporting_docs = generate_full_chain(params)

            # Collect warnings from supporting docs
            for dt, draft in supporting_docs.items():
                all_warnings.extend(draft.warnings)

        # Step 3: Build combined UCF assembly
        full_ucf = list(pipeline_result.ucf_assembly)  # Start with base UCF
        for doc_type, draft in supporting_docs.items():
            if doc_type in SUPPORT_DOC_UCF_MAP:
                ucf_sec, authority = SUPPORT_DOC_UCF_MAP[doc_type]
                full_ucf.append(UCFMapping(
                    ucf_section=ucf_sec,
                    doc_type=doc_type,
                    sections=[{
                        "section_id": s.section_id,
                        "heading": s.heading,
                        "content": s.content,
                        "authority": s.authority,
                    } for s in draft.sections],
                    authority=authority,
                ))

        # Sort by UCF section order
        section_order = list(UCFSection)
        full_ucf.sort(key=lambda m: section_order.index(m.ucf_section))

        # Step 4: Save supporting docs to version store
        for doc_type, draft in supporting_docs.items():
            # Create a synthetic PipelineStage key for version tracking
            sections_as_dicts = [{
                "section_id": s.section_id,
                "heading": s.heading,
                "content": s.content,
                "authority": s.authority,
                "rationale": s.rationale,
                "confidence": s.confidence,
            } for s in draft.sections]
            # Use PWS stage key as fallback (version store requires PipelineStage)
            # In production, extend PipelineStage enum — for now, store under metadata
            if sections_as_dicts:
                self.version_store.save(
                    package_id, PipelineStage.PWS,
                    sections_as_dicts,
                    metadata={"doc_type": doc_type, "is_supporting": True},
                )

        # Step 5: Compute totals
        base_sections = sum(len(o.sections) for o in pipeline_result.documents.values())
        support_sections = sum(len(d.sections) for d in supporting_docs.values())
        total_docs = len(pipeline_result.documents) + len(supporting_docs)

        # Step 6: Derive approval summary
        approval_summary = self._derive_approval_summary(params)

        return ChainResult(
            package_id=package_id,
            pipeline_result=pipeline_result,
            supporting_docs=supporting_docs,
            full_ucf_assembly=full_ucf,
            total_documents=total_docs,
            total_sections=base_sections + support_sections,
            warnings=all_warnings,
            generated_at=datetime.now(timezone.utc).isoformat(),
            approval_summary=approval_summary,
        )

    def generate_single(self, doc_type: str, params: dict[str, Any]) -> DocumentDraft:
        """Generate a single supporting document by type."""
        return generate_document(doc_type, params)

    def _derive_approval_summary(self, params: dict[str, Any]) -> dict[str, str]:
        """Derive approval chain summary from params."""
        value = params.get("estimated_value", 0)
        sole_source = (
            params.get("sole_source", False) or
            params.get("competition_type") == "sole_source"
        )

        summary = {}

        # BCM
        chain, approver = _get_bcm_approval(value)
        summary["bcm_approver"] = approver
        summary["bcm_chain"] = chain

        # SSA
        summary["ssa_appointment"] = _get_ssa_appointment(value)

        # J&A (if applicable)
        if sole_source:
            ja_approver, ja_auth = _get_ja_approval(value)
            summary["ja_approver"] = ja_approver
            summary["ja_authority"] = ja_auth

        return summary

    @staticmethod
    def list_available_doc_types() -> list[dict[str, str]]:
        """List all available document types with descriptions."""
        descriptions = {
            "ja": "Justification & Approval (FAR 6.302/6.304)",
            "bcm": "Business Clearance Memorandum (TSA IGPM 0103.19)",
            "df": "Determination & Findings (various FAR parts)",
            "ap": "Acquisition Plan (HSAM Appendix Z / TSA MD 300.25)",
            "ssp": "Source Selection Plan (FAR 15.303)",
            "sb_review": "DHS Form 700-22 Small Business Review",
            "cor_nomination": "COR Nomination Letter (TSA MD 300.9)",
            "eval_worksheet": "Evaluation Worksheets (FAR 15.305)",
            "award_notice": "Award Notification (FAR 5.301 / DHS 2140-01)",
            "security_requirements": "Security Requirements (HSAR 3052.204-71/72)",
        }
        return [
            {"doc_type": dt, "description": descriptions.get(dt, dt)}
            for dt in DOCUMENT_ENGINES
        ]
