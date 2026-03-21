"""
Protest Data Pipeline — FastAPI Router
=======================================
Exposes the Tango ingestion pipeline, canonical protest case queries,
and ingestion run history via REST endpoints.

All endpoints are Tier 2 (AI-assisted, CO-reviewed) except the raw
ingestion trigger which is an admin/ops function.

Mounts at: /api/v1/phase2/protests/
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.phase2.protest_data.tango_client import (
    TangoClient,
    TangoConfig,
    TangoError,
)
from backend.phase2.protest_data.normalization import ProtestNormalizationService
from backend.phase2.protest_data.ingestion import (
    ProtestDataStore,
    ProtestIngestionService,
)
from backend.phase2.protest_data.repository import DatabaseProtestStore
from backend.phase2.protest_data.models import ProtestOutcome
from backend.phase2.protest_data.router_analytics import router as analytics_router

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/protests", tags=["protest-data"])

# Mount analytics sub-router at /protests/analytics/
router.include_router(analytics_router)


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_config = TangoConfig.from_env()
_client = TangoClient(_config) if _config.api_key else None
_normalizer = ProtestNormalizationService()

# Database-backed store (replaces in-memory ProtestDataStore)
try:
    _store = DatabaseProtestStore()
    _store.create_tables()
    logger.info("Protest data: using PostgreSQL store")
except Exception as exc:
    logger.warning("Failed to init DB store, falling back to in-memory: %s", exc)
    _store = ProtestDataStore()

_service = (
    ProtestIngestionService(client=_client, normalizer=_normalizer, store=_store)
    if _client
    else None
)


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class ProtestCaseResponse(BaseModel):
    id: str
    case_number: str
    outcome: str
    agency: str
    agency_abbreviation: str
    protester: str
    solicitation_number: str
    title: str
    value: float | None
    filed_date: str | None
    decision_date: str | None
    fiscal_year: int | None
    decision_url: str
    provider_name: str
    provider_id: str
    grounds_count: int
    signals_count: int


class IngestionRunResponse(BaseModel):
    run_id: str
    provider: str
    status: str
    fetched: int
    normalized: int
    failed: int
    duration_s: float | None
    error_count: int


class IngestRequest(BaseModel):
    agency: str | None = None
    outcome: str | None = None
    filed_after: str | None = None  # ISO date
    filed_before: str | None = None  # ISO date
    max_pages: int = Field(default=5, ge=1, le=50)
    page_size: int = Field(default=50, ge=1, le=100)
    start_page: int = Field(default=1, ge=1, le=2000)


class StoreStatsResponse(BaseModel):
    total_cases: int
    total_runs: int
    raw_payloads_stored: int
    outcomes: dict[str, int]
    tango_connected: bool
    store_type: str = "postgresql"


class HealthResponse(BaseModel):
    tango_reachable: bool
    api_key_configured: bool
    store_cases: int
    store_type: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def protest_data_health():
    """Check Tango API connectivity and store state."""
    key_configured = _client is not None
    reachable = False
    if _client:
        try:
            reachable = _client.health_check()
        except Exception:
            pass
    store_type = "postgresql" if isinstance(_store, DatabaseProtestStore) else "in-memory"
    return HealthResponse(
        tango_reachable=reachable,
        api_key_configured=key_configured,
        store_cases=_store.total_cases,
        store_type=store_type,
    )


@router.post("/ingest", response_model=IngestionRunResponse)
async def trigger_ingestion(req: IngestRequest):
    """
    Trigger a protest data ingestion from Tango.
    Fetches, normalizes, and stores canonical protest records.
    """
    if not _service:
        raise HTTPException(
            status_code=503,
            detail="Tango API key not configured. Set TANGO_API_KEY environment variable.",
        )

    filed_after = date.fromisoformat(req.filed_after) if req.filed_after else None
    filed_before = date.fromisoformat(req.filed_before) if req.filed_before else None

    try:
        run = _service.ingest(
            agency=req.agency,
            outcome=req.outcome,
            filed_after=filed_after,
            filed_before=filed_before,
            max_pages=req.max_pages,
            page_size=req.page_size,
            start_page=req.start_page,
        )
    except TangoError as exc:
        raise HTTPException(status_code=502, detail=f"Tango API error: {exc}")

    summary = run.to_summary()
    return IngestionRunResponse(**summary)


@router.get("/cases", response_model=list[ProtestCaseResponse])
async def list_cases(
    agency: str | None = Query(None, description="Filter by agency abbreviation (e.g. DHS, TSA)"),
    outcome: str | None = Query(None, description="Filter by outcome (sustained, denied, dismissed, etc.)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List canonical protest cases from the store."""
    if isinstance(_store, DatabaseProtestStore):
        cases = _store.list_cases(agency=agency, outcome=outcome, limit=limit, offset=offset)
    else:
        # Fallback for in-memory store
        cases = list(_store.cases.values())
        if agency:
            cases = [c for c in cases if c.agency_abbreviation == agency.upper()]
        if outcome:
            try:
                target = ProtestOutcome(outcome.lower())
                cases = [c for c in cases if c.outcome == target]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid outcome: {outcome}")
        cases.sort(key=lambda c: c.filed_date or date.min, reverse=True)
        cases = cases[offset:offset + limit]

    return [_case_to_response(c) for c in cases]


@router.get("/cases/{case_number}", response_model=ProtestCaseResponse)
async def get_case(case_number: str):
    """Get a single protest case by GAO B-number."""
    case = _store.get_case(case_number)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_number} not found")
    return _case_to_response(case)


@router.get("/stats", response_model=StoreStatsResponse)
async def get_stats():
    """Get summary statistics for the protest data store."""
    summary = _store.summary()
    store_type = "postgresql" if isinstance(_store, DatabaseProtestStore) else "in-memory"
    return StoreStatsResponse(
        tango_connected=_client is not None,
        store_type=store_type,
        **summary,
    )


@router.get("/runs", response_model=list[IngestionRunResponse])
async def list_runs(limit: int = Query(20, ge=1, le=100)):
    """List recent ingestion runs."""
    if isinstance(_store, DatabaseProtestStore):
        runs = _store.list_runs(limit=limit)
        return [IngestionRunResponse(**r.to_summary()) for r in runs]
    else:
        runs = _store.ingestion_runs[-limit:]
        runs.reverse()
        return [IngestionRunResponse(**r.to_summary()) for r in runs]


@router.post("/ingest-single/{tango_id}", response_model=ProtestCaseResponse)
async def ingest_single(tango_id: str):
    """Fetch and normalize a single protest record by Tango case_id."""
    if not _service:
        raise HTTPException(status_code=503, detail="Tango API key not configured.")

    case = _service.ingest_single(tango_id)
    if not case:
        raise HTTPException(status_code=502, detail=f"Failed to ingest record {tango_id}")
    return _case_to_response(case)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _case_to_response(case) -> ProtestCaseResponse:
    return ProtestCaseResponse(
        id=case.id,
        case_number=case.case_number,
        outcome=case.outcome.value if hasattr(case.outcome, "value") else str(case.outcome),
        agency=case.agency,
        agency_abbreviation=case.agency_abbreviation,
        protester=case.protester,
        solicitation_number=case.solicitation_number,
        title=case.title,
        value=case.value,
        filed_date=case.filed_date.isoformat() if case.filed_date else None,
        decision_date=case.decision_date.isoformat() if case.decision_date else None,
        fiscal_year=case.fiscal_year,
        decision_url=case.decision_url,
        provider_name=case.provider_name,
        provider_id=case.provider_id,
        grounds_count=len(case.grounds),
        signals_count=len(case.signals),
    )
