"""
Tango API Shared Infrastructure
================================
Shared configuration, error types, and base HTTP client for all Tango
(MakeGov) API adapters.  Individual adapters (protest_data, tango_entities,
etc.) import from here rather than duplicating connection logic.

Design note: protest_data.tango_client predates this module and carries its
own copy of these types.  A future refactor will have it import from here;
for now both coexist without conflict.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TANGO_BASE_URL = "https://tango.makegov.com/api"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RATE_LIMIT = 2  # requests per second
MAX_RETRIES = 3
BACKOFF_BASE = 1.5  # seconds


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

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
            timeout=float(os.environ.get("TANGO_TIMEOUT", str(DEFAULT_TIMEOUT))),
            rate_limit=float(os.environ.get("TANGO_RATE_LIMIT", str(DEFAULT_RATE_LIMIT))),
            max_retries=int(os.environ.get("TANGO_MAX_RETRIES", str(MAX_RETRIES))),
        )


# ---------------------------------------------------------------------------
# Base client
# ---------------------------------------------------------------------------

class BaseTangoClient:
    """
    Shared HTTP adapter for any Tango API endpoint.

    Provides: connection pooling, X-API-KEY auth, rate limiting,
    retry with exponential backoff, and typed error mapping.
    Subclasses add endpoint-specific methods.
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
                    "User-Agent": "FedProcure/1.0",
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

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (401, 403):
                raise TangoAuthError(f"Authentication failed ({resp.status_code})")
            elif resp.status_code == 404:
                raise TangoNotFoundError(f"Resource not found: {path}")
            elif resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", str(BACKOFF_BASE ** attempt)))
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

    def health_check(self) -> bool:
        """Override in subclasses with an appropriate lightweight call."""
        raise NotImplementedError
