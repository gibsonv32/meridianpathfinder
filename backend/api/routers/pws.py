from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.audit.audit_service import audit_service
from backend.core.document_gen.pws_engine import pws_engine
from backend.schemas.pws import (
    PWSConvertRequest,
    PWSConvertResponse,
    PWSTemplateGenerateRequest,
    PWSTemplateGenerateResponse,
    PWSTemplateListResponse,
)

router = APIRouter(prefix="/pws", tags=["pws"])


@router.post("/convert", response_model=PWSConvertResponse)
async def convert_sow_to_pws(payload: PWSConvertRequest) -> PWSConvertResponse:
    result = pws_engine.convert_sow_to_pws(payload.sow_text)
    persisted = await audit_service.persist_generated_document(
        package_id=payload.package_id,
        document_type="pws",
        dcode="D109",
        title="Generated PWS",
        content=result.content.model_dump(),
        source_provenance=result.metadata.source_provenance,
        confidence_score=result.metadata.confidence_score,
        requires_acceptance=result.metadata.requires_acceptance,
    )
    result.document_id = persisted.document_id
    result.acceptance_status = persisted.acceptance_status
    result.accepted_by = persisted.accepted_by
    result.accepted_at = persisted.accepted_at
    return result


@router.get("/templates", response_model=PWSTemplateListResponse)
async def list_pws_templates() -> PWSTemplateListResponse:
    return pws_engine.list_templates()


@router.post("/generate-from-template", response_model=PWSTemplateGenerateResponse)
async def generate_from_template(payload: PWSTemplateGenerateRequest) -> PWSTemplateGenerateResponse:
    try:
        result = pws_engine.generate_from_template(payload.template_id, payload.customization)
        persisted = await audit_service.persist_generated_document(
            package_id=payload.package_id,
            document_type="pws",
            dcode="D109",
            title=result.content.name,
            content=result.content.model_dump(),
            source_provenance=result.metadata.source_provenance,
            confidence_score=result.metadata.confidence_score,
            requires_acceptance=result.metadata.requires_acceptance,
        )
        result.document_id = persisted.document_id
        result.acceptance_status = persisted.acceptance_status
        result.accepted_by = persisted.accepted_by
        result.accepted_at = persisted.accepted_at
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
