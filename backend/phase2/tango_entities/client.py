"""
Tango Entity Client
===================
HTTP adapter for the Tango (MakeGov) entities API.

Provides contractor/entity search and lookup by UEI.
Uses the shared BaseTangoClient for connection management.
"""
from __future__ import annotations

import logging
from dataclasses import field
from typing import Any

from ..tango_common import (
    BaseTangoClient,
    TangoConfig,
    TangoError,
    TangoNotFoundError,
)
from .models import (
    Address,
    BusinessType,
    EntityProfile,
    EntitySearchResult,
)

logger = logging.getLogger(__name__)


class TangoEntityClient(BaseTangoClient):
    """
    HTTP adapter for the Tango entities endpoint.

    Usage:
        client = TangoEntityClient(TangoConfig.from_env())
        results = client.search_entities("Booz Allen")
        profile = client.get_entity("U4LVEH1UKWL8")
    """

    def search_entities(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> EntitySearchResult:
        """
        Search entities by name (legal name or DBA).

        The Tango API's `search` parameter does full-text matching
        against legal_business_name and dba_name.
        """
        params: dict[str, Any] = {
            "search": query,
            "page": page,
            "page_size": page_size,
        }

        data = self._request("GET", "/entities/", params=params)
        profiles = [self._parse_entity(r) for r in data.get("results", [])]

        return EntitySearchResult(
            profiles=profiles,
            total_count=data.get("count", len(profiles)),
            page=page,
            page_size=page_size,
            has_next=data.get("next") is not None,
            query=query,
        )

    def get_entity(self, uei: str) -> EntityProfile:
        """Retrieve a single entity by UEI."""
        data = self._request("GET", f"/entities/{uei}/")
        return self._parse_entity(data)

    def health_check(self) -> bool:
        """Quick connectivity test — returns True if entities API is reachable."""
        try:
            self._request("GET", "/entities/", params={"page": 1, "page_size": 1})
            return True
        except TangoError:
            return False

    # -- parsing --

    @staticmethod
    def _parse_entity(raw: dict[str, Any]) -> EntityProfile:
        """Parse a raw Tango entity JSON object into an EntityProfile."""
        # Business types
        business_types = []
        for bt in (raw.get("business_types") or []):
            if isinstance(bt, dict):
                business_types.append(BusinessType(
                    code=bt.get("code", ""),
                    description=bt.get("description", ""),
                ))

        # SBA business types
        sba_types = []
        for bt in (raw.get("sba_business_types") or []):
            if isinstance(bt, dict):
                sba_types.append(BusinessType(
                    code=bt.get("code", ""),
                    description=bt.get("description", ""),
                ))

        # Address
        addr_raw = raw.get("physical_address") or {}
        address = Address(
            address_line1=addr_raw.get("address_line1", ""),
            address_line2=addr_raw.get("address_line2", ""),
            city=addr_raw.get("city", ""),
            state=addr_raw.get("state_or_province_code", ""),
            zip_code=addr_raw.get("zip_code", ""),
            zip_plus4=addr_raw.get("zip_code_plus4", ""),
            country_code=addr_raw.get("country_code", "USA"),
        )

        # Purpose of registration
        por = raw.get("purpose_of_registration") or {}
        por_desc = por.get("description", "") or por.get("code", "")

        return EntityProfile(
            uei=raw.get("uei", ""),
            legal_business_name=raw.get("legal_business_name", "").strip(),
            dba_name=(raw.get("dba_name") or "").strip(),
            entity_url=(raw.get("entity_url") or ""),
            cage_code=(raw.get("cage_code") or ""),
            primary_naics=(raw.get("primary_naics") or ""),
            purpose_of_registration=por_desc,
            business_types=business_types,
            sba_business_types=sba_types,
            address=address,
            raw_payload=raw,
        )
