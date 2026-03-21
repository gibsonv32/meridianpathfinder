"""
Tango Opportunity Client
========================
HTTP adapter for the Tango (MakeGov) opportunities API.

Provides opportunity search, listing, and detail retrieval.
Uses the shared BaseTangoClient for connection management.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from ..tango_common import (
    BaseTangoClient,
    TangoConfig,
    TangoError,
    TangoNotFoundError,
)
from .models import (
    NOTICE_TYPE_MAP,
    SET_ASIDE_MAP,
    Opportunity,
    OpportunityMeta,
    OpportunityOffice,
    OpportunitySearchResult,
    PlaceOfPerformance,
)

logger = logging.getLogger(__name__)


class TangoOpportunityClient(BaseTangoClient):
    """
    HTTP adapter for the Tango opportunities endpoint.

    Usage:
        client = TangoOpportunityClient(TangoConfig.from_env())
        results = client.search_opportunities("TSA baggage screening")
        results = client.list_opportunities(page=1, page_size=10)
        opp = client.get_opportunity("24630534-acb1-4a72-a6b0-119e9406129f")
    """

    def list_opportunities(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> OpportunitySearchResult:
        """
        List opportunities with pagination (no search filter).

        Returns most recently updated opportunities first (Tango default).
        """
        params: dict[str, Any] = {
            "page": page,
            "page_size": min(page_size, 10),  # Tango caps at 10
        }

        data = self._request("GET", "/opportunities/", params=params)
        opps = [self._parse_opportunity(r) for r in data.get("results", [])]

        return OpportunitySearchResult(
            opportunities=opps,
            total_count=data.get("count", len(opps)),
            page=page,
            page_size=page_size,
            has_next=data.get("next") is not None,
        )

    def search_opportunities(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> OpportunitySearchResult:
        """
        Search opportunities by keyword (title, solicitation number, etc).

        The Tango API's `search` parameter does full-text matching.
        """
        params: dict[str, Any] = {
            "search": query,
            "page": page,
            "page_size": min(page_size, 10),
        }

        data = self._request("GET", "/opportunities/", params=params)
        opps = [self._parse_opportunity(r) for r in data.get("results", [])]

        return OpportunitySearchResult(
            opportunities=opps,
            total_count=data.get("count", len(opps)),
            page=page,
            page_size=page_size,
            has_next=data.get("next") is not None,
            query=query,
        )

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        """Retrieve a single opportunity by its Tango UUID."""
        data = self._request("GET", f"/opportunities/{opportunity_id}/")
        return self._parse_opportunity(data)

    def fetch_page(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> tuple[list[Opportunity], int, bool]:
        """
        Low-level page fetch for bulk ingestion.

        Returns (opportunities, total_count, has_next).
        """
        params: dict[str, Any] = {
            "page": page,
            "page_size": min(page_size, 10),
        }
        if search:
            params["search"] = search

        data = self._request("GET", "/opportunities/", params=params)
        opps = [self._parse_opportunity(r) for r in data.get("results", [])]
        return opps, data.get("count", 0), data.get("next") is not None

    def health_check(self) -> bool:
        """Quick connectivity test."""
        try:
            self._request("GET", "/opportunities/", params={"page": 1, "page_size": 1})
            return True
        except TangoError:
            return False

    # -- parsing --

    @staticmethod
    def _parse_datetime(val: Any) -> Optional[datetime]:
        """Parse an ISO datetime string, returning None on failure."""
        if not val:
            return None
        try:
            if isinstance(val, datetime):
                return val
            # Handle timezone-aware strings
            s = str(val)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _parse_opportunity(cls, raw: dict[str, Any]) -> Opportunity:
        """Parse a raw Tango opportunity JSON object into an Opportunity."""
        # Office
        office_raw = raw.get("office") or {}
        office = OpportunityOffice(
            office_code=office_raw.get("office_code", ""),
            office_name=office_raw.get("office_name", ""),
            agency_code=office_raw.get("agency_code", ""),
            agency_name=office_raw.get("agency_name", ""),
            department_code=office_raw.get("department_code", ""),
            department_name=office_raw.get("department_name", ""),
        )

        # Place of performance
        pop_raw = raw.get("place_of_performance") or {}
        pop = PlaceOfPerformance(
            city=pop_raw.get("city") or "",
            state=pop_raw.get("state") or "",
            zip_code=pop_raw.get("zip") or "",
            country=pop_raw.get("country") or "USA",
            street_address=pop_raw.get("street_address") or "",
        )

        # Meta
        meta_raw = raw.get("meta") or {}
        notice_raw = meta_raw.get("notice_type") or {}
        notice_code = notice_raw.get("code", "")
        meta = OpportunityMeta(
            notices_count=meta_raw.get("notices_count", 0),
            attachments_count=meta_raw.get("attachments_count", 0),
            notice_type_code=notice_code,
            notice_type_name=notice_raw.get("type", "") or NOTICE_TYPE_MAP.get(notice_code, ""),
        )

        # Set-aside normalization
        set_aside_code = raw.get("set_aside") or "NONE"
        set_aside_name = SET_ASIDE_MAP.get(set_aside_code, set_aside_code)

        # NAICS as string
        naics = raw.get("naics_code")
        naics_str = str(naics) if naics is not None else ""

        return Opportunity(
            opportunity_id=raw.get("opportunity_id", ""),
            title=(raw.get("title") or "").strip(),
            solicitation_number=(raw.get("solicitation_number") or "").strip(),
            sam_url=raw.get("sam_url") or "",
            active=raw.get("active", True),
            award_number=raw.get("award_number"),
            first_notice_date=cls._parse_datetime(raw.get("first_notice_date")),
            last_notice_date=cls._parse_datetime(raw.get("last_notice_date")),
            response_deadline=cls._parse_datetime(raw.get("response_deadline")),
            naics_code=naics_str,
            psc_code=(raw.get("psc_code") or "").strip(),
            set_aside_code=set_aside_code,
            set_aside_name=set_aside_name,
            office=office,
            place_of_performance=pop,
            meta=meta,
            raw_payload=raw,
        )
