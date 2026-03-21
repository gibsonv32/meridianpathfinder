"""Phase 2 API Router — Protest Risk, Solicitation Assembly, PIL Pricing, Evaluation Workspace."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.phase2.protest_scoring import ProtestRiskEngine
from backend.phase2.solicitation_assembly import SolicitationAssemblyEngine
from backend.phase2.pil_pricing import PILPricingEngine
from backend.phase2.evaluation_workspace import EvaluationWorkspace, EvalRole
from backend.phase2.schemas_phase2 import (
    ProtestRiskRequest, ProtestRiskResponse, RiskFactorResponse,
    AssembleRequest, AssemblyResponse, SectionMappingResponse, JLMTraceResponse,
    PILAnalysisRequest, PILAnalysisResponse, RateComparisonResponse,
    CreateWorkspaceRequest, AddOfferorRequest, SubmitScoreRequest,
    AdvancePhaseRequest, WorkspaceResponse,
)

from backend.phase2.tango_entities.router import router as entities_router
from backend.phase2.protest_data.router_protest_data import router as protest_data_router
from backend.phase2.tango_opportunities.router import router as opportunities_router

from backend.phase2.completeness_validator import (
    ValidateCompletenessRequest,
    CompletenessValidationResponse,
    completeness_validator,
)

from backend.phase2.workflow_gate_engine import workflow_gate_engine, AcquisitionPhase, PHASE_ORDER
from backend.phase2.workflow_schemas import (
    GateCheckRequest,
    GateCheckResponse,
    PhaseAdvanceRequest,
    PhaseAdvanceResponse,
    PhaseRoadmapResponse,
)
from backend.core.package_service import package_service

router = APIRouter(prefix="/phase2", tags=["phase2"])
router.include_router(protest_data_router)
router.include_router(entities_router)
router.include_router(opportunities_router)

# --- Singletons (will be replaced by DI in production) ---
_protest_engine = ProtestRiskEngine()
_assembly_engine = SolicitationAssemblyEngine()
_pil_engine = PILPricingEngine()
_eval_workspace = EvaluationWorkspace()


# ── Protest Risk ──────────────────────────────────────────────────────────────

@router.post("/protest-risk", response_model=ProtestRiskResponse)
async def assess_protest_risk(req: ProtestRiskRequest):
    """Score GAO protest risk for a procurement. Tier 2 — CO reviews output."""
    result = _protest_engine.score(
        value=req.value,
        sole_source=req.sole_source,
        incumbent_rebid=req.incumbent_rebid,
        evaluation_type=req.evaluation_type,
        num_offerors_expected=req.num_offerors_expected,
        has_discussions=req.has_discussions,
        set_aside_type=req.set_aside_type,
        has_oci_plan=req.has_oci_plan,
        j_l_m_traced=req.j_l_m_traced,
        price_analysis_method=req.price_analysis_method,
        past_performance_weighted=req.past_performance_weighted,
        debriefing_required=req.debriefing_required,
    )
    return ProtestRiskResponse(
        overall_score=result.overall_score,
        overall_risk=result.overall_risk.value,
        factors=[
            RiskFactorResponse(
                factor_id=f.factor_id, name=f.name, description=f.description,
                risk_level=f.risk_level.value, score=f.score,
                mitigation=f.mitigation, authority=f.authority,
            ) for f in result.factors
        ],
        summary=result.summary,
        recommendations=result.recommendations,
        source_provenance=["FAR 33", "GAO Bid Protest Regulations", "4 C.F.R. Part 21"],
        confidence_score=0.85,
    )


# ── Solicitation Assembly ─────────────────────────────────────────────────────

@router.post("/solicitation/assemble", response_model=AssemblyResponse)
async def assemble_solicitation(req: AssembleRequest):
    """Map documents to UCF sections and check J-L-M traceability. Tier 2."""
    result = _assembly_engine.assemble(
        package_id=req.package_id,
        title=req.title,
        value=req.value,
        documents=req.documents,
        posting_deadline_days=req.posting_deadline_days,
        services=req.services,
        it_related=req.it_related,
    )
    return AssemblyResponse(
        package_id=result.package_id,
        title=result.title,
        assembly_status=result.status.value,
        sections=[
            SectionMappingResponse(
                section=s.section, dcode=s.dcode, document_type=s.document_type,
                title=s.title, required=s.required, present=s.present,
                accepted=s.accepted, document_id=s.document_id,
            ) for s in result.sections
        ],
        jlm_traceability=[
            JLMTraceResponse(
                j_reference=j.j_reference, l_instruction=j.l_instruction,
                m_factor=j.m_factor, traced=j.traced, gap=j.gap,
            ) for j in result.jlm_traceability
        ],
        completeness_pct=result.completeness_pct,
        missing_sections=result.missing_sections,
        clauses=[{"number": c["number"], "title": c["title"]} for c in result.clauses],
        posting_deadline_days=result.posting_deadline_days,
        warnings=result.warnings,
        source_provenance=["FAR Part 12", "FAR Part 15", "HSAR"],
        confidence_score=0.90,
        requires_acceptance=True,
    )


# ── PIL Pricing ───────────────────────────────────────────────────────────────

@router.post("/pil/analyze", response_model=PILAnalysisResponse)
async def analyze_pil_pricing(req: PILAnalysisRequest):
    """Compare proposed labor rates against DHS PIL benchmarks. Tier 2."""
    result = _pil_engine.analyze(req.labor_categories)
    return PILAnalysisResponse(
        comparisons=[
            RateComparisonResponse(
                labor_category=c.labor_category, proposed_rate=c.proposed_rate,
                pil_min=c.pil_min, pil_max=c.pil_max, pil_avg=c.pil_avg,
                status=c.status.value, variance_pct=c.variance_pct,
                vehicle=c.vehicle, recommendation=c.recommendation,
            ) for c in result.comparisons
        ],
        rates_within_range=result.rates_within_range,
        rates_above_ceiling=result.rates_above_ceiling,
        rates_below_floor=result.rates_below_floor,
        rates_no_benchmark=result.rates_no_benchmark,
        overall_assessment=result.overall_assessment,
        recommended_vehicle=result.recommended_vehicle,
        source_provenance=["DHS PIL FY2025", "GSA PACTS-III"],
        confidence_score=0.80,
        requires_acceptance=True,
    )


# ── Evaluation Workspace ──────────────────────────────────────────────────────

@router.post("/evaluation/workspace", response_model=WorkspaceResponse)
async def create_eval_workspace(req: CreateWorkspaceRequest):
    """Create a protected evaluation workspace. Tier 2 — CO/SSEB Chair only."""
    try:
        ws = _eval_workspace.create_workspace(
            package_id=req.package_id, title=req.title,
            actor=req.actor, role=EvalRole(req.role), factors=req.factors,
        )
        return _workspace_response(ws)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/evaluation/{workspace_id}/offeror", response_model=WorkspaceResponse)
async def add_offeror(workspace_id: str, req: AddOfferorRequest):
    """Add an offeror to the evaluation workspace. CO only."""
    try:
        ws = _eval_workspace.add_offeror(
            workspace_id, name=req.name,
            proposal_received=req.proposal_received,
            actor=req.actor, role=EvalRole(req.role),
        )
        return _workspace_response(ws)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluation/{workspace_id}/score", response_model=WorkspaceResponse)
async def submit_score(workspace_id: str, req: SubmitScoreRequest):
    """Submit an individual evaluation score. SSEB members only."""
    try:
        ws = _eval_workspace.submit_individual_score(
            workspace_id, evaluator=req.evaluator, role=EvalRole(req.role),
            offeror_id=req.offeror_id, factor_id=req.factor_id,
            rating=req.rating, strengths=req.strengths,
            weaknesses=req.weaknesses, deficiencies=req.deficiencies,
            narrative=req.narrative,
        )
        return _workspace_response(ws)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/evaluation/{workspace_id}/advance", response_model=WorkspaceResponse)
async def advance_phase(workspace_id: str, req: AdvancePhaseRequest):
    """Advance evaluation to next phase. SSEB Chair/CO only."""
    try:
        _eval_workspace.advance_phase(
            workspace_id, actor=req.actor, role=EvalRole(req.role),
        )
        ws = _eval_workspace.get_workspace(workspace_id)
        return _workspace_response(ws)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except (KeyError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/evaluation/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str):
    """Get current workspace state."""
    try:
        ws = _eval_workspace.get_workspace(workspace_id)
        return _workspace_response(ws)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/evaluation/{workspace_id}/matrix")
async def get_comparison_matrix(workspace_id: str, actor: str, role: str):
    """Get comparison matrix of consensus scores. Tier 3 decision support only."""
    try:
        matrix = _eval_workspace.get_comparison_matrix(
            workspace_id, actor=actor, role=EvalRole(role),
        )
        return matrix
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _workspace_response(ws) -> WorkspaceResponse:
    return WorkspaceResponse(
        workspace_id=ws.workspace_id,
        package_id=ws.package_id,
        title=ws.title,
        phase=ws.phase.value,
        factors=[{"factor_id": f.factor_id, "name": f.name, "weight": f.weight} for f in ws.factors],
        offerors=[{"offeror_id": o.offeror_id, "name": o.name, "in_competitive_range": o.in_competitive_range} for o in ws.offerors],
        score_count=len(ws.individual_scores),
        consensus_count=len(ws.consensus_scores),
        audit_log_count=len(ws.audit_log),
    )



# ── Phase-Aware Helper ───────────────────────────────────────────────────────

def _build_params_from_detail(detail) -> dict:
    """Extract acquisition params from a package detail for PolicyService evaluation."""
    return {
        "title": getattr(detail, "title", ""),
        "value": getattr(detail, "value", 0),
        "naics": getattr(detail, "naics", ""),
        "psc": getattr(detail, "psc", ""),
        "services": getattr(detail, "services", False),
        "it_related": getattr(detail, "it_related", False),
        "sole_source": getattr(detail, "sole_source", False),
        "commercial_item": getattr(detail, "commercial_item", False),
        "emergency": getattr(detail, "emergency", False),
        "vendor_on_site": getattr(detail, "vendor_on_site", False),
        "competition_type": getattr(detail, "competition_type", "full_and_open"),
    }

# ── PR Package Completeness Validator ─────────────────────────────────────────

@router.post(
    "/completeness/validate",
    response_model=CompletenessValidationResponse,
    summary="Validate PR package completeness",
    description="Checks acquisition params against PolicyService to identify missing/incomplete documents.",
    tags=["completeness"],
)
async def validate_completeness(request: ValidateCompletenessRequest):
    """Run completeness check: required D-codes vs documents in hand."""
    return completeness_validator.validate(request)


# ── Workflow Gate Engine ──────────────────────────────────────────────────────

@router.post(
    "/workflow/check-gate",
    response_model=GateCheckResponse,
    summary="Check if a package can advance to the next phase",
    tags=["workflow"],
)
async def check_gate(request: GateCheckRequest):
    """Check gate requirements for advancing to the next phase. Tier 1 — deterministic."""
    detail = await package_service.get_package_detail(request.package_id)
    documents = {doc.dcode: doc.status for doc in detail.documents}
    # Phase-aware: re-evaluate required dcodes including branch-specific documents
    from backend.phase2.policy_engine import PolicyService
    _policy = PolicyService()
    params = _build_params_from_detail(detail)
    next_phase = workflow_gate_engine.get_next_phase(detail.phase)
    # Evaluate with TARGET phase to get docs needed for that phase
    fresh_eval = _policy.evaluate(params, phase=next_phase or detail.phase)
    required_dcodes = set(fresh_eval.required_dcodes) | set(detail.required_dcodes)
    next_phase = workflow_gate_engine.get_next_phase(detail.phase)
    if next_phase is None:
        return GateCheckResponse(
            allowed=False, current_phase=detail.phase, target_phase="(none)",
            completeness_pct=100.0, min_completeness_pct=100.0,
            completeness_met=True, overridable=False, gate_description="",
            notes=["Package is in the final phase — no further advancement."],
        )
    result = workflow_gate_engine.check_gate(detail.phase, next_phase, documents, required_dcodes)
    return GateCheckResponse(
        allowed=result.allowed, current_phase=result.current_phase,
        target_phase=result.target_phase, failed_requirements=result.failed_requirements,
        passed_requirements=result.passed_requirements, completeness_pct=result.completeness_pct,
        min_completeness_pct=result.min_completeness_pct, completeness_met=result.completeness_met,
        overridable=result.overridable, gate_description=result.gate_description, notes=result.notes,
    )


@router.post(
    "/workflow/advance",
    response_model=PhaseAdvanceResponse,
    summary="Advance a package to the next phase (with optional CO override)",
    tags=["workflow"],
)
async def advance_phase(request: PhaseAdvanceRequest):
    """Attempt to advance package phase. CO can override waivable gates with rationale."""
    detail = await package_service.get_package_detail(request.package_id)
    documents = {doc.dcode: doc.status for doc in detail.documents}
    required_dcodes = set(detail.required_dcodes)
    next_phase = workflow_gate_engine.get_next_phase(detail.phase)
    if next_phase is None:
        gate = GateCheckResponse(
            allowed=False, current_phase=detail.phase, target_phase="(none)",
            completeness_pct=100.0, min_completeness_pct=100.0,
            completeness_met=True, overridable=False, gate_description="",
            notes=["Package is in the final phase — no further advancement."],
        )
        return PhaseAdvanceResponse(
            success=False, previous_phase=detail.phase, new_phase=detail.phase,
            gate_check=gate,
        )
    result = workflow_gate_engine.advance(
        detail.phase, next_phase, documents, required_dcodes,
        override=request.override,
        override_rationale=request.override_rationale,
        actor=request.actor,
    )
    # If advance succeeded, update the package phase in DB
    if result.success:
        from backend.database.db import AsyncSessionLocal, init_database
        from backend.database.models import AcquisitionPackage
        from sqlalchemy import select
        from datetime import datetime, UTC
        await init_database()
        async with AsyncSessionLocal() as session:
            stmt = select(AcquisitionPackage).where(AcquisitionPackage.id == request.package_id)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                record.phase = next_phase
                record.updated_at = datetime.now(UTC)
                await session.commit()
    gate = GateCheckResponse(
        allowed=result.gate_check.allowed, current_phase=result.gate_check.current_phase,
        target_phase=result.gate_check.target_phase,
        failed_requirements=result.gate_check.failed_requirements,
        passed_requirements=result.gate_check.passed_requirements,
        completeness_pct=result.gate_check.completeness_pct,
        min_completeness_pct=result.gate_check.min_completeness_pct,
        completeness_met=result.gate_check.completeness_met,
        overridable=result.gate_check.overridable,
        gate_description=result.gate_check.gate_description,
        notes=result.gate_check.notes,
    )
    return PhaseAdvanceResponse(
        success=result.success, previous_phase=result.previous_phase,
        new_phase=result.new_phase, gate_check=gate,
        override_used=result.override_used,
        override_rationale=result.override_rationale,
    )


@router.get(
    "/workflow/roadmap/{package_id}",
    response_model=PhaseRoadmapResponse,
    summary="Get full phase roadmap with gate status",
    tags=["workflow"],
)
async def get_roadmap(package_id: str):
    """Get the phase roadmap showing completed/current/blocked/future phases."""
    detail = await package_service.get_package_detail(package_id)
    documents = {doc.dcode: doc.status for doc in detail.documents}
    required_dcodes = set(detail.required_dcodes)
    roadmap = workflow_gate_engine.get_phase_roadmap(detail.phase, documents, required_dcodes)
    return PhaseRoadmapResponse(
        package_id=package_id, current_phase=detail.phase, phases=roadmap,
    )


@router.get(
    "/workflow/phases",
    summary="List all acquisition phases in order",
    tags=["workflow"],
)
async def list_phases():
    """List the defined acquisition lifecycle phases."""
    return {"phases": [{"name": p.value, "index": i} for i, p in enumerate(PHASE_ORDER)]}

