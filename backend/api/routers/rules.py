"""Patched rules router — adds PolicyService enrichment to /evaluate
and new /evaluate/v2 endpoint.

This file REPLACES backend/api/routers/rules.py on Spark.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.core.rules_engine.service import rules_engine_service
from backend.phase2.rules_migration import (
    EnrichedRulesEvaluationResponse,
    PolicyV2Response,
    run_policy_evaluation,
    to_enrichment,
    to_v2_response,
)
from backend.schemas.rules import (
    AcquisitionParams,
    ThresholdItem,
    ThresholdMatrixResponse,
    ThresholdUpdateRequest,
)

router = APIRouter(prefix="/rules", tags=["rules"])


# ── Thresholds (unchanged) ────────────────────────────────────────────────────

@router.get("/thresholds", response_model=ThresholdMatrixResponse)
async def get_thresholds(
    as_of_date: date | None = Query(default=None),
    active_only: bool = Query(default=False),
) -> ThresholdMatrixResponse:
    return ThresholdMatrixResponse(
        thresholds=await rules_engine_service.list_thresholds(
            as_of_date=as_of_date, active_only=active_only
        )
    )


@router.post("/thresholds", response_model=ThresholdItem)
async def update_threshold(payload: ThresholdUpdateRequest) -> ThresholdItem:
    try:
        return await rules_engine_service.update_threshold(
            name=payload.name,
            value=payload.value,
            authority=payload.authority,
            effective_date=payload.effective_date,
            overlay_level=payload.overlay_level,
            unit=payload.unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/thresholds/{name}", response_model=ThresholdItem)
async def put_threshold(name: str, payload: ThresholdUpdateRequest) -> ThresholdItem:
    try:
        return await rules_engine_service.update_threshold(
            name=name,
            value=payload.value,
            authority=payload.authority,
            effective_date=payload.effective_date,
            overlay_level=payload.overlay_level,
            unit=payload.unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Evaluate V1 (backward-compatible + enrichment) ────────────────────────────

@router.post("/evaluate", response_model=EnrichedRulesEvaluationResponse)
async def evaluate_rules(payload: AcquisitionParams) -> EnrichedRulesEvaluationResponse:
    """Evaluate acquisition parameters. Returns original V1 fields + PolicyService enrichment.

    The V1 fields (tier, required_dcodes, q_codes_evaluated, approvers, posting_deadline_days,
    authority_chain, notes) are produced by the original RulesEngineService with DB-backed
    thresholds — fully backward-compatible.

    The new `policy_evaluation` field contains the PolicyService output with Q-code trace,
    corrected D-codes, clause selection, and posting rule detail.
    """
    # Run old engine (DB-backed, backward-compatible)
    old_result = await rules_engine_service.evaluate(payload)

    # Run PolicyService (in-memory, enriched)
    policy_params = {
        "value": payload.value,
        "services": payload.services,
        "it_related": payload.it_related,
        "sole_source": payload.sole_source,
        "commercial_item": payload.commercial_item,
        "emergency": payload.emergency,
        "competition_type": payload.competition_type,
    }
    policy_result = run_policy_evaluation(policy_params, payload.as_of_date)
    enrichment = to_enrichment(policy_result)

    return EnrichedRulesEvaluationResponse(
        tier=old_result.tier.model_dump(),
        required_dcodes=old_result.required_dcodes,
        q_codes_evaluated=old_result.q_codes_evaluated,
        approvers=old_result.approvers,
        posting_deadline_days=old_result.posting_deadline_days,
        authority_chain=old_result.authority_chain,
        notes=old_result.notes,
        policy_evaluation=enrichment,
    )


# ── Evaluate V2 (full PolicyService output) ───────────────────────────────────

@router.post("/evaluate/v2", response_model=PolicyV2Response)
async def evaluate_rules_v2(payload: AcquisitionParams) -> PolicyV2Response:
    """Evaluate acquisition parameters using the PolicyService directly.

    Returns full Q-code trace, corrected D-codes, clause selection,
    posting rule detail, and J&A approval ladder. No backward-compatibility
    shim — this is the new canonical response format.
    """
    policy_params = {
        "value": payload.value,
        "services": payload.services,
        "it_related": payload.it_related,
        "sole_source": payload.sole_source,
        "commercial_item": payload.commercial_item,
        "emergency": payload.emergency,
        "competition_type": payload.competition_type,
    }
    result = run_policy_evaluation(policy_params, payload.as_of_date)
    return to_v2_response(result)
