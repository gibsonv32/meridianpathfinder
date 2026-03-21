from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app

PACKAGE_PAYLOAD = {
    "title": "R5 Document Persistence Package",
    "value": 20000000,
    "naics": "541512",
    "psc": "D323",
    "services": True,
    "it_related": True,
    "sole_source": False,
    "commercial_item": False,
    "competition_type": "full_and_open",
}

SOW_PAYLOAD = {
    "sow_text": (
        "The contractor shall provide five (5) full-time equivalent NOC analysts to monitor TSA network "
        "infrastructure on a 24/7 basis. The contractor will ensure adequate cybersecurity protection for all TSA "
        "systems in a workmanlike manner. The contractor shall provide monthly status reports. The contractor should "
        "make best efforts to respond to security incidents promptly."
    )
}

IGCE_PAYLOAD = {
    "title": "TSA Cybersecurity Operations Support IGCE",
    "naics_code": "541512",
    "psc": "D323",
    "estimated_value": 20000000,
    "contract_type": "firm_fixed_price",
    "labor_categories": [{"title": "Cybersecurity Analyst", "estimated_hours": 4160}],
}


async def request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_pws_persists_to_db_and_is_retrievable() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200

    status_code, body = await request_json(
        "POST",
        "/api/v1/pws/convert",
        {**SOW_PAYLOAD, "package_id": package["package_id"]},
    )
    assert status_code == 200
    document_id = body["document_id"]

    get_status, fetched = await request_json("GET", f"/api/v1/documents/{document_id}")
    assert get_status == 200
    assert fetched["document_id"] == document_id
    assert fetched["package_id"] == package["package_id"]
    assert fetched["dcode"] == "D109"
    assert fetched["acceptance_status"] == "pending"
    assert fetched["content"]["structured_pws"] == body["content"]["structured_pws"]


@pytest.mark.asyncio
async def test_igce_persists_to_db_and_is_retrievable() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200

    status_code, body = await request_json(
        "POST",
        "/api/v1/igce/generate",
        {**IGCE_PAYLOAD, "package_id": package["package_id"]},
    )
    assert status_code == 200
    document_id = body["document_id"]

    get_status, fetched = await request_json("GET", f"/api/v1/documents/{document_id}")
    assert get_status == 200
    assert fetched["document_id"] == document_id
    assert fetched["dcode"] == "D104"
    assert fetched["content"]["title"] == IGCE_PAYLOAD["title"]


@pytest.mark.asyncio
async def test_document_accept_updates_package_completeness() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200
    package_id = package["package_id"]

    gen_status, generated = await request_json(
        "POST",
        "/api/v1/pws/convert",
        {**SOW_PAYLOAD, "package_id": package_id},
    )
    assert gen_status == 200

    pending_status, pending = await request_json("GET", f"/api/v1/packages/{package_id}/completeness")
    assert pending_status == 200
    assert any(doc["dcode"] == "D109" and doc["status"] == "pending" for doc in pending["documents"])

    accept_status, accepted = await request_json(
        "POST",
        f"/api/v1/documents/{generated['document_id']}/accept",
        {"actor": "vince"},
    )
    assert accept_status == 200
    assert accepted["acceptance_status"] == "accepted"

    completeness_status, completeness = await request_json("GET", f"/api/v1/packages/{package_id}/completeness")
    assert completeness_status == 200
    assert any(doc["dcode"] == "D109" and doc["status"] == "satisfied" for doc in completeness["documents"])


@pytest.mark.asyncio
async def test_document_modify_creates_version_history() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200

    gen_status, generated = await request_json(
        "POST",
        "/api/v1/pws/convert",
        {**SOW_PAYLOAD, "package_id": package["package_id"]},
    )
    assert gen_status == 200

    modify_status, modified = await request_json(
        "POST",
        f"/api/v1/documents/{generated['document_id']}/modify",
        {
            "actor": "vince",
            "content": {"structured_pws": "Modified PWS body"},
            "rationale": "Clarified language",
        },
    )
    assert modify_status == 200
    assert modified["version"] == 2
    assert modified["parent_document_id"] == generated["document_id"]
    assert modified["acceptance_status"] == "modified"

    versions_status, versions = await request_json("GET", f"/api/v1/documents/{generated['document_id']}/versions")
    assert versions_status == 200
    assert len(versions["versions"]) == 2
    assert [item["version"] for item in versions["versions"]] == [1, 2]


@pytest.mark.asyncio
async def test_document_override_requires_rationale() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200

    gen_status, generated = await request_json(
        "POST",
        "/api/v1/pws/convert",
        {**SOW_PAYLOAD, "package_id": package["package_id"]},
    )
    assert gen_status == 200

    override_status, _ = await request_json(
        "POST",
        f"/api/v1/documents/{generated['document_id']}/override",
        {"actor": "vince", "content": {"structured_pws": "Override body"}},
    )
    assert override_status == 422


@pytest.mark.asyncio
async def test_package_documents_endpoint_lists_generated_docs() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200
    package_id = package["package_id"]

    pws_status, _ = await request_json("POST", "/api/v1/pws/convert", {**SOW_PAYLOAD, "package_id": package_id})
    igce_status, _ = await request_json("POST", "/api/v1/igce/generate", {**IGCE_PAYLOAD, "package_id": package_id})
    assert pws_status == 200
    assert igce_status == 200

    list_status, listing = await request_json("GET", f"/api/v1/packages/{package_id}/documents")
    assert list_status == 200
    assert listing["package_id"] == package_id
    assert {doc["dcode"] for doc in listing["documents"]} == {"D104", "D109"}
