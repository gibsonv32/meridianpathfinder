"""
Tango/SAM.gov Opportunities API Router
=======================================
FastAPI endpoints for federal contract opportunity search, listing,
ingestion, and analytics.

Dual-source architecture:
  - SAM.gov = primary (richer data, free, 1,000 records/request)
  - Tango = fallback (when SAM is unavailable or for protest cross-ref)

Endpoints:
    GET  /health              — Source connectivity check
    GET  /search              — Search opportunities (SAM primary, Tango fallback)
    GET  /list                — List from DB with filters
    GET  /by-id/{opp_id}      — Get opportunity by ID
    GET  /by-solicitation     — Find by solicitation number
    GET  /stats               — Summary statistics
    POST /ingest              — Trigger ingestion (SAM primary)
    POST /ingest/tango        — Trigger ingestion from Tango
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..tango_common import (
    TangoConfig,
    TangoError,
    TangoAuthError,
    TangoNotFoundError,
    TangoRateLimitError,
)
from .client import TangoOpportunityClient
from .sam_client import SAMGovOpportunityClient
from .repository import OpportunityStore, SyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

# ---------------------------------------------------------------------------
# Shared singletons (lazy init)
# ---------------------------------------------------------------------------

_tango_client: TangoOpportunityClient | None = None
_sam_client: SAMGovOpportunityClient | None = None
_store: OpportunityStore | None = None
_store_available: bool | None = None


def _get_tango_client() -> TangoOpportunityClient:
    global _tango_client
    if _tango_client is None:
        _tango_client = TangoOpportunityClient(TangoConfig.from_env())
    return _tango_client


def _get_sam_client() -> SAMGovOpportunityClient:
    global _sam_client
    if _sam_client is None:
        _sam_client = SAMGovOpportunityClient()
    return _sam_client


def _get_store() -> OpportunityStore | None:
    global _store, _store_available
    if _store_available is False:
        return None
    if _store is None:
        try:
            _store = OpportunityStore()
            _store.create_tables()
            _store_available = True
            logger.info("OpportunityStore connected to PostgreSQL")
        except Exception as exc:
            logger.warning("OpportunityStore unavailable: %s", exc)
            _store_available = False
            return None
    return _store


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    """Trigger opportunity ingestion."""
    max_pages: int = Field(default=10, ge=1, le=4000)
    start_page: int = Field(default=1, ge=1, le=4000)
    search: Optional[str] = Field(default=None, description="Optional search filter")


class SAMIngestRequest(BaseModel):
    """Trigger SAM.gov opportunity ingestion."""
    days_back: int = Field(default=30, ge=1, le=180, description="Days to look back (ignored if posted_from/posted_to set)")
    limit: int = Field(default=1000, ge=1, le=1000, description="Records per request")
    offset: int = Field(default=0, ge=0, description="Starting offset")
    notice_types: str = Field(default="o,p,k,r,s,a", description="SAM ptype codes")
    naics: Optional[str] = Field(default=None, description="NAICS code filter")
    department: Optional[str] = Field(default=None, description="Department name filter")
    keyword: Optional[str] = Field(default=None, description="Title keyword filter")
    posted_from: Optional[str] = Field(default=None, description="Start date MM/DD/YYYY (overrides days_back)")
    posted_to: Optional[str] = Field(default=None, description="End date MM/DD/YYYY (overrides days_back)")


class OpportunitySummaryResponse(BaseModel):
    """Compact opportunity for list/search responses."""
    opportunity_id: str
    title: str
    solicitation_number: str
    active: bool
    is_open: bool
    is_awarded: bool
    award_number: Optional[str]
    first_notice_date: Optional[str]
    last_notice_date: Optional[str]
    response_deadline: Optional[str]
    naics_code: str
    psc_code: str
    set_aside: str
    notice_type: str
    agency: str
    agency_name: str
    department: str
    office: str
    location: str
    sam_url: str
    notices_count: int
    attachments_count: int


class SearchResponse(BaseModel):
    """Paginated search response."""
    query: str
    total_count: int
    page: int
    page_size: int
    has_next: bool
    source: str  # "sam.gov", "tango_api", or "postgresql"
    results: list[OpportunitySummaryResponse]


class HealthResponse(BaseModel):
    """Health check response."""
    sam_gov_reachable: bool
    sam_gov_api_key_configured: bool
    tango_reachable: bool
    tango_api_key_configured: bool
    db_available: bool
    db_record_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def opportunities_health():
    """Check SAM.gov, Tango, and DB connectivity."""
    sam = _get_sam_client()
    sam_key = bool(sam.api_key)
    sam_reachable = False
    if sam_key:
        try:
            sam_reachable = sam.health_check()
        except Exception:
            pass

    tango = _get_tango_client()
    tango_key = bool(tango._config.api_key)
    tango_reachable = False
    if tango_key:
        try:
            tango_reachable = tango.health_check()
        except Exception:
            pass

    store = _get_store()
    db_count = 0
    if store:
        try:
            stats = store.summary()
            db_count = stats.get("total", 0)
        except Exception:
            pass

    return HealthResponse(
        sam_gov_reachable=sam_reachable,
        sam_gov_api_key_configured=sam_key,
        tango_reachable=tango_reachable,
        tango_api_key_configured=tango_key,
        db_available=store is not None,
        db_record_count=db_count,
    )


@router.get("/search", response_model=SearchResponse)
def search_opportunities(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    source: str = Query("auto", description="Source: auto (SAM→Tango), sam, tango, db"),
    days_back: int = Query(180, ge=1, le=180, description="Days to look back (SAM only)"),
):
    """
    Search opportunities by keyword.

    Default (source=auto): tries SAM.gov first (richer data), falls back to
    Tango if SAM fails, falls back to DB if both fail.
    """
    # DB path
    if source == "db":
        store = _get_store()
        if not store:
            raise HTTPException(status_code=503, detail="Database not available")
        results = store.search(q, limit=page_size)
        return SearchResponse(
            query=q, total_count=len(results), page=1, page_size=page_size,
            has_next=False, source="postgresql",
            results=[OpportunitySummaryResponse(**o.to_summary()) for o in results],
        )

    # SAM path
    if source in ("auto", "sam"):
        sam = _get_sam_client()
        if sam.api_key:
            try:
                offset = (page - 1) * page_size
                result = sam.search(q, days_back=days_back, limit=page_size, offset=offset)
                # Persist
                _persist_batch(result.opportunities)
                return SearchResponse(
                    query=q, total_count=result.total_count, page=page,
                    page_size=page_size, has_next=result.has_next, source="sam.gov",
                    results=[OpportunitySummaryResponse(**o.to_summary()) for o in result.opportunities],
                )
            except Exception as exc:
                logger.warning("SAM.gov search failed: %s", exc)
                if source == "sam":
                    raise HTTPException(status_code=502, detail=f"SAM.gov error: {exc}")

    # Tango path (fallback or explicit)
    if source in ("auto", "tango"):
        tango = _get_tango_client()
        try:
            result = tango.search_opportunities(q, page=page, page_size=min(page_size, 10))
            _persist_batch(result.opportunities)
            return SearchResponse(
                query=q, total_count=result.total_count, page=result.page,
                page_size=result.page_size, has_next=result.has_next, source="tango_api",
                results=[OpportunitySummaryResponse(**o.to_summary()) for o in result.opportunities],
            )
        except TangoAuthError:
            raise HTTPException(status_code=503, detail="Tango API authentication failed")
        except TangoRateLimitError:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        except TangoError as exc:
            raise HTTPException(status_code=502, detail=f"Tango error: {exc}")

    raise HTTPException(status_code=503, detail="No data source available")


@router.get("/list", response_model=SearchResponse)
def list_opportunities(
    agency: Optional[str] = Query(None, description="Filter by agency abbreviation"),
    active_only: bool = Query(False, description="Only active opportunities"),
    set_aside: Optional[str] = Query(None, description="Set-aside code filter"),
    naics: Optional[str] = Query(None, description="NAICS code filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List opportunities from PostgreSQL with filters."""
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    results = store.list_opportunities(
        agency=agency, active_only=active_only, set_aside=set_aside,
        naics=naics, limit=limit, offset=offset,
    )
    return SearchResponse(
        query=f"agency={agency or 'all'} active={active_only} set_aside={set_aside or 'all'} naics={naics or 'all'}",
        total_count=len(results), page=1, page_size=limit,
        has_next=len(results) == limit, source="postgresql",
        results=[OpportunitySummaryResponse(**o.to_summary()) for o in results],
    )


