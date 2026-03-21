from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.audit.audit_service import audit_service
from backend.core.document_gen.igce_engine import igce_engine
from backend.schemas.igce import IGCEGenerateRequest, IGCEGenerateResponse, IGCERetrieveResponse

router = APIRouter(prefix="/igce", tags=["igce"])


@router.post("/generate", response_model=IGCEGenerateResponse)
async def generate_igce(payload: IGCEGenerateRequest) -> IGCEGenerateResponse:
    result = await igce_engine.generate(payload)
    persisted = await audit_service.persist_generated_document(
        package_id=payload.package_id,
        document_type="igce",
        dcode="D104",
        title=result.content.title,
        content=result.content.model_dump(mode="json"),
        source_provenance=result.metadata.source_provenance,
        confidence_score=result.metadata.confidence_score,
        requires_acceptance=result.metadata.requires_acceptance,
    )
    result.document_id = persisted.document_id
    result.content.igce_id = persisted.document_id
    result.acceptance_status = persisted.acceptance_status
    result.accepted_by = persisted.accepted_by
    result.accepted_at = persisted.accepted_at
    return result


@router.get("/{igce_id}", response_model=IGCERetrieveResponse)
async def get_igce(igce_id: str) -> IGCERetrieveResponse:
    try:
        return await igce_engine.get(igce_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
