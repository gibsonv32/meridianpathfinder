"""
Opportunity ORM Models
======================
SQLAlchemy models for persisting federal contract opportunities.
Follows the same pattern as protests.py — separate from dataclass models.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.database.models.base import Base


class OpportunityRecord(Base):
    """Persisted opportunity from Tango/SAM.gov."""

    __tablename__ = "opportunities"

    # Primary key — Tango's UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(String(64), unique=True, nullable=False, index=True)

    # Core fields
    title = Column(Text, nullable=False, default="")
    solicitation_number = Column(String(128), nullable=True, index=True)
    sam_url = Column(Text, nullable=True)

    # Status
    active = Column(Boolean, nullable=False, default=True)
    award_number = Column(String(128), nullable=True)

    # Dates
    first_notice_date = Column(DateTime(timezone=True), nullable=True)
    last_notice_date = Column(DateTime(timezone=True), nullable=True)
    response_deadline = Column(DateTime(timezone=True), nullable=True)

    # Classification
    naics_code = Column(String(10), nullable=True)
    psc_code = Column(String(10), nullable=True)
    set_aside_code = Column(String(20), nullable=True)
    set_aside_name = Column(String(128), nullable=True)
    notice_type_code = Column(String(5), nullable=True)
    notice_type_name = Column(String(128), nullable=True)

    # Office
    office_code = Column(String(20), nullable=True)
    office_name = Column(String(256), nullable=True)
    agency_code = Column(String(10), nullable=True)
    agency_name = Column(String(256), nullable=True)
    department_code = Column(String(10), nullable=True)
    department_name = Column(String(256), nullable=True)
    agency_abbreviation = Column(String(20), nullable=True, index=True)

    # Place of performance
    pop_city = Column(String(128), nullable=True)
    pop_state = Column(String(20), nullable=True)
    pop_zip = Column(String(32), nullable=True)
    pop_country = Column(String(10), nullable=True, default="USA")

    # Meta
    notices_count = Column(Integer, nullable=True, default=0)
    attachments_count = Column(Integer, nullable=True, default=0)

    # Provenance
    raw_payload = Column(JSONB, nullable=True)

    # Enrichment (fetched from SAM.gov description API)
    description_text = Column(Text, nullable=True)
    description_fetched_at = Column(DateTime(timezone=True), nullable=True)
    point_of_contact = Column(JSONB, nullable=True)
    resource_links = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_opp_agency_active", "agency_abbreviation", "active"),
        Index("ix_opp_naics_active", "naics_code", "active"),
        Index("ix_opp_response_deadline", "response_deadline"),
        Index("ix_opp_set_aside_active", "set_aside_code", "active"),
        Index("ix_opp_last_notice", "last_notice_date"),
    )

    def __repr__(self) -> str:
        return f"<OpportunityRecord {self.solicitation_number or self.opportunity_id}>"


class OpportunityIngestionRun(Base):
    """Tracks each ingestion run for opportunities."""

    __tablename__ = "opportunity_ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    pages_fetched = Column(Integer, nullable=False, default=0)
    records_upserted = Column(Integer, nullable=False, default=0)
    records_failed = Column(Integer, nullable=False, default=0)
    search_query = Column(String(256), nullable=True)
    parameters = Column(JSONB, nullable=True)
    errors = Column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<OpportunityIngestionRun {self.started_at} ({self.records_upserted} upserted)>"
