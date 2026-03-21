"""
Canonical Entity Models
=======================
Domain models for contractor/entity profiles.  These are FedProcure's
internal representation — decoupled from Tango's raw API shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Small-business type code mapping
# ---------------------------------------------------------------------------
# Maps Tango/SAM business_type codes to FedProcure small-business categories.
# Only codes that indicate a small-business set-aside eligibility are included.

SB_TYPE_CODES: dict[str, str] = {
    "27": "SDB",       # Self-Certified Small Disadvantaged Business
    "A5": "VOSB",      # Veteran Owned Small Business
    "QF": "SDVOSB",    # Service-Disabled Veteran Owned Small Business
    "8W": "WOSB",      # Woman Owned Small Business
    "A2": "WOB",       # Woman Owned Business (broader than WOSB)
    "23": "MBE",       # Minority Owned Business
    "8A": "8(a)",      # 8(a) program participant
    "XX": "HUBZone",   # HUBZone (code varies by data source)
    "JS": "SB-JV",     # Small Business Joint Venture
    "JV": "SDVOSB-JV", # SDVOSB Joint Venture
    "NB": "NativeAm",  # Native American Owned
    "OY": "BlackAm",   # Black American Owned
    "PI": "HispAm",    # Hispanic American Owned
    "HQ": "DOT-DBE",   # DOT Certified Disadvantaged Business Enterprise
}


@dataclass
class BusinessType:
    """A single business type classification from SAM.gov registration."""
    code: str
    description: str

    def is_small_business(self) -> bool:
        """Whether this type indicates small-business eligibility."""
        return self.code in SB_TYPE_CODES

    def sb_category(self) -> str:
        """Return the FedProcure small-business category abbreviation, or ''."""
        return SB_TYPE_CODES.get(self.code, "")


@dataclass
class Address:
    """Physical address for an entity."""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    zip_plus4: str = ""
    country_code: str = "USA"

    @property
    def state_city(self) -> str:
        """Compact location string, e.g. 'Arlington, VA'."""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or ""


@dataclass
class EntityProfile:
    """
    Canonical contractor/entity profile.

    Sourced from Tango entities API (which mirrors SAM.gov registration data).
    Used for:
      - Protester enrichment (cross-ref with protest cases)
      - Market research (NAICS, small-business eligibility)
      - Responsibility determination support
    """
    # Identity
    uei: str                           # Unique Entity Identifier (primary key)
    legal_business_name: str           # Official registered name
    dba_name: str = ""                 # Doing Business As
    entity_url: str = ""               # Company website

    # Registration
    cage_code: str = ""                # CAGE code
    primary_naics: str = ""            # Primary NAICS code
    purpose_of_registration: str = ""  # e.g. "All Awards", "Federal Assistance Awards"

    # Classifications
    business_types: list[BusinessType] = field(default_factory=list)
    sba_business_types: list[BusinessType] = field(default_factory=list)

    # Location
    address: Address = field(default_factory=Address)

    # Provenance
    provider_name: str = "tango"
    raw_payload: dict[str, Any] = field(default_factory=dict)

    # -- derived properties --

    @property
    def is_small_business(self) -> bool:
        """Whether any business type indicates small-business status."""
        return any(bt.is_small_business() for bt in self.business_types)

    @property
    def small_business_categories(self) -> list[str]:
        """List of applicable small-business category abbreviations."""
        return [bt.sb_category() for bt in self.business_types if bt.sb_category()]

    @property
    def display_name(self) -> str:
        """Best display name: DBA if available, else legal name."""
        return self.dba_name.strip() or self.legal_business_name.strip()

    def to_summary(self) -> dict[str, Any]:
        """Compact summary dict for API responses and dashboard cards."""
        return {
            "uei": self.uei,
            "name": self.display_name,
            "legal_name": self.legal_business_name,
            "dba_name": self.dba_name,
            "cage_code": self.cage_code,
            "primary_naics": self.primary_naics,
            "location": self.address.state_city,
            "is_small_business": self.is_small_business,
            "sb_categories": self.small_business_categories,
            "entity_url": self.entity_url,
        }


@dataclass
class EntitySearchResult:
    """Paginated search result from entity lookups."""
    profiles: list[EntityProfile]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    query: str = ""
