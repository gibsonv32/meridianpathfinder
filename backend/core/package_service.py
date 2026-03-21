from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database.db import AsyncSessionLocal, init_database
from backend.database.models import AcquisitionPackage, PackageDocument
from backend.database.seed import RESPONSIBLE_PARTY_BY_DCODE, SOURCE_ATTRIBUTION_BY_DCODE
from backend.schemas.packages import (
    PackageCompletenessResponse,
    PackageCreateRequest,
    PackageCreateResponse,
    PackageDetailResponse,
    PackageDocumentPatchRequest,
    PackageDocumentStatus,
    PackageListResponse,
    PackageQueueItem,
)
from backend.core.rules_engine.service import rules_engine_service


class PackageService:
    async def create_package(self, payload: PackageCreateRequest) -> PackageCreateResponse:
        await init_database()
        evaluation = await rules_engine_service.evaluate(payload)
        package_id = f"pkg_{uuid4().hex[:8]}"
        async with AsyncSessionLocal() as session:
            package = AcquisitionPackage(
                id=package_id,
                title=payload.title,
                value=payload.value,
                naics=payload.naics,
                psc=payload.psc,
                services=payload.services,
                it_related=payload.it_related,
                sole_source=payload.sole_source,
                commercial_item=payload.commercial_item,
                emergency=payload.emergency,
                vendor_on_site=payload.vendor_on_site,
                competition_type=payload.competition_type,
                posting_deadline_days=evaluation.posting_deadline_days,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(package)
            for dcode in evaluation.required_dcodes:
                session.add(PackageDocument(
                    package_id=package_id,
                    dcode=dcode,
                    status="missing",
                    responsible_party=RESPONSIBLE_PARTY_BY_DCODE.get(dcode, "CO"),
                    source_attribution=SOURCE_ATTRIBUTION_BY_DCODE.get(dcode),
                ))
            await session.commit()
        return PackageCreateResponse(package_id=package_id, title=payload.title, required_dcodes=evaluation.required_dcodes, completeness_summary={"satisfied": 0, "pending": 0, "missing": len(evaluation.required_dcodes), "total": len(evaluation.required_dcodes)})

    async def list_packages(self, statuses: list[str] | None = None) -> PackageListResponse:
        await init_database()
        async with AsyncSessionLocal() as session:
            stmt = select(AcquisitionPackage).options(selectinload(AcquisitionPackage.documents))
            if statuses:
                stmt = stmt.where(AcquisitionPackage.status.in_(statuses))
            records = (await session.execute(stmt)).scalars().all()
        items = [self._to_queue_item(record) for record in records]
        items.sort(key=lambda item: (item.urgency_rank, item.deadline, -item.value))
        return PackageListResponse(items=items)

    async def get_package_detail(self, package_id: str) -> PackageDetailResponse:
        record = await self._get(package_id)
        documents = self._document_models(record.documents)
        summary = self._summary(record.documents)
        return PackageDetailResponse(
            package_id=record.id,
            title=record.title,
            value=record.value,
            phase=record.phase,
            status=record.status,
            deadline=record.deadline,
            blocking_reason=record.blocking_reason,
            required_dcodes=sorted(doc.dcode for doc in record.documents),
            completeness_summary=summary,
            documents=documents,
            approvers=await self._approvers(record),
            posting_deadline_days=record.posting_deadline_days,
            source_attribution=sorted({doc.source_attribution for doc in documents if doc.source_attribution}),
            updated_at=record.updated_at,
        )

    async def get_completeness(self, package_id: str) -> PackageCompletenessResponse:
        record = await self._get(package_id)
        return await self._to_completeness(record)

    async def update_document(self, package_id: str, dcode: str, payload: PackageDocumentPatchRequest) -> PackageCompletenessResponse:
        await init_database()
        async with AsyncSessionLocal() as session:
            stmt = select(AcquisitionPackage).where(AcquisitionPackage.id == package_id).options(selectinload(AcquisitionPackage.documents))
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record is None:
                raise ValueError(f"Unknown package: {package_id}")
            target = next((doc for doc in record.documents if doc.dcode == dcode), None)
            if target is None:
                raise ValueError(f"Document {dcode} is not required for package {package_id}")
            target.status = payload.status
            record.updated_at = datetime.now(UTC)
            self._recompute_status(record)
            await session.commit()
            await session.refresh(record)
        return await self.get_completeness(package_id)

    async def _to_completeness(self, record: AcquisitionPackage) -> PackageCompletenessResponse:
        documents = self._document_models(record.documents)
        return PackageCompletenessResponse(
            package_id=record.id,
            title=record.title,
            required_dcodes=sorted(doc.dcode for doc in record.documents),
            completeness_summary=self._summary(record.documents),
            documents=documents,
            approvers=await self._approvers(record),
            posting_deadline_days=record.posting_deadline_days,
            updated_at=record.updated_at,
        )

    def _document_models(self, documents: list[PackageDocument]) -> list[PackageDocumentStatus]:
        return [
            PackageDocumentStatus(
                dcode=doc.dcode,
                status=doc.status,
                responsible_party=doc.responsible_party,
                satisfied=doc.status == "satisfied",
                source_attribution=doc.source_attribution,
            )
            for doc in sorted(documents, key=lambda item: item.dcode)
        ]

    def _summary(self, documents: list[PackageDocument]) -> dict[str, int]:
        counts = Counter(doc.status for doc in documents)
        return {"satisfied": counts.get("satisfied", 0), "pending": counts.get("pending", 0), "missing": counts.get("missing", 0), "total": len(documents)}

    def _recompute_status(self, record: AcquisitionPackage) -> None:
        summary = self._summary(record.documents)
        if summary["missing"] > 0:
            record.status = "blocked" if summary["satisfied"] == 0 else "action"
            record.blocking_reason = "Required package documents still missing"
        else:
            record.status = "ready"
            record.blocking_reason = None

    def _urgency_rank(self, status: str) -> int:
        return {"blocked": 0, "action": 1, "ready": 2}.get(status, 9)

    def _to_queue_item(self, record: AcquisitionPackage) -> PackageQueueItem:
        summary = self._summary(record.documents)
        return PackageQueueItem(
            package_id=record.id,
            title=record.title,
            value=record.value,
            phase=record.phase,
            status=record.status,
            deadline=record.deadline,
            document_readiness=f"{summary['satisfied']}/{summary['total']}",
            blocking_reason=record.blocking_reason,
            urgency_rank=self._urgency_rank(record.status),
        )

    async def _get(self, package_id: str) -> AcquisitionPackage:
        await init_database()
        async with AsyncSessionLocal() as session:
            stmt = select(AcquisitionPackage).where(AcquisitionPackage.id == package_id).options(selectinload(AcquisitionPackage.documents))
            record = (await session.execute(stmt)).scalar_one_or_none()
        if record is None:
            raise ValueError(f"Unknown package: {package_id}")
        return record

    async def _approvers(self, record: AcquisitionPackage) -> dict[str, str]:
        payload = PackageCreateRequest(
            title=record.title,
            value=record.value,
            naics=record.naics,
            psc=record.psc,
            services=record.services,
            it_related=record.it_related,
            sole_source=record.sole_source,
            commercial_item=record.commercial_item,
            emergency=record.emergency,
            vendor_on_site=record.vendor_on_site,
            competition_type=record.competition_type,
        )
        evaluation = await rules_engine_service.evaluate(payload)
        return evaluation.approvers


package_service = PackageService()
