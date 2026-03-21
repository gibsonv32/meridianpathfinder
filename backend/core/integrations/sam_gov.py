"""
SAM.gov Integration Client — Empirically Validated 2026-03-20
==============================================================
Replaces prior stub that targeted dead FPDS endpoint.

Validated findings:
- Opportunities API v2 search: WORKING (api_key query param)
- resourceLinks downloads: WORKING (GET + api_key, NOT HEAD)
- Award notices (ptype=a): WORKING for IGCE comparables
- FPDS /contractadmin/v1/contracts: DEAD (404) — removed
- Entity API v3: needs different pagination — kept as stub
- Max date range: ~180 days per query
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

import httpx


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class SAMGovResult:
    comparable_contracts: list[dict]
    used_fallback: bool
    warning: str | None = None


@dataclass
class OpportunityResult:
    notice_id: str
    title: str
    solicitation_number: str | None = None
    agency: str | None = None
    posted_date: str | None = None
    notice_type: str | None = None
    naics_code: str | None = None
    classification_code: str | None = None
    set_aside: str | None = None
    response_deadline: str | None = None
    ui_link: str | None = None
    resource_links: list[str] = field(default_factory=list)
    award: dict | None = None


@dataclass
class DownloadResult:
    url: str
    success: bool
    file_type: str = "unknown"
    content_length: int = 0
    file_hash: str | None = None
    local_path: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Magic bytes for file type detection
# ---------------------------------------------------------------------------

MAGIC_BYTES: list[tuple[bytes, str, str]] = [
    (b"%PDF", "pdf", ".pdf"),
    (b"PK\x03\x04", "docx_or_zip", ".docx"),
    (b"\xd0\xcf\x11\xe0", "doc_legacy", ".doc"),
    (b"{\\rtf", "rtf", ".rtf"),
]


def _detect_file_type(header: bytes) -> tuple[str, str]:
    """Return (type_name, extension) from first bytes."""
    for magic, name, ext in MAGIC_BYTES:
        if header[: len(magic)] == magic:
            return name, ext
    return "unknown", ".bin"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SAMGovClient:
    """
    SAM.gov API client — empirically validated against live endpoints.

    Usage::

        client = SAMGovClient()  # reads SAM_GOV_API_KEY env var
        awards = await client.get_comparable_contracts("541512", "D323", 20_000_000)
        opps   = await client.search_opportunities(naics="541512", days_back=90)
        dl     = await client.download_resource(opps[0].resource_links[0])
    """

    MAX_DATE_RANGE_DAYS = 180  # Empirically validated limit

    def __init__(self) -> None:
        self.api_key = os.getenv("SAM_GOV_API_KEY")
        self.base_opportunities = "https://api.sam.gov/opportunities/v2/search"
        self.base_entity = "https://api.sam.gov/entity-information/v3/entities"
        self.base_exclusions = "https://api.sam.gov/exclusions/v2/search"
        self._cache: dict[str, tuple[datetime, list[dict], bool, str | None]] = {}

    # ------------------------------------------------------------------
    # Opportunity Search
    # ------------------------------------------------------------------

    async def search_opportunities(
        self,
        naics: str | None = None,
        department: str | None = None,
        notice_types: str = "o,k",  # Solicitation + Combined Synopsis
        days_back: int = 90,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OpportunityResult]:
        """
        Search SAM.gov Opportunities API.

        Args:
            naics: NAICS code (e.g. "541512")
            department: e.g. "HOMELAND SECURITY, DEPARTMENT OF"
            notice_types: Comma-separated ptype codes (o=solicitation, k=combined, a=award, r=sources sought)
            days_back: Max 180 (enforced)
            limit: Results per page
        """
        if not self.api_key:
            return []

        days_back = min(days_back, self.MAX_DATE_RANGE_DAYS)
        posted_from = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")

        params: dict = {
            "api_key": self.api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "ptype": notice_types,
            "limit": limit,
            "offset": offset,
        }
        if naics:
            params["ncode"] = naics
        if department:
            params["deptname"] = department

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.base_opportunities, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: list[OpportunityResult] = []
        for raw in data.get("opportunitiesData", []):
            results.append(
                OpportunityResult(
                    notice_id=raw.get("noticeId", ""),
                    title=raw.get("title", ""),
                    solicitation_number=raw.get("solicitationNumber"),
                    agency=raw.get("fullParentPathName"),
                    posted_date=raw.get("postedDate"),
                    notice_type=raw.get("type"),
                    naics_code=raw.get("naicsCode"),
                    classification_code=raw.get("classificationCode"),
                    set_aside=raw.get("typeOfSetAsideDescription"),
                    response_deadline=raw.get("responseDeadLine"),
                    ui_link=raw.get("uiLink"),
                    resource_links=raw.get("resourceLinks") or [],
                    award=raw.get("award"),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Comparable Contracts (IGCE) — now uses Opportunities ptype=a
    # ------------------------------------------------------------------

    async def get_comparable_contracts(
        self,
        naics_code: str,
        psc: str,
        estimated_value: float,
        agency: str = "7020",
    ) -> SAMGovResult:
        """
        Get comparable contracts for IGCE.
        Uses Opportunities API award notices (ptype=a) instead of dead FPDS endpoint.
        """
        cache_key = f"{agency}:{naics_code}:{psc}:{int(estimated_value)}"
        cached = self._cache.get(cache_key)
        if cached and (datetime.now(UTC) - cached[0]).total_seconds() < 86400:
            return SAMGovResult(
                comparable_contracts=cached[1],
                used_fallback=cached[2],
                warning=cached[3],
            )

        if not self.api_key:
            data = self._fallback_contracts(naics_code, psc, estimated_value)
            self._cache[cache_key] = (datetime.now(UTC), data, True, "SAM_GOV_API_KEY not configured")
            return SAMGovResult(comparable_contracts=data, used_fallback=True, warning="SAM_GOV_API_KEY not configured")

        try:
            opps = await self.search_opportunities(
                naics=naics_code,
                notice_types="a",  # Award notices only
                days_back=180,
                limit=25,
            )

            contracts: list[dict] = []
            for opp in opps:
                if not opp.award:
                    continue
                award = opp.award
                awardee = award.get("awardee", {})
                location = awardee.get("location", {})
                contracts.append(
                    {
                        "piid": award.get("number", "N/A"),
                        "vendor_name": awardee.get("name", "Unknown"),
                        "agency": (opp.agency or "")[:30],
                        "naics": opp.naics_code or naics_code,
                        "psc": opp.classification_code or psc,
                        "obligated_amount": float(award.get("amount", 0)),
                        "contract_type": "See award notice",
                        "pop_start": award.get("date", "N/A"),
                        "pop_end": "N/A",
                        "awardee_uei": awardee.get("ueiSAM"),
                        "awardee_cage": awardee.get("cageCode"),
                        "awardee_city": location.get("city", {}).get("name"),
                        "awardee_state": location.get("state", {}).get("code"),
                        "source": f"SAM.gov Opportunities Award API noticeId={opp.notice_id}",
                    }
                )

            if len(contracts) < 3:
                fallback = self._fallback_contracts(naics_code, psc, estimated_value)
                self._cache[cache_key] = (
                    datetime.now(UTC),
                    fallback,
                    True,
                    f"Only {len(contracts)} live awards found; using fallback",
                )
                return SAMGovResult(
                    comparable_contracts=fallback,
                    used_fallback=True,
                    warning=f"Only {len(contracts)} live awards found; using fallback data",
                )

            self._cache[cache_key] = (datetime.now(UTC), contracts, False, None)
            return SAMGovResult(comparable_contracts=contracts, used_fallback=False)

        except Exception as exc:
            data = self._fallback_contracts(naics_code, psc, estimated_value)
            self._cache[cache_key] = (datetime.now(UTC), data, True, f"SAM.gov error: {exc}")
            return SAMGovResult(comparable_contracts=data, used_fallback=True, warning=f"SAM.gov error: {exc}")

    # ------------------------------------------------------------------
    # File Downloads (for PWS Pathway B)
    # ------------------------------------------------------------------

    async def download_resource(
        self,
        resource_url: str,
        dest_dir: str = "/tmp/sam_downloads",
        max_size: int = 100_000_000,
    ) -> DownloadResult:
        """
        Download a file from a SAM.gov resourceLinks URL.

        CRITICAL (empirically validated 2026-03-20):
        - Must use GET, not HEAD (HEAD returns 403)
        - Must append ?api_key= to the download URL
        - Content-Type is always application/octet-stream — use magic bytes
        """
        if not self.api_key:
            return DownloadResult(url=resource_url, success=False, error="No API key")

        Path(dest_dir).mkdir(parents=True, exist_ok=True)

        sep = "&" if "?" in resource_url else "?"
        auth_url = f"{resource_url}{sep}api_key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                async with client.stream("GET", auth_url) as resp:
                    if resp.status_code != 200:
                        return DownloadResult(
                            url=resource_url,
                            success=False,
                            error=f"HTTP {resp.status_code}",
                        )

                    chunks: list[bytes] = []
                    total = 0
                    hasher = hashlib.sha256()

                    async for chunk in resp.aiter_bytes(65536):
                        total += len(chunk)
                        if total > max_size:
                            return DownloadResult(
                                url=resource_url,
                                success=False,
                                error=f"Exceeds {max_size} byte limit",
                            )
                        chunks.append(chunk)
                        hasher.update(chunk)

                    if not chunks:
                        return DownloadResult(url=resource_url, success=False, error="Empty body")

                    header = chunks[0][:16]

                    # Reject XML error responses masquerading as 200
                    if header[:5] == b"<?xml" or b"AccessDenied" in chunks[0][:200]:
                        return DownloadResult(
                            url=resource_url,
                            success=False,
                            error="XML error response, not file content",
                        )

                    file_type, ext = _detect_file_type(header)
                    file_hash = hasher.hexdigest()
                    filename = f"{file_hash[:16]}{ext}"
                    filepath = Path(dest_dir) / filename

                    with open(filepath, "wb") as f:
                        for c in chunks:
                            f.write(c)

                    return DownloadResult(
                        url=resource_url,
                        success=True,
                        file_type=file_type,
                        content_length=total,
                        file_hash=file_hash,
                        local_path=str(filepath),
                    )

        except httpx.TimeoutException:
            return DownloadResult(url=resource_url, success=False, error="Timeout")
        except Exception as e:
            return DownloadResult(url=resource_url, success=False, error=str(e))

    # ------------------------------------------------------------------
    # Entity / Exclusions (stubs — need correct pagination params)
    # ------------------------------------------------------------------

    async def lookup_entity(self, vendor_name: str) -> dict:
        """Stub — Entity API v3 needs different pagination params (not yet validated)."""
        return {"vendor_name": vendor_name, "small_business": False, "source": "SAM Entity API (stub)"}

    async def check_exclusions(self, vendor_name: str) -> dict:
        """Stub — Exclusions API not yet empirically validated."""
        return {"vendor_name": vendor_name, "excluded": False, "source": "SAM Exclusions API (stub)"}

    # ------------------------------------------------------------------
    # Fallback data
    # ------------------------------------------------------------------

    def _fallback_contracts(self, naics_code: str, psc: str, estimated_value: float) -> list[dict]:
        base = [
            ("70T02024F1001", "CyberShield Federal", 18_400_000, "Firm-Fixed-Price"),
            ("70T02024F1002", "Patriot NOC Services", 21_250_000, "Time-and-Materials"),
            ("70T02024F1003", "Aegis Ops LLC", 19_800_000, "Firm-Fixed-Price"),
            ("70T02024F1004", "Sentinel Network Defense", 22_600_000, "Labor-Hour"),
            ("70T02024F1005", "Blue Vector Systems", 19_150_000, "Firm-Fixed-Price"),
        ]
        return [
            {
                "piid": piid,
                "vendor_name": vendor,
                "agency": "DHS/TSA",
                "naics": naics_code,
                "psc": psc,
                "obligated_amount": amount,
                "contract_type": ctype,
                "pop_start": "2024-10-01",
                "pop_end": "2025-09-30",
                "source": f"Fallback comparable PIID {piid}",
            }
            for piid, vendor, amount, ctype in base
        ]
