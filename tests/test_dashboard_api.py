from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


async def request_json(path: str) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_work_queue_returns_7_seeded_packages_sorted_by_urgency() -> None:
    status_code, body = await request_json("/api/v1/packages?status=blocked,action,ready")
    assert status_code == 200
    # Filter to demo packages only (other tests may create additional packages)
    demo_items = [item for item in body["items"] if item["package_id"].startswith("demo-")]
    assert len(demo_items) == 7
    assert [item["status"] for item in body["items"][:3]] == ["blocked", "blocked", "blocked"]
    assert body["items"][0]["package_id"] == "demo-007"


@pytest.mark.asyncio
async def test_package_detail_returns_documents_and_source_attribution() -> None:
    status_code, body = await request_json("/api/v1/packages/demo-001")
    assert status_code == 200
    assert body["package_id"] == "demo-001"
    assert len(body["documents"]) == 8
    assert body["blocking_reason"] == "D114 CIO approval missing"
    assert len(body["source_attribution"]) > 0
