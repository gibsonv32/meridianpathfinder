"""
Protest Analytics — Statistical Baselines (Phase 2)
====================================================
Computes real probabilities from the historical protest database to feed
the protest risk scoring engine with data-driven baselines instead of
static assumptions.

Queries run against PostgreSQL via the sync engine (same as repository.py).

Key metrics:
  - Sustain rate by agency
  - Sustain rate by ground type
  - Outcome distribution by contract value bracket
  - Filing trends by fiscal year
  - Protester frequency (repeat filers)
  - Agency risk ranking (composite score)

These baselines replace the hardcoded weights in the 10-factor risk engine
with empirical probabilities, giving COs evidence-based risk assessments.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import func, case, cast, Float, Integer, select, and_
from sqlalchemy.orm import Session

from backend.database.models.protests import (
    ProtestCaseRecord,
    ProtestGroundRecord,
    ProtestSignalRecord,
)
from backend.phase2.protest_data.repository import SyncSessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Value brackets for contract value analysis
# ---------------------------------------------------------------------------

VALUE_BRACKETS = [
    ("micro", 0, 15_000),
    ("simplified_low", 15_000, 250_000),
    ("simplified_high", 250_000, 350_000),
    ("below_5m", 350_000, 5_000_000),
    ("5m_to_50m", 5_000_000, 50_000_000),
    ("50m_to_100m", 50_000_000, 100_000_000),
    ("above_100m", 100_000_000, None),
]


# ---------------------------------------------------------------------------
# Data classes for results
# ---------------------------------------------------------------------------

@dataclass
class AgencyBaseline:
    agency: str
    total_protests: int
    sustained: int
    denied: int
    dismissed: int
    withdrawn: int
    corrective_action: int
    sustain_rate: float  # sustained / (sustained + denied) — cases reaching decision
    effectiveness_rate: float  # (sustained + corrective_action) / total
    avg_protests_per_year: float


@dataclass
class GroundBaseline:
    ground_type: str
    total_cited: int
    in_sustained_cases: int
    in_denied_cases: int
    sustain_rate: float  # how often cases citing this ground are sustained
    prevalence: float  # % of all protests citing this ground


@dataclass
class ValueBracketBaseline:
    bracket: str
    min_value: float
    max_value: float | None
    total_protests: int
    sustained: int
    sustain_rate: float
    effectiveness_rate: float


@dataclass
class FiscalYearTrend:
    fiscal_year: int
    total_filed: int
    sustained: int
    denied: int
    dismissed: int
    withdrawn: int
    sustain_rate: float


@dataclass
class RepeatProtester:
    name: str
    total_protests: int
    sustained: int
    sustain_rate: float
    agencies_protested: list[str]


@dataclass
class ProtestBaselines:
    """Complete statistical baselines computed from the protest database."""
    computed_at: str
    total_cases: int
    date_range: tuple[str | None, str | None]

    # Core baselines
    overall_sustain_rate: float
    overall_effectiveness_rate: float

    # Breakdowns
    by_agency: list[AgencyBaseline]
    by_ground: list[GroundBaseline]
    by_value_bracket: list[ValueBracketBaseline]
    by_fiscal_year: list[FiscalYearTrend]
    top_repeat_protesters: list[RepeatProtester]

    # Agency risk ranking (top 20 by composite risk)
    agency_risk_ranking: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Analytics Service
# ---------------------------------------------------------------------------

class ProtestAnalyticsService:
    """
    Computes statistical baselines from the protest database.
    All methods are synchronous (use sync PostgreSQL sessions).
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or SyncSessionLocal

    def _session(self) -> Session:
        return self._session_factory()

    def compute_all(self) -> ProtestBaselines:
        """Compute all baselines. Returns a complete ProtestBaselines object."""
        from datetime import datetime, timezone

        with self._session() as session:
            total = session.execute(
                select(func.count()).select_from(ProtestCaseRecord)
            ).scalar_one()

            date_range = session.execute(
                select(
                    func.min(ProtestCaseRecord.filed_date),
                    func.max(ProtestCaseRecord.filed_date),
                )
            ).one()

            overall = self._overall_rates(session)
            by_agency = self._by_agency(session)
            by_ground = self._by_ground(session, total)
            by_value = self._by_value_bracket(session)
            by_fy = self._by_fiscal_year(session)
            top_protesters = self._top_repeat_protesters(session)
            risk_ranking = self._agency_risk_ranking(by_agency)

        return ProtestBaselines(
            computed_at=datetime.now(timezone.utc).isoformat(),
            total_cases=total,
            date_range=(
                date_range[0].isoformat() if date_range[0] else None,
                date_range[1].isoformat() if date_range[1] else None,
            ),
            overall_sustain_rate=overall["sustain_rate"],
            overall_effectiveness_rate=overall["effectiveness_rate"],
            by_agency=by_agency,
            by_ground=by_ground,
            by_value_bracket=by_value,
            by_fiscal_year=by_fy,
            top_repeat_protesters=top_protesters,
            agency_risk_ranking=risk_ranking,
        )

    # --- Individual computations ---

    def _overall_rates(self, session: Session) -> dict[str, float]:
        row = session.execute(
            select(
                func.count().label("total"),
                func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                func.sum(case((ProtestCaseRecord.outcome == "corrective_action", 1), else_=0)).label("corrective"),
            )
        ).one()

        total = row.total or 0
        sustained = row.sustained or 0
        denied = row.denied or 0
        corrective = row.corrective or 0
        decided = sustained + denied

        return {
            "sustain_rate": sustained / decided if decided > 0 else 0.0,
            "effectiveness_rate": (sustained + corrective) / total if total > 0 else 0.0,
        }

    def _by_agency(self, session: Session) -> list[AgencyBaseline]:
        rows = session.execute(
            select(
                ProtestCaseRecord.agency_abbreviation,
                func.count().label("total"),
                func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                func.sum(case((ProtestCaseRecord.outcome == "dismissed", 1), else_=0)).label("dismissed"),
                func.sum(case((ProtestCaseRecord.outcome == "withdrawn", 1), else_=0)).label("withdrawn"),
                func.sum(case((ProtestCaseRecord.outcome == "corrective_action", 1), else_=0)).label("corrective"),
                func.count(func.distinct(ProtestCaseRecord.fiscal_year)).label("fy_count"),
            )
            .where(ProtestCaseRecord.agency_abbreviation != "")
            .group_by(ProtestCaseRecord.agency_abbreviation)
            .having(func.count() >= 5)  # minimum sample size
            .order_by(func.count().desc())
        ).all()

        results = []
        for r in rows:
            decided = (r.sustained or 0) + (r.denied or 0)
            total = r.total or 0
            fy_count = r.fy_count or 1
            results.append(AgencyBaseline(
                agency=r.agency_abbreviation,
                total_protests=total,
                sustained=r.sustained or 0,
                denied=r.denied or 0,
                dismissed=r.dismissed or 0,
                withdrawn=r.withdrawn or 0,
                corrective_action=r.corrective or 0,
                sustain_rate=((r.sustained or 0) / decided) if decided > 0 else 0.0,
                effectiveness_rate=((r.sustained or 0) + (r.corrective or 0)) / total if total > 0 else 0.0,
                avg_protests_per_year=total / fy_count,
            ))
        return results

    def _by_ground(self, session: Session, total_cases: int) -> list[GroundBaseline]:
        rows = session.execute(
            select(
                ProtestGroundRecord.ground_type,
                func.count(func.distinct(ProtestGroundRecord.case_id)).label("total_cited"),
                func.sum(case(
                    (ProtestCaseRecord.outcome == "sustained", 1), else_=0
                )).label("in_sustained"),
                func.sum(case(
                    (ProtestCaseRecord.outcome == "denied", 1), else_=0
                )).label("in_denied"),
            )
            .join(ProtestCaseRecord, ProtestGroundRecord.case_id == ProtestCaseRecord.id)
            .group_by(ProtestGroundRecord.ground_type)
            .order_by(func.count(func.distinct(ProtestGroundRecord.case_id)).desc())
        ).all()

        results = []
        for r in rows:
            cited = r.total_cited or 0
            in_sustained = r.in_sustained or 0
            in_denied = r.in_denied or 0
            decided = in_sustained + in_denied
            results.append(GroundBaseline(
                ground_type=r.ground_type,
                total_cited=cited,
                in_sustained_cases=in_sustained,
                in_denied_cases=in_denied,
                sustain_rate=in_sustained / decided if decided > 0 else 0.0,
                prevalence=cited / total_cases if total_cases > 0 else 0.0,
            ))
        return results

    def _by_value_bracket(self, session: Session) -> list[ValueBracketBaseline]:
        results = []
        for bracket_name, min_val, max_val in VALUE_BRACKETS:
            conditions = [ProtestCaseRecord.value.isnot(None)]
            if min_val is not None:
                conditions.append(ProtestCaseRecord.value >= min_val)
            if max_val is not None:
                conditions.append(ProtestCaseRecord.value < max_val)

            row = session.execute(
                select(
                    func.count().label("total"),
                    func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                    func.sum(case((ProtestCaseRecord.outcome == "corrective_action", 1), else_=0)).label("corrective"),
                    func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                ).where(and_(*conditions))
            ).one()

            total = row.total or 0
            sustained = row.sustained or 0
            denied = row.denied or 0
            corrective = row.corrective or 0
            decided = sustained + denied

            results.append(ValueBracketBaseline(
                bracket=bracket_name,
                min_value=min_val or 0,
                max_value=max_val,
                total_protests=total,
                sustained=sustained,
                sustain_rate=sustained / decided if decided > 0 else 0.0,
                effectiveness_rate=(sustained + corrective) / total if total > 0 else 0.0,
            ))
        return results

    def _by_fiscal_year(self, session: Session) -> list[FiscalYearTrend]:
        rows = session.execute(
            select(
                ProtestCaseRecord.fiscal_year,
                func.count().label("total"),
                func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                func.sum(case((ProtestCaseRecord.outcome == "dismissed", 1), else_=0)).label("dismissed"),
                func.sum(case((ProtestCaseRecord.outcome == "withdrawn", 1), else_=0)).label("withdrawn"),
            )
            .where(ProtestCaseRecord.fiscal_year.isnot(None))
            .group_by(ProtestCaseRecord.fiscal_year)
            .order_by(ProtestCaseRecord.fiscal_year)
        ).all()

        results = []
        for r in rows:
            sustained = r.sustained or 0
            denied = r.denied or 0
            decided = sustained + denied
            results.append(FiscalYearTrend(
                fiscal_year=r.fiscal_year,
                total_filed=r.total or 0,
                sustained=sustained,
                denied=denied,
                dismissed=r.dismissed or 0,
                withdrawn=r.withdrawn or 0,
                sustain_rate=sustained / decided if decided > 0 else 0.0,
            ))
        return results

    def _top_repeat_protesters(self, session: Session, limit: int = 25) -> list[RepeatProtester]:
        # Get protesters with most filings
        subq = (
            select(
                ProtestCaseRecord.protester,
                func.count().label("total"),
                func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
            )
            .where(ProtestCaseRecord.protester != "")
            .group_by(ProtestCaseRecord.protester)
            .having(func.count() >= 3)
            .order_by(func.count().desc())
            .limit(limit)
            .subquery()
        )

        rows = session.execute(select(subq)).all()

        results = []
        for r in rows:
            # Get agencies this protester has filed against
            agencies = session.execute(
                select(func.distinct(ProtestCaseRecord.agency_abbreviation))
                .where(
                    ProtestCaseRecord.protester == r.protester,
                    ProtestCaseRecord.agency_abbreviation != "",
                )
            ).scalars().all()

            total = r.total or 0
            sustained = r.sustained or 0
            decided_cases = session.execute(
                select(func.count()).select_from(ProtestCaseRecord).where(
                    ProtestCaseRecord.protester == r.protester,
                    ProtestCaseRecord.outcome.in_(["sustained", "denied"]),
                )
            ).scalar_one()

            results.append(RepeatProtester(
                name=r.protester,
                total_protests=total,
                sustained=sustained,
                sustain_rate=sustained / decided_cases if decided_cases > 0 else 0.0,
                agencies_protested=list(agencies),
            ))
        return results

    def _agency_risk_ranking(self, agency_baselines: list[AgencyBaseline]) -> list[dict[str, Any]]:
        """
        Composite risk score per agency. Higher = more protest risk for a CO.

        Score = weighted combination of:
          - Protest volume (30%): normalized protests per year
          - Sustain rate (40%): how often protests are sustained
          - Effectiveness rate (30%): sustained + corrective action
        """
        if not agency_baselines:
            return []

        # Normalize each factor to 0-1
        max_volume = max(a.avg_protests_per_year for a in agency_baselines) or 1
        max_sustain = max(a.sustain_rate for a in agency_baselines) or 1
        max_effectiveness = max(a.effectiveness_rate for a in agency_baselines) or 1

        rankings = []
        for a in agency_baselines:
            volume_score = a.avg_protests_per_year / max_volume
            sustain_score = a.sustain_rate / max_sustain
            effectiveness_score = a.effectiveness_rate / max_effectiveness

            composite = (
                0.30 * volume_score +
                0.40 * sustain_score +
                0.30 * effectiveness_score
            )

            rankings.append({
                "agency": a.agency,
                "composite_risk": round(composite, 4),
                "volume_score": round(volume_score, 4),
                "sustain_score": round(sustain_score, 4),
                "effectiveness_score": round(effectiveness_score, 4),
                "total_protests": a.total_protests,
                "sustain_rate": round(a.sustain_rate, 4),
                "sample_size": a.sustained + a.denied,
            })

        rankings.sort(key=lambda x: x["composite_risk"], reverse=True)
        return rankings[:20]

    # --- Convenience methods for the risk engine ---

    def get_agency_sustain_rate(self, agency_abbrev: str) -> float | None:
        """Quick lookup: sustain rate for a specific agency."""
        with self._session() as session:
            row = session.execute(
                select(
                    func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                    func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                ).where(ProtestCaseRecord.agency_abbreviation == agency_abbrev.upper())
            ).one()
            decided = (row.sustained or 0) + (row.denied or 0)
            if decided < 5:  # insufficient sample
                return None
            return (row.sustained or 0) / decided

    def get_ground_sustain_rate(self, ground_type: str) -> float | None:
        """Quick lookup: sustain rate for cases citing a specific ground type."""
        with self._session() as session:
            row = session.execute(
                select(
                    func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                    func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                )
                .select_from(ProtestGroundRecord)
                .join(ProtestCaseRecord, ProtestGroundRecord.case_id == ProtestCaseRecord.id)
                .where(ProtestGroundRecord.ground_type == ground_type)
            ).one()
            decided = (row.sustained or 0) + (row.denied or 0)
            if decided < 5:
                return None
            return (row.sustained or 0) / decided

    def get_protester_history(self, protester_name: str) -> dict[str, Any] | None:
        """Quick lookup: protest history for a specific contractor."""
        with self._session() as session:
            row = session.execute(
                select(
                    func.count().label("total"),
                    func.sum(case((ProtestCaseRecord.outcome == "sustained", 1), else_=0)).label("sustained"),
                    func.sum(case((ProtestCaseRecord.outcome == "denied", 1), else_=0)).label("denied"),
                ).where(ProtestCaseRecord.protester.ilike(f"%{protester_name}%"))
            ).one()
            total = row.total or 0
            if total == 0:
                return None
            return {
                "protester": protester_name,
                "total_protests": total,
                "sustained": row.sustained or 0,
                "denied": row.denied or 0,
                "is_repeat_filer": total >= 3,
            }
