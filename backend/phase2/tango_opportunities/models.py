"""
Canonical Opportunity Models
============================
Domain models for federal contract opportunities sourced from Tango/SAM.gov.
These are FedProcure's internal representation — decoupled from Tango's raw
API shape.

Used for:
  - Market intelligence (upcoming procurements by agency/NAICS)
  - Protest risk cross-reference (match solicitation numbers to protest cases)
  - Acquisition planning (pipeline visibility for COs)
  - Set-aside tracking and small-business goal monitoring
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Notice type mapping
# ---------------------------------------------------------------------------

NOTICE_TYPE_MAP: dict[str, str] = {
    "o": "Solicitation",
    "p": "Pre-solicitation",
    "k": "Combined Synopsis/Solicitation",
    "r": "Sources Sought",
    "g": "Sale of Surplus Property",
    "s": "Special Notice",
    "i": "Intent to Bundle",
    "a": "Award Notice",
    "u": "Justification and Approval",
    "f": "Fair Opportunity / Limited Sources Justification",
}

# ---------------------------------------------------------------------------
# Set-aside normalization
# ---------------------------------------------------------------------------

SET_ASIDE_MAP: dict[str, str] = {
    "NONE": "Full & Open",
    "SBA": "Small Business",
    "SBP": "Small Business",
    "8A": "8(a)",
    "8AN": "8(a) Sole Source",
    "HZC": "HUBZone",
    "HZS": "HUBZone Sole Source",
    "SDVOSBC": "SDVOSB",
    "SDVOSBS": "SDVOSB Sole Source",
    "WOSB": "WOSB",
    "WOSBSS": "WOSB Sole Source",
    "EDWOSB": "EDWOSB",
    "EDWOSBSS": "EDWOSB Sole Source",
    "VSA": "VOSB",
    "VSS": "VOSB Sole Source",
}


@dataclass
class OpportunityOffice:
    """Contracting office that posted the opportunity."""
    office_code: str = ""
    office_name: str = ""
    agency_code: str = ""
    agency_name: str = ""
    department_code: str = ""
    department_name: str = ""


@dataclass
class PlaceOfPerformance:
    """Geographic location where work will be performed."""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "USA"
    street_address: str = ""

    @property
    def location_string(self) -> str:
        parts = []
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country and self.country != "USA":
            parts.append(self.country)
        return ", ".join(parts) if parts else self.country


@dataclass
class OpportunityMeta:
    """Metadata about the opportunity's notices and attachments."""
    notices_count: int = 0
    attachments_count: int = 0
    notice_type_code: str = ""
    notice_type_name: str = ""


@dataclass
class Opportunity:
    """
    Canonical federal contract opportunity.

    Sourced from Tango opportunities API (which mirrors SAM.gov data).
    The opportunity_id is Tango's UUID, not the SAM.gov notice ID.
    """
    # Identity
    opportunity_id: str                     # Tango UUID (primary key)
    title: str = ""
    solicitation_number: str = ""           # The actual solicitation/RFP number
    sam_url: str = ""

    # Status
    active: bool = True
    award_number: Optional[str] = None      # Non-null = awarded

    # Dates
    first_notice_date: Optional[datetime] = None
    last_notice_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None

    # Classification
    naics_code: str = ""
    psc_code: str = ""
    set_aside_code: str = ""                # Raw code from Tango
    set_aside_name: str = ""                # Normalized name

    # Office
    office: OpportunityOffice = field(default_factory=OpportunityOffice)

    # Location
    place_of_performance: PlaceOfPerformance = field(default_factory=PlaceOfPerformance)

    # Meta
    meta: OpportunityMeta = field(default_factory=OpportunityMeta)

    # Provenance
    provider_name: str = "tango"
    raw_payload: dict[str, Any] = field(default_factory=dict)

    # -- derived properties --

    @property
    def is_awarded(self) -> bool:
        return self.award_number is not None

    @property
    def is_open(self) -> bool:
        """Whether the opportunity is still accepting responses."""
        if not self.active:
            return False
        if self.response_deadline and self.response_deadline.replace(tzinfo=None) < datetime.utcnow():
            return False
        return True

    @property
    def is_set_aside(self) -> bool:
        return self.set_aside_code not in ("NONE", "", None)

    @property
    def agency_abbreviation(self) -> str:
        """Best-effort agency abbreviation from department/agency name."""
        name = (self.office.agency_name or "").upper()
        if "TSA" in name or "TRANSPORTATION SECURITY" in name:
            return "TSA"
        if "DHS" in name or "HOMELAND SECURITY" in name:
            return "DHS"
        dept = (self.office.department_name or "").upper()
        if "HOMELAND" in dept:
            return "DHS"
        if "DEFENSE" in dept:
            return "DOD"
        if "NAVY" in name:
            return "NAVY"
        if "AIR FORCE" in name:
            return "USAF"
        if "ARMY" in name:
            return "ARMY"
        if "VETERANS" in dept:
            return "VA"
        if "HEALTH" in dept:
            return "HHS"
        if "ENERGY" in dept:
            return "DOE"
        if "JUSTICE" in dept:
            return "DOJ"
        if "GSA" in name or "GENERAL SERVICES" in name:
            return "GSA"
        if "NASA" in name:
            return "NASA"
        return self.office.agency_code or "UNK"

    def to_summary(self) -> dict[str, Any]:
        """Compact summary dict for API responses."""
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "solicitation_number": self.solicitation_number,
            "active": self.active,
            "is_open": self.is_open,
            "is_awarded": self.is_awarded,
            "award_number": self.award_number,
            "first_notice_date": self.first_notice_date.isoformat() if self.first_notice_date else None,
            "last_notice_date": self.last_notice_date.isoformat() if self.last_notice_date else None,
            "response_deadline": self.response_deadline.isoformat() if self.response_deadline else None,
            "naics_code": self.naics_code,
            "psc_code": self.psc_code,
            "set_aside": self.set_aside_name or self.set_aside_code,
            "notice_type": self.meta.notice_type_name,
            "agency": self.agency_abbreviation,
            "agency_name": self.office.agency_name,
            "department": self.office.department_name,
            "office": self.office.office_name,
            "location": self.place_of_performance.location_string,
            "sam_url": self.sam_url,
            "notices_count": self.meta.notices_count,
            "attachments_count": self.meta.attachments_count,
        }


@dataclass
class OpportunitySearchResult:
    """Paginated search result from opportunity lookups."""
    opportunities: list[Opportunity]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    query: str = ""
