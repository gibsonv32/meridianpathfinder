from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


async def request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_create_package_returns_8_required_dcodes_for_20m_it_services() -> None:
    status_code, body = await request_json(
        "POST",
        "/api/v1/packages",
        {
            "title": "TSA Cybersecurity Operations Support",
            "value": 20000000,
            "naics": "541512",
            "psc": "D323",
            "services": True,
            "it_related": True,
            "sole_source": False,
            "commercial_item": False,
            "competition_type": "full_and_open",
        },
    )
    assert status_code == 200
    assert body["required_dcodes"] == [
        "D101",
        "D102",
        "D104",
        "D106",
        "D107",
        "D109",
        "D110",
        "D114",
    ]
    assert body["completeness_summary"] == {"satisfied": 0, "pending": 0, "missing": 8, "total": 8}


@pytest.mark.asyncio
async def test_mark_5_of_8_documents_satisfied_updates_completeness() -> None:
    create_status, create_body = await request_json(
        "POST",
        "/api/v1/packages",
        {
            "title": "TSA Cybersecurity Operations Support",
            "value": 20000000,
            "naics": "541512",
            "psc": "D323",
            "services": True,
            "it_related": True,
            "sole_source": False,
            "commercial_item": False,
            "competition_type": "full_and_open",
        },
    )
    assert create_status == 200
    package_id = create_body["package_id"]

    for dcode in ["D101", "D102", "D104", "D106", "D107"]:
        patch_status, patch_body = await request_json(
            "PATCH",
            f"/api/v1/packages/{package_id}/documents/{dcode}",
            {"status": "satisfied"},
        )
        assert patch_status == 200
        assert any(doc["dcode"] == dcode and doc["status"] == "satisfied" for doc in patch_body["documents"])

    completeness_status, completeness_body = await request_json(
        "GET",
        f"/api/v1/packages/{package_id}/completeness",
    )
    assert completeness_status == 200
    assert completeness_body["completeness_summary"] == {"satisfied": 5, "pending": 0, "missing": 3, "total": 8}
    assert len(completeness_body["required_dcodes"]) == 8
