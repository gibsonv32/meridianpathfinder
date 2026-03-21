"""
Protest Data Normalization Service
==================================
Transforms raw provider records (TangoProtestRecord) into canonical
FedProcure protest models (ProtestCase, ProtestGround, ProtestEntity,
ProtestSignal).

Normalization layers:
  1. Outcome mapping     — provider-specific strings → ProtestOutcome enum
  2. Agency normalization — abbreviation lookup, spelling correction
  3. Ground taxonomy      — free-text grounds → ProtestGroundType enum
  4. Entity extraction    — party names → ProtestEntity with role
  5. Signal derivation    — map case characteristics to PF01-PF10 factors
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

from .models import (
    EntityRole,
    IngestionRun,
    ProtestCase,
    ProtestEntity,
    ProtestGround,
    ProtestGroundType,
    ProtestOutcome,
    ProtestSignal,
    SignalSeverity,
)
from .tango_client import TangoProtestRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outcome mapping
# ---------------------------------------------------------------------------

_OUTCOME_MAP: dict[str, ProtestOutcome] = {
    # Tango / GAO canonical values
    "sustained": ProtestOutcome.SUSTAINED,
    "denied": ProtestOutcome.DENIED,
    "dismissed": ProtestOutcome.DISMISSED,
    "withdrawn": ProtestOutcome.WITHDRAWN,
    "corrective action": ProtestOutcome.CORRECTIVE_ACTION,
    "corrective_action": ProtestOutcome.CORRECTIVE_ACTION,
    # Capitalized (Tango API uses title-case)
    "Sustained": ProtestOutcome.SUSTAINED,
    "Denied": ProtestOutcome.DENIED,
    "Dismissed": ProtestOutcome.DISMISSED,
    "Withdrawn": ProtestOutcome.WITHDRAWN,
    # Common variations
    "sustain": ProtestOutcome.SUSTAINED,
    "deny": ProtestOutcome.DENIED,
    "dismiss": ProtestOutcome.DISMISSED,
    "withdrawn before decision": ProtestOutcome.WITHDRAWN,
    "withdrawn - agency corrective action": ProtestOutcome.CORRECTIVE_ACTION,
    "mixed": ProtestOutcome.MIXED,
    "partially sustained": ProtestOutcome.MIXED,
    "partial": ProtestOutcome.MIXED,
}


def normalize_outcome(raw: str | None) -> ProtestOutcome:
    """Map a raw outcome string to the canonical enum."""
    if not raw:
        return ProtestOutcome.UNKNOWN
    key = raw.strip().lower()
    return _OUTCOME_MAP.get(key, ProtestOutcome.UNKNOWN)


# ---------------------------------------------------------------------------
# Agency normalization
# ---------------------------------------------------------------------------

_AGENCY_ABBREVS: dict[str, str] = {
    # --- Top-level departments ---
    "department of homeland security": "DHS",
    "dhs": "DHS",
    "department of defense": "DOD",
    "dod": "DOD",
    "department of the army": "DOD",
    "department of the navy": "DOD",
    "department of the air force": "DOD",
    "department of veterans affairs": "VA",
    "va": "VA",
    "general services administration": "GSA",
    "gsa": "GSA",
    "department of health and human services": "HHS",
    "hhs": "HHS",
    "department of justice": "DOJ",
    "doj": "DOJ",
    "department of energy": "DOE",
    "doe": "DOE",
    "department of state": "DOS",
    "dos": "DOS",
    "department of the interior": "DOI",
    "doi": "DOI",
    "department of agriculture": "USDA",
    "usda": "USDA",
    "department of labor": "DOL",
    "dol": "DOL",
    "department of commerce": "DOC",
    "doc": "DOC",
    "department of education": "ED",
    "department of housing and urban development": "HUD",
    "hud": "HUD",
    "department of transportation": "DOT",
    "dot": "DOT",
    "department of treasury": "TREAS",
    "department of the treasury": "TREAS",
    "national aeronautics and space administration": "NASA",
    "nasa": "NASA",
    "environmental protection agency": "EPA",
    "epa": "EPA",
    "social security administration": "SSA",
    "ssa": "SSA",
    "small business administration": "SBA",
    "sba": "SBA",

    # --- DHS sub-agencies ---
    "transportation security administration": "TSA",
    "tsa": "TSA",
    "u.s. customs and border protection": "CBP",
    "customs and border protection": "CBP",
    "cbp": "CBP",
    "immigration and customs enforcement": "ICE",
    "u.s. immigration and customs enforcement": "ICE",
    "ice": "ICE",
    "federal emergency management agency": "FEMA",
    "fema": "FEMA",
    "u.s. coast guard": "USCG",
    "coast guard": "USCG",
    "uscg": "USCG",
    "u.s. secret service": "USSS",
    "secret service": "USSS",
    "cybersecurity and infrastructure security agency": "CISA",
    "cisa": "CISA",
    "u.s. citizenship and immigration services": "USCIS",
    "citizenship and immigration services": "USCIS",
    "uscis": "USCIS",
    "science and technology directorate": "DHS",
    "management directorate": "DHS",

    # --- DOD sub-agencies / components ---
    "naval supply systems command": "DOD",
    "naval sea systems command": "DOD",
    "naval air systems command": "DOD",
    "naval information warfare systems command": "DOD",
    "naval facilities engineering systems command": "DOD",
    "marine corps": "DOD",
    "army corps of engineers": "DOD",
    "army materiel command": "DOD",
    "army contracting command": "DOD",
    "air force materiel command": "DOD",
    "air force life cycle management center": "DOD",
    "space force": "DOD",
    "defense logistics agency": "DOD",
    "dla": "DOD",
    "defense information systems agency": "DOD",
    "disa": "DOD",
    "defense health agency": "DOD",
    "dha": "DOD",
    "defense contract management agency": "DOD",
    "dcma": "DOD",
    "defense advanced research projects agency": "DOD",
    "darpa": "DOD",
    "missile defense agency": "DOD",
    "mda": "DOD",
    "u.s. special operations command": "DOD",
    "u.s. transportation command": "DOD",

    # --- USDA sub-agencies ---
    "forest service": "USDA",
    "u.s. forest service": "USDA",
    "agricultural research service": "USDA",
    "animal and plant health inspection service": "USDA",
    "aphis": "USDA",
    "food safety and inspection service": "USDA",
    "natural resources conservation service": "USDA",
    "rural development": "USDA",
    "farm service agency": "USDA",

    # --- DOI sub-agencies ---
    "bureau of land management": "DOI",
    "blm": "DOI",
    "national park service": "DOI",
    "nps": "DOI",
    "u.s. fish and wildlife service": "DOI",
    "fish and wildlife service": "DOI",
    "bureau of reclamation": "DOI",
    "bureau of indian affairs": "DOI",
    "u.s. geological survey": "DOI",
    "usgs": "DOI",

    # --- HHS sub-agencies ---
    "centers for disease control and prevention": "HHS",
    "cdc": "HHS",
    "national institutes of health": "HHS",
    "nih": "HHS",
    "food and drug administration": "HHS",
    "fda": "HHS",
    "centers for medicare and medicaid services": "HHS",
    "cms": "HHS",
    "indian health service": "HHS",

    # --- DOJ sub-agencies ---
    "federal bureau of investigation": "DOJ",
    "fbi": "DOJ",
    "bureau of prisons": "DOJ",
    "drug enforcement administration": "DOJ",
    "dea": "DOJ",
    "bureau of alcohol, tobacco, firearms and explosives": "DOJ",
    "atf": "DOJ",
    "u.s. marshals service": "DOJ",

    # --- DOT sub-agencies ---
    "federal aviation administration": "DOT",
    "faa": "DOT",
    "federal highway administration": "DOT",
    "fhwa": "DOT",
    "federal transit administration": "DOT",
    "federal railroad administration": "DOT",
    "federal motor carrier safety administration": "DOT",

    # --- DOC sub-agencies ---
    "national oceanic and atmospheric administration": "DOC",
    "noaa": "DOC",
    "census bureau": "DOC",
    "u.s. census bureau": "DOC",
    "national institute of standards and technology": "DOC",
    "nist": "DOC",
    "patent and trademark office": "DOC",

    # --- DOE sub-agencies ---
    "national nuclear security administration": "DOE",
    "nnsa": "DOE",

    # --- Independent agencies ---
    "office of personnel management": "OPM",
    "opm": "OPM",
    "nuclear regulatory commission": "NRC",
    "nrc": "NRC",
    "national science foundation": "NSF",
    "nsf": "NSF",
    "securities and exchange commission": "SEC",
    "sec": "SEC",
    "federal communications commission": "FCC",
    "fcc": "FCC",
    "agency for international development": "USAID",
    "usaid": "USAID",
    "u.s. agency for international development": "USAID",

    # --- GSA sub-agencies ---
    "federal acquisition service": "GSA",
    "public buildings service": "GSA",
    "federal trade commission": "FTC",
    "ftc": "FTC",
    "export-import bank": "EXIM",
    "export-import bank of the united states": "EXIM",
}


def normalize_agency(raw: str | None) -> tuple[str, str]:
    """
    Return (full_name, abbreviation) from a raw agency string.

    Handles the Tango API's colon-separated format:
        "Department of Homeland Security : Transportation Security Administration"

    Resolution order:
      1. Try sub-agency (last part) via direct lookup
      2. Try parent department (first part) via direct lookup
      3. Try sub-agency via substring match
      4. Try parent department via substring match
      5. Fall back to (cleaned_raw, "")

    This ensures sub-agencies map to the correct parent and avoids
    false substring matches across unrelated agencies.
    """
    if not raw:
        return ("", "")
    cleaned = raw.strip()

    # Tango uses "Parent : Sub-agency" format
    parts = [p.strip() for p in cleaned.split(" : ")] if " : " in cleaned else [cleaned]

    # --- Phase 1: Direct lookup (exact match, fast) ---
    # Try sub-agency first (most specific), then parent
    for part in reversed(parts):
        key = part.lower()
        abbrev = _AGENCY_ABBREVS.get(key, "")
        if abbrev:
            return (cleaned, abbrev)

    # --- Phase 2: Substring match, scoped per part ---
    # Try sub-agency substring first, then parent.
    # Each part only matches against its own substring scan — no cross-contamination.
    for part in reversed(parts):
        key = part.lower()
        # Try longest patterns first to avoid short-pattern false positives
        for pattern, ab in sorted(_AGENCY_ABBREVS.items(), key=lambda x: -len(x[0])):
            # Only match patterns that are at least 8 chars to avoid abbreviation collisions
            if len(pattern) >= 8 and pattern in key:
                return (cleaned, ab)

    return (cleaned, "")


# ---------------------------------------------------------------------------
# Ground taxonomy mapping
# ---------------------------------------------------------------------------

_GROUND_PATTERNS: list[tuple[str, ProtestGroundType]] = [
    (r"evaluat", ProtestGroundType.EVALUATION_ERROR),
    (r"cost.*(?:real|analy)", ProtestGroundType.COST_PRICE_ANALYSIS),
    (r"price.*(?:real|analy)", ProtestGroundType.COST_PRICE_ANALYSIS),
    (r"unequal|disparate|unfair.*treat", ProtestGroundType.UNEQUAL_TREATMENT),
    (r"discussion|clarification", ProtestGroundType.DISCUSSIONS_CLARIFICATIONS),
    (r"sole.*source|j&a|justification.*approval", ProtestGroundType.SOLE_SOURCE_JA),
    (r"small.*business|set.?aside|8\(a\)|hubzone|sdvosb|wosb", ProtestGroundType.SMALL_BUSINESS_SET_ASIDE),
    (r"conflict.*interest|oci|organizational.*conflict", ProtestGroundType.ORGANIZATIONAL_CONFLICT),
    (r"solicitation|ambi[gq]u|defect.*solicit", ProtestGroundType.SOLICITATION_DEFICIENCY),
    (r"best.*value|trade.?off|tradeoff", ProtestGroundType.BEST_VALUE_TRADEOFF),
    (r"past.*perform", ProtestGroundType.PAST_PERFORMANCE),
    (r"technical.*evaluat|technical.*scor", ProtestGroundType.TECHNICAL_EVALUATION),
    (r"responsib", ProtestGroundType.AWARDEE_RESPONSIBILITY),
    (r"timeli|untimely|\bfiled late\b|\blate filing\b|\blate\b", ProtestGroundType.TIMELINESS),
    (r"protective.*order", ProtestGroundType.PROTECTIVE_ORDER),
    (r"debrief", ProtestGroundType.DEBRIEFING),
]


def classify_ground(raw_text: str) -> ProtestGroundType:
    """Map free-text protest ground to canonical taxonomy via pattern matching."""
    text = raw_text.lower()
    for pattern, ground_type in _GROUND_PATTERNS:
        if re.search(pattern, text):
            return ground_type
    return ProtestGroundType.OTHER


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y%m%d",
]


def parse_date(raw: str | None) -> date | None:
    """Attempt to parse a date from multiple common formats."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date: %r", raw)
    return None


