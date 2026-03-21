from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AIOutputMetadata(BaseModel):
    source_provenance: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    requires_acceptance: bool = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generated_by: str = "fedprocure-ai"


class AIGeneratedDocument(BaseModel):
    document_id: str
    document_type: str
    content: Any
    metadata: AIOutputMetadata
    acceptance_status: str = "pending"
    accepted_by: str | None = None
    accepted_at: datetime | None = None
