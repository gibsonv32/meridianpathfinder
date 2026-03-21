from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.models.base import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    package_id: Mapped[str | None] = mapped_column(
        ForeignKey("acquisition_packages.id", ondelete="CASCADE"), index=True, nullable=True
    )
    parent_document_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    dcode: Mapped[str] = mapped_column(String(10))
    document_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict] = mapped_column(JSON)
    source_provenance: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.9)
    requires_acceptance: Mapped[bool] = mapped_column(Boolean, default=True)
    acceptance_status: Mapped[str] = mapped_column(String(20), default="pending")
    accepted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
