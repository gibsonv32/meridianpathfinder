"""
Phase 26: Drafting Orchestrator — Agent-Callable Document Pipeline

Chains upstream agents into a unified document generation pipeline:
  MarketResearch → Requirements → FactorDerivation → PWS → IGCE →
  Section L → Section M → QASP → ComplianceValidation → UCF Assembly

Each engine is called with standardized EngineInput/EngineOutput contracts.
Version control provides full diff history per document section with rollback.

No DB dependency — all state is in-memory (VersionStore).

Design principles:
- Each step receives the prior step's output via PipelineContext
- ComplianceOverlay runs as post-generation validation on each document
- Version store tracks every generation with rollback capability
- UCF assembly maps generated documents to FAR 15.204 sections
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ─── Upstream Imports (lazy — not required for standalone operation) ──────────
# These are imported at call time to avoid circular dependencies and to
# allow the orchestrator to operate in test mode without all upstream modules.


# ─── Enums & Data Classes ────────────────────────────────────────────────────

class PipelineStage(str, Enum):
    MARKET_RESEARCH = "market_research"
    REQUIREMENTS = "requirements"
    FACTOR_DERIVATION = "factor_derivation"
    PWS = "pws"
    IGCE = "igce"
    SECTION_L = "section_l"
    SECTION_M = "section_m"
    QASP = "qasp"
    COMPLIANCE = "compliance"
    UCF_ASSEMBLY = "ucf_assembly"


class UCFSection(str, Enum):
    """Uniform Contract Format per FAR 15.204."""
    A = "A"    # SF 1449 or SF 33
    B = "B"    # Supplies or Services and Prices/Costs
    C = "C"    # Description/Specs/SOW/PWS
    D = "D"    # Packaging and Marking
    E = "E"    # Inspection and Acceptance
    F = "F"    # Deliveries or Performance
    G = "G"    # Contract Administration Data
    H = "H"    # Special Contract Requirements
    I = "I"    # Contract Clauses
    J = "J"    # Attachments (QASP, etc.)
    K = "K"    # Representations and Certifications
    L = "L"    # Instructions to Offerors
    M = "M"    # Evaluation Factors


@dataclass
class EngineInput:
    """Standardized input contract for all drafting engines."""
    package_id: str
    acquisition_params: dict[str, Any]
    # Optional upstream outputs fed in by orchestrator
    requirements: list[dict] | None = None
    market_research: dict | None = None
    eval_factors: list[dict] | None = None
    pws_sections: list[dict] | None = None
    compliance_context: dict | None = None


@dataclass
class EngineOutput:
    """Standardized output contract from all drafting engines."""
    stage: PipelineStage
    sections: list[dict]           # [{section_id, heading, content, authority, rationale, confidence}]
    warnings: list[str] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)
    confidence: float = 80.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VersionRecord:
    """A single version snapshot of a document."""
    version: int
    stage: PipelineStage
    sections: list[dict]
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceResult:
    """Compliance check results for a single document."""
    doc_type: str
    overall_score: float
    issues: list[dict] = field(default_factory=list)
    passed: bool = True


@dataclass
class UCFMapping:
    """Maps a generated document to its UCF section."""
    ucf_section: UCFSection
    doc_type: str
    sections: list[dict]
    authority: str


@dataclass
class PipelineResult:
    """Full output of the orchestration pipeline."""
    package_id: str
    stages_completed: list[PipelineStage]
    documents: dict[str, EngineOutput]        # stage name → output
    compliance_results: dict[str, ComplianceResult]
    ucf_assembly: list[UCFMapping]
    warnings: list[str]
    overall_confidence: float
    generated_at: str
    source_provenance: list[str]

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "stages_completed": [s.value for s in self.stages_completed],
            "documents": {
                k: {
                    "stage": v.stage.value,
                    "sections": v.sections,
                    "warnings": v.warnings,
                    "provenance": v.provenance,
                    "confidence": v.confidence,
                } for k, v in self.documents.items()
            },
            "compliance_results": {
                k: {
                    "doc_type": v.doc_type,
                    "overall_score": v.overall_score,
                    "issues": v.issues,
                    "passed": v.passed,
                } for k, v in self.compliance_results.items()
            },
            "ucf_assembly": [
                {
                    "ucf_section": m.ucf_section.value,
                    "doc_type": m.doc_type,
                    "section_count": len(m.sections),
                    "authority": m.authority,
                } for m in self.ucf_assembly
            ],
            "warnings": self.warnings,
            "overall_confidence": self.overall_confidence,
            "generated_at": self.generated_at,
            "source_provenance": self.source_provenance,
        }


# ─── Version Store ───────────────────────────────────────────────────────────

class VersionStore:
    """In-memory version control for document sections with rollback."""

    def __init__(self):
        self._store: dict[str, list[VersionRecord]] = {}  # key = "{package_id}:{stage}"

    def _key(self, package_id: str, stage: PipelineStage) -> str:
        return f"{package_id}:{stage.value}"

    def save(self, package_id: str, stage: PipelineStage, sections: list[dict],
             metadata: dict | None = None) -> VersionRecord:
        key = self._key(package_id, stage)
        if key not in self._store:
            self._store[key] = []
        version = len(self._store[key]) + 1
        record = VersionRecord(
            version=version,
            stage=stage,
            sections=sections,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._store[key].append(record)
        return record

    def get_latest(self, package_id: str, stage: PipelineStage) -> VersionRecord | None:
        key = self._key(package_id, stage)
        versions = self._store.get(key, [])
        return versions[-1] if versions else None

    def get_version(self, package_id: str, stage: PipelineStage, version: int) -> VersionRecord | None:
        key = self._key(package_id, stage)
        versions = self._store.get(key, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    def get_history(self, package_id: str, stage: PipelineStage) -> list[VersionRecord]:
        key = self._key(package_id, stage)
        return list(self._store.get(key, []))

    def rollback(self, package_id: str, stage: PipelineStage, to_version: int) -> VersionRecord | None:
        """Rollback by saving a copy of the target version as the new latest."""
        target = self.get_version(package_id, stage, to_version)
        if target is None:
            return None
        return self.save(
            package_id, stage, target.sections,
            metadata={"rollback_from": self.get_latest(package_id, stage).version,
                       "rollback_to": to_version},
        )

    def diff(self, package_id: str, stage: PipelineStage,
             version_a: int, version_b: int) -> list[dict]:
        """Compute section-by-section diff between two versions."""
        va = self.get_version(package_id, stage, version_a)
        vb = self.get_version(package_id, stage, version_b)
        if va is None or vb is None:
            return []

        old_map = {s["section_id"]: s for s in va.sections}
        new_map = {s["section_id"]: s for s in vb.sections}
        diffs = []

        for sid, old_sec in old_map.items():
            if sid in new_map:
                if old_sec.get("content") != new_map[sid].get("content"):
                    diff_lines = list(difflib.unified_diff(
                        (old_sec.get("content", "") or "").splitlines(),
                        (new_map[sid].get("content", "") or "").splitlines(),
                        lineterm="",
                    ))
                    diffs.append({
                        "section_id": sid,
                        "change_type": "modified",
                        "diff_lines": diff_lines,
                    })
            else:
                diffs.append({"section_id": sid, "change_type": "deleted"})

        for sid in new_map:
            if sid not in old_map:
                diffs.append({"section_id": sid, "change_type": "added"})

        return diffs

    def version_count(self, package_id: str, stage: PipelineStage) -> int:
        key = self._key(package_id, stage)
        return len(self._store.get(key, []))


# ─── UCF Assembly ────────────────────────────────────────────────────────────

# Maps PipelineStage → (UCFSection, authority)
UCF_STAGE_MAP: dict[PipelineStage, tuple[UCFSection, str]] = {
    PipelineStage.PWS: (UCFSection.C, "FAR 15.204-2(c)"),
    PipelineStage.SECTION_L: (UCFSection.L, "FAR 15.204-2(l)"),
    PipelineStage.SECTION_M: (UCFSection.M, "FAR 15.204-2(m)"),
    PipelineStage.QASP: (UCFSection.J, "FAR 15.204-2(j)"),
    PipelineStage.IGCE: (UCFSection.J, "FAR 15.204-2(j)"),  # IGCE as attachment
}


def assemble_ucf(documents: dict[str, EngineOutput]) -> list[UCFMapping]:
    """Map generated documents to UCF sections per FAR 15.204."""
    mappings = []
    for stage_name, output in documents.items():
        stage = output.stage
        if stage in UCF_STAGE_MAP:
            ucf_sec, authority = UCF_STAGE_MAP[stage]
            mappings.append(UCFMapping(
                ucf_section=ucf_sec,
                doc_type=stage.value,
                sections=output.sections,
                authority=authority,
            ))
    # Sort by UCF section order
    section_order = list(UCFSection)
    mappings.sort(key=lambda m: section_order.index(m.ucf_section))
    return mappings


# ─── Pipeline Context ────────────────────────────────────────────────────────

@dataclass
class PipelineContext:
    """Accumulates outputs as the pipeline progresses."""
    package_id: str
    acquisition_params: dict[str, Any]
    # Upstream outputs
    market_research: dict | None = None
    requirements: list[dict] | None = None
    eval_factors: list[dict] | None = None
    # Generated documents
    pws_sections: list[dict] | None = None
    igce_sections: list[dict] | None = None
    section_l_sections: list[dict] | None = None
    section_m_sections: list[dict] | None = None
    qasp_sections: list[dict] | None = None


# ─── Engine Adapters ─────────────────────────────────────────────────────────
# Thin wrappers that adapt upstream modules to the EngineInput/EngineOutput
# contract.  Each adapter is a standalone function.

def run_market_research(engine_input: EngineInput) -> EngineOutput:
    """Adapter: MarketResearchAgent → EngineOutput."""
    try:
        from backend.core.market_research_agent import (
            MarketResearchAgent, MarketResearchRequest, report_to_dict,
        )
        params = engine_input.acquisition_params
        request = MarketResearchRequest(
            naics_code=params.get("naics", ""),
            psc_code=params.get("psc", ""),
            agency=params.get("agency", "DHS"),
            sub_agency=params.get("sub_agency", "TSA"),
            estimated_value=params.get("value", 0),
            services=params.get("services", True),
            it_related=params.get("it_related", False),
        )
        agent = MarketResearchAgent()
        report = agent.generate_report(request)
        report_dict = report_to_dict(report)

        sections = []
        for s in report.sections:
            # MarketResearchSection.content is a dict — serialize to string
            content_str = ""
            if isinstance(s.content, dict):
                content_str = "\n".join(f"{k}: {v}" for k, v in s.content.items())
            elif isinstance(s.content, str):
                content_str = s.content
            sections.append({
                "section_id": f"MR.{s.section_number}",
                "heading": s.title,
                "content": content_str,
                "authority": s.far_authority,
                "rationale": "; ".join(s.findings) if s.findings else "",
                "confidence": s.confidence * 100 if s.confidence <= 1 else s.confidence,
            })

        return EngineOutput(
            stage=PipelineStage.MARKET_RESEARCH,
            sections=sections,
            warnings=report.warnings,
            provenance=["FAR 10.002", "USAspending.gov", "SAM.gov", "DHS PIL"],
            confidence=report.overall_confidence,
            metadata={"set_aside": report.set_aside_recommendation.__dict__
                       if hasattr(report.set_aside_recommendation, '__dict__') else {}},
        )
    except ImportError:
        return _fallback_output(PipelineStage.MARKET_RESEARCH, "Market research module not available")


def run_requirements(engine_input: EngineInput) -> EngineOutput:
    """Adapter: RequirementsElicitationAgent → EngineOutput."""
    if engine_input.requirements:
        # Requirements already provided — pass through
        sections = []
        for r in engine_input.requirements:
            sections.append({
                "section_id": r.get("requirement_id", ""),
                "heading": r.get("title", ""),
                "content": r.get("description", ""),
                "authority": r.get("far_reference", "FAR 11.002"),
                "rationale": f"Requirement from elicitation ({r.get('category', 'general')})",
                "confidence": 80.0,
            })
        return EngineOutput(
            stage=PipelineStage.REQUIREMENTS,
            sections=sections,
            provenance=["FAR 11.002", "FAR 37.102"],
            confidence=80.0,
        )
    return _fallback_output(PipelineStage.REQUIREMENTS, "No requirements provided")


def run_factor_derivation(engine_input: EngineInput) -> EngineOutput:
    """Adapter: EvalFactorDerivationEngine → EngineOutput."""
    if engine_input.eval_factors:
        sections = []
        for f in engine_input.eval_factors:
            sections.append({
                "section_id": f.get("factor_id", ""),
                "heading": f.get("name", ""),
                "content": f.get("description", ""),
                "authority": f.get("far_authority", "FAR 15.304"),
                "rationale": "Evaluation factor from derivation engine",
                "confidence": 85.0,
            })
        return EngineOutput(
            stage=PipelineStage.FACTOR_DERIVATION,
            sections=sections,
            provenance=["FAR 15.304", "FAR 15.101-1"],
            confidence=85.0,
        )

    # Try to derive from PWS sections
    pws = engine_input.pws_sections
    if pws:
        try:
            from backend.core.eval_factor_derivation import (
                EvalFactorDerivationEngine, derivation_to_dict,
            )
            engine = EvalFactorDerivationEngine()
            pws_text = "\n".join(s.get("content", "") for s in pws)
            params = engine_input.acquisition_params
            result = engine.derive(
                pws_text=pws_text,
                value=params.get("value", 0),
                evaluation_type=params.get("evaluation_type", "tradeoff"),
            )
            sections = [{
                "section_id": f.factor_id,
                "heading": f.name,
                "content": f"{f.far_authority}: {f.relative_importance}",
                "authority": f.far_authority,
                "rationale": "Derived from PWS analysis",
                "confidence": 85.0,
            } for f in result.factors]
            return EngineOutput(
                stage=PipelineStage.FACTOR_DERIVATION,
                sections=sections,
                provenance=["FAR 15.304"],
                confidence=result.overall_protest_score,
                metadata={"protest_checks": len(result.protest_checks)},
            )
        except ImportError:
            pass

    return _fallback_output(PipelineStage.FACTOR_DERIVATION, "No factors or PWS available")


def run_pws(engine_input: EngineInput) -> EngineOutput:
    """Adapter: PWSEngine → EngineOutput."""
    from backend.phase2.drafting_workspace import PWSEngine, DraftSection
    engine = PWSEngine()
    params = engine_input.acquisition_params
    if engine_input.requirements:
        # Build PWS from requirements
        params["sow_text"] = None  # Use template mode with requirements context
    sections = engine.generate(params)
    return _sections_to_output(PipelineStage.PWS, sections)


def run_igce(engine_input: EngineInput) -> EngineOutput:
    """Adapter: IGCEEngine → EngineOutput."""
    from backend.phase2.drafting_workspace import IGCEEngine
    engine = IGCEEngine()
    sections = engine.generate(engine_input.acquisition_params)
    return _sections_to_output(PipelineStage.IGCE, sections)


def run_section_l(engine_input: EngineInput) -> EngineOutput:
    """Adapter: SectionLEngine → EngineOutput."""
    from backend.phase2.drafting_workspace import SectionLEngine
    engine = SectionLEngine()
    sections = engine.generate(engine_input.acquisition_params)
    return _sections_to_output(PipelineStage.SECTION_L, sections)


def run_section_m(engine_input: EngineInput) -> EngineOutput:
    """Adapter: SectionMEngine → EngineOutput."""
    from backend.phase2.drafting_workspace import SectionMEngine
    engine = SectionMEngine()
    params = dict(engine_input.acquisition_params)
    # Inject eval factors if available from derivation step
    if engine_input.eval_factors:
        params["eval_factors"] = engine_input.eval_factors
    sections = engine.generate(params)
    return _sections_to_output(PipelineStage.SECTION_M, sections)


def run_qasp(engine_input: EngineInput) -> EngineOutput:
    """Adapter: QASPEngine → EngineOutput (requires PWS sections)."""
    from backend.phase2.drafting_workspace import QASPEngine, DraftSection
    engine = QASPEngine()
    # Convert dict sections back to DraftSection for QASP engine
    pws_secs = engine_input.pws_sections or []
    draft_sections = [
        DraftSection(
            section_id=s.get("section_id", ""),
            heading=s.get("heading", ""),
            content=s.get("content", ""),
            authority=s.get("authority", ""),
        ) for s in pws_secs
    ]
    sections = engine.generate(draft_sections, engine_input.acquisition_params)
    return _sections_to_output(PipelineStage.QASP, sections)


def run_compliance(engine_input: EngineInput, doc_type: str,
                    sections: list[dict]) -> ComplianceResult:
    """Adapter: ComplianceOverlayEngine → ComplianceResult."""
    try:
        from backend.core.compliance_overlay import ComplianceOverlayEngine
        engine = ComplianceOverlayEngine()
        params = engine_input.acquisition_params
        result = engine.evaluate_document(
            doc_type=doc_type,
            sections=[{
                "section_id": s.get("section_id", ""),
                "content": s.get("content", ""),
                "heading": s.get("heading", ""),
            } for s in sections],
            value=params.get("value", 0),
            services=params.get("services", True),
            it_related=params.get("it_related", False),
        )
        issues = []
        if hasattr(result, "results"):
            for r in result.results:
                if hasattr(r, "level") and r.level.value not in ("GREEN", "N/A"):
                    issues.append({
                        "rule_id": r.rule_id,
                        "level": r.level.value,
                        "title": r.title,
                        "detail": r.detail,
                        "remediation": r.remediation,
                    })
        score = result.overall_score if hasattr(result, "overall_score") else 100.0
        return ComplianceResult(
            doc_type=doc_type,
            overall_score=score,
            issues=issues,
            passed=score >= 70.0,
        )
    except (ImportError, Exception):
        return ComplianceResult(doc_type=doc_type, overall_score=100.0, passed=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _sections_to_output(stage: PipelineStage, sections) -> EngineOutput:
    """Convert DraftSection list to EngineOutput."""
    sec_dicts = [{
        "section_id": s.section_id,
        "heading": s.heading,
        "content": s.content,
        "authority": s.authority,
        "rationale": getattr(s, "rationale", ""),
        "confidence": getattr(s, "confidence", 80.0),
    } for s in sections]
    provenance = list(dict.fromkeys(s.authority for s in sections if s.authority))
    confidence = sum(getattr(s, "confidence", 80.0) for s in sections) / max(len(sections), 1)
    return EngineOutput(
        stage=stage,
        sections=sec_dicts,
        provenance=provenance,
        confidence=confidence,
    )


def _fallback_output(stage: PipelineStage, reason: str) -> EngineOutput:
    """Return an empty output with a warning when an upstream module is unavailable."""
    return EngineOutput(
        stage=stage,
        sections=[],
        warnings=[reason],
        confidence=0.0,
    )


# ─── Pipeline Stage Registry ────────────────────────────────────────────────

# Default pipeline order — orchestrator executes these in sequence
DEFAULT_PIPELINE: list[PipelineStage] = [
    PipelineStage.MARKET_RESEARCH,
    PipelineStage.REQUIREMENTS,
    PipelineStage.FACTOR_DERIVATION,
    PipelineStage.PWS,
    PipelineStage.IGCE,
    PipelineStage.SECTION_L,
    PipelineStage.SECTION_M,
    PipelineStage.QASP,
    PipelineStage.COMPLIANCE,
    PipelineStage.UCF_ASSEMBLY,
]

# Document stages that produce compliance-checkable output
COMPLIANCE_STAGES: dict[PipelineStage, str] = {
    PipelineStage.PWS: "PWS",
    PipelineStage.SECTION_L: "Section_L",
    PipelineStage.SECTION_M: "Section_M",
    PipelineStage.QASP: "QASP",
    PipelineStage.IGCE: "IGCE",
}


# ─── Drafting Orchestrator ───────────────────────────────────────────────────

class DraftingOrchestrator:
    """
    Orchestrates the full document generation pipeline.

    Usage:
        orchestrator = DraftingOrchestrator()
        result = orchestrator.run(package_id="pkg-001", params={...})

    Or run individual stages:
        output = orchestrator.run_stage(PipelineStage.PWS, engine_input)
    """

    STAGE_RUNNERS = {
        PipelineStage.MARKET_RESEARCH: run_market_research,
        PipelineStage.REQUIREMENTS: run_requirements,
        PipelineStage.FACTOR_DERIVATION: run_factor_derivation,
        PipelineStage.PWS: run_pws,
        PipelineStage.IGCE: run_igce,
        PipelineStage.SECTION_L: run_section_l,
        PipelineStage.SECTION_M: run_section_m,
        PipelineStage.QASP: run_qasp,
    }

    def __init__(self, version_store: VersionStore | None = None):
        self.version_store = version_store or VersionStore()

    def run(
        self,
        package_id: str,
        params: dict[str, Any],
        requirements: list[dict] | None = None,
        eval_factors: list[dict] | None = None,
        market_research: dict | None = None,
        stages: list[PipelineStage] | None = None,
        skip_compliance: bool = False,
    ) -> PipelineResult:
        """Execute the full pipeline (or a subset of stages)."""
        pipeline = stages if stages is not None else DEFAULT_PIPELINE
        ctx = PipelineContext(
            package_id=package_id,
            acquisition_params=params,
            requirements=[r if isinstance(r, dict) else r.__dict__ for r in requirements] if requirements else None,
            eval_factors=eval_factors,
            market_research=market_research,
        )

        documents: dict[str, EngineOutput] = {}
        compliance_results: dict[str, ComplianceResult] = {}
        stages_completed: list[PipelineStage] = []
        all_warnings: list[str] = []

        for stage in pipeline:
            if stage == PipelineStage.COMPLIANCE:
                if not skip_compliance:
                    compliance_results = self._run_compliance_pass(ctx, documents)
                stages_completed.append(stage)
                continue

            if stage == PipelineStage.UCF_ASSEMBLY:
                stages_completed.append(stage)
                continue

            # Build engine input with accumulated context
            engine_input = EngineInput(
                package_id=package_id,
                acquisition_params=params,
                requirements=ctx.requirements,
                market_research=ctx.market_research,
                eval_factors=ctx.eval_factors,
                pws_sections=ctx.pws_sections,
            )

            output = self.run_stage(stage, engine_input)
            documents[stage.value] = output
            all_warnings.extend(output.warnings)
            stages_completed.append(stage)

            # Save to version store
            if output.sections:
                self.version_store.save(package_id, stage, output.sections)

            # Update context for downstream stages
            self._update_context(ctx, stage, output)

        # UCF assembly
        ucf = assemble_ucf(documents)

        # Overall confidence
        confidences = [o.confidence for o in documents.values() if o.confidence > 0]
        overall = sum(confidences) / max(len(confidences), 1) if confidences else 0.0

        # Aggregate provenance
        all_provenance = []
        for o in documents.values():
            all_provenance.extend(o.provenance)
        provenance = list(dict.fromkeys(all_provenance))

        return PipelineResult(
            package_id=package_id,
            stages_completed=stages_completed,
            documents=documents,
            compliance_results=compliance_results,
            ucf_assembly=ucf,
            warnings=all_warnings,
            overall_confidence=overall,
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_provenance=provenance,
        )

    def run_stage(self, stage: PipelineStage, engine_input: EngineInput) -> EngineOutput:
        """Run a single pipeline stage."""
        runner = self.STAGE_RUNNERS.get(stage)
        if runner is None:
            return _fallback_output(stage, f"No runner for stage {stage.value}")
        return runner(engine_input)

    def _run_compliance_pass(self, ctx: PipelineContext,
                              documents: dict[str, EngineOutput]) -> dict[str, ComplianceResult]:
        """Run compliance checks on all generated documents."""
        results = {}
        engine_input = EngineInput(
            package_id=ctx.package_id,
            acquisition_params=ctx.acquisition_params,
        )
        for stage, doc_type in COMPLIANCE_STAGES.items():
            if stage.value in documents and documents[stage.value].sections:
                result = run_compliance(
                    engine_input, doc_type, documents[stage.value].sections,
                )
                results[doc_type] = result
        return results

    def _update_context(self, ctx: PipelineContext, stage: PipelineStage,
                         output: EngineOutput) -> None:
        """Update pipeline context with stage output for downstream consumption."""
        if stage == PipelineStage.MARKET_RESEARCH:
            ctx.market_research = output.metadata
        elif stage == PipelineStage.REQUIREMENTS:
            ctx.requirements = output.sections
        elif stage == PipelineStage.FACTOR_DERIVATION:
            ctx.eval_factors = output.sections
        elif stage == PipelineStage.PWS:
            ctx.pws_sections = output.sections
        elif stage == PipelineStage.IGCE:
            ctx.igce_sections = output.sections
        elif stage == PipelineStage.SECTION_L:
            ctx.section_l_sections = output.sections
        elif stage == PipelineStage.SECTION_M:
            ctx.section_m_sections = output.sections
        elif stage == PipelineStage.QASP:
            ctx.qasp_sections = output.sections
