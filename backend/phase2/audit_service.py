"""
AuditService — Phase 2 refactored. Pure append-only event log.
Document lifecycle moved to DocumentService.
"""
from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from backend.database.db import AsyncSessionLocal, init_database
from backend.database.models import AuditEventRecord
from backend.schemas.audit import AuditEvent


class ImmutableAuditError(RuntimeError):
    pass


class AuditService:
    """Append-only audit event log. No document lifecycle — that's DocumentService."""

    async def append_event(self, *, actor: str, action_type: str, target_type: str, target_id: str, package_id: str | None = None, before_state: dict | None = None, after_state: dict | None = None, ai_output_id: str | None = None, source_provenance: list[str] | None = None, rationale: str | None = None) -> AuditEvent:
        await init_database()
        event = AuditEventRecord(id=f"audit_{uuid4().hex[:10]}", timestamp=datetime.now(UTC), actor=actor, action_type=action_type, target_type=target_type, target_id=target_id, package_id=package_id, before_state=jsonable_encoder(before_state) if before_state is not None else None, after_state=jsonable_encoder(after_state) if after_state is not None else None, ai_output_id=ai_output_id, source_provenance=source_provenance or [], rationale=rationale)
        async with AsyncSessionLocal() as session:
            session.add(event)
            await session.commit()
        return self._to_event(event)

    async def get_package_events(self, package_id: str) -> list[AuditEvent]:
        await init_database()
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(select(AuditEventRecord).where(AuditEventRecord.package_id == package_id).order_by(AuditEventRecord.timestamp))).scalars().all()
        return [self._to_event(row) for row in rows]

    async def export_package(self, package_id: str) -> list[AuditEvent]:
        return await self.get_package_events(package_id)

    def update_event(self, *_args, **_kwargs) -> None:
        raise ImmutableAuditError("Audit trail is append-only; UPDATE is not allowed")

    def delete_event(self, *_args, **_kwargs) -> None:
        raise ImmutableAuditError("Audit trail is append-only; DELETE is not allowed")

    # --- Backward compatibility delegation to DocumentService ---
    # These methods exist so callers that still import audit_service.persist_generated_document
    # continue to work during migration. They delegate to document_service.

    async def persist_generated_document(self, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.persist_generated_document(**kwargs)

    async def accept_document(self, *args, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.accept_document(*args, **kwargs)

    async def modify_document(self, *args, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.modify_document(*args, **kwargs)

    async def override_document(self, *args, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.override_document(*args, **kwargs)

    async def get_document(self, *args, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.get_document(*args, **kwargs)

    async def list_package_documents(self, *args, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.list_package_documents(*args, **kwargs)

    async def list_document_versions(self, *args, **kwargs):
        from backend.core.document_service import document_service
        return await document_service.list_document_versions(*args, **kwargs)

    def _to_event(self, row: AuditEventRecord) -> AuditEvent:
        return AuditEvent(id=row.id, timestamp=row.timestamp, actor=row.actor, action_type=row.action_type, target_type=row.target_type, target_id=row.target_id, package_id=row.package_id, before_state=row.before_state, after_state=row.after_state, ai_output_id=row.ai_output_id, source_provenance=list(row.source_provenance or []), rationale=row.rationale)


audit_service = AuditService()