@router.get("/by-id/{opportunity_id}")
def get_opportunity_by_id(opportunity_id: str):
    """Get opportunity by ID. Checks DB first."""
    store = _get_store()
    if store:
        opp = store.get(opportunity_id)
        if opp:
            return {"source": "postgresql", **opp.to_summary()}

    # Try Tango API
    tango = _get_tango_client()
    try:
        opp = tango.get_opportunity(opportunity_id)
        if store:
            try:
                store.upsert(opp)
            except Exception:
                pass
        return {"source": "tango_api", **opp.to_summary()}
    except TangoNotFoundError:
        raise HTTPException(status_code=404, detail=f"Opportunity not found: {opportunity_id}")
    except TangoError as exc:
        raise HTTPException(status_code=502, detail=f"API error: {exc}")


@router.get("/by-solicitation")
def get_by_solicitation(
    number: str = Query(..., min_length=2, description="Solicitation number"),
):
    """Find opportunities by solicitation number from local DB."""
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    results = store.get_by_solicitation(number)
    if not results:
        # Try SAM.gov live search
        sam = _get_sam_client()
        if sam.api_key:
            try:
                result = sam.search(number, days_back=180, limit=10)
                _persist_batch(result.opportunities)
                matched = [o for o in result.opportunities if o.solicitation_number == number]
                if matched:
                    return {
                        "solicitation_number": number,
                        "count": len(matched),
                        "source": "sam.gov",
                        "results": [o.to_summary() for o in matched],
                    }
            except Exception:
                pass
        raise HTTPException(status_code=404, detail=f"No opportunities found: {number}")

    return {
        "solicitation_number": number,
        "count": len(results),
        "source": "postgresql",
        "results": [o.to_summary() for o in results],
    }


