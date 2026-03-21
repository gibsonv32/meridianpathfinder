from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


async def post_json(path: str, payload: dict) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(path, json=payload)
    return response.status_code, response.json()


async def get_json(path: str) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_thresholds_endpoint_returns_seed_data() -> None:
    status_code, body = await get_json("/api/v1/rules/thresholds")
    assert status_code == 200
    threshold_names = {item["name"] for item in body["thresholds"]}
    assert {
        "sat",
        "micro_purchase",
        "commercial_sap",
        "cost_data",
        "subcontracting_plan",
        "acquisition_plan",
        "ssac_encouraged",
        "ssac_required",
    }.issubset(threshold_names)


@pytest.mark.asyncio
async def test_rules_engine_routes_20m_it_services_procurement() -> None:
    status_code, body = await post_json(
        "/api/v1/rules/evaluate",
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
    assert body["approvers"]["j_and_a"] == "HCA"
    assert body["posting_deadline_days"] == 30
    assert body["tier"]["acquisition_plan_required"] is True


@pytest.mark.asyncio
async def test_admin_threshold_update_preserves_history_and_changes_evaluation() -> None:
    update_status, update_body = await post_json(
        "/api/v1/rules/thresholds",
        {
            "name": "sat",
            "value": 25000000,
            "authority": "Test override",
            "effective_date": "2026-10-01",
            "overlay_level": 3,
        },
    )
    assert update_status == 200
    assert update_body["value"] == 25000000

    thresholds_status, thresholds_body = await get_json("/api/v1/rules/thresholds")
    assert thresholds_status == 200
    sat_rows = [item for item in thresholds_body["thresholds"] if item["name"] == "sat"]
    assert len(sat_rows) == 2

    pre_status, pre_body = await post_json(
        "/api/v1/rules/evaluate",
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
            "as_of_date": "2026-09-30",
        },
    )
    assert pre_status == 200
    assert "D107" in pre_body["required_dcodes"]
    assert pre_body["posting_deadline_days"] == 30

    post_status, post_body = await post_json(
        "/api/v1/rules/evaluate",
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
            "as_of_date": "2026-10-01",
        },
    )
    assert post_status == 200
    assert "D107" not in post_body["required_dcodes"]
    assert post_body["posting_deadline_days"] == 0