# ---------------------------------------------------------------------------
# Full normalization
# ---------------------------------------------------------------------------

class ProtestNormalizationService:
    """
    Transforms TangoProtestRecord → ProtestCase with populated relations.

    This is the single normalization entry point.  Future providers can
    either produce TangoProtestRecord-shaped objects or get their own
    normalize_from_<provider> method that converges on the same ProtestCase output.
    """

    PROVIDER_NAME = "tango"

    def normalize(self, record: TangoProtestRecord) -> ProtestCase:
        """Convert a single raw Tango record to a canonical ProtestCase."""
        filed = parse_date(record.filed_date)
        decided = parse_date(record.decision_date)
        agency_full, agency_abbrev = normalize_agency(record.agency)

        case = ProtestCase(
            case_number=record.case_number,
            outcome=normalize_outcome(record.outcome),
            agency=agency_full,
            agency_abbreviation=agency_abbrev,
            protester=record.protester or "",
            solicitation_number=record.solicitation_number or "",
            title=record.title or "",
            value=record.value,
            filed_date=filed,
            decision_date=decided,
            decision_url=record.decision_url or "",
            provider_name=self.PROVIDER_NAME,
            provider_id=record.tango_id,
            raw_payload=record.raw_payload,
        )

        # Grounds
        case.grounds = self._normalize_grounds(case.id, record.grounds)

        # Entities
        case.entities = self._extract_entities(case.id, record)

        # Signals (derived from case + grounds)
        case.signals = self._derive_signals(case)

        case.normalized_at = datetime.utcnow()
        return case

    def normalize_batch(
        self, records: list[TangoProtestRecord]
    ) -> tuple[list[ProtestCase], list[tuple[TangoProtestRecord, str]]]:
        """
        Normalize a batch of records.
        Returns (successes, failures) where failures include the error message.
        """
        successes: list[ProtestCase] = []
        failures: list[tuple[TangoProtestRecord, str]] = []

        for record in records:
            try:
                case = self.normalize(record)
                successes.append(case)
            except Exception as exc:
                logger.error("Normalization failed for %s: %s", record.tango_id, exc)
                failures.append((record, str(exc)))

        return successes, failures

    # -- internal --

    @staticmethod
    def _normalize_grounds(case_id: str, raw_grounds: list[str]) -> list[ProtestGround]:
        """Map raw ground strings to canonical ProtestGround objects."""
        grounds: list[ProtestGround] = []
        for text in raw_grounds:
            if not text or not text.strip():
                continue
            grounds.append(ProtestGround(
                case_id=case_id,
                ground_type=classify_ground(text),
                raw_text=text.strip(),
            ))
        return grounds

    @staticmethod
    def _extract_entities(case_id: str, record: TangoProtestRecord) -> list[ProtestEntity]:
        """Extract named entities from the record."""
        entities: list[ProtestEntity] = []

        if record.protester:
            entities.append(ProtestEntity(
                case_id=case_id,
                name=record.protester,
                role=EntityRole.PROTESTER,
                normalized_name=record.protester.strip(),
            ))

        if record.agency:
            entities.append(ProtestEntity(
                case_id=case_id,
                name=record.agency,
                role=EntityRole.AGENCY,
                normalized_name=record.agency.strip(),
            ))

        return entities

    @staticmethod
    def _derive_signals(case: ProtestCase) -> list[ProtestSignal]:
        """
        Derive risk signals from the normalized case.
        Maps protest grounds to ProtestRiskEngine factor IDs (PF01–PF10).
        """
        signals: list[ProtestSignal] = []
        ground_types = {g.ground_type for g in case.grounds}

        # Map ground types to risk factor IDs
        _GROUND_TO_FACTOR: dict[ProtestGroundType, tuple[str, str]] = {
            ProtestGroundType.SOLE_SOURCE_JA: ("PF01", "Competition adequacy"),
            ProtestGroundType.EVALUATION_ERROR: ("PF02", "Evaluation criteria traceability"),
            ProtestGroundType.BEST_VALUE_TRADEOFF: ("PF03", "Evaluation methodology"),
            ProtestGroundType.ORGANIZATIONAL_CONFLICT: ("PF05", "Organizational conflict of interest"),
            ProtestGroundType.DISCUSSIONS_CLARIFICATIONS: ("PF06", "Discussions conduct"),
            ProtestGroundType.SMALL_BUSINESS_SET_ASIDE: ("PF07", "Small business set-aside compliance"),
            ProtestGroundType.DEBRIEFING: ("PF08", "Debriefing quality"),
            ProtestGroundType.COST_PRICE_ANALYSIS: ("PF10", "Price analysis methodology"),
            ProtestGroundType.UNEQUAL_TREATMENT: ("PF06", "Discussions conduct"),
            ProtestGroundType.PAST_PERFORMANCE: ("PF02", "Past performance evaluation"),
            ProtestGroundType.TECHNICAL_EVALUATION: ("PF02", "Technical evaluation documentation"),
        }

        severity = (
            SignalSeverity.HIGH
            if case.outcome == ProtestOutcome.SUSTAINED
            else SignalSeverity.MEDIUM
            if case.outcome in (ProtestOutcome.CORRECTIVE_ACTION, ProtestOutcome.MIXED)
            else SignalSeverity.LOW
        )

        confidence = (
            0.9 if case.outcome == ProtestOutcome.SUSTAINED
            else 0.7 if case.outcome == ProtestOutcome.CORRECTIVE_ACTION
            else 0.5
        )

        for gt in ground_types:
            if gt in _GROUND_TO_FACTOR:
                factor_id, factor_desc = _GROUND_TO_FACTOR[gt]
                signals.append(ProtestSignal(
                    case_id=case.id,
                    signal_type=factor_id,
                    severity=severity,
                    description=f"{factor_desc} — {case.outcome.value} ({case.case_number})",
                    evidence_text=f"GAO {case.case_number}: {case.title or 'No title'}",
                    confidence=confidence,
                ))

        return signals