@router.get("/stats")
def opportunity_stats():
    """Summary statistics from the opportunity store."""
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")
    return store.summary()


@router.post("/ingest")
def ingest_from_sam(request: SAMIngestRequest):
    """
    Ingest opportunities from SAM.gov into PostgreSQL.

    At 1,000 records/request, a single call can ingest an entire month
    of opportunities. For larger backfills, increase offset.
    """
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    sam = _get_sam_client()
    if not sam.api_key:
        raise HTTPException(status_code=503, detail="SAM_GOV_API_KEY not configured")

    started_at = datetime.now(timezone.utc)
    total_new = 0
    total_updated = 0
    errors: list[str] = []
    pages_fetched = 0

    try:
        opps, total_count, has_next = sam.fetch_page(
            days_back=request.days_back,
            limit=request.limit,
            offset=request.offset,
            notice_types=request.notice_types,
            naics=request.naics,
            department=request.department,
            keyword=request.keyword,
            posted_from_override=request.posted_from,
            posted_to_override=request.posted_to,
        )
        pages_fetched = 1

        if opps:
            new, updated = store.upsert_batch(opps)
            total_new = new
            total_updated = updated

    except Exception as exc:
        errors.append(str(exc))

    run_id = store.save_run(
        started_at=started_at,
        pages_fetched=pages_fetched,
        records_upserted=total_new + total_updated,
        records_failed=0,
        search_query=request.keyword,
        parameters={
            "source": "sam.gov",
            "days_back": request.days_back,
            "posted_from": request.posted_from,
            "posted_to": request.posted_to,
            "limit": request.limit,
            "offset": request.offset,
            "notice_types": request.notice_types,
            "naics": request.naics,
            "department": request.department,
        },
        errors=errors if errors else None,
    )

    return {
        "run_id": run_id,
        "source": "sam.gov",
        "pages_fetched": pages_fetched,
        "records_available": total_count if pages_fetched > 0 else 0,
        "new_records": total_new,
        "updated_records": total_updated,
        "has_next": has_next if pages_fetched > 0 else False,
        "next_offset": request.offset + request.limit if has_next else None,
        "errors": errors,
        "store_stats": store.summary(),
    }


