"""Integration tests for PolicyService wiring into the live API.

Validates:
1. V1 /evaluate backward compatibility (existing fields unchanged)
2. V1 /evaluate enrichment (policy_evaluation field present)
3. V2 /evaluate/v2 full PolicyService output
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


async def post_json(path: str, payload: dict) -> tuple[int, dict]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(path, json=payload)
    return resp.status_code, resp.json()


CANONICAL_20M = {
    "title": "TSA Cybersecurity Operations Support",
    "value": 20000000,
    "naics": "541512",
    "psc": "D323",
    "services": True,
    "it_related": True,
    "sole_source": False,
    "commercial_item": False,
    "competition_type": "full_and_open",
}


# ── V1 Backward Compatibility ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_v1_backward_compatible_fields():
    """Existing V1 fields must be identical to pre-migration."""
    status, body = await post_json("/api/v1/rules/evaluate", CANONICAL_20M)
    assert status == 200
    # All original fields still present
    assert body["required_dcodes"] == ["D101", "D102", "D104", "D106", "D107", "D109", "D110", "D114"]
    assert body["approvers"]["j_and_a"] == "HCA"
    assert body["posting_deadline_days"] == 30
    assert body["tier"]["acquisition_plan_required"] is True
    assert body["tier"]["tier_name"] == "major_acquisition"
    assert len(body["authority_chain"]) > 0
    assert len(body["notes"]) > 0


@pytest.mark.asyncio
async def test_v1_enrichment_present():
    """V1 response now includes policy_evaluation enrichment."""
    status, body = await post_json("/api/v1/rules/evaluate", CANONICAL_20M)
    assert status == 200
    pe = body["policy_evaluation"]
    assert pe is not None
    assert pe["tier_name"] == "major_acquisition"
    assert pe["nodes_evaluated"] >= 10
    assert len(pe["qcode_trace"]) >= 10
    assert pe["ja_approver"] == "HCA"
    assert pe["posting_days"] == 30
    assert len(pe["applicable_clauses"]) > 0
    assert "D102" in pe["corrected_dcodes"]
    assert "D114" in pe["corrected_dcodes"]


@pytest.mark.asyncio
async def test_v1_enrichment_has_qcode_trace():
    """Q-code trace entries must have code, question, answer, authority."""
    status, body = await post_json("/api/v1/rules/evaluate", CANONICAL_20M)
    assert status == 200
    for entry in body["policy_evaluation"]["qcode_trace"]:
        assert entry["code"].startswith("Q")
        assert len(entry["question"]) > 0
        assert len(entry["answer"]) > 0
        assert len(entry["authority"]) > 0


# ── V2 Full PolicyService Output ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_v2_endpoint_exists():
    """V2 endpoint should return full PolicyService output."""
    status, body = await post_json("/api/v1/rules/evaluate/v2", CANONICAL_20M)
    assert status == 200
    assert body["tier_name"] == "major_acquisition"
    assert body["posting_deadline_days"] == 30
    assert body["ja_approver"] == "HCA"
    assert len(body["qcode_trace"]) >= 10
    assert len(body["applicable_clauses"]) > 0
    assert "D102" in body["required_dcodes"]


@pytest.mark.asyncio
async def test_v2_sole_source():
    """V2 sole source should show J&A D-code and correct approver."""
    params = {**CANONICAL_20M, "sole_source": True, "competition_type": "sole_source"}
    status, body = await post_json("/api/v1/rules/evaluate/v2", params)
    assert status == 200
    assert "D108" in body["required_dcodes"]
    assert body["ja_approver"] == "HCA"
    assert body["posting_deadline_days"] == 15


@pytest.mark.asyncio
async def test_v2_micro_purchase():
    """V2 micro purchase: minimal output."""
    params = {
        "title": "Office Supplies", "value": 5000, "naics": "339940",
        "psc": "7510", "services": False, "it_related": False,
    }
    status, body = await post_json("/api/v1/rules/evaluate/v2", params)
    assert status == 200
    assert body["tier_name"] == "micro_purchase"
    assert body["posting_deadline_days"] == 0
    assert len(body["required_dcodes"]) == 0


@pytest.mark.asyncio
async def test_v2_clauses_for_commercial_it():
    """V2 should return applicable clauses for commercial IT."""
    params = {
        "title": "COTS Software", "value": 2000000, "naics": "511210",
        "psc": "7030", "services": False, "it_related": True,
        "commercial_item": True,
    }
    status, body = await post_json("/api/v1/rules/evaluate/v2", params)
    assert status == 200
    clause_numbers = [c["clause_number"] for c in body["applicable_clauses"]]
    assert "52.212-4" in clause_numbers  # Commercial
    assert "52.239-1" in clause_numbers  # IT privacy


@pytest.mark.asyncio
async def test_v2_thresholds_in_response():
    """V2 should include all threshold values checked."""
    status, body = await post_json("/api/v1/rules/evaluate/v2", CANONICAL_20M)
    assert status == 200
    assert body["thresholds_checked"]["sat"] == 350000
    assert body["thresholds_checked"]["gao_protest_civilian_task_order"] == 10000000
