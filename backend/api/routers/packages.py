from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.core.package_service import package_service
from backend.core.audit.audit_service import audit_service
from backend.schemas.audit import DocumentListResponse
from backend.schemas.packages import (
    PackageCompletenessResponse,
    PackageCreateRequest,
    PackageCreateResponse,
    PackageDetailResponse,
    PackageDocumentPatchRequest,
    PackageListResponse,
)

router = APIRouter(prefix="/packages", tags=["packages"])


@router.post("", response_model=PackageCreateResponse)
async def create_package(payload: PackageCreateRequest) -> PackageCreateResponse:
    return await package_service.create_package(payload)


@router.get("", response_model=PackageListResponse)
async def list_packages(status: str | None = Query(default=None)) -> PackageListResponse:
    statuses = [item.strip() for item in status.split(",")] if status else None
    return await package_service.list_packages(statuses=statuses)


@router.get("/{package_id}", response_model=PackageDetailResponse)
async def get_package_detail(package_id: str) -> PackageDetailResponse:
    try:
        return await package_service.get_package_detail(package_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{package_id}/completeness", response_model=PackageCompletenessResponse)
async def get_package_completeness(package_id: str) -> PackageCompletenessResponse:
    try:
        return await package_service.get_completeness(package_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{package_id}/documents", response_model=DocumentListResponse)
async def list_package_documents(package_id: str) -> DocumentListResponse:
    try:
        return await audit_service.list_package_documents(package_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{package_id}/documents/{dcode}", response_model=PackageCompletenessResponse)
async def update_package_document(package_id: str, dcode: str, payload: PackageDocumentPatchRequest) -> PackageCompletenessResponse:
    try:
        return await package_service.update_document(package_id, dcode, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