@router.post("/ingest/tango")
def ingest_from_tango(request: IngestRequest):
    """
    Trigger ingestion from Tango API (fallback/supplement).

    Use POST /ingest for SAM.gov (primary, richer data).
    """
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    tango = _get_tango_client()
    started_at = datetime.now(timezone.utc)
    total_new = 0
    total_updated = 0
    total_failed = 0
    pages_fetched = 0
    errors: list[str] = []

    for page_num in range(request.start_page, request.start_page + request.max_pages):
        try:
            opps, total_count, has_next = tango.fetch_page(
                page=page_num, page_size=10, search=request.search
            )
            pages_fetched += 1

            if not opps:
                break

            new, updated = store.upsert_batch(opps)
            total_new += new
            total_updated += updated

            if not has_next:
                break

        except TangoRateLimitError:
            errors.append(f"Rate limited at page {page_num}")
            break
        except TangoError as exc:
            errors.append(f"Page {page_num}: {exc}")
            total_failed += 1
            if total_failed > 5:
                break

    run_id = store.save_run(
        started_at=started_at,
        pages_fetched=pages_fetched,
        records_upserted=total_new + total_updated,
        records_failed=total_failed,
        search_query=request.search,
        parameters={"source": "tango", "start_page": request.start_page, "max_pages": request.max_pages},
        errors=errors if errors else None,
    )

    return {
        "run_id": run_id,
        "source": "tango",
        "pages_fetched": pages_fetched,
        "new_records": total_new,
        "updated_records": total_updated,
        "failed": total_failed,
        "errors": errors,
        "store_stats": store.summary(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _persist_batch(opps: list) -> None:
    """Opportunistically persist a batch of opportunities."""
    store = _get_store()
    if store and opps:
        try:
            new, updated = store.upsert_batch(opps)
            if new > 0:
                logger.info("Persist: %d new, %d updated", new, updated)
        except Exception as exc:
            logger.warning("Failed to persist: %s", exc)


# ---------------------------------------------------------------------------
# Cross-reference: Protests <-> Opportunities
# ---------------------------------------------------------------------------

@router.get("/cross-ref/by-solicitation")
def cross_ref_by_solicitation(
    solicitation: str = Query(..., description="Solicitation number"),
):
    """
    Return both opportunity details AND protest history for a solicitation.
    """
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    from sqlalchemy import text

    with SyncSessionLocal() as session:
        opp_rows = session.execute(
            text("""
                SELECT opportunity_id, title, solicitation_number, active,
                       naics_code, psc_code, set_aside_code, set_aside_name,
                       notice_type_name, agency_abbreviation, agency_name,
                       department_name, office_name,
                       pop_city, pop_state, pop_country,
                       first_notice_date, last_notice_date, response_deadline,
                       sam_url
                FROM opportunities
                WHERE solicitation_number = :sol
                ORDER BY last_notice_date DESC NULLS LAST
                LIMIT 5
            """),
            {"sol": solicitation},
        ).fetchall()

        protest_rows = session.execute(
            text("""
                SELECT case_number, protester, outcome, agency_abbreviation,
                       filed_date, decision_date, value, title, decision_url
                FROM protest_cases
                WHERE solicitation_number = :sol
                ORDER BY filed_date DESC
            """),
            {"sol": solicitation},
        ).fetchall()

    opp_cols = [
        "opportunity_id", "title", "solicitation_number", "active",
        "naics_code", "psc_code", "set_aside_code", "set_aside_name",
        "notice_type_name", "agency_abbreviation", "agency_name",
        "department_name", "office_name",
        "pop_city", "pop_state", "pop_country",
        "first_notice_date", "last_notice_date", "response_deadline",
        "sam_url",
    ]
    protest_cols = [
        "case_number", "protester", "outcome", "agency_abbreviation",
        "filed_date", "decision_date", "value", "title", "decision_url",
    ]

    return {
        "solicitation_number": solicitation,
        "opportunities": [dict(zip(opp_cols, [str(v) if v is not None else None for v in r])) for r in opp_rows],
        "protests": [dict(zip(protest_cols, [str(v) if v is not None else None for v in r])) for r in protest_rows],
        "protest_count": len(protest_rows),
        "has_sustained": any(r[2] == "sustained" for r in protest_rows),
        "has_opportunity_data": len(opp_rows) > 0,
    }


@router.get("/cross-ref/enrich-protests")
def enrich_protests_with_opportunities(
    agency: str | None = Query(None, description="Filter by agency abbreviation"),
    outcome: str | None = Query(None, description="Filter by outcome"),
    year: int | None = Query(None, description="Filter by filing year"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Return protests enriched with opportunity data (NAICS, set-aside, description).
    Only returns protests that have a matching opportunity.
    """
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    from sqlalchemy import text

    where_clauses = []
    params: dict = {"lim": limit, "off": offset}

    if agency:
        where_clauses.append("pc.agency_abbreviation = :agency")
        params["agency"] = agency
    if outcome:
        where_clauses.append("pc.outcome = :outcome")
        params["outcome"] = outcome
    if year:
        where_clauses.append("date_part('year', pc.filed_date) = :yr")
        params["yr"] = year

    where_sql = ("AND " + " AND ".join(where_clauses)) if where_clauses else ""

    with SyncSessionLocal() as session:
        rows = session.execute(
            text(f"""
                SELECT DISTINCT ON (pc.case_number)
                    pc.case_number, pc.protester, pc.outcome,
                    pc.agency_abbreviation as protest_agency,
                    pc.filed_date, pc.decision_date, pc.value,
                    pc.solicitation_number,
                    o.title as opp_title,
                    o.naics_code, o.psc_code,
                    o.set_aside_code, o.set_aside_name,
                    o.notice_type_name,
                    o.agency_abbreviation as opp_agency,
                    o.department_name,
                    o.pop_state,
                    o.sam_url
                FROM protest_cases pc
                JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                WHERE 1=1 {where_sql}
                ORDER BY pc.case_number, o.last_notice_date DESC NULLS LAST
                LIMIT :lim OFFSET :off
            """),
            params,
        ).fetchall()

        count_row = session.execute(
            text(f"""
                SELECT count(DISTINCT pc.case_number)
                FROM protest_cases pc
                JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                WHERE 1=1 {where_sql}
            """),
            params,
        ).fetchone()

    cols = [
        "case_number", "protester", "outcome", "protest_agency",
        "filed_date", "decision_date", "value", "solicitation_number",
        "opp_title", "naics_code", "psc_code",
        "set_aside_code", "set_aside_name", "notice_type_name",
        "opp_agency", "department_name", "pop_state", "sam_url",
    ]

    return {
        "total": count_row[0] if count_row else 0,
        "limit": limit,
        "offset": offset,
        "results": [dict(zip(cols, [str(v) if v is not None else None for v in r])) for r in rows],
    }


@router.get("/cross-ref/analytics")
def cross_ref_analytics():
    """
    Protest analytics enriched with opportunity data.
    """
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    from sqlalchemy import text

    with SyncSessionLocal() as session:
        coverage = session.execute(text("""
            SELECT
                (SELECT count(*) FROM protest_cases) as total_protests,
                (SELECT count(*) FROM opportunities) as total_opportunities,
                count(DISTINCT pc.case_number) as matched_protests,
                count(DISTINCT o.solicitation_number) as matched_solicitations
            FROM protest_cases pc
            JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
        """)).fetchone()

        by_naics = session.execute(text("""
            WITH matched AS (
                SELECT DISTINCT ON (pc.case_number)
                    pc.case_number, pc.outcome, o.naics_code
                FROM protest_cases pc
                JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                ORDER BY pc.case_number, o.last_notice_date DESC NULLS LAST
            )
            SELECT naics_code,
                   count(*) as protests,
                   count(CASE WHEN outcome='sustained' THEN 1 END) as sustained,
                   count(CASE WHEN outcome='denied' THEN 1 END) as denied,
                   count(CASE WHEN outcome='dismissed' THEN 1 END) as dismissed
            FROM matched
            WHERE naics_code IS NOT NULL
            GROUP BY naics_code ORDER BY protests DESC LIMIT 20
        """)).fetchall()

        by_set_aside = session.execute(text("""
            WITH matched AS (
                SELECT DISTINCT ON (pc.case_number)
                    pc.case_number, pc.outcome, o.set_aside_name
                FROM protest_cases pc
                JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                ORDER BY pc.case_number, o.last_notice_date DESC NULLS LAST
            )
            SELECT COALESCE(set_aside_name, 'Unknown') as set_aside,
                   count(*) as protests,
                   count(CASE WHEN outcome='sustained' THEN 1 END) as sustained,
                   count(CASE WHEN outcome='denied' THEN 1 END) as denied,
                   count(CASE WHEN outcome='dismissed' THEN 1 END) as dismissed
            FROM matched
            GROUP BY set_aside_name ORDER BY protests DESC
        """)).fetchall()

        by_notice_type = session.execute(text("""
            WITH matched AS (
                SELECT DISTINCT ON (pc.case_number)
                    pc.case_number, pc.outcome, o.notice_type_name
                FROM protest_cases pc
                JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                ORDER BY pc.case_number, o.last_notice_date DESC NULLS LAST
            )
            SELECT COALESCE(notice_type_name, 'Unknown') as notice_type,
                   count(*) as protests,
                   count(CASE WHEN outcome='sustained' THEN 1 END) as sustained,
                   count(CASE WHEN outcome='denied' THEN 1 END) as denied
            FROM matched
            GROUP BY notice_type_name ORDER BY protests DESC
        """)).fetchall()

    return {
        "coverage": {
            "total_protests": coverage[0],
            "total_opportunities": coverage[1],
            "matched_protests": coverage[2],
            "matched_solicitations": coverage[3],
            "match_rate_pct": round(coverage[2] / max(coverage[0], 1) * 100, 1),
        },
        "by_naics": [
            {"naics": r[0], "protests": r[1], "sustained": r[2], "denied": r[3], "dismissed": r[4]}
            for r in by_naics
        ],
        "by_set_aside": [
            {"set_aside": r[0], "protests": r[1], "sustained": r[2], "denied": r[3], "dismissed": r[4]}
            for r in by_set_aside
        ],
        "by_notice_type": [
            {"notice_type": r[0], "protests": r[1], "sustained": r[2], "denied": r[3]}
            for r in by_notice_type
        ],
    }


@router.get("/cross-ref/protest-risk/{solicitation_number}")
def protest_risk_for_solicitation(solicitation_number: str):
    """
    Quick protest risk check for a solicitation.
    Returns prior protests + similar NAICS/set-aside benchmarks.
    """
    store = _get_store()
    if not store:
        raise HTTPException(status_code=503, detail="Database not available")

    from sqlalchemy import text

    with SyncSessionLocal() as session:
        direct = session.execute(
            text("""
                SELECT case_number, protester, outcome, filed_date, decision_date
                FROM protest_cases
                WHERE solicitation_number = :sol
                ORDER BY filed_date DESC
            """),
            {"sol": solicitation_number},
        ).fetchall()

        opp = session.execute(
            text("""
                SELECT naics_code, set_aside_code, agency_abbreviation
                FROM opportunities
                WHERE solicitation_number = :sol
                ORDER BY last_notice_date DESC NULLS LAST
                LIMIT 1
            """),
            {"sol": solicitation_number},
        ).fetchone()

        naics_stats = None
        set_aside_stats = None

        if opp and opp[0]:
            naics_stats = session.execute(
                text("""
                    WITH matched AS (
                        SELECT DISTINCT ON (pc.case_number) pc.outcome
                        FROM protest_cases pc
                        JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                        WHERE o.naics_code = :naics
                        ORDER BY pc.case_number, o.last_notice_date DESC NULLS LAST
                    )
                    SELECT count(*) as total,
                           count(CASE WHEN outcome='sustained' THEN 1 END) as sustained,
                           count(CASE WHEN outcome='denied' THEN 1 END) as denied
                    FROM matched
                """),
                {"naics": opp[0]},
            ).fetchone()

        if opp and opp[1]:
            set_aside_stats = session.execute(
                text("""
                    WITH matched AS (
                        SELECT DISTINCT ON (pc.case_number) pc.outcome
                        FROM protest_cases pc
                        JOIN opportunities o ON pc.solicitation_number = o.solicitation_number AND pc.solicitation_number IS NOT NULL AND pc.solicitation_number != ''
                        WHERE o.set_aside_code = :sa
                        ORDER BY pc.case_number, o.last_notice_date DESC NULLS LAST
                    )
                    SELECT count(*) as total,
                           count(CASE WHEN outcome='sustained' THEN 1 END) as sustained,
                           count(CASE WHEN outcome='denied' THEN 1 END) as denied
                    FROM matched
                """),
                {"sa": opp[1]},
            ).fetchone()

    risk_level = "LOW"
    if len(direct) > 0:
        risk_level = "HIGH" if any(r[2] == "sustained" for r in direct) else "MEDIUM"

    return {
        "solicitation_number": solicitation_number,
        "risk_level": risk_level,
        "direct_protests": [
            {"case": r[0], "protester": r[1], "outcome": r[2],
             "filed": str(r[3]) if r[3] else None,
             "decided": str(r[4]) if r[4] else None}
            for r in direct
        ],
        "opportunity": {
            "naics_code": opp[0] if opp else None,
            "set_aside_code": opp[1] if opp else None,
            "agency": opp[2] if opp else None,
        } if opp else None,
        "naics_benchmark": {
            "total_protests": naics_stats[0],
            "sustained": naics_stats[1],
            "denied": naics_stats[2],
            "sustain_rate_pct": round(naics_stats[1] / max(naics_stats[0], 1) * 100, 1),
        } if naics_stats else None,
        "set_aside_benchmark": {
            "total_protests": set_aside_stats[0],
            "sustained": set_aside_stats[1],
            "denied": set_aside_stats[2],
            "sustain_rate_pct": round(set_aside_stats[1] / max(set_aside_stats[0], 1) * 100, 1),
        } if set_aside_stats else None,
    }
