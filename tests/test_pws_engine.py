from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app

SAMPLE_SOW = (
    "The contractor shall provide five (5) full-time equivalent NOC analysts to monitor TSA network "
    "infrastructure on a 24/7 basis. The contractor will ensure adequate cybersecurity protection for all TSA "
    "systems in a workmanlike manner. The contractor shall provide monthly status reports. The contractor should "
    "make best efforts to respond to security incidents promptly."
)


async def request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_convert_sow_catches_required_nlp_flags_and_generates_qasp() -> None:
    status_code, body = await request_json("POST", "/api/v1/pws/convert", {"sow_text": SAMPLE_SOW})
    assert status_code == 200
    assert body["metadata"]["requires_acceptance"] is True
    assert 0 <= body["metadata"]["confidence_score"] <= 1
    assert any("FAR 37.602" in source for source in body["metadata"]["source_provenance"])

    payload = body["content"]
    originals = [flag["original_text"].lower() for flag in payload["flags"]]
    assert any("full-time equivalent" in item or "five (5)" in item for item in originals)
    assert "adequate" in originals
    assert "workmanlike" in originals
    assert "contractor will" in originals
    assert "should" in originals
    assert "best efforts" in originals
    assert "promptly" in originals

    assert all("confidence_score" in flag for flag in payload["flags"])
    assert "3.1" in payload["structured_pws"]
    assert len(payload["qasp_items"]) == 4
    assert len(payload["prs_matrix"]) == 4
    assert len(payload["redlines"]) == 4


@pytest.mark.asyncio
async def test_template_listing_and_generation_work() -> None:
    list_status, list_body = await request_json("GET", "/api/v1/pws/templates")
    assert list_status == 200
    assert len(list_body["templates"]) >= 2

    gen_status, gen_body = await request_json(
        "POST",
        "/api/v1/pws/generate-from-template",
        {"template_id": "noc-operations", "customization": {}},
    )
    assert gen_status == 200
    assert gen_body["metadata"]["requires_acceptance"] is True
    assert gen_body["content"]["template_id"] == "noc-operations"
    assert "3.1" in gen_body["content"]["generated_pws"]
    assert len(gen_body["content"]["qasp_items"]) >= 3
    assert len(gen_body["content"]["prs_matrix"]) >= 3
