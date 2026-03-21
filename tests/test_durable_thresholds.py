from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


async def get_json(path: str) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code, response.json()


async def put_json(path: str, payload: dict) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_threshold_effective_date_history() -> None:
    pre_status, pre_body = await get_json("/api/v1/rules/thresholds?as_of_date=2025-09-30&active_only=true")
    assert pre_status == 200
    assert not any(item["name"] == "sat" for item in pre_body["thresholds"])

    effective_status, effective_body = await get_json("/api/v1/rules/thresholds?as_of_date=2025-10-01&active_only=true")
    assert effective_status == 200
    sat = next(item for item in effective_body["thresholds"] if item["name"] == "sat")
    assert sat["value"] == 350000


@pytest.mark.asyncio
async def test_threshold_overlay_resolution_prefers_higher_overlay() -> None:
    status_code, body = await put_json(
        "/api/v1/rules/thresholds/acquisition_plan",
        {
            "name": "acquisition_plan",
            "value": 5000000,
            "authority": "TSA MD 300.25",
            "effective_date": "2025-10-01",
            "overlay_level": 3,
        },
    )
    assert status_code == 200
    assert body["overlay_level"] == 3

    thresholds_status, thresholds_body = await get_json("/api/v1/rules/thresholds?as_of_date=2025-10-01&active_only=true")
    assert thresholds_status == 200
    acquisition_plan = next(item for item in thresholds_body["thresholds"] if item["name"] == "acquisition_plan")
    assert acquisition_plan["value"] == 5000000
    assert acquisition_plan["overlay_level"] == 3
