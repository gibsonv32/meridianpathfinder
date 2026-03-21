from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.rules import AcquisitionParams

DocumentStatusValue = Literal["satisfied", "pending", "missing"]
PackageQueueStatus = Literal["blocked", "action", "ready"]


class ResponsibleParty(BaseModel):
    role: str


class PackageCreateRequest(AcquisitionParams):
    pass


class PackageCreateResponse(BaseModel):
    package_id: str
    title: str
    required_dcodes: list[str]
    completeness_summary: dict[str, int]


class PackageDocumentStatus(BaseModel):
    dcode: str
    status: DocumentStatusValue
    responsible_party: str
    satisfied: bool
    source_attribution: str | None = None


class PackageCompletenessResponse(BaseModel):
    package_id: str
    title: str
    required_dcodes: list[str]
    completeness_summary: dict[str, int]
    documents: list[PackageDocumentStatus]
    approvers: dict[str, str]
    posting_deadline_days: int
    updated_at: datetime


class PackageDocumentPatchRequest(BaseModel):
    status: DocumentStatusValue = Field(description="satisfied|pending|missing")


class PackageQueueItem(BaseModel):
    package_id: str
    title: str
    value: float
    phase: str
    status: PackageQueueStatus
    deadline: str
    document_readiness: str
    blocking_reason: str | None = None
    urgency_rank: int


class PackageListResponse(BaseModel):
    items: list[PackageQueueItem]


class PackageDetailResponse(BaseModel):
    package_id: str
    title: str
    value: float
    phase: str
    status: PackageQueueStatus
    deadline: str
    blocking_reason: str | None = None
    required_dcodes: list[str]
    completeness_summary: dict[str, int]
    documents: list[PackageDocumentStatus]
    approvers: dict[str, str]
    posting_deadline_days: int
    source_attribution: list[str]
    updated_at: datetime
