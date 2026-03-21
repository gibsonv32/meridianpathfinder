"""
Tango Entities Adapter
======================
Contractor/entity lookup service backed by the Tango (MakeGov) entities API.

This is a **lookup service**, not a batch ingestion pipeline.  The primary
use case is enriching protest cases with contractor profile data:

    protester name  →  Tango entity search  →  EntityProfile
        ↓
    UEI, CAGE, NAICS, small-business status, address

Cross-reference value:
  - PF03 (contractor risk): protest history + business profile
  - Market research: NAICS / small-business eligibility checks
  - Responsibility determination support data

Evidence tier: Structured third-party (Tango → SAM.gov registration data).
All results require human review before use in official records.
"""

from .client import TangoEntityClient
from .models import EntityProfile, BusinessType, Address

__all__ = [
    "TangoEntityClient",
    "EntityProfile",
    "BusinessType",
    "Address",
]
