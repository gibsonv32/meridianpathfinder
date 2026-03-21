"""
Tango Entities Test Suite
=========================
Tests for the entity lookup service: models, client parsing, router endpoints.
All tests use mocked HTTP responses — no live API calls.

Run:  python3 -m pytest backend/phase2/tango_entities/test_tango_entities.py -q
"""
from __future__ import annotations

import json
import pytest
from dataclasses import asdict
from typing import Any
from unittest.mock import MagicMock, patch

from .models import (
    Address,
    BusinessType,
    EntityProfile,
    EntitySearchResult,
    SB_TYPE_CODES,
)
from .client import TangoEntityClient
from ..tango_common import (
    TangoConfig,
    TangoError,
    TangoAuthError,
    TangoNotFoundError,
    TangoRateLimitError,
)


# ---------------------------------------------------------------------------
# Fixtures — sample Tango API responses
# ---------------------------------------------------------------------------

SAMPLE_ENTITY_RAW: dict[str, Any] = {
    "uei": "U4LVEH1UKWL8",
    "legal_business_name": "BOOZ ALLEN HAMILTON INC.",
    "dba_name": "Booz Allen",
    "entity_url": "https://www.boozallen.com",
    "cage_code": "17038",
    "primary_naics": "541611",
    "business_types": [
        {"code": "2X", "description": "For Profit Organization"},
        {"code": "F", "description": "Business or Organization"},
    ],
    "sba_business_types": None,
    "physical_address": {
        "city": "McLean",
        "state_or_province_code": "VA",
        "zip_code": "22102",
        "zip_code_plus4": "7901",
        "country_code": "USA",
        "address_line1": "8283 Greensboro Dr",
        "address_line2": "",
    },
    "purpose_of_registration": {"code": "Z2", "description": "All Awards"},
}

SAMPLE_SB_ENTITY_RAW: dict[str, Any] = {
    "uei": "ABC123DEF456",
    "legal_business_name": "VETERAN TECH SOLUTIONS LLC",
    "dba_name": "",
    "entity_url": "https://www.vetstech.com",
    "cage_code": "99ZZZ",
    "primary_naics": "541512",
    "business_types": [
        {"code": "27", "description": "Self Certified Small Disadvantaged Business"},
        {"code": "A5", "description": "Veteran Owned Business"},
        {"code": "QF", "description": "Service Disabled Veteran Owned Business"},
        {"code": "2X", "description": "For Profit Organization"},
        {"code": "F", "description": "Business or Organization"},
    ],
    "sba_business_types": [
        {"code": "8A", "description": "8(a) Program Participant"},
    ],
    "physical_address": {
        "city": "Reston",
        "state_or_province_code": "VA",
        "zip_code": "20190",
        "zip_code_plus4": "",
        "country_code": "USA",
        "address_line1": "123 Innovation Way",
        "address_line2": "Suite 400",
    },
    "purpose_of_registration": {"code": "Z2", "description": "All Awards"},
}

SAMPLE_LIST_RESPONSE: dict[str, Any] = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [SAMPLE_ENTITY_RAW, SAMPLE_SB_ENTITY_RAW],
}

SAMPLE_PAGINATED_RESPONSE: dict[str, Any] = {
    "count": 150,
    "next": "https://tango.makegov.com/api/entities/?page=2&page_size=10&search=test",
    "previous": None,
    "results": [SAMPLE_ENTITY_RAW],
}


# ===========================================================================
# Model Tests
# ===========================================================================

class TestBusinessType:
    """Tests for BusinessType model."""

    def test_sb_code_recognized(self):
        bt = BusinessType(code="QF", description="SDVOSB")
        assert bt.is_small_business() is True
        assert bt.sb_category() == "SDVOSB"

    def test_non_sb_code(self):
        bt = BusinessType(code="2X", description="For Profit Organization")
        assert bt.is_small_business() is False
        assert bt.sb_category() == ""

    def test_all_sb_codes_mapped(self):
        """Every code in SB_TYPE_CODES should produce a non-empty category."""
        for code, category in SB_TYPE_CODES.items():
            bt = BusinessType(code=code, description="test")
            assert bt.is_small_business() is True
            assert bt.sb_category() == category
            assert len(category) > 0

    def test_veteran_code(self):
        bt = BusinessType(code="A5", description="Veteran Owned Business")
        assert bt.is_small_business() is True
        assert bt.sb_category() == "VOSB"

    def test_wosb_code(self):
        bt = BusinessType(code="8W", description="Woman Owned Small Business")
        assert bt.is_small_business() is True
        assert bt.sb_category() == "WOSB"


