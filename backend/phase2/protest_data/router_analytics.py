"""
Protest Analytics — FastAPI Router
===================================
Exposes statistical baselines computed from the protest database.
These endpoints power the CO dashboard risk indicators and the
protest risk engine's data-driven scoring.

Mounts at: /api/v1/phase2/protests/analytics/
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.phase2.protest_data.analytics import ProtestAnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["protest-analytics"])

_analytics = ProtestAnalyticsService()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AgencyBaselineResponse(BaseModel):
    agency: str
    total_protests: int
    sustained: int
    denied: int
    dismissed: int
    withdrawn: int
    corrective_action: int
    sustain_rate: float
    effectiveness_rate: float
    avg_protests_per_year: float


class GroundBaselineResponse(BaseModel):
    ground_type: str
    total_cited: int
    in_sustained_cases: int
    in_denied_cases: int
    sustain_rate: float
    prevalence: float


class FiscalYearTrendResponse(BaseModel):
    fiscal_year: int
    total_filed: int
    sustained: int
    denied: int
    dismissed: int
    withdrawn: int
    sustain_rate: float


class ValueBracketResponse(BaseModel):
    bracket: str
    min_value: float
    max_value: float | None
    total_protests: int
    sustained: int
    sustain_rate: float
    effectiveness_rate: float


class RepeatProtesterResponse(BaseModel):
    name: str
    total_protests: int
    sustained: int
    sustain_rate: float
    agencies_protested: list[str]


class AgencyRiskResponse(BaseModel):
    agency: str
    composite_risk: float
    volume_score: float
    sustain_score: float
    effectiveness_score: float
    total_protests: int
    sustain_rate: float
    sample_size: int


class FullBaselinesResponse(BaseModel):
    computed_at: str
    total_cases: int
    date_range: list[str | None]
    overall_sustain_rate: float
    overall_effectiveness_rate: float
    by_agency: list[AgencyBaselineResponse]
    by_ground: list[GroundBaselineResponse]
    by_value_bracket: list[ValueBracketResponse]
    by_fiscal_year: list[FiscalYearTrendResponse]
    top_repeat_protesters: list[RepeatProtesterResponse]
    agency_risk_ranking: list[AgencyRiskResponse]


class QuickLookupResponse(BaseModel):
    query: str
    result: dict[str, Any] | None
    sample_sufficient: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/baselines", response_model=FullBaselinesResponse)
async def compute_baselines():
    """
    Compute full statistical baselines from the protest database.
    Returns sustain rates by agency, ground type, value bracket, fiscal year,
    plus repeat protesters and agency risk rankings.

    Note: This queries the full database and may take 1-2 seconds on large datasets.
    """
    try:
        baselines = _analytics.compute_all()
    except Exception as exc:
        logger.error("Failed to compute baselines: %s", exc)
        raise HTTPException(status_code=500, detail=f"Analytics computation failed: {exc}")

    return FullBaselinesResponse(
        computed_at=baselines.computed_at,
        total_cases=baselines.total_cases,
        date_range=list(baselines.date_range),
        overall_sustain_rate=baselines.overall_sustain_rate,
        overall_effectiveness_rate=baselines.overall_effectiveness_rate,
        by_agency=[AgencyBaselineResponse(**asdict(a)) for a in baselines.by_agency],
        by_ground=[GroundBaselineResponse(**asdict(g)) for g in baselines.by_ground],
        by_value_bracket=[ValueBracketResponse(**asdict(v)) for v in baselines.by_value_bracket],
        by_fiscal_year=[FiscalYearTrendResponse(**asdict(f)) for f in baselines.by_fiscal_year],
        top_repeat_protesters=[RepeatProtesterResponse(**asdict(p)) for p in baselines.top_repeat_protesters],
        agency_risk_ranking=[AgencyRiskResponse(**r) for r in baselines.agency_risk_ranking],
    )


@router.get("/agency/{agency_abbrev}", response_model=QuickLookupResponse)
async def agency_sustain_rate(agency_abbrev: str):
    """Quick lookup: sustain rate for a specific agency."""
    rate = _analytics.get_agency_sustain_rate(agency_abbrev)
    return QuickLookupResponse(
        query=f"agency:{agency_abbrev.upper()}",
        result={"sustain_rate": round(rate, 4)} if rate is not None else None,
        sample_sufficient=rate is not None,
    )


@router.get("/ground/{ground_type}", response_model=QuickLookupResponse)
async def ground_sustain_rate(ground_type: str):
    """Quick lookup: sustain rate for cases citing a specific ground type."""
    rate = _analytics.get_ground_sustain_rate(ground_type)
    return QuickLookupResponse(
        query=f"ground:{ground_type}",
        result={"sustain_rate": round(rate, 4)} if rate is not None else None,
        sample_sufficient=rate is not None,
    )


@router.get("/protester", response_model=QuickLookupResponse)
async def protester_history(name: str = Query(..., min_length=2, description="Protester name (partial match)")):
    """Quick lookup: protest history for a specific contractor."""
    result = _analytics.get_protester_history(name)
    return QuickLookupResponse(
        query=f"protester:{name}",
        result=result,
        sample_sufficient=result is not None,
    )
