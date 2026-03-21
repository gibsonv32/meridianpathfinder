from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.database.db import AsyncSessionLocal
from backend.main import app


async def request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_audit_middleware_captures_post() -> None:
    status_code, body = await request_json(
        "POST",
        "/api/v1/packages",
        {
            "title": "R2 Middleware Package",
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
    package_id = body["package_id"]

    stream_status, stream = await request_json("GET", f"/api/v1/audit/{package_id}")
    assert stream_status == 200
    assert any(event["action_type"] == "create" and event["target_type"] == "package" for event in stream["events"])


@pytest.mark.asyncio
async def test_audit_middleware_skips_get() -> None:
    status_code, _ = await request_json("GET", "/api/v1/health")
    assert status_code == 200

    async with AsyncSessionLocal() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM audit_events"))).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_audit_db_rejects_update_delete() -> None:
    status_code, body = await request_json(
        "POST",
        "/api/v1/packages",
        {
            "title": "R2 Audit Lock Package",
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

    async with AsyncSessionLocal() as session:
        event_id = (await session.execute(text("SELECT id FROM audit_events ORDER BY timestamp LIMIT 1"))).scalar_one()
        original = (await session.execute(text("SELECT actor FROM audit_events WHERE id = :id"), {"id": event_id})).scalar_one()
        await session.execute(text("UPDATE audit_events SET actor = 'tampered' WHERE id = :id"), {"id": event_id})
        await session.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id})
        await session.commit()
        actor_after = (await session.execute(text("SELECT actor FROM audit_events WHERE id = :id"), {"id": event_id})).scalar_one()
        count_after = (await session.execute(text("SELECT COUNT(*) FROM audit_events WHERE id = :id"), {"id": event_id})).scalar_one()

    assert actor_after == original
    assert count_after == 1
