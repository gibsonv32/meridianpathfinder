"""
Canonical Protest Data Models
=============================
FedProcure-native data model for GAO bid protests.  Provider-agnostic —
all source records (Tango, future scrapers, manual entry) normalize into
these types before storage or analytics.

Tables / domain objects:
  ProtestCase       — one per GAO B-number
  ProtestGround     — protest ground / basis (many-to-one with case)
  ProtestEntity     — named party in the protest (protester, intervenor, agency)
  ProtestSignal     — derived risk signal extracted from a case for scoring
  IngestionRun      — audit record for each bulk ingest execution
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProtestOutcome(str, Enum):
    """Canonical outcome taxonomy — all providers map to these values."""
    SUSTAINED = "sustained"
    DENIED = "denied"
    DISMISSED = "dismissed"
    WITHDRAWN = "withdrawn"
    CORRECTIVE_ACTION = "corrective_action"  # agency took voluntary corrective action
    MIXED = "mixed"  # partial sustain
    UNKNOWN = "unknown"


class ProtestGroundType(str, Enum):
    """Canonical protest ground taxonomy aligned with GAO categories."""
    EVALUATION_ERROR = "evaluation_error"
    COST_PRICE_ANALYSIS = "cost_price_analysis"
    UNEQUAL_TREATMENT = "unequal_treatment"
    DISCUSSIONS_CLARIFICATIONS = "discussions_clarifications"
    SOLE_SOURCE_JA = "sole_source_ja"
    SMALL_BUSINESS_SET_ASIDE = "small_business_set_aside"
    ORGANIZATIONAL_CONFLICT = "organizational_conflict"
    SOLICITATION_DEFICIENCY = "solicitation_deficiency"
    BEST_VALUE_TRADEOFF = "best_value_tradeoff"
    PAST_PERFORMANCE = "past_performance"
    TECHNICAL_EVALUATION = "technical_evaluation"
    AWARDEE_RESPONSIBILITY = "awardee_responsibility"
    TIMELINESS = "timeliness"
    PROTECTIVE_ORDER = "protective_order"
    DEBRIEFING = "debriefing"
    OTHER = "other"


class EntityRole(str, Enum):
    PROTESTER = "protester"
    INTERVENOR = "intervenor"
    AGENCY = "agency"
    AWARDEE = "awardee"


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IngestionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # some records failed normalization


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

@dataclass
class ProtestCase:
    """
    Canonical protest case — one per GAO B-number.
    Source-agnostic; provider_id + provider_name trace back to the raw source.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    case_number: str = ""  # GAO B-number (e.g. B-421234)
    outcome: ProtestOutcome = ProtestOutcome.UNKNOWN
    agency: str = ""  # normalized agency name
    agency_abbreviation: str = ""  # e.g. DHS, DOD, VA
    protester: str = ""
    solicitation_number: str = ""
    title: str = ""
    value: float | None = None
    filed_date: date | None = None
    decision_date: date | None = None
    decision_url: str = ""
    fiscal_year: int | None = None

    # provenance
    provider_name: str = ""  # "tango", "manual", etc.
    provider_id: str = ""  # original record id from the provider
    raw_payload: dict[str, Any] = field(default_factory=dict)

    # relations (populated by normalization)
    grounds: list[ProtestGround] = field(default_factory=list)
    entities: list[ProtestEntity] = field(default_factory=list)
    signals: list[ProtestSignal] = field(default_factory=list)

    # metadata
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    normalized_at: datetime | None = None

    def __post_init__(self):
        if self.filed_date and not self.fiscal_year:
            # Federal FY starts Oct 1 of prior calendar year
            self.fiscal_year = (
                self.filed_date.year + 1
                if self.filed_date.month >= 10
                else self.filed_date.year
            )


@dataclass
class ProtestGround:
    """One ground / basis cited in a protest."""
    id: str = field(default_factory=lambda: str(uuid4()))
    case_id: str = ""
    ground_type: ProtestGroundType = ProtestGroundType.OTHER
    raw_text: str = ""  # original text from source
    sustained: bool = False  # was this specific ground sustained?


@dataclass
class ProtestEntity:
    """Named party in the protest."""
    id: str = field(default_factory=lambda: str(uuid4()))
    case_id: str = ""
    name: str = ""
    role: EntityRole = EntityRole.PROTESTER
    normalized_name: str = ""  # cleaned / canonical name


@dataclass
class ProtestSignal:
    """
    Derived risk signal extracted from a protest case.
    Used by ProtestRiskEngine to enrich scoring with historical evidence.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    case_id: str = ""
    signal_type: str = ""  # maps to ProtestRiskEngine factor_id (PF01-PF10)
    severity: SignalSeverity = SignalSeverity.LOW
    description: str = ""
    evidence_text: str = ""  # excerpt from decision or source
    confidence: float = 0.0  # 0.0–1.0


@dataclass
class IngestionRun:
    """
    Audit record for a single ingestion execution.
    Tracks success/failure counts, timing, and errors for observability.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    provider_name: str = ""
    status: IngestionStatus = IngestionStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    records_fetched: int = 0
    records_normalized: int = 0
    records_failed: int = 0
    errors: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)  # filter params used

    def complete(self, *, status: IngestionStatus | None = None) -> None:
        """Mark run as finished."""
        self.completed_at = datetime.utcnow()
        if status:
            self.status = status
        elif self.records_failed > 0 and self.records_normalized > 0:
            self.status = IngestionStatus.PARTIAL
        elif self.records_failed > 0:
            self.status = IngestionStatus.FAILED
        else:
            self.status = IngestionStatus.COMPLETED

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_summary(self) -> dict[str, Any]:
        return {
            "run_id": self.id,
            "provider": self.provider_name,
            "status": self.status.value,
            "fetched": self.records_fetched,
            "normalized": self.records_normalized,
            "failed": self.records_failed,
            "duration_s": self.duration_seconds,
            "error_count": len(self.errors),
        }
