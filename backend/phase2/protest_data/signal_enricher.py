"""
Protest Signal Enricher
========================
Derives risk signals from structured protest data (no decision text needed).
Runs as a batch job against all cases in PostgreSQL that lack signals.

Signal sources (from structured fields only):
  1. Agency risk signal — based on agency-specific sustain rates
  2. Repeat protester signal — contractor with history of filing
  3. Solicitation pattern signal — same solicitation protested multiple times
  4. Temporal clustering signal — multiple protests in short window
  5. High-value signal — contract value above thresholds
  6. Outcome-based severity — case outcome determines signal weight

These enrich the protest risk engine (PF01-PF10) without needing
GAO decision text. Ground-level signals will be added when decision
text becomes available (requires residential IP or browser automation
to bypass GAO WAF).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, and_, text
from sqlalchemy.orm import Session

from backend.database.models.protests import (
    ProtestCaseRecord,
    ProtestGroundRecord,
    ProtestSignalRecord,
)
from backend.phase2.protest_data.repository import SyncSessionLocal

logger = logging.getLogger(__name__)


class ProtestSignalEnricher:
    """
    Batch-enriches protest cases with derived risk signals.
    Works purely from structured data — no decision text required.
    """

    def __init__(self, session_factory=None):
        self._sf = session_factory or SyncSessionLocal

    def enrich_all(self, batch_size: int = 500) -> dict[str, Any]:
        """
        Enrich all cases that have zero signals.
        Returns summary stats.
        """
        stats = {
            "cases_processed": 0,
            "signals_created": 0,
            "errors": 0,
        }

        # Pre-compute lookup tables
        agency_rates = self._compute_agency_sustain_rates()
        protester_counts = self._compute_protester_counts()
        solicitation_counts = self._compute_solicitation_protest_counts()

        with self._sf() as session:
            # Find cases with no signals
            case_ids = session.execute(
                select(ProtestCaseRecord.id)
                .outerjoin(ProtestSignalRecord, ProtestCaseRecord.id == ProtestSignalRecord.case_id)
                .where(ProtestSignalRecord.id.is_(None))
            ).scalars().all()

            logger.info("Found %d cases needing signal enrichment", len(case_ids))

            # Process in batches
            for i in range(0, len(case_ids), batch_size):
                batch_ids = case_ids[i:i + batch_size]
                cases = session.execute(
                    select(ProtestCaseRecord).where(ProtestCaseRecord.id.in_(batch_ids))
                ).scalars().all()

                for case in cases:
                    try:
                        signals = self._derive_signals(
                            case, agency_rates, protester_counts, solicitation_counts
                        )
                        for sig in signals:
                            session.add(sig)
                        stats["signals_created"] += len(signals)
                        stats["cases_processed"] += 1
                    except Exception as e:
                        logger.error("Error enriching case %s: %s", case.case_number, e)
                        stats["errors"] += 1

                session.commit()
                logger.info(
                    "Batch %d-%d: %d signals created",
                    i, min(i + batch_size, len(case_ids)), stats["signals_created"]
                )

        return stats

    def _derive_signals(
        self,
        case: ProtestCaseRecord,
        agency_rates: dict[str, float],
        protester_counts: dict[str, int],
        solicitation_counts: dict[str, int],
    ) -> list[ProtestSignalRecord]:
        """Derive all applicable signals for a single case."""
        signals = []
        from uuid import uuid4

        # Base severity from outcome
        severity, confidence = self._outcome_severity(case.outcome)

        # --- PF01: Agency risk signal ---
        agency_rate = agency_rates.get(case.agency_abbreviation)
        if agency_rate is not None and agency_rate > 0.05:
            risk_level = (
                "high" if agency_rate > 0.15
                else "medium" if agency_rate > 0.08
                else "low"
            )
            signals.append(ProtestSignalRecord(
                id=str(uuid4()),
                case_id=case.id,
                signal_type="PF01",
                severity=risk_level,
                description=(
                    f"Agency {case.agency_abbreviation} has {agency_rate:.1%} sustain rate "
                    f"(above 5% baseline)"
                ),
                evidence_text=(
                    f"Historical sustain rate for {case.agency_abbreviation} protests"
                ),
                confidence=min(0.9, confidence + 0.1),
            ))

        # --- PF03: Repeat protester signal ---
        protest_count = protester_counts.get(case.protester, 0)
        if protest_count >= 3:
            signals.append(ProtestSignalRecord(
                id=str(uuid4()),
                case_id=case.id,
                signal_type="PF03",
                severity="medium" if protest_count >= 10 else "low",
                description=(
                    f"Protester '{case.protester}' has filed {protest_count} protests "
                    f"({'serial filer' if protest_count >= 10 else 'repeat filer'})"
                ),
                evidence_text=f"{protest_count} total protests by {case.protester}",
                confidence=0.95,  # factual, high confidence
            ))

        # --- PF04: Solicitation clustering signal ---
        if case.solicitation_number:
            sol_count = solicitation_counts.get(case.solicitation_number, 0)
            if sol_count >= 2:
                signals.append(ProtestSignalRecord(
                    id=str(uuid4()),
                    case_id=case.id,
                    signal_type="PF04",
                    severity="high" if sol_count >= 4 else "medium",
                    description=(
                        f"Solicitation {case.solicitation_number} has {sol_count} protests "
                        f"(multi-protest solicitation)"
                    ),
                    evidence_text=(
                        f"{sol_count} protests filed against {case.solicitation_number}"
                    ),
                    confidence=0.95,
                ))

        # --- PF09: High-value signal ---
        if case.value and case.value > 0:
            if case.value >= 100_000_000:
                signals.append(ProtestSignalRecord(
                    id=str(uuid4()),
                    case_id=case.id,
                    signal_type="PF09",
                    severity="high",
                    description=f"High-value procurement (${case.value:,.0f})",
                    evidence_text=f"Contract value ${case.value:,.0f} exceeds $100M SSAC threshold",
                    confidence=0.95,
                ))
            elif case.value >= 50_000_000:
                signals.append(ProtestSignalRecord(
                    id=str(uuid4()),
                    case_id=case.id,
                    signal_type="PF09",
                    severity="medium",
                    description=f"Major procurement (${case.value:,.0f})",
                    evidence_text=f"Contract value ${case.value:,.0f} exceeds $50M threshold",
                    confidence=0.95,
                ))

        # --- PF10: Outcome severity signal ---
        if case.outcome in ("sustained", "corrective_action"):
            signals.append(ProtestSignalRecord(
                id=str(uuid4()),
                case_id=case.id,
                signal_type="PF10",
                severity=severity,
                description=(
                    f"Protest {case.outcome} — {case.case_number} "
                    f"against {case.agency_abbreviation or 'unknown agency'}"
                ),
                evidence_text=f"GAO {case.case_number}: {case.title or 'No title'}",
                confidence=confidence,
            ))

        return signals

    def _outcome_severity(self, outcome: str) -> tuple[str, float]:
        """Map outcome to severity and confidence."""
        mapping = {
            "sustained": ("high", 0.95),
            "corrective_action": ("high", 0.85),
            "mixed": ("medium", 0.75),
            "denied": ("low", 0.90),
            "dismissed": ("low", 0.85),
            "withdrawn": ("low", 0.70),
            "unknown": ("low", 0.50),
        }
        return mapping.get(outcome, ("low", 0.50))

    def _compute_agency_sustain_rates(self) -> dict[str, float]:
        """Pre-compute sustain rate per agency."""
        with self._sf() as session:
            rows = session.execute(text("""
                SELECT 
                    agency_abbreviation,
                    SUM(CASE WHEN outcome = 'sustained' THEN 1 ELSE 0 END)::float /
                    NULLIF(SUM(CASE WHEN outcome IN ('sustained', 'denied') THEN 1 ELSE 0 END), 0) as rate
                FROM protest_cases
                WHERE agency_abbreviation != ''
                GROUP BY agency_abbreviation
                HAVING SUM(CASE WHEN outcome IN ('sustained', 'denied') THEN 1 ELSE 0 END) >= 5
            """)).all()
            return {r[0]: r[1] for r in rows if r[1] is not None}

    def _compute_protester_counts(self) -> dict[str, int]:
        """Pre-compute protest count per protester."""
        with self._sf() as session:
            rows = session.execute(text("""
                SELECT protester, COUNT(*) as cnt
                FROM protest_cases
                WHERE protester != ''
                GROUP BY protester
                HAVING COUNT(*) >= 3
            """)).all()
            return {r[0]: r[1] for r in rows}

    def _compute_solicitation_protest_counts(self) -> dict[str, int]:
        """Pre-compute protest count per solicitation number."""
        with self._sf() as session:
            rows = session.execute(text("""
                SELECT solicitation_number, COUNT(*) as cnt
                FROM protest_cases
                WHERE solicitation_number != ''
                GROUP BY solicitation_number
                HAVING COUNT(*) >= 2
            """)).all()
            return {r[0]: r[1] for r in rows}
