"""
SAM.gov Opportunities Client
=============================
Sync HTTP adapter for the SAM.gov Opportunities API v2.

Primary source for federal contract opportunities — richer data than Tango:
  - Point of contact (CO name, email, phone)
  - Description URL
  - Resource/document links
  - Office address
  - Structured place of performance
  - Archive dates
  - Award details (awardee name, UEI, CAGE, amount)

Rate limits (registered tier):
  - 1,000 requests/day
  - 1,000 records/request
  - 180-day max date range per query

Usage:
    client = SAMGovOpportunityClient()
    results = client.search("TSA baggage screening", limit=50)
    results = client.list_recent(days_back=90, limit=1000)
    results = client.list_by_agency("7013", days_back=180)  # TSA agency code
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

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

# SAM.gov notice type codes → our canonical names
SAM_NOTICE_TYPE_MAP: dict[str, str] = {
    "Solicitation": "Solicitation",
    "Combined Synopsis/Solicitation": "Combined Synopsis/Solicitation",
    "Presolicitation": "Pre-solicitation",
    "Sources Sought": "Sources Sought",
    "Special Notice": "Special Notice",
    "Sale of Surplus Property": "Sale of Surplus Property",
    "Intent to Bundle Requirements (Alarm)": "Intent to Bundle",
    "Award Notice": "Award Notice",
    "Justification": "Justification and Approval",
    "Fair Opportunity / Limited Sources Justification": "Fair Opportunity / Limited Sources Justification",
}

# SAM.gov ptype codes for query params
SAM_PTYPE_MAP: dict[str, str] = {
    "o": "Solicitation",
    "p": "Presolicitation",
    "k": "Combined Synopsis/Solicitation",
    "r": "Sources Sought",
    "s": "Special Notice",
    "g": "Sale of Surplus Property",
    "i": "Intent to Bundle",
    "a": "Award Notice",
    "u": "Justification",
    "f": "Fair Opportunity / Limited Sources Justification",
}


class SAMGovOpportunityClient:
    """
    Sync HTTP client for SAM.gov Opportunities API v2.

    Provides the same interface as TangoOpportunityClient so the router
    can use either interchangeably.
    """

    BASE_URL = "https://api.sam.gov/opportunities/v2/search"
    MAX_DATE_RANGE_DAYS = 180
    MAX_RECORDS_PER_REQUEST = 1000
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SAM_GOV_API_KEY", "")
        self._last_request_time: float = 0.0
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=self.DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "FedProcure/1.0",
                },
            )
        return self._client

    def close(self) -> None:
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _throttle(self) -> None:
        """Rate limit to ~2 req/sec to be a good citizen."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a SAM.gov API request with rate limiting."""
        if not self.api_key:
            raise ValueError("SAM_GOV_API_KEY not configured")

        client = self._get_client()
        params["api_key"] = self.api_key

        self._throttle()
        self._last_request_time = time.monotonic()

        resp = client.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()

    # -- public methods --

    def search(
        self,
        query: str,
        *,
        days_back: int = 180,
        limit: int = 100,
        offset: int = 0,
        notice_types: str = "o,p,k,r,s",
    ) -> OpportunitySearchResult:
        """
        Search opportunities by keyword.

        SAM.gov uses `title` param for keyword search.
        """
        days_back = min(days_back, self.MAX_DATE_RANGE_DAYS)
        posted_from = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")

        params = {
            "title": query,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": notice_types,
            "limit": min(limit, self.MAX_RECORDS_PER_REQUEST),
            "offset": offset,
        }

        data = self._request(params)
        total = data.get("totalRecords", 0)
        opps = [self._parse_opportunity(raw) for raw in data.get("opportunitiesData", [])]

        return OpportunitySearchResult(
            opportunities=opps,
            total_count=total,
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            has_next=(offset + limit) < total,
            query=query,
        )

    def list_recent(
        self,
        *,
        days_back: int = 30,
        limit: int = 1000,
        offset: int = 0,
        notice_types: str = "o,p,k,r,s",
        naics: str | None = None,
        set_aside: str | None = None,
    ) -> OpportunitySearchResult:
        """
        List recent opportunities with optional filters.

        Up to 1,000 records per request — no need for pagination
        for most use cases.
        """
        days_back = min(days_back, self.MAX_DATE_RANGE_DAYS)
        posted_from = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")

        params: dict[str, Any] = {
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": notice_types,
            "limit": min(limit, self.MAX_RECORDS_PER_REQUEST),
            "offset": offset,
        }
        if naics:
            params["ncode"] = naics
        if set_aside:
            params["typeOfSetAside"] = set_aside

        data = self._request(params)
        total = data.get("totalRecords", 0)
        opps = [self._parse_opportunity(raw) for raw in data.get("opportunitiesData", [])]

        return OpportunitySearchResult(
            opportunities=opps,
            total_count=total,
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            has_next=(offset + limit) < total,
        )

    def list_by_agency(
        self,
        department_name: str,
        *,
        days_back: int = 180,
        limit: int = 1000,
        offset: int = 0,
        notice_types: str = "o,p,k,r,s",
    ) -> OpportunitySearchResult:
        """List opportunities for a specific department/agency."""
        days_back = min(days_back, self.MAX_DATE_RANGE_DAYS)
        posted_from = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")

        params: dict[str, Any] = {
            "deptname": department_name,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": notice_types,
            "limit": min(limit, self.MAX_RECORDS_PER_REQUEST),
            "offset": offset,
        }

        data = self._request(params)
        total = data.get("totalRecords", 0)
        opps = [self._parse_opportunity(raw) for raw in data.get("opportunitiesData", [])]

        return OpportunitySearchResult(
            opportunities=opps,
            total_count=total,
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            has_next=(offset + limit) < total,
        )

    def fetch_page(
        self,
        *,
        days_back: int = 180,
        limit: int = 1000,
        offset: int = 0,
        notice_types: str = "o,p,k,r,s,a",
        naics: str | None = None,
        department: str | None = None,
        keyword: str | None = None,
        posted_from_override: str | None = None,
        posted_to_override: str | None = None,
    ) -> tuple[list[Opportunity], int, bool]:
        """
        Low-level page fetch for bulk ingestion.

        Returns (opportunities, total_count, has_next).
        At 1,000 records/request, a 38K dataset needs only 39 requests.
        """
        if posted_from_override and posted_to_override:
            posted_from = posted_from_override
            posted_to = posted_to_override
        else:
            days_back = min(days_back, self.MAX_DATE_RANGE_DAYS)
            posted_from = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
            posted_to = datetime.now().strftime("%m/%d/%Y")

        params: dict[str, Any] = {
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": notice_types,
            "limit": min(limit, self.MAX_RECORDS_PER_REQUEST),
            "offset": offset,
        }
        if naics:
            params["ncode"] = naics
        if department:
            params["deptname"] = department
        if keyword:
            params["title"] = keyword

        data = self._request(params)
        total = data.get("totalRecords", 0)
        opps = [self._parse_opportunity(raw) for raw in data.get("opportunitiesData", [])]
        has_next = (offset + limit) < total

        return opps, total, has_next

    def health_check(self) -> bool:
        """Quick connectivity test."""
        try:
            posted_from = (datetime.now() - timedelta(days=7)).strftime("%m/%d/%Y")
            posted_to = datetime.now().strftime("%m/%d/%Y")
            params = {
                "postedFrom": posted_from,
                "postedTo": posted_to,
                "ptype": "o",
                "limit": 1,
                "offset": 0,
            }
            self._request(params)
            return True
        except Exception:
            return False

    # -- parsing --

    @staticmethod
    def _parse_datetime(val: Any) -> Optional[datetime]:
        """Parse SAM.gov date strings (various formats)."""
        if not val:
            return None
        try:
            if isinstance(val, datetime):
                return val
            s = str(val)
            # SAM uses multiple formats
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            # ISO fallback
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _parse_opportunity(cls, raw: dict[str, Any]) -> Opportunity:
        """Parse a raw SAM.gov opportunity JSON into our canonical Opportunity."""

        # Office — SAM uses hierarchical path format
        full_path = raw.get("fullParentPathName", "")
        full_code = raw.get("fullParentPathCode", "")
        path_parts = full_path.split(".")
        code_parts = full_code.split(".")

        department_name = path_parts[0] if len(path_parts) > 0 else ""
        agency_name = path_parts[1] if len(path_parts) > 1 else department_name
        office_name = path_parts[-1] if len(path_parts) > 2 else ""
        department_code = code_parts[0] if len(code_parts) > 0 else ""
        agency_code = code_parts[1] if len(code_parts) > 1 else ""
        office_code = code_parts[-1] if len(code_parts) > 2 else ""

        office = OpportunityOffice(
            office_code=office_code,
            office_name=office_name,
            agency_code=agency_code,
            agency_name=agency_name,
            department_code=department_code,
            department_name=department_name,
        )

        # Place of performance — SAM uses nested objects
        pop_raw = raw.get("placeOfPerformance") or {}
        city_raw = pop_raw.get("city") or {}
        state_raw = pop_raw.get("state") or {}
        country_raw = pop_raw.get("country") or {}

        pop = PlaceOfPerformance(
            city=city_raw.get("name", "") or "",
            state=state_raw.get("code", "") or "",
            zip_code=pop_raw.get("zip", "") or "",
            country=country_raw.get("code", "") or "USA",
        )

        # Notice type
        notice_type_raw = raw.get("type", "")
        notice_type_name = SAM_NOTICE_TYPE_MAP.get(notice_type_raw, notice_type_raw)
        # Reverse-map to single-letter code for consistency with Tango
        notice_type_code = ""
        for code, name in SAM_PTYPE_MAP.items():
            if name == raw.get("baseType", notice_type_raw):
                notice_type_code = code
                break

        meta = OpportunityMeta(
            notices_count=0,  # SAM doesn't provide this directly
            attachments_count=len(raw.get("resourceLinks") or []),
            notice_type_code=notice_type_code,
            notice_type_name=notice_type_name,
        )

        # Set-aside
        set_aside_code = raw.get("typeOfSetAside") or "NONE"
        set_aside_name = raw.get("typeOfSetAsideDescription") or SET_ASIDE_MAP.get(set_aside_code, set_aside_code)

        # NAICS
        naics = raw.get("naicsCode", "")
        naics_str = str(naics) if naics else ""

        # Active — SAM returns "Yes"/"No" string
        active_raw = raw.get("active", "Yes")
        active = active_raw in ("Yes", "yes", True, "true", "1")

        # Award
        award_raw = raw.get("award") or {}
        award_number = award_raw.get("number") if award_raw else None

        # Point of contact — enrich raw_payload for downstream use
        poc_list = raw.get("pointOfContact") or []
        primary_poc = next((p for p in poc_list if p.get("type") == "primary"), poc_list[0] if poc_list else {})

        # Build enriched raw payload with SAM-exclusive fields
        enriched_payload = dict(raw)
        enriched_payload["_source"] = "sam.gov"
        enriched_payload["_primary_poc"] = primary_poc

        return Opportunity(
            opportunity_id=raw.get("noticeId", ""),
            title=(raw.get("title") or "").strip(),
            solicitation_number=(raw.get("solicitationNumber") or "").strip(),
            sam_url=raw.get("uiLink") or "",
            active=active,
            award_number=award_number,
            first_notice_date=cls._parse_datetime(raw.get("postedDate")),
            last_notice_date=cls._parse_datetime(raw.get("postedDate")),  # SAM doesn't separate these
            response_deadline=cls._parse_datetime(raw.get("responseDeadLine")),
            naics_code=naics_str,
            psc_code=(raw.get("classificationCode") or "").strip(),
            set_aside_code=set_aside_code,
            set_aside_name=set_aside_name,
            office=office,
            place_of_performance=pop,
            meta=meta,
            provider_name="sam.gov",
            raw_payload=enriched_payload,
        )
