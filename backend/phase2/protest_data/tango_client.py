"""
Tango API Client Adapter
========================
HTTP client for the Tango (MakeGov) GAO bid-protest API.

Provider adapter pattern — Tango is a pluggable source, not a hard dependency.
If Tango is unavailable the system degrades gracefully; the canonical protest
data layer never surfaces a raw Tango type beyond this module.

Auth: X-API-KEY header (key from TANGO_API_KEY env var).
Base URL: https://tango.makegov.com/api/
Rate limit: conservative 2 req/s default with exponential backoff.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TANGO_BASE_URL = "https://tango.makegov.com/api"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RATE_LIMIT = 2  # requests per second
MAX_RETRIES = 3
BACKOFF_BASE = 1.5  # seconds


class TangoError(Exception):
    """Base exception for Tango API errors."""


class TangoAuthError(TangoError):
    """API key invalid or missing."""


class TangoRateLimitError(TangoError):
    """Rate limit exceeded."""


class TangoNotFoundError(TangoError):
    """Requested resource not found."""


class TangoUnavailableError(TangoError):
    """Service temporarily unavailable (5xx or network failure)."""


@dataclass
class TangoConfig:
    """Client configuration — immutable after construction."""
    api_key: str = ""
    base_url: str = TANGO_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    rate_limit: float = DEFAULT_RATE_LIMIT
    max_retries: int = MAX_RETRIES

    @classmethod
    def from_env(cls) -> TangoConfig:
        """Build config from environment variables."""
        return cls(
            api_key=os.environ.get("TANGO_API_KEY", ""),
            base_url=os.environ.get("TANGO_BASE_URL", TANGO_BASE_URL),
            timeout=float(os.environ.get("TANGO_TIMEOUT", DEFAULT_TIMEOUT)),
            rate_limit=float(os.environ.get("TANGO_RATE_LIMIT", DEFAULT_RATE_LIMIT)),
            max_retries=int(os.environ.get("TANGO_MAX_RETRIES", MAX_RETRIES)),
        )


@dataclass
class TangoProtestRecord:
    """Raw protest record as returned by the Tango API (before normalization)."""
    tango_id: str  # Tango case_id (UUID)
    case_number: str  # GAO B-number (e.g. b-423306)
    filed_date: str | None = None
    decision_date: str | None = None
    outcome: str | None = None  # Sustained, Denied, Dismissed, Withdrawn, etc.
    protester: str | None = None
    agency: str | None = None  # "Parent Dept : Sub-agency" format
    solicitation_number: str | None = None
    title: str | None = None
    value: float | None = None  # Not in current Tango API; reserved for future
    case_type: str | None = None  # "Bid Protest", "Bid Protest: Reconsideration"
    posted_date: str | None = None
    due_date: str | None = None
    docket_url: str | None = None
    decision_url: str | None = None
    grounds: list[str] = field(default_factory=list)  # Not in list endpoint; may be in detail
    docket: list[dict[str, Any]] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TangoListResponse:
    """Paginated list response from the protests endpoint."""
    records: list[TangoProtestRecord]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class TangoClient:
    """
    HTTP adapter for the Tango (MakeGov) bid-protest API.

    Usage:
        client = TangoClient(TangoConfig.from_env())
        response = client.list_protests(agency="DHS", outcome="sustained")
        detail = client.get_protest(tango_id="12345", expand_docket=True)
    """

    def __init__(self, config: TangoConfig | None = None):
        self._config = config or TangoConfig.from_env()
        self._last_request_time: float = 0.0
        self._client: httpx.Client | None = None

    # -- lifecycle --

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            if not self._config.api_key:
                raise TangoAuthError("TANGO_API_KEY not set")
            self._client = httpx.Client(
                base_url=self._config.base_url,
                headers={
                    "X-API-KEY": self._config.api_key,
                    "Accept": "application/json",
                    "User-Agent": "FedProcure/1.0 (protest-data-pipeline)",
                },
                timeout=self._config.timeout,
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- rate limiting --

    def _throttle(self) -> None:
        """Enforce rate limit between requests."""
        if self._config.rate_limit <= 0:
            return
        min_interval = 1.0 / self._config.rate_limit
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    # -- core request --

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue an HTTP request with retry, rate limiting, and error mapping."""
        client = self._get_client()
        last_exc: Exception | None = None

        for attempt in range(1, self._config.max_retries + 1):
            self._throttle()
            self._last_request_time = time.monotonic()

            try:
                resp = client.request(method, path, params=params)
            except httpx.TimeoutException as exc:
                last_exc = TangoUnavailableError(f"Timeout on attempt {attempt}: {exc}")
                logger.warning("Tango timeout (attempt %d/%d)", attempt, self._config.max_retries)
                time.sleep(BACKOFF_BASE ** attempt)
                continue
            except httpx.HTTPError as exc:
                last_exc = TangoUnavailableError(f"HTTP error on attempt {attempt}: {exc}")
                logger.warning("Tango HTTP error (attempt %d/%d): %s", attempt, self._config.max_retries, exc)
                time.sleep(BACKOFF_BASE ** attempt)
                continue

            # Map status codes to typed errors
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401 or resp.status_code == 403:
                raise TangoAuthError(f"Authentication failed ({resp.status_code})")
            elif resp.status_code == 404:
                raise TangoNotFoundError(f"Resource not found: {path}")
            elif resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", BACKOFF_BASE ** attempt))
                logger.warning("Tango rate limit hit, waiting %.1fs", retry_after)
                last_exc = TangoRateLimitError("Rate limit exceeded")
                time.sleep(retry_after)
                continue
            elif resp.status_code >= 500:
                last_exc = TangoUnavailableError(f"Server error {resp.status_code}")
                logger.warning("Tango server error %d (attempt %d/%d)", resp.status_code, attempt, self._config.max_retries)
                time.sleep(BACKOFF_BASE ** attempt)
                continue
            else:
                raise TangoError(f"Unexpected status {resp.status_code}: {resp.text[:200]}")

        raise last_exc or TangoUnavailableError("Max retries exceeded")

    # -- public API --

    def list_protests(
        self,
        *,
        agency: str | None = None,
        outcome: str | None = None,
        filed_after: date | None = None,
        filed_before: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> TangoListResponse:
        """
        Retrieve a paginated list of GAO bid-protest records.

        Filters:
            agency: Contracting agency name or abbreviation
            outcome: sustained | denied | dismissed | withdrawn
            filed_after / filed_before: Date range for filing date
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if agency:
            params["agency"] = agency
        if outcome:
            params["outcome"] = outcome
        if filed_after:
            params["filed_after"] = filed_after.isoformat()
        if filed_before:
            params["filed_before"] = filed_before.isoformat()

        data = self._request("GET", "/protests/", params=params)
        records = [self._parse_protest_record(r) for r in data.get("results", [])]

        return TangoListResponse(
            records=records,
            total_count=data.get("count", len(records)),
            page=page,
            page_size=page_size,
            has_next=data.get("next") is not None,
        )

    def get_protest(
        self,
        tango_id: str,
        *,
        expand_docket: bool = False,
    ) -> TangoProtestRecord:
        """Retrieve full detail for a single protest record."""
        params: dict[str, Any] = {}
        if expand_docket:
            params["expand"] = "docket"

        data = self._request("GET", f"/protests/{tango_id}/", params=params)
        return self._parse_protest_record(data)

    def health_check(self) -> bool:
        """Quick connectivity test — returns True if API is reachable."""
        try:
            self._request("GET", "/protests/", params={"page": 1, "page_size": 1})
            return True
        except TangoError:
            return False

    # -- parsing --

    @staticmethod
    def _parse_protest_record(raw: dict[str, Any]) -> TangoProtestRecord:
        """Parse a raw JSON object into a TangoProtestRecord.

        Handles both the real Tango API shape and legacy/test shapes for
        backwards compatibility with existing tests.
        """
        return TangoProtestRecord(
            # Real API: case_id (UUID).  Fallbacks for tests/legacy.
            tango_id=str(raw.get("case_id", raw.get("id", raw.get("tango_id", "")))),
            case_number=raw.get("case_number", raw.get("b_number", "")),
            filed_date=raw.get("filed_date", raw.get("date_filed")),
            decision_date=raw.get("decision_date", raw.get("date_decided")),
            outcome=raw.get("outcome", raw.get("status")),
            protester=raw.get("protester", raw.get("protestant")),
            agency=raw.get("agency", raw.get("contracting_agency")),
            solicitation_number=raw.get("solicitation_number", raw.get("solicitation_no")),
            title=raw.get("title", raw.get("description")),
            value=raw.get("value", raw.get("contract_value")),
            case_type=raw.get("case_type"),
            posted_date=raw.get("posted_date"),
            due_date=raw.get("due_date"),
            docket_url=raw.get("docket_url"),
            decision_url=raw.get("decision_url", raw.get("url")),
            grounds=raw.get("grounds", raw.get("protest_grounds", [])),
            docket=raw.get("docket", []),
            raw_payload=raw,
        )
