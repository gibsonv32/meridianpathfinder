"""
Protest Data — SQLAlchemy ORM Models
=====================================
Persistent storage for GAO bid protest data.  Maps the canonical dataclass
models (backend.phase2.protest_data.models) to PostgreSQL tables.

Tables:
  protest_cases      — one row per GAO B-number
  protest_grounds    — protest grounds (many-to-one with case)
  protest_entities   — named parties (many-to-one with case)
  protest_signals    — derived risk signals (many-to-one with case)
  ingestion_runs     — audit trail for bulk ingestion executions
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.models.base import Base


# ---------------------------------------------------------------------------
# protest_cases
# ---------------------------------------------------------------------------

class ProtestCaseRecord(Base):
    __tablename__ = "protest_cases"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    agency: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    agency_abbreviation: Mapped[str] = mapped_column(String(20), nullable=False, default="", index=True)
    protester: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    solicitation_number: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    filed_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    decision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    decision_url: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Provenance
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", index=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Timestamps
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    normalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    grounds: Mapped[list[ProtestGroundRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    entities: Mapped[list[ProtestEntityRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    signals: Mapped[list[ProtestSignalRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_protest_cases_agency_outcome", "agency_abbreviation", "outcome"),
        Index("ix_protest_cases_filed_fy", "filed_date", "fiscal_year"),
    )


# ---------------------------------------------------------------------------
# protest_grounds
# ---------------------------------------------------------------------------

class ProtestGroundRecord(Base):
    __tablename__ = "protest_grounds"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("protest_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    ground_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sustained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    case: Mapped[ProtestCaseRecord] = relationship(back_populates="grounds")


# ---------------------------------------------------------------------------
# protest_entities
# ---------------------------------------------------------------------------

class ProtestEntityRecord(Base):
    __tablename__ = "protest_entities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("protest_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="protester")
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    case: Mapped[ProtestCaseRecord] = relationship(back_populates="entities")


# ---------------------------------------------------------------------------
# protest_signals
# ---------------------------------------------------------------------------

class ProtestSignalRecord(Base):
    __tablename__ = "protest_signals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("protest_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    case: Mapped[ProtestCaseRecord] = relationship(back_populates="signals")


# ---------------------------------------------------------------------------
# ingestion_runs
# ---------------------------------------------------------------------------

class IngestionRunRecord(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    records_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_normalized: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
