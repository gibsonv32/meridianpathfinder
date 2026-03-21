from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from backend.database.db import AsyncSessionLocal, init_database
from backend.database.models import AcquisitionPackage, AuditEventRecord, GeneratedDocument, PackageDocument
from backend.schemas.audit import (
    AuditEvent,
    DocumentListResponse,
    DocumentRecord,
    DocumentVersionsResponse,
)


class ImmutableAuditError(RuntimeError):
    pass


class AuditService:
    async def append_event(
        self,
        *,
        actor: str,
        action_type: str,
        target_type: str,
        target_id: str,
        package_id: str | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        ai_output_id: str | None = None,
        source_provenance: list[str] | None = None,
        rationale: str | None = None,
    ) -> AuditEvent:
        await init_database()
        event = AuditEventRecord(
            id=f"audit_{uuid4().hex[:10]}",
            timestamp=datetime.now(UTC),
            actor=actor,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            package_id=package_id,
            before_state=jsonable_encoder(before_state) if before_state is not None else None,
            after_state=jsonable_encoder(after_state) if after_state is not None else None,
            ai_output_id=ai_output_id,
            source_provenance=source_provenance or [],
            rationale=rationale,
        )
        async with AsyncSessionLocal() as session:
            session.add(event)
            await session.commit()
        return self._to_event(event)

    async def persist_generated_document(
        self,
        *,
        package_id: str | None,
        document_type: str,
        dcode: str,
        title: str,
        content: object,
        source_provenance: list[str],
        confidence_score: float,
        requires_acceptance: bool,
        actor: str = "system",
    ) -> DocumentRecord:
        await init_database()
        timestamp = datetime.now(UTC)
        document = GeneratedDocument(
            id=f"doc_{uuid4().hex[:8]}",
            package_id=package_id,
            parent_document_id=None,
            dcode=dcode,
            document_type=document_type,
            title=title,
            content=jsonable_encoder(content),
            source_provenance=source_provenance,
            confidence_score=confidence_score,
            requires_acceptance=requires_acceptance,
            acceptance_status="pending",
            accepted_by=None,
            accepted_at=None,
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
        )
        async with AsyncSessionLocal() as session:
            session.add(document)
            await session.flush()
            if package_id:
                await self._upsert_package_document_status(session, package_id, dcode, "pending")
            session.add(
                AuditEventRecord(
                    id=f"audit_{uuid4().hex[:10]}",
                    timestamp=timestamp,
                    actor=actor,
                    action_type="generate",
                    target_type="document",
                    target_id=document.id,
                    package_id=package_id,
                    after_state=jsonable_encoder(self._to_document(document).model_dump()),
                    ai_output_id=document.id,
                    source_provenance=source_provenance,
                )
            )
            await session.commit()
            await session.refresh(document)
        return self._to_document(document)

    async def accept_document(self, document_id: str, actor: str, section_id: str | None = None) -> DocumentRecord:
        await init_database()
        async with AsyncSessionLocal() as session:
            document = await session.get(GeneratedDocument, document_id)
            if document is None:
                raise ValueError(f"Unknown document: {document_id}")
            before = self._to_document(document).model_dump()
            document.acceptance_status = "accepted"
            document.accepted_by = actor
            document.accepted_at = datetime.now(UTC)
            document.updated_at = datetime.now(UTC)
            if document.package_id:
                await self._upsert_package_document_status(session, document.package_id, document.dcode, "satisfied")
            rationale = f"Accepted section {section_id}" if section_id else "Document accepted"
            session.add(
                AuditEventRecord(
                    id=f"audit_{uuid4().hex[:10]}",
                    timestamp=datetime.now(UTC),
                    actor=actor,
                    action_type="accept",
                    target_type="document",
                    target_id=document.id,
                    package_id=document.package_id,
                    before_state=jsonable_encoder(before),
                    after_state=jsonable_encoder(self._to_document(document).model_dump()),
                    ai_output_id=document.id,
                    source_provenance=document.source_provenance,
                    rationale=rationale,
                )
            )
            await session.commit()
            await session.refresh(document)
            return self._to_document(document)

    async def modify_document(self, document_id: str, content: dict, actor: str, rationale: str | None = None) -> DocumentRecord:
        return await self._create_document_version(
            document_id=document_id,
            content=content,
            actor=actor,
            rationale=rationale,
            acceptance_status="modified",
            action_type="modify",
        )

    async def override_document(self, document_id: str, content: dict, actor: str, rationale: str) -> DocumentRecord:
        return await self._create_document_version(
            document_id=document_id,
            content=content,
            actor=actor,
            rationale=rationale,
            acceptance_status="overridden",
            action_type="override",
        )

    async def get_document(self, document_id: str) -> DocumentRecord:
        document = await self._get_document_model(document_id)
        return self._to_document(document)

    async def list_package_documents(self, package_id: str) -> DocumentListResponse:
        await init_database()
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(GeneratedDocument)
                    .where(GeneratedDocument.package_id == package_id)
                    .order_by(GeneratedDocument.created_at, GeneratedDocument.version)
                )
            ).scalars().all()
        return DocumentListResponse(package_id=package_id, documents=[self._to_document(row) for row in rows])

    async def list_document_versions(self, document_id: str) -> DocumentVersionsResponse:
        document = await self._get_document_model(document_id)
        root_id = document.parent_document_id or document.id
        await init_database()
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(GeneratedDocument)
                    .where(
                        (GeneratedDocument.id == root_id) | (GeneratedDocument.parent_document_id == root_id)
                    )
                    .order_by(GeneratedDocument.version)
                )
            ).scalars().all()
        return DocumentVersionsResponse(document_id=document_id, versions=[self._to_document(row) for row in rows])

    async def get_package_events(self, package_id: str) -> list[AuditEvent]:
        await init_database()
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(AuditEventRecord)
                    .where(AuditEventRecord.package_id == package_id)
                    .order_by(AuditEventRecord.timestamp)
                )
            ).scalars().all()
        return [self._to_event(row) for row in rows]

    async def export_package(self, package_id: str) -> list[AuditEvent]:
        return await self.get_package_events(package_id)

    def update_event(self, *_args, **_kwargs) -> None:
        raise ImmutableAuditError("Audit trail is append-only; UPDATE is not allowed")

    def delete_event(self, *_args, **_kwargs) -> None:
        raise ImmutableAuditError("Audit trail is append-only; DELETE is not allowed")

    async def _create_document_version(
        self,
        *,
        document_id: str,
        content: object,
        actor: str,
        rationale: str | None,
        acceptance_status: str,
        action_type: str,
    ) -> DocumentRecord:
        await init_database()
        async with AsyncSessionLocal() as session:
            current = await session.get(GeneratedDocument, document_id)
            if current is None:
                raise ValueError(f"Unknown document: {document_id}")
            before = self._to_document(current).model_dump()
            root_id = current.parent_document_id or current.id
            version_count = (
                await session.execute(
                    select(GeneratedDocument)
                    .where((GeneratedDocument.id == root_id) | (GeneratedDocument.parent_document_id == root_id))
                    .order_by(GeneratedDocument.version.desc())
                )
            ).scalars().first()
            next_version = 2 if version_count is None else version_count.version + 1
            new_doc = GeneratedDocument(
                id=f"doc_{uuid4().hex[:8]}",
                package_id=current.package_id,
                parent_document_id=root_id,
                dcode=current.dcode,
                document_type=current.document_type,
                title=current.title,
                content=jsonable_encoder(content),
                source_provenance=current.source_provenance,
                confidence_score=current.confidence_score,
                requires_acceptance=current.requires_acceptance,
                acceptance_status=acceptance_status,
                accepted_by=actor if acceptance_status == "accepted" else None,
                accepted_at=datetime.now(UTC) if acceptance_status == "accepted" else None,
                version=next_version,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(new_doc)
            await session.flush()
            if current.package_id:
                status = "satisfied" if acceptance_status == "accepted" else "pending"
                await self._upsert_package_document_status(session, current.package_id, current.dcode, status)
            session.add(
                AuditEventRecord(
                    id=f"audit_{uuid4().hex[:10]}",
                    timestamp=datetime.now(UTC),
                    actor=actor,
                    action_type=action_type,
                    target_type="document",
                    target_id=new_doc.id,
                    package_id=current.package_id,
                    before_state=jsonable_encoder(before),
                    after_state=jsonable_encoder(self._to_document(new_doc).model_dump()),
                    ai_output_id=new_doc.id,
                    source_provenance=current.source_provenance,
                    rationale=rationale,
                )
            )
            await session.commit()
            await session.refresh(new_doc)
            return self._to_document(new_doc)

    async def _upsert_package_document_status(self, session, package_id: str, dcode: str, status: str) -> None:
        target = (
            await session.execute(
                select(PackageDocument).where(
                    PackageDocument.package_id == package_id,
                    PackageDocument.dcode == dcode,
                )
            )
        ).scalar_one_or_none()
        if target is not None:
            target.status = status

        package = await session.get(AcquisitionPackage, package_id)
        if package is None:
            return

        docs = (
            await session.execute(select(PackageDocument).where(PackageDocument.package_id == package_id))
        ).scalars().all()
        missing = sum(1 for doc in docs if doc.status == "missing")
        satisfied = sum(1 for doc in docs if doc.status == "satisfied")
        package.updated_at = datetime.now(UTC)
        if missing > 0:
            package.status = "blocked" if satisfied == 0 else "action"
            package.blocking_reason = "Required package documents still missing"
        else:
            package.status = "ready"
            package.blocking_reason = None

    async def _get_document_model(self, document_id: str) -> GeneratedDocument:
        await init_database()
        async with AsyncSessionLocal() as session:
            document = await session.get(GeneratedDocument, document_id)
        if document is None:
            raise ValueError(f"Unknown document: {document_id}")
        return document

    def _to_document(self, document: GeneratedDocument) -> DocumentRecord:
        return DocumentRecord(
            document_id=document.id,
            package_id=document.package_id,
            parent_document_id=document.parent_document_id,
            dcode=document.dcode,
            document_type=document.document_type,
            title=document.title,
            content=document.content,
            source_provenance=list(document.source_provenance or []),
            confidence_score=document.confidence_score,
            requires_acceptance=document.requires_acceptance,
            acceptance_status=document.acceptance_status,
            status=document.acceptance_status,
            accepted_by=document.accepted_by,
            accepted_at=document.accepted_at,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
            ai_output_id=document.id,
        )

    def _to_event(self, row: AuditEventRecord) -> AuditEvent:
        return AuditEvent(
            id=row.id,
            timestamp=row.timestamp,
            actor=row.actor,
            action_type=row.action_type,
            target_type=row.target_type,
            target_id=row.target_id,
            package_id=row.package_id,
            before_state=row.before_state,
            after_state=row.after_state,
            ai_output_id=row.ai_output_id,
            source_provenance=list(row.source_provenance or []),
            rationale=row.rationale,
        )


audit_service = AuditService()