class TestAddress:
    """Tests for Address model."""

    def test_state_city_both_present(self):
        addr = Address(city="McLean", state="VA")
        assert addr.state_city == "McLean, VA"

    def test_state_city_only_city(self):
        addr = Address(city="McLean", state="")
        assert addr.state_city == "McLean"

    def test_state_city_only_state(self):
        addr = Address(city="", state="VA")
        assert addr.state_city == "VA"

    def test_state_city_empty(self):
        addr = Address()
        assert addr.state_city == ""


class TestEntityProfile:
    """Tests for EntityProfile model."""

    def test_parse_large_contractor(self):
        """Booz Allen — large business, no SB categories."""
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        assert profile.uei == "U4LVEH1UKWL8"
        assert profile.legal_business_name == "BOOZ ALLEN HAMILTON INC."
        assert profile.dba_name == "Booz Allen"
        assert profile.cage_code == "17038"
        assert profile.primary_naics == "541611"
        assert profile.is_small_business is False
        assert profile.small_business_categories == []
        assert profile.address.city == "McLean"
        assert profile.address.state == "VA"
        assert profile.display_name == "Booz Allen"

    def test_parse_small_business(self):
        """Veteran Tech Solutions — SDVOSB + SDB."""
        profile = TangoEntityClient._parse_entity(SAMPLE_SB_ENTITY_RAW)
        assert profile.uei == "ABC123DEF456"
        assert profile.is_small_business is True
        cats = profile.small_business_categories
        assert "SDB" in cats
        assert "SDVOSB" in cats
        assert "VOSB" in cats

    def test_display_name_uses_dba(self):
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        assert profile.display_name == "Booz Allen"

    def test_display_name_falls_back_to_legal(self):
        profile = TangoEntityClient._parse_entity(SAMPLE_SB_ENTITY_RAW)
        assert profile.display_name == "VETERAN TECH SOLUTIONS LLC"

    def test_to_summary(self):
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        summary = profile.to_summary()
        assert summary["uei"] == "U4LVEH1UKWL8"
        assert summary["name"] == "Booz Allen"
        assert summary["location"] == "McLean, VA"
        assert summary["is_small_business"] is False
        assert isinstance(summary["sb_categories"], list)

    def test_null_business_types(self):
        """Handle null business_types gracefully."""
        raw = {**SAMPLE_ENTITY_RAW, "business_types": None}
        profile = TangoEntityClient._parse_entity(raw)
        assert profile.business_types == []
        assert profile.is_small_business is False

    def test_null_address(self):
        """Handle null physical_address gracefully."""
        raw = {**SAMPLE_ENTITY_RAW, "physical_address": None}
        profile = TangoEntityClient._parse_entity(raw)
        assert profile.address.city == ""
        assert profile.address.state_city == ""

    def test_null_optional_fields(self):
        """Handle null optional string fields."""
        raw = {
            "uei": "TEST1",
            "legal_business_name": "TEST CORP",
            "dba_name": None,
            "entity_url": None,
            "cage_code": None,
            "primary_naics": None,
            "business_types": None,
            "sba_business_types": None,
            "physical_address": None,
            "purpose_of_registration": None,
        }
        profile = TangoEntityClient._parse_entity(raw)
        assert profile.uei == "TEST1"
        assert profile.dba_name == ""
        assert profile.entity_url == ""
        assert profile.cage_code == ""
        assert profile.primary_naics == ""

    def test_sba_business_types_parsed(self):
        profile = TangoEntityClient._parse_entity(SAMPLE_SB_ENTITY_RAW)
        assert len(profile.sba_business_types) == 1
        assert profile.sba_business_types[0].code == "8A"


# ===========================================================================
# Client Tests (mocked HTTP)
# ===========================================================================

