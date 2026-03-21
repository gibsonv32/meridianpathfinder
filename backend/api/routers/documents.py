from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.audit.audit_service import audit_service
from backend.schemas.audit import (
    DocumentAcceptRequest,
    DocumentModifyRequest,
    DocumentOverrideRequest,
    DocumentRecord,
    DocumentVersionsResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=DocumentRecord)
async def get_document(document_id: str) -> DocumentRecord:
    try:
        return await audit_service.get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{document_id}/versions", response_model=DocumentVersionsResponse)
async def get_document_versions(document_id: str) -> DocumentVersionsResponse:
    try:
        return await audit_service.list_document_versions(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{document_id}/accept", response_model=DocumentRecord)
async def accept_document(document_id: str, payload: DocumentAcceptRequest) -> DocumentRecord:
    try:
        return await audit_service.accept_document(document_id, payload.actor, payload.section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{document_id}/modify", response_model=DocumentRecord)
async def modify_document(document_id: str, payload: DocumentModifyRequest) -> DocumentRecord:
    try:
        return await audit_service.modify_document(document_id, payload.content, payload.actor, payload.rationale)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{document_id}/override", response_model=DocumentRecord)
async def override_document(document_id: str, payload: DocumentOverrideRequest) -> DocumentRecord:
    try:
        return await audit_service.override_document(document_id, payload.content, payload.actor, payload.rationale)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
