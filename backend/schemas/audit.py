from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ActionType = Literal["create", "update", "accept", "modify", "override", "generate", "review"]
TargetType = Literal["package", "document", "threshold", "rule", "igce", "pws"]


class AuditEvent(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    action_type: ActionType
    target_type: TargetType
    target_id: str
    package_id: str | None = None
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    ai_output_id: str | None = None
    source_provenance: list[str] = Field(default_factory=list)
    rationale: str | None = None


class AuditStreamResponse(BaseModel):
    package_id: str
    events: list[AuditEvent]


class AuditExportRequest(BaseModel):
    package_id: str


class AuditExportResponse(BaseModel):
    package_id: str
    exported_at: datetime
    event_count: int
    events: list[AuditEvent]


class DocumentRecord(BaseModel):
    document_id: str
    package_id: str | None = None
    parent_document_id: str | None = None
    dcode: str
    document_type: str
    title: str
    content: Any
    source_provenance: list[str] = Field(default_factory=list)
    confidence_score: float
    requires_acceptance: bool = True
    acceptance_status: str = "pending"
    status: str = "pending"
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    version: int = 1
    created_at: datetime
    updated_at: datetime
    ai_output_id: str | None = None


class DocumentListResponse(BaseModel):
    package_id: str
    documents: list[DocumentRecord]


class DocumentVersionsResponse(BaseModel):
    document_id: str
    versions: list[DocumentRecord]


class DocumentAcceptRequest(BaseModel):
    actor: str = "human"
    section_id: str | None = None


class DocumentModifyRequest(BaseModel):
    actor: str = "human"
    content: Any
    rationale: str | None = None


class DocumentOverrideRequest(BaseModel):
    actor: str = "human"
    content: Any
    rationale: str
