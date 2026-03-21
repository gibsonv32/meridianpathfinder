from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.audit.audit_service import ImmutableAuditError
from backend.main import app

PACKAGE_PAYLOAD = {
    "title": "Task 7 Audit Demo Package",
    "value": 20000000,
    "naics": "541512",
    "psc": "D323",
    "services": True,
    "it_related": True,
    "sole_source": False,
    "commercial_item": False,
    "competition_type": "full_and_open",
}

SOW_TEXT = "The contractor shall provide five (5) full-time equivalent NOC analysts to monitor TSA network infrastructure on a 24/7 basis. The contractor will ensure adequate cybersecurity protection for all TSA systems in a workmanlike manner. The contractor shall provide monthly status reports. The contractor should make best efforts to respond to security incidents promptly."


async def request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(method, path, json=payload)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_audit_trail_captures_create_generate_accept_modify_override_and_export() -> None:
    create_status, package = await request_json("POST", "/api/v1/packages", PACKAGE_PAYLOAD)
    assert create_status == 200
    package_id = package["package_id"]

    pws_status, _ = await request_json("POST", "/api/v1/pws/convert", {"sow_text": SOW_TEXT, "package_id": package_id})
    assert pws_status == 200

    stream_status, stream = await request_json("GET", f"/api/v1/audit/{package_id}")
    assert stream_status == 200
    generated_events = [event for event in stream["events"] if event["action_type"] == "generate"]
    assert generated_events
    document_id = generated_events[-1]["target_id"]

    for section_id in ["3.1", "3.2", "3.3"]:
        status_code, _ = await request_json("POST", f"/api/v1/documents/{document_id}/accept", {"section_id": section_id, "actor": "vince"})
        assert status_code == 200

    modify_status, modified = await request_json(
        "POST",
        f"/api/v1/documents/{document_id}/modify",
        {"content": "Modified PWS content", "actor": "vince", "rationale": "Clarified metric wording"},
    )
    assert modify_status == 200
    assert modified["status"] == "modified"

    override_status, overridden = await request_json(
        "POST",
        f"/api/v1/documents/{document_id}/override",
        {"content": "Override PWS content", "actor": "vince", "rationale": "Human override for program-specific nuance"},
    )
    assert override_status == 200
    assert overridden["status"] == "overridden"

    stream_status, stream = await request_json("GET", f"/api/v1/audit/{package_id}")
    assert stream_status == 200
    actions = [event["action_type"] for event in stream["events"]]
    assert actions.count("create") >= 1
    assert actions.count("generate") >= 1
    assert actions.count("accept") == 3
    assert actions.count("modify") == 1
    assert actions.count("override") >= 1

    export_status, exported = await request_json("POST", "/api/v1/audit/export", {"package_id": package_id})
    assert export_status == 200
    assert exported["event_count"] == len(exported["events"])
    assert exported["event_count"] >= 6
    assert all(event["timestamp"] for event in exported["events"])


def test_audit_table_rejects_update_and_delete() -> None:
    from backend.core.audit.audit_service import audit_service

    with pytest.raises(ImmutableAuditError):
        audit_service.update_event("audit_1", {})
    with pytest.raises(ImmutableAuditError):
        audit_service.delete_event("audit_1")
