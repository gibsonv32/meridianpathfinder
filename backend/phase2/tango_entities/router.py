"""
Tango Entities API Router
=========================
FastAPI endpoints for contractor/entity lookup.

Endpoints:
    GET  /health          — Tango entities API connectivity check
    GET  /search          — Search entities by name
    GET  /by-uei/{uei}    — Get entity by UEI
    POST /lookup-protester — Match a protester name to entity profiles
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..tango_common import (
    TangoConfig,
    TangoError,
    TangoAuthError,
    TangoNotFoundError,
    TangoRateLimitError,
)
from .client import TangoEntityClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entities", tags=["entities"])

# ---------------------------------------------------------------------------
# Shared client (lazy init)
# ---------------------------------------------------------------------------
_client: TangoEntityClient | None = None


def _get_client() -> TangoEntityClient:
    global _client
    if _client is None:
        _client = TangoEntityClient(TangoConfig.from_env())
    return _client


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ProtesterLookupRequest(BaseModel):
    """Request to look up a protester by name."""
    protester_name: str
    max_results: int = 5


class EntitySummary(BaseModel):
    """Compact entity representation for API responses."""
    uei: str
    name: str
    legal_name: str
    dba_name: str
    cage_code: str
    primary_naics: str
    location: str
    is_small_business: bool
    sb_categories: list[str]
    entity_url: str


class SearchResponse(BaseModel):
    """Paginated search response."""
    query: str
    total_count: int
    page: int
    page_size: int
    has_next: bool
    results: list[EntitySummary]


class HealthResponse(BaseModel):
    """Health check response."""
    tango_entities_reachable: bool
    api_key_configured: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def entities_health():
    """Check Tango entities API connectivity."""
    client = _get_client()
    key_present = bool(client._config.api_key)
    reachable = False
    if key_present:
        try:
            reachable = client.health_check()
        except Exception:
            pass
    return HealthResponse(
        tango_entities_reachable=reachable,
        api_key_configured=key_present,
    )


@router.get("/search", response_model=SearchResponse)
def search_entities(
    q: str = Query(..., min_length=2, description="Search query (entity name)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Search entities by name (legal name or DBA).

    Returns contractor profiles matching the query, with small-business
    classification and location data.
    """
    client = _get_client()
    try:
        result = client.search_entities(q, page=page, page_size=page_size)
    except TangoAuthError:
        raise HTTPException(status_code=503, detail="Tango API authentication failed")
    except TangoRateLimitError:
        raise HTTPException(status_code=429, detail="Tango API rate limit exceeded")
    except TangoError as exc:
        raise HTTPException(status_code=502, detail=f"Tango API error: {exc}")

    return SearchResponse(
        query=q,
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
        has_next=result.has_next,
        results=[EntitySummary(**p.to_summary()) for p in result.profiles],
    )


@router.get("/by-uei/{uei}")
def get_entity_by_uei(uei: str):
    """
    Get a single entity profile by UEI (Unique Entity Identifier).

    Returns full entity profile including business types, address,
    and small-business classification.
    """
    client = _get_client()
    try:
        profile = client.get_entity(uei)
    except TangoNotFoundError:
        raise HTTPException(status_code=404, detail=f"Entity not found: {uei}")
    except TangoAuthError:
        raise HTTPException(status_code=503, detail="Tango API authentication failed")
    except TangoRateLimitError:
        raise HTTPException(status_code=429, detail="Tango API rate limit exceeded")
    except TangoError as exc:
        raise HTTPException(status_code=502, detail=f"Tango API error: {exc}")

    return profile.to_summary()


@router.post("/lookup-protester")
def lookup_protester(request: ProtesterLookupRequest):
    """
    Match a protester name to entity profiles.

    Given a protester name from a GAO protest case, searches the Tango
    entities database for matching contractor profiles.  Returns matches
    with small-business status and location — feeds PF03 (contractor risk)
    in the protest risk scoring engine.

    This is structured evidence, not a definitive match.  The CO must
    verify identity before relying on the cross-reference.
    """
    client = _get_client()
    try:
        result = client.search_entities(
            request.protester_name,
            page=1,
            page_size=request.max_results,
        )
    except TangoAuthError:
        raise HTTPException(status_code=503, detail="Tango API authentication failed")
    except TangoRateLimitError:
        raise HTTPException(status_code=429, detail="Tango API rate limit exceeded")
    except TangoError as exc:
        raise HTTPException(status_code=502, detail=f"Tango API error: {exc}")

    return {
        "protester_name": request.protester_name,
        "matches_found": result.total_count,
        "results": [p.to_summary() for p in result.profiles],
        "evidence_tier": "structured_third_party",
        "note": "Entity match is probabilistic. CO must verify identity before use in official records.",
    }
