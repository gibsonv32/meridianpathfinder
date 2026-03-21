"""
Protest Data — PostgreSQL Repository
=====================================
Drop-in replacement for the in-memory ProtestDataStore.  Uses synchronous
SQLAlchemy sessions because the ingestion pipeline (Tango HTTP client) is
synchronous.

The router wraps calls in asyncio.to_thread() so FastAPI's event loop is
never blocked.

Usage:
    from backend.phase2.protest_data.repository import DatabaseProtestStore
    store = DatabaseProtestStore()   # uses default sync engine
    store.upsert_case(case)          # persists to PostgreSQL
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, select, func as sa_func
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models.protests import (
    IngestionRunRecord,
    ProtestCaseRecord,
    ProtestEntityRecord,
    ProtestGroundRecord,
    ProtestSignalRecord,
)
from .models import (
    EntityRole,
    IngestionRun,
    IngestionStatus,
    ProtestCase,
    ProtestEntity,
    ProtestGround,
    ProtestGroundType,
    ProtestOutcome,
    ProtestSignal,
    SignalSeverity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sync engine (ingestion pipeline is synchronous)
# ---------------------------------------------------------------------------

_SYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    os.getenv("DATABASE_URL", "postgresql+asyncpg://fedprocure:fedprocure_dev@db:5432/fedprocure")
    .replace("+asyncpg", "")
    .replace("postgresql://", "postgresql+psycopg2://"),
)

_sync_engine = create_engine(_SYNC_DATABASE_URL, pool_pre_ping=True, pool_size=5)
SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Dataclass ↔ ORM converters
# ---------------------------------------------------------------------------

def _case_to_record(case: ProtestCase) -> ProtestCaseRecord:
    """Convert a domain dataclass to an ORM record."""
    return ProtestCaseRecord(
        id=case.id,
        case_number=case.case_number,
        outcome=case.outcome.value,
        agency=case.agency,
        agency_abbreviation=case.agency_abbreviation,
        protester=case.protester,
        solicitation_number=case.solicitation_number,
        title=case.title,
        value=case.value,
        filed_date=case.filed_date,
        decision_date=case.decision_date,
        fiscal_year=case.fiscal_year,
        decision_url=case.decision_url,
        provider_name=case.provider_name,
        provider_id=case.provider_id,
        raw_payload=case.raw_payload,
        ingested_at=case.ingested_at.replace(tzinfo=timezone.utc) if case.ingested_at and case.ingested_at.tzinfo is None else case.ingested_at,
        normalized_at=case.normalized_at.replace(tzinfo=timezone.utc) if case.normalized_at and case.normalized_at.tzinfo is None else case.normalized_at,
        grounds=[
            ProtestGroundRecord(
                id=g.id, case_id=case.id,
                ground_type=g.ground_type.value, raw_text=g.raw_text, sustained=g.sustained,
            )
            for g in case.grounds
        ],
        entities=[
            ProtestEntityRecord(
                id=e.id, case_id=case.id,
                name=e.name, role=e.role.value, normalized_name=e.normalized_name,
            )
            for e in case.entities
        ],
        signals=[
            ProtestSignalRecord(
                id=s.id, case_id=case.id,
                signal_type=s.signal_type, severity=s.severity.value,
                description=s.description, evidence_text=s.evidence_text,
                confidence=s.confidence,
            )
            for s in case.signals
        ],
    )


def _record_to_case(rec: ProtestCaseRecord) -> ProtestCase:
    """Convert an ORM record back to a domain dataclass."""
    case = ProtestCase(
        id=rec.id,
        case_number=rec.case_number,
        outcome=ProtestOutcome(rec.outcome),
        agency=rec.agency,
        agency_abbreviation=rec.agency_abbreviation,
        protester=rec.protester,
        solicitation_number=rec.solicitation_number,
        title=rec.title,
        value=rec.value,
        filed_date=rec.filed_date,
        decision_date=rec.decision_date,
        fiscal_year=rec.fiscal_year,
        decision_url=rec.decision_url,
        provider_name=rec.provider_name,
        provider_id=rec.provider_id,
        raw_payload=rec.raw_payload or {},
        ingested_at=rec.ingested_at or datetime.now(timezone.utc),
        normalized_at=rec.normalized_at,
    )
    case.grounds = [
        ProtestGround(
            id=g.id, case_id=g.case_id,
            ground_type=ProtestGroundType(g.ground_type),
            raw_text=g.raw_text, sustained=g.sustained,
        )
        for g in (rec.grounds or [])
    ]
    case.entities = [
        ProtestEntity(
            id=e.id, case_id=e.case_id,
            name=e.name, role=EntityRole(e.role),
            normalized_name=e.normalized_name,
        )
        for e in (rec.entities or [])
    ]
    case.signals = [
        ProtestSignal(
            id=s.id, case_id=s.case_id,
            signal_type=s.signal_type, severity=SignalSeverity(s.severity),
            description=s.description, evidence_text=s.evidence_text,
            confidence=s.confidence,
        )
        for s in (rec.signals or [])
    ]
    return case


def _run_to_record(run: IngestionRun) -> IngestionRunRecord:
    return IngestionRunRecord(
        id=run.id,
        provider_name=run.provider_name,
        status=run.status.value,
        started_at=run.started_at.replace(tzinfo=timezone.utc) if run.started_at and run.started_at.tzinfo is None else run.started_at,
        completed_at=run.completed_at.replace(tzinfo=timezone.utc) if run.completed_at and run.completed_at.tzinfo is None else run.completed_at,
        records_fetched=run.records_fetched,
        records_normalized=run.records_normalized,
        records_failed=run.records_failed,
        errors=run.errors,
        parameters=run.parameters,
    )


def _record_to_run(rec: IngestionRunRecord) -> IngestionRun:
    run = IngestionRun(
        id=rec.id,
        provider_name=rec.provider_name,
        status=IngestionStatus(rec.status),
        started_at=rec.started_at or datetime.now(timezone.utc),
        completed_at=rec.completed_at,
        records_fetched=rec.records_fetched,
        records_normalized=rec.records_normalized,
        records_failed=rec.records_failed,
        errors=rec.errors or [],
        parameters=rec.parameters or {},
    )
    return run


# ---------------------------------------------------------------------------
# DatabaseProtestStore
# ---------------------------------------------------------------------------

class DatabaseProtestStore:
    """
    PostgreSQL-backed protest data store.
    Same interface as the in-memory ProtestDataStore so ProtestIngestionService
    works without changes.
    """

    def __init__(self, session_factory: sessionmaker | None = None):
        self._session_factory = session_factory or SyncSessionLocal

    def _session(self) -> Session:
        return self._session_factory()

    def upsert_case(self, case: ProtestCase) -> bool:
        """
        Insert or update a canonical case.
        Returns True if new, False if updated existing.
        """
        with self._session() as session:
            existing = session.execute(
                select(ProtestCaseRecord).where(
                    ProtestCaseRecord.case_number == case.case_number
                )
            ).scalar_one_or_none()

            if existing:
                # Update: delete old children, replace with new data
                case.id = existing.id
                session.delete(existing)
                session.flush()
                record = _case_to_record(case)
                session.add(record)
                session.commit()
                return False
            else:
                record = _case_to_record(case)
                session.add(record)
                session.commit()
                return True

    def store_raw(self, provider_id: str, payload: dict) -> None:
        """
        Raw payload is stored as part of the case record (raw_payload JSONB column).
        This method is a no-op for the DB store since raw_payload is persisted
        with the case in upsert_case().
        """
        pass  # raw_payload is stored on ProtestCaseRecord.raw_payload

    def save_run(self, run: IngestionRun) -> None:
        with self._session() as session:
            record = _run_to_record(run)
            session.merge(record)
            session.commit()

    def get_case(self, case_number: str) -> ProtestCase | None:
        with self._session() as session:
            rec = session.execute(
                select(ProtestCaseRecord).where(
                    ProtestCaseRecord.case_number == case_number
                )
            ).scalar_one_or_none()
            return _record_to_case(rec) if rec else None

    def get_cases_by_agency(self, abbreviation: str) -> list[ProtestCase]:
        with self._session() as session:
            recs = session.execute(
                select(ProtestCaseRecord).where(
                    ProtestCaseRecord.agency_abbreviation == abbreviation
                )
            ).scalars().all()
            return [_record_to_case(r) for r in recs]

    def get_sustained_cases(self) -> list[ProtestCase]:
        with self._session() as session:
            recs = session.execute(
                select(ProtestCaseRecord).where(
                    ProtestCaseRecord.outcome == "sustained"
                )
            ).scalars().all()
            return [_record_to_case(r) for r in recs]

    def list_cases(
        self,
        *,
        agency: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProtestCase]:
        with self._session() as session:
            stmt = select(ProtestCaseRecord)
            if agency:
                stmt = stmt.where(ProtestCaseRecord.agency_abbreviation == agency.upper())
            if outcome:
                stmt = stmt.where(ProtestCaseRecord.outcome == outcome.lower())
            stmt = stmt.order_by(ProtestCaseRecord.filed_date.desc().nullslast())
            stmt = stmt.offset(offset).limit(limit)
            recs = session.execute(stmt).scalars().all()
            return [_record_to_case(r) for r in recs]

    def list_runs(self, limit: int = 20) -> list[IngestionRun]:
        with self._session() as session:
            recs = session.execute(
                select(IngestionRunRecord)
                .order_by(IngestionRunRecord.started_at.desc())
                .limit(limit)
            ).scalars().all()
            return [_record_to_run(r) for r in recs]

    @property
    def total_cases(self) -> int:
        with self._session() as session:
            return session.execute(
                select(sa_func.count()).select_from(ProtestCaseRecord)
            ).scalar_one()

    @property
    def total_runs(self) -> int:
        with self._session() as session:
            return session.execute(
                select(sa_func.count()).select_from(IngestionRunRecord)
            ).scalar_one()

    def summary(self) -> dict[str, Any]:
        with self._session() as session:
            total = session.execute(
                select(sa_func.count()).select_from(ProtestCaseRecord)
            ).scalar_one()

            outcome_rows = session.execute(
                select(
                    ProtestCaseRecord.outcome,
                    sa_func.count().label("cnt"),
                ).group_by(ProtestCaseRecord.outcome)
            ).all()
            outcomes = {row.outcome: row.cnt for row in outcome_rows}

            run_count = session.execute(
                select(sa_func.count()).select_from(IngestionRunRecord)
            ).scalar_one()

            return {
                "total_cases": total,
                "total_runs": run_count,
                "raw_payloads_stored": total,  # every case has raw_payload
                "outcomes": outcomes,
            }

    def create_tables(self) -> None:
        """Create protest tables if they don't exist (for standalone init)."""
        from backend.database.models.protests import (
            ProtestCaseRecord,
            ProtestGroundRecord,
            ProtestEntityRecord,
            ProtestSignalRecord,
            IngestionRunRecord,
        )
        from backend.database.models.base import Base
        Base.metadata.create_all(_sync_engine, tables=[
            ProtestCaseRecord.__table__,
            ProtestGroundRecord.__table__,
            ProtestEntityRecord.__table__,
            ProtestSignalRecord.__table__,
            IngestionRunRecord.__table__,
        ])
        logger.info("Protest data tables created/verified.")
