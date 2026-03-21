"""
Opportunity Repository
======================
PostgreSQL persistence layer for opportunities.
Follows the same pattern as protest_data/repository.py — sync psycopg2
engine alongside the app's async engine.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from backend.database.models.opportunities import OpportunityIngestionRun, OpportunityRecord
from .models import (
    Opportunity,
    OpportunityMeta,
    OpportunityOffice,
    PlaceOfPerformance,
    SET_ASIDE_MAP,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sync DB engine (parallel to async engine in db.py)
# ---------------------------------------------------------------------------

_SYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    os.getenv("DATABASE_URL", "postgresql+asyncpg://fedprocure:fedprocure_dev@db:5432/fedprocure")
    .replace("+asyncpg", "")
    .replace("postgresql://", "postgresql+psycopg2://"),
)
_sync_engine = create_engine(_SYNC_DATABASE_URL, pool_pre_ping=True, pool_size=5)
SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)


class OpportunityStore:
    """
    PostgreSQL-backed opportunity store.

    Provides CRUD + bulk upsert + analytical queries.
    """

    def create_tables(self) -> None:
        """Create opportunity tables if they don't exist."""
        from backend.database.models.base import Base
        Base.metadata.create_all(_sync_engine, tables=[
            OpportunityRecord.__table__,
            OpportunityIngestionRun.__table__,
        ])
        logger.info("Opportunity tables ensured")

    # -- write --

    def upsert(self, opp: Opportunity) -> bool:
        """
        Insert or update an opportunity. Returns True if new, False if updated.
        """
        with SyncSessionLocal() as session:
            existing = session.query(OpportunityRecord).filter_by(
                opportunity_id=opp.opportunity_id
            ).first()

            if existing:
                # Update mutable fields
                existing.title = opp.title
                existing.solicitation_number = opp.solicitation_number
                existing.sam_url = opp.sam_url
                existing.active = opp.active
                existing.award_number = opp.award_number
                existing.first_notice_date = opp.first_notice_date
                existing.last_notice_date = opp.last_notice_date
                existing.response_deadline = opp.response_deadline
                existing.naics_code = opp.naics_code
                existing.psc_code = opp.psc_code
                existing.set_aside_code = opp.set_aside_code
                existing.set_aside_name = opp.set_aside_name
                existing.notice_type_code = opp.meta.notice_type_code
                existing.notice_type_name = opp.meta.notice_type_name
                existing.office_code = opp.office.office_code
                existing.office_name = opp.office.office_name
                existing.agency_code = opp.office.agency_code
                existing.agency_name = opp.office.agency_name
                existing.department_code = opp.office.department_code
                existing.department_name = opp.office.department_name
                existing.agency_abbreviation = opp.agency_abbreviation
                existing.pop_city = opp.place_of_performance.city
                existing.pop_state = opp.place_of_performance.state
                existing.pop_zip = opp.place_of_performance.zip_code
                existing.pop_country = opp.place_of_performance.country
                existing.notices_count = opp.meta.notices_count
                existing.attachments_count = opp.meta.attachments_count
                existing.raw_payload = opp.raw_payload
                existing.updated_at = datetime.now(timezone.utc)
                session.commit()
                return False
            else:
                record = self._opp_to_record(opp)
                session.add(record)
                session.commit()
                return True

    def upsert_batch(self, opps: list[Opportunity]) -> tuple[int, int]:
        """
        Batch upsert. Returns (new_count, updated_count).
        """
        new_count = 0
        updated_count = 0
        with SyncSessionLocal() as session:
            # Pre-fetch existing IDs for this batch
            opp_ids = [o.opportunity_id for o in opps]
            existing_records = {
                r.opportunity_id: r
                for r in session.query(OpportunityRecord).filter(
                    OpportunityRecord.opportunity_id.in_(opp_ids)
                ).all()
            }

            for opp in opps:
                existing = existing_records.get(opp.opportunity_id)
                if existing:
                    existing.title = opp.title
                    existing.solicitation_number = opp.solicitation_number
                    existing.sam_url = opp.sam_url
                    existing.active = opp.active
                    existing.award_number = opp.award_number
                    existing.first_notice_date = opp.first_notice_date
                    existing.last_notice_date = opp.last_notice_date
                    existing.response_deadline = opp.response_deadline
                    existing.naics_code = opp.naics_code
                    existing.psc_code = opp.psc_code
                    existing.set_aside_code = opp.set_aside_code
                    existing.set_aside_name = opp.set_aside_name
                    existing.notice_type_code = opp.meta.notice_type_code
                    existing.notice_type_name = opp.meta.notice_type_name
                    existing.office_code = opp.office.office_code
                    existing.office_name = opp.office.office_name
                    existing.agency_code = opp.office.agency_code
                    existing.agency_name = opp.office.agency_name
                    existing.department_code = opp.office.department_code
                    existing.department_name = opp.office.department_name
                    existing.agency_abbreviation = opp.agency_abbreviation
                    existing.pop_city = opp.place_of_performance.city
                    existing.pop_state = opp.place_of_performance.state
                    existing.pop_zip = opp.place_of_performance.zip_code
                    existing.pop_country = opp.place_of_performance.country
                    existing.notices_count = opp.meta.notices_count
                    existing.attachments_count = opp.meta.attachments_count
                    existing.raw_payload = opp.raw_payload
                    existing.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                else:
                    record = self._opp_to_record(opp)
                    session.add(record)
                    new_count += 1

            session.commit()
        return new_count, updated_count

    # -- read --

    def get(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get a single opportunity by Tango ID."""
        with SyncSessionLocal() as session:
            record = session.query(OpportunityRecord).filter_by(
                opportunity_id=opportunity_id
            ).first()
            if not record:
                return None
            return self._record_to_opp(record)

    def get_by_solicitation(self, solicitation_number: str) -> list[Opportunity]:
        """Find opportunities by solicitation number."""
        with SyncSessionLocal() as session:
            records = session.query(OpportunityRecord).filter_by(
                solicitation_number=solicitation_number
            ).all()
            return [self._record_to_opp(r) for r in records]

    def list_opportunities(
        self,
        *,
        agency: Optional[str] = None,
        active_only: bool = False,
        set_aside: Optional[str] = None,
        naics: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Opportunity]:
        """List opportunities with optional filters."""
        with SyncSessionLocal() as session:
            q = session.query(OpportunityRecord)
            if agency:
                q = q.filter(OpportunityRecord.agency_abbreviation == agency.upper())
            if active_only:
                q = q.filter(OpportunityRecord.active == True)
            if set_aside:
                q = q.filter(OpportunityRecord.set_aside_code == set_aside)
            if naics:
                q = q.filter(OpportunityRecord.naics_code == naics)
            q = q.order_by(OpportunityRecord.last_notice_date.desc().nullslast())
            q = q.offset(offset).limit(limit)
            return [self._record_to_opp(r) for r in q.all()]

    def search(self, query: str, *, limit: int = 50) -> list[Opportunity]:
        """Simple text search on title and solicitation number."""
        with SyncSessionLocal() as session:
            pattern = f"%{query}%"
            records = session.query(OpportunityRecord).filter(
                (OpportunityRecord.title.ilike(pattern)) |
                (OpportunityRecord.solicitation_number.ilike(pattern))
            ).order_by(
                OpportunityRecord.last_notice_date.desc().nullslast()
            ).limit(limit).all()
            return [self._record_to_opp(r) for r in records]

    # -- analytics --

    def summary(self) -> dict:
        """Summary statistics for the opportunity store."""
        with SyncSessionLocal() as session:
            total = session.query(func.count(OpportunityRecord.id)).scalar() or 0
            active = session.query(func.count(OpportunityRecord.id)).filter(
                OpportunityRecord.active == True
            ).scalar() or 0
            awarded = session.query(func.count(OpportunityRecord.id)).filter(
                OpportunityRecord.award_number.isnot(None)
            ).scalar() or 0

            # Open = active + deadline in future or null
            open_count = session.query(func.count(OpportunityRecord.id)).filter(
                OpportunityRecord.active == True,
                (OpportunityRecord.response_deadline.is_(None) |
                 (OpportunityRecord.response_deadline > datetime.now(timezone.utc)))
            ).scalar() or 0

            # Top agencies
            agency_rows = session.query(
                OpportunityRecord.agency_abbreviation,
                func.count(OpportunityRecord.id)
            ).group_by(
                OpportunityRecord.agency_abbreviation
            ).order_by(
                func.count(OpportunityRecord.id).desc()
            ).limit(15).all()

            # Set-aside breakdown
            set_aside_rows = session.query(
                OpportunityRecord.set_aside_name,
                func.count(OpportunityRecord.id)
            ).group_by(
                OpportunityRecord.set_aside_name
            ).order_by(
                func.count(OpportunityRecord.id).desc()
            ).all()

            # Notice type breakdown
            notice_rows = session.query(
                OpportunityRecord.notice_type_name,
                func.count(OpportunityRecord.id)
            ).group_by(
                OpportunityRecord.notice_type_name
            ).order_by(
                func.count(OpportunityRecord.id).desc()
            ).all()

            return {
                "total": total,
                "active": active,
                "awarded": awarded,
                "open": open_count,
                "by_agency": {r[0] or "UNK": r[1] for r in agency_rows},
                "by_set_aside": {r[0] or "Unknown": r[1] for r in set_aside_rows},
                "by_notice_type": {r[0] or "Unknown": r[1] for r in notice_rows},
                "store_type": "postgresql",
            }

    # -- ingestion runs --

    def save_run(
        self,
        *,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
        pages_fetched: int = 0,
        records_upserted: int = 0,
        records_failed: int = 0,
        search_query: Optional[str] = None,
        parameters: Optional[dict] = None,
        errors: Optional[list] = None,
    ) -> str:
        """Record an ingestion run. Returns the run ID."""
        run = OpportunityIngestionRun(
            id=uuid4(),
            started_at=started_at,
            finished_at=finished_at or datetime.now(timezone.utc),
            pages_fetched=pages_fetched,
            records_upserted=records_upserted,
            records_failed=records_failed,
            search_query=search_query,
            parameters=parameters,
            errors=errors,
        )
        with SyncSessionLocal() as session:
            session.add(run)
            session.commit()
            return str(run.id)

    # -- converters --

    @staticmethod
    def _opp_to_record(opp: Opportunity) -> OpportunityRecord:
        """Dataclass → ORM record."""
        return OpportunityRecord(
            id=uuid4(),
            opportunity_id=opp.opportunity_id,
            title=opp.title,
            solicitation_number=opp.solicitation_number,
            sam_url=opp.sam_url,
            active=opp.active,
            award_number=opp.award_number,
            first_notice_date=opp.first_notice_date,
            last_notice_date=opp.last_notice_date,
            response_deadline=opp.response_deadline,
            naics_code=opp.naics_code,
            psc_code=opp.psc_code,
            set_aside_code=opp.set_aside_code,
            set_aside_name=opp.set_aside_name,
            notice_type_code=opp.meta.notice_type_code,
            notice_type_name=opp.meta.notice_type_name,
            office_code=opp.office.office_code,
            office_name=opp.office.office_name,
            agency_code=opp.office.agency_code,
            agency_name=opp.office.agency_name,
            department_code=opp.office.department_code,
            department_name=opp.office.department_name,
            agency_abbreviation=opp.agency_abbreviation,
            pop_city=opp.place_of_performance.city,
            pop_state=opp.place_of_performance.state,
            pop_zip=opp.place_of_performance.zip_code,
            pop_country=opp.place_of_performance.country,
            notices_count=opp.meta.notices_count,
            attachments_count=opp.meta.attachments_count,
            raw_payload=opp.raw_payload,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _record_to_opp(record: OpportunityRecord) -> Opportunity:
        """ORM record → dataclass."""
        return Opportunity(
            opportunity_id=record.opportunity_id,
            title=record.title or "",
            solicitation_number=record.solicitation_number or "",
            sam_url=record.sam_url or "",
            active=record.active,
            award_number=record.award_number,
            first_notice_date=record.first_notice_date,
            last_notice_date=record.last_notice_date,
            response_deadline=record.response_deadline,
            naics_code=record.naics_code or "",
            psc_code=record.psc_code or "",
            set_aside_code=record.set_aside_code or "",
            set_aside_name=record.set_aside_name or "",
            office=OpportunityOffice(
                office_code=record.office_code or "",
                office_name=record.office_name or "",
                agency_code=record.agency_code or "",
                agency_name=record.agency_name or "",
                department_code=record.department_code or "",
                department_name=record.department_name or "",
            ),
            place_of_performance=PlaceOfPerformance(
                city=record.pop_city or "",
                state=record.pop_state or "",
                zip_code=record.pop_zip or "",
                country=record.pop_country or "USA",
            ),
            meta=OpportunityMeta(
                notices_count=record.notices_count or 0,
                attachments_count=record.attachments_count or 0,
                notice_type_code=record.notice_type_code or "",
                notice_type_name=record.notice_type_name or "",
            ),
            raw_payload=record.raw_payload or {},
        )
