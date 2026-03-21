from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app

PAYLOAD = {
    "title": "TSA Cybersecurity Operations Support IGCE",
    "naics_code": "541512",
    "psc": "D323",
    "estimated_value": 20000000,
    "contract_type": "firm_fixed_price",
    "labor_categories": [
        {"title": "Cybersecurity Analyst", "estimated_hours": 4160},
        {"title": "Network Operations Specialist", "estimated_hours": 4160},
    ],
}


async def request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_generate_igce_returns_comparables_rate_analysis_and_far_methodology() -> None:
    status_code, body = await request_json("POST", "/api/v1/igce/generate", PAYLOAD)
    assert status_code == 200
    assert body["metadata"]["requires_acceptance"] is True
    assert 0 <= body["metadata"]["confidence_score"] <= 1
    assert len(body["content"]["comparable_contracts"]) >= 3
    assert all(item["piid"] for item in body["content"]["comparable_contracts"][:3])
    assert len(body["content"]["rate_analysis"]) >= 2
    assert "FAR 37.102(a)(2)" in body["content"]["methodology"]
    assert any("PIID" in source or "70T0" in source for source in body["metadata"]["source_provenance"])


@pytest.mark.asyncio
async def test_retrieve_generated_igce_by_id() -> None:
    status_code, body = await request_json("POST", "/api/v1/igce/generate", PAYLOAD)
    assert status_code == 200
    get_status, fetched = await request_json("GET", f"/api/v1/igce/{body['document_id']}")
    assert get_status == 200
    assert fetched["document_id"] == body["document_id"]
    assert fetched["content"]["igce_id"] == body["document_id"]
    assert fetched["content"]["title"] == PAYLOAD["title"]


@pytest.mark.asyncio
async def test_sam_gov_failure_falls_back_gracefully() -> None:
    status_code, body = await request_json("POST", "/api/v1/igce/generate", PAYLOAD)
    assert status_code == 200
    assert body["content"]["used_fallback_data"] is True
    assert any("SAM_GOV_API_KEY not configured" in source or "SAM.gov unavailable" in source for source in body["metadata"]["source_provenance"])
