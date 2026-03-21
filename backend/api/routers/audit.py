from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from backend.core.audit.audit_service import audit_service
from backend.schemas.audit import AuditExportRequest, AuditExportResponse, AuditStreamResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{package_id}", response_model=AuditStreamResponse)
async def get_audit_stream(package_id: str) -> AuditStreamResponse:
    return AuditStreamResponse(package_id=package_id, events=await audit_service.get_package_events(package_id))


@router.post("/export", response_model=AuditExportResponse)
async def export_audit(payload: AuditExportRequest) -> AuditExportResponse:
    events = await audit_service.export_package(payload.package_id)
    return AuditExportResponse(package_id=payload.package_id, exported_at=datetime.now(UTC), event_count=len(events), events=events)
