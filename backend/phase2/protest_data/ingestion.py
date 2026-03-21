"""
Protest Data Ingestion Pipeline
===============================
Orchestrates fetching from provider (Tango), normalization, storage of
both raw payloads and canonical records, and run-level audit logging.

Usage:
    service = ProtestIngestionService(
        client=TangoClient(TangoConfig.from_env()),
        normalizer=ProtestNormalizationService(),
    )
    run = service.ingest(agency="DHS", outcome="sustained")
    print(run.to_summary())

All ingested data is held in-memory for Phase 1.  Phase 2 will add
database persistence via SQLAlchemy / asyncpg.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from .models import (
    IngestionRun,
    IngestionStatus,
    ProtestCase,
)
from .normalization import ProtestNormalizationService
from .tango_client import (
    TangoClient,
    TangoError,
    TangoListResponse,
    TangoProtestRecord,
)

logger = logging.getLogger(__name__)


class ProtestDataStore:
    """
    In-memory store for Phase 1.  Provides the interface that a future
    database-backed store will implement.
    """

    def __init__(self):
        self.cases: dict[str, ProtestCase] = {}       # keyed by case.id
        self.by_case_number: dict[str, str] = {}       # case_number → case.id
        self.raw_payloads: dict[str, dict] = {}         # provider_id → raw JSON
        self.ingestion_runs: list[IngestionRun] = []

    def upsert_case(self, case: ProtestCase) -> bool:
        """
        Insert or update a canonical case.
        Returns True if new, False if updated existing.
        """
        existing_id = self.by_case_number.get(case.case_number)
        if existing_id:
            # Update: newer data wins
            self.cases[existing_id] = case
            case.id = existing_id  # preserve original ID
            return False
        else:
            self.cases[case.id] = case
            self.by_case_number[case.case_number] = case.id
            return True

    def store_raw(self, provider_id: str, payload: dict) -> None:
        """Store raw provider payload for audit trail."""
        self.raw_payloads[provider_id] = payload

    def save_run(self, run: IngestionRun) -> None:
        self.ingestion_runs.append(run)

    def get_case(self, case_number: str) -> ProtestCase | None:
        cid = self.by_case_number.get(case_number)
        return self.cases.get(cid) if cid else None

    def get_cases_by_agency(self, abbreviation: str) -> list[ProtestCase]:
        return [
            c for c in self.cases.values()
            if c.agency_abbreviation == abbreviation
        ]

    def get_sustained_cases(self) -> list[ProtestCase]:
        from .models import ProtestOutcome
        return [
            c for c in self.cases.values()
            if c.outcome == ProtestOutcome.SUSTAINED
        ]

    @property
    def total_cases(self) -> int:
        return len(self.cases)

    @property
    def total_runs(self) -> int:
        return len(self.ingestion_runs)

    def summary(self) -> dict[str, Any]:
        from .models import ProtestOutcome
        outcomes: dict[str, int] = {}
        for c in self.cases.values():
            outcomes[c.outcome.value] = outcomes.get(c.outcome.value, 0) + 1
        return {
            "total_cases": self.total_cases,
            "total_runs": self.total_runs,
            "raw_payloads_stored": len(self.raw_payloads),
            "outcomes": outcomes,
        }


class ProtestIngestionService:
    """
    Orchestrates end-to-end ingestion:
      fetch (paginated) → store raw → normalize → store canonical → log run
    """

    def __init__(
        self,
        client: TangoClient,
        normalizer: ProtestNormalizationService | None = None,
        store: ProtestDataStore | None = None,
    ):
        self.client = client
        self.normalizer = normalizer or ProtestNormalizationService()
        self.store = store or ProtestDataStore()

    def ingest(
        self,
        *,
        agency: str | None = None,
        outcome: str | None = None,
        filed_after: date | None = None,
        filed_before: date | None = None,
        max_pages: int = 10,
        page_size: int = 50,
        start_page: int = 1,
    ) -> IngestionRun:
        """
        Run a full ingestion cycle with the given filters.

        Fetches all pages up to max_pages, normalizes each record, and
        stores both raw and canonical data.  Returns an IngestionRun
        with complete audit metadata.
        """
        run = IngestionRun(
            provider_name="tango",
            parameters={
                "agency": agency,
                "outcome": outcome,
                "filed_after": filed_after.isoformat() if filed_after else None,
                "filed_before": filed_before.isoformat() if filed_before else None,
                "max_pages": max_pages,
                "page_size": page_size,
                "start_page": start_page,
            },
        )

        all_records: list[TangoProtestRecord] = []

        try:
            # Phase: Fetch
            all_records = self._fetch_all_pages(
                agency=agency,
                outcome=outcome,
                filed_after=filed_after,
                filed_before=filed_before,
                max_pages=max_pages,
                page_size=page_size,
                start_page=start_page,
            )
            run.records_fetched = len(all_records)
            logger.info("Fetched %d records from Tango", len(all_records))

            # Phase: Store raw payloads
            for record in all_records:
                self.store.store_raw(record.tango_id, record.raw_payload)

            # Phase: Normalize
            successes, failures = self.normalizer.normalize_batch(all_records)
            run.records_normalized = len(successes)
            run.records_failed = len(failures)

            for _record, error_msg in failures:
                run.errors.append(f"{_record.tango_id}: {error_msg}")

            # Phase: Store canonical
            new_count = 0
            for case in successes:
                is_new = self.store.upsert_case(case)
                if is_new:
                    new_count += 1

            logger.info(
                "Normalized %d/%d records (%d new, %d updated, %d failed)",
                len(successes), len(all_records), new_count,
                len(successes) - new_count, len(failures),
            )

        except TangoError as exc:
            run.errors.append(f"Tango API error: {exc}")
            logger.error("Ingestion failed: %s", exc)

        except Exception as exc:
            run.errors.append(f"Unexpected error: {exc}")
            logger.exception("Unexpected ingestion error")

        finally:
            run.complete()
            self.store.save_run(run)

        return run

    def ingest_single(self, tango_id: str, *, expand_docket: bool = True) -> ProtestCase | None:
        """Fetch and normalize a single protest record by Tango ID."""
        try:
            record = self.client.get_protest(tango_id, expand_docket=expand_docket)
            self.store.store_raw(record.tango_id, record.raw_payload)
            case = self.normalizer.normalize(record)
            self.store.upsert_case(case)
            return case
        except TangoError as exc:
            logger.error("Failed to ingest single record %s: %s", tango_id, exc)
            return None

    def _fetch_all_pages(
        self,
        *,
        agency: str | None,
        outcome: str | None,
        filed_after: date | None,
        filed_before: date | None,
        max_pages: int,
        page_size: int,
        start_page: int = 1,
    ) -> list[TangoProtestRecord]:
        """Paginate through the Tango list endpoint."""
        records: list[TangoProtestRecord] = []

        for page in range(start_page, start_page + max_pages):
            response = self.client.list_protests(
                agency=agency,
                outcome=outcome,
                filed_after=filed_after,
                filed_before=filed_before,
                page=page,
                page_size=page_size,
            )
            records.extend(response.records)
            logger.debug(
                "Page %d: %d records (total so far: %d / %d)",
                page, len(response.records), len(records), response.total_count,
            )

            if not response.has_next:
                break

        return records