class TestTangoEntityClient:
    """Tests for TangoEntityClient with mocked HTTP responses."""

    def _make_client(self) -> TangoEntityClient:
        config = TangoConfig(api_key="test-key", rate_limit=0)
        return TangoEntityClient(config)

    @patch.object(TangoEntityClient, "_request")
    def test_search_entities(self, mock_request):
        mock_request.return_value = SAMPLE_LIST_RESPONSE
        client = self._make_client()
        result = client.search_entities("Booz Allen")

        assert result.total_count == 2
        assert len(result.profiles) == 2
        assert result.profiles[0].uei == "U4LVEH1UKWL8"
        assert result.query == "Booz Allen"
        assert result.has_next is False
        mock_request.assert_called_once_with(
            "GET", "/entities/",
            params={"search": "Booz Allen", "page": 1, "page_size": 10},
        )

    @patch.object(TangoEntityClient, "_request")
    def test_search_pagination(self, mock_request):
        mock_request.return_value = SAMPLE_PAGINATED_RESPONSE
        client = self._make_client()
        result = client.search_entities("test", page=1, page_size=10)

        assert result.total_count == 150
        assert result.has_next is True
        assert len(result.profiles) == 1

    @patch.object(TangoEntityClient, "_request")
    def test_search_empty_results(self, mock_request):
        mock_request.return_value = {"count": 0, "next": None, "previous": None, "results": []}
        client = self._make_client()
        result = client.search_entities("nonexistent-company-xyz")

        assert result.total_count == 0
        assert result.profiles == []
        assert result.has_next is False

    @patch.object(TangoEntityClient, "_request")
    def test_get_entity(self, mock_request):
        mock_request.return_value = SAMPLE_ENTITY_RAW
        client = self._make_client()
        profile = client.get_entity("U4LVEH1UKWL8")

        assert profile.uei == "U4LVEH1UKWL8"
        assert profile.legal_business_name == "BOOZ ALLEN HAMILTON INC."
        mock_request.assert_called_once_with("GET", "/entities/U4LVEH1UKWL8/")

    @patch.object(TangoEntityClient, "_request")
    def test_get_entity_not_found(self, mock_request):
        mock_request.side_effect = TangoNotFoundError("Not found")
        client = self._make_client()
        with pytest.raises(TangoNotFoundError):
            client.get_entity("INVALID_UEI")

    @patch.object(TangoEntityClient, "_request")
    def test_health_check_success(self, mock_request):
        mock_request.return_value = {"count": 1, "results": []}
        client = self._make_client()
        assert client.health_check() is True

    @patch.object(TangoEntityClient, "_request")
    def test_health_check_failure(self, mock_request):
        mock_request.side_effect = TangoError("Connection failed")
        client = self._make_client()
        assert client.health_check() is False

    @patch.object(TangoEntityClient, "_request")
    def test_auth_error(self, mock_request):
        mock_request.side_effect = TangoAuthError("Bad key")
        client = self._make_client()
        with pytest.raises(TangoAuthError):
            client.search_entities("test")

    @patch.object(TangoEntityClient, "_request")
    def test_rate_limit_error(self, mock_request):
        mock_request.side_effect = TangoRateLimitError("Too many requests")
        client = self._make_client()
        with pytest.raises(TangoRateLimitError):
            client.search_entities("test")


# ===========================================================================
# Router Tests (mocked client)
# ===========================================================================

