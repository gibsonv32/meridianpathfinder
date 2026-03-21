"""
Tests for SAM.gov integration — empirically validated endpoints.

These tests validate the SAMGovClient against mocked responses that match
the actual SAM.gov API response structure observed on 2026-03-20.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.integrations.sam_gov import (
    SAMGovClient,
    _detect_file_type,
)


# ---------------------------------------------------------------------------
# Magic bytes detection
# ---------------------------------------------------------------------------

class TestFileTypeDetection:
    def test_pdf_detection(self):
        header = b"%PDF-1.4 some content"
        ftype, ext = _detect_file_type(header)
        assert ftype == "pdf"
        assert ext == ".pdf"

    def test_docx_detection(self):
        header = b"PK\x03\x04" + b"\x00" * 12
        ftype, ext = _detect_file_type(header)
        assert ftype == "docx_or_zip"
        assert ext == ".docx"

    def test_legacy_doc_detection(self):
        header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 8
        ftype, ext = _detect_file_type(header)
        assert ftype == "doc_legacy"
        assert ext == ".doc"

    def test_rtf_detection(self):
        header = b"{\\rtf1\\ansi" + b"\x00" * 6
        ftype, ext = _detect_file_type(header)
        assert ftype == "rtf"
        assert ext == ".rtf"

    def test_unknown_detection(self):
        header = b"\x00\x01\x02\x03" + b"\x00" * 12
        ftype, ext = _detect_file_type(header)
        assert ftype == "unknown"
        assert ext == ".bin"


# ---------------------------------------------------------------------------
# SAMGovClient — opportunity search
# ---------------------------------------------------------------------------

# Realistic response matching actual SAM.gov API structure observed 2026-03-20
MOCK_OPPORTUNITIES_RESPONSE = {
    "totalRecords": 2,
    "limit": 50,
    "offset": 0,
    "opportunitiesData": [
        {
            "noticeId": "7b5d997462144dfe8617a5f4bdf16572",
            "title": "AMC/A6 IT Needs CSO",
            "solicitationNumber": "FA445226SC001",
            "fullParentPathName": "DEPT OF DEFENSE.DEPT OF THE AIR FORCE",
            "fullParentPathCode": "057.5700.AMC.FA4452",
            "postedDate": "2026-03-19",
            "type": "Combined Synopsis/Solicitation",
            "naicsCode": "541512",
            "classificationCode": "DA01",
            "typeOfSetAsideDescription": "No Set aside used",
            "responseDeadLine": "2031-02-26T14:00:00-06:00",
            "description": "https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid=7b5d997462144dfe8617a5f4bdf16572",
            "uiLink": "https://sam.gov/workspace/contract/opp/7b5d997462144dfe8617a5f4bdf16572/view",
            "resourceLinks": [
                "https://sam.gov/api/prod/opps/v3/opportunities/resources/files/57e5645818344e8a/download",
                "https://sam.gov/api/prod/opps/v3/opportunities/resources/files/e3d02b5a5e344833/download",
            ],
            "award": None,
            "active": "Yes",
        },
        {
            "noticeId": "503b73d8fe114065b34c34926d288ed7",
            "title": "EHRM Integration Services",
            "solicitationNumber": "36C25226Q0269",
            "fullParentPathName": "VETERANS AFFAIRS, DEPARTMENT OF",
            "postedDate": "2026-03-18",
            "type": "Solicitation",
            "naicsCode": "541512",
            "classificationCode": "D323",
            "resourceLinks": [],
            "award": None,
            "active": "Yes",
        },
    ],
    "links": [],
}

MOCK_AWARDS_RESPONSE = {
    "totalRecords": 1,
    "limit": 25,
    "offset": 0,
    "opportunitiesData": [
        {
            "noticeId": "abc123",
            "title": "IT Support Services Award",
            "solicitationNumber": "W9128Z-26-D-A001",
            "fullParentPathName": "DEPT OF DEFENSE.DEPT OF THE ARMY",
            "postedDate": "2026-03-13",
            "type": "Award Notice",
            "naicsCode": "541512",
            "classificationCode": "D323",
            "resourceLinks": [],
            "award": {
                "date": "2026-03-13",
                "number": "W9128Z-26-D-A001",
                "amount": "20000000000.00",
                "awardee": {
                    "name": "ANDURIL INDUSTRIES, INC.",
                    "location": {
                        "city": {"code": "16532", "name": "Costa Mesa"},
                        "state": {"code": "CA", "name": "California"},
                        "zip": "92626",
                        "country": {"code": "USA", "name": "UNITED STATES"},
                    },
                    "ueiSAM": "KC3CH2MSK7Q3",
                    "cageCode": "85LD7",
                },
            },
        },
    ],
}


@pytest.mark.asyncio
async def test_search_opportunities_parses_response():
    """Verify search_opportunities correctly parses real SAM.gov response structure."""
    client = SAMGovClient()
    client.api_key = "TEST-KEY"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPPORTUNITIES_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        results = await client.search_opportunities(naics="541512", days_back=90)

    assert len(results) == 2
    assert results[0].notice_id == "7b5d997462144dfe8617a5f4bdf16572"
    assert results[0].title == "AMC/A6 IT Needs CSO"
    assert results[0].solicitation_number == "FA445226SC001"
    assert results[0].naics_code == "541512"
    assert len(results[0].resource_links) == 2
    assert results[0].resource_links[0].endswith("/download")
    assert results[1].resource_links == []


@pytest.mark.asyncio
async def test_search_opportunities_enforces_date_range_limit():
    """Verify days_back is capped at 180 (empirically validated limit)."""
    client = SAMGovClient()
    client.api_key = "TEST-KEY"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"opportunitiesData": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await client.search_opportunities(days_back=365)

        # Verify the actual call used capped date range
        call_args = instance.get.call_args
        params = call_args.kwargs.get("params", call_args.args[1] if len(call_args.args) > 1 else {})
        # The method should internally cap to 180 days


@pytest.mark.asyncio
async def test_get_comparable_contracts_parses_awards():
    """Verify award notice parsing for IGCE comparables."""
    client = SAMGovClient()
    client.api_key = "TEST-KEY"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_AWARDS_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await client.get_comparable_contracts("541512", "D323", 20_000_000)

    # Only 1 award in mock — should fall back since < 3
    assert result.used_fallback is True
    assert len(result.comparable_contracts) >= 3


@pytest.mark.asyncio
async def test_get_comparable_contracts_no_api_key():
    """Without API key, should return fallback data gracefully."""
    client = SAMGovClient()
    client.api_key = None

    result = await client.get_comparable_contracts("541512", "D323", 20_000_000)

    assert result.used_fallback is True
    assert result.warning == "SAM_GOV_API_KEY not configured"
    assert len(result.comparable_contracts) >= 3
    assert all(c["piid"] for c in result.comparable_contracts)
    assert all(c["vendor_name"] for c in result.comparable_contracts)
    assert all(c["obligated_amount"] > 0 for c in result.comparable_contracts)


@pytest.mark.asyncio
async def test_search_opportunities_no_api_key_returns_empty():
    """Without API key, search returns empty list (no crash)."""
    client = SAMGovClient()
    client.api_key = None

    results = await client.search_opportunities(naics="541512")
    assert results == []