class TestEntitiesRouter:
    """Tests for FastAPI router endpoints with mocked client."""

    def _mock_client(self):
        """Create a mock client and patch it into the router."""
        from . import router as router_module
        mock = MagicMock(spec=TangoEntityClient)
        mock._config = TangoConfig(api_key="test-key")
        router_module._client = mock
        return mock

    def _reset_client(self):
        from . import router as router_module
        router_module._client = None

    def test_health_endpoint(self):
        mock = self._mock_client()
        mock.health_check.return_value = True
        from .router import entities_health
        resp = entities_health()
        assert resp.tango_entities_reachable is True
        assert resp.api_key_configured is True
        self._reset_client()

    def test_health_unreachable(self):
        mock = self._mock_client()
        mock.health_check.side_effect = Exception("down")
        from .router import entities_health
        resp = entities_health()
        assert resp.tango_entities_reachable is False
        self._reset_client()

    def test_search_endpoint(self):
        mock = self._mock_client()
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        mock.search_entities.return_value = EntitySearchResult(
            profiles=[profile],
            total_count=1,
            page=1,
            page_size=10,
            has_next=False,
            query="Booz Allen",
        )
        from .router import search_entities
        resp = search_entities(q="Booz Allen", page=1, page_size=10)
        assert resp.total_count == 1
        assert len(resp.results) == 1
        assert resp.results[0].uei == "U4LVEH1UKWL8"
        self._reset_client()

    def test_search_auth_error(self):
        mock = self._mock_client()
        mock.search_entities.side_effect = TangoAuthError("Bad key")
        from .router import search_entities
        with pytest.raises(Exception) as exc_info:
            search_entities(q="test", page=1, page_size=10)
        assert "503" in str(exc_info.value.status_code)
        self._reset_client()

    def test_search_rate_limit(self):
        mock = self._mock_client()
        mock.search_entities.side_effect = TangoRateLimitError("Rate limited")
        from .router import search_entities
        with pytest.raises(Exception) as exc_info:
            search_entities(q="test", page=1, page_size=10)
        assert "429" in str(exc_info.value.status_code)
        self._reset_client()

    def test_get_by_uei_endpoint(self):
        mock = self._mock_client()
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        mock.get_entity.return_value = profile
        from .router import get_entity_by_uei
        resp = get_entity_by_uei("U4LVEH1UKWL8")
        assert resp["uei"] == "U4LVEH1UKWL8"
        assert resp["name"] == "Booz Allen"
        self._reset_client()

    def test_get_by_uei_not_found(self):
        mock = self._mock_client()
        mock.get_entity.side_effect = TangoNotFoundError("Not found")
        from .router import get_entity_by_uei
        with pytest.raises(Exception) as exc_info:
            get_entity_by_uei("INVALID")
        assert "404" in str(exc_info.value.status_code)
        self._reset_client()

    def test_lookup_protester_endpoint(self):
        mock = self._mock_client()
        profile = TangoEntityClient._parse_entity(SAMPLE_SB_ENTITY_RAW)
        mock.search_entities.return_value = EntitySearchResult(
            profiles=[profile],
            total_count=1,
            page=1,
            page_size=5,
            has_next=False,
            query="Veteran Tech Solutions",
        )
        from .router import lookup_protester, ProtesterLookupRequest
        req = ProtesterLookupRequest(protester_name="Veteran Tech Solutions")
        resp = lookup_protester(req)
        assert resp["protester_name"] == "Veteran Tech Solutions"
        assert resp["matches_found"] == 1
        assert resp["results"][0]["is_small_business"] is True
        assert resp["evidence_tier"] == "structured_third_party"
        self._reset_client()

    def test_lookup_protester_no_matches(self):
        mock = self._mock_client()
        mock.search_entities.return_value = EntitySearchResult(
            profiles=[],
            total_count=0,
            page=1,
            page_size=5,
            has_next=False,
            query="Nonexistent Corp",
        )
        from .router import lookup_protester, ProtesterLookupRequest
        req = ProtesterLookupRequest(protester_name="Nonexistent Corp")
        resp = lookup_protester(req)
        assert resp["matches_found"] == 0
        assert resp["results"] == []
        self._reset_client()


# ===========================================================================
# Cross-reference Tests (protest → entity enrichment)
# ===========================================================================

class TestProtestEntityCrossReference:
    """Tests for the cross-reference use case: protest protester → entity profile."""

    def test_protester_name_to_search_query(self):
        """A protester name from a protest case can be used as a search query."""
        # Simulate: protest case has protester="BOOZ ALLEN HAMILTON INC."
        protester_name = "BOOZ ALLEN HAMILTON INC."
        # The search should find the entity
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        assert profile.legal_business_name == protester_name

    def test_sb_enrichment_for_risk_scoring(self):
        """Small business data feeds PF03 (contractor risk factor)."""
        profile = TangoEntityClient._parse_entity(SAMPLE_SB_ENTITY_RAW)
        # This data would feed into the protest risk scoring engine
        risk_data = {
            "is_small_business": profile.is_small_business,
            "sb_categories": profile.small_business_categories,
            "naics": profile.primary_naics,
            "location": profile.address.state_city,
        }
        assert risk_data["is_small_business"] is True
        assert len(risk_data["sb_categories"]) >= 2
        assert risk_data["naics"] == "541512"

    def test_large_business_no_sb_enrichment(self):
        """Large businesses should not have SB categories."""
        profile = TangoEntityClient._parse_entity(SAMPLE_ENTITY_RAW)
        assert profile.is_small_business is False
        assert profile.small_business_categories == []

    def test_summary_format_for_dashboard(self):
        """Summary dict is the format used by the CO dashboard risk card."""
        profile = TangoEntityClient._parse_entity(SAMPLE_SB_ENTITY_RAW)
        summary = profile.to_summary()
        # Dashboard needs these fields
        required_fields = {"uei", "name", "legal_name", "cage_code",
                          "primary_naics", "location", "is_small_business",
                          "sb_categories"}
        assert required_fields.issubset(summary.keys())
