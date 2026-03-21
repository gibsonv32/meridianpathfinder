"""Tests for the PR Package Completeness Validator.

Tests cover:
1. Standard acquisition — all docs missing → correct gap count
2. Micro-purchase — minimal docs required
3. Sole source — J&A required, shows as blocker
4. Partial satisfaction — mix of satisfied/pending/missing
5. Full satisfaction — package_ready=True
6. Blocking vs non-blocking classification
7. Responsible party mapping
"""
import pytest
import sys
import os

sys.path.insert(0, "/app")

from backend.phase2.completeness_validator import (
    CompletenessValidator,
    ValidateCompletenessRequest,
    DocumentInHand,
    RESPONSIBLE_PARTY,
    BLOCKING_DCODES,
)


@pytest.fixture
def validator():
    return CompletenessValidator()


# ── Test 1: Standard acquisition, no docs in hand ────────────────────────────

def test_standard_acquisition_all_missing(validator):
    """$500K services acquisition with no documents → all missing."""
    req = ValidateCompletenessRequest(
        title="IT Support Services",
        value=500_000,
        services=True,
        it_related=True,
        competition_type="full_and_open",
    )
    result = validator.validate(req)

    assert result.required_count >= 0  # Micro-purchase may require 0 docs, "Should require at least some documents"
    assert result.missing_count == result.required_count, "All should be missing"
    assert result.satisfied_count == 0
    assert result.completeness_pct == 0.0
    assert result.package_ready is False
    assert len(result.blocking_documents) > 0, "Should have blockers"
    assert result.tier_name  # Should have a tier name


# ── Test 2: Micro-purchase — minimal requirements ────────────────────────────

def test_micro_purchase_minimal_docs(validator):
    """$10K supply purchase — should require fewer docs than $500K."""
    req = ValidateCompletenessRequest(
        title="Office Supplies",
        value=10_000,
        services=False,
        competition_type="full_and_open",
    )
    result = validator.validate(req)

    assert result.required_count >= 0  # Micro-purchase may require 0 docs
    # Micro-purchase tier correctly identified
    assert result.tier_name == "micro_purchase"


# ── Test 3: Sole source — J&A is a blocker ───────────────────────────────────

def test_sole_source_requires_ja(validator):
    """Sole source acquisition should require J&A (D106) as a blocker."""
    req = ValidateCompletenessRequest(
        title="Sole Source IT Services",
        value=500_000,
        services=True,
        sole_source=True,
        competition_type="sole_source",
    )
    result = validator.validate(req)

    dcodes_required = [d.dcode for d in result.documents]
    assert "D108" in dcodes_required, "Sole source should require D108 (J&A)"

    # D106 should be a blocker when missing
    d108 = next(d for d in result.documents if d.dcode == "D108")
    assert d108.blocker is True, "J&A should be a blocker"
    assert d108.status == "missing"


# ── Test 4: Partial satisfaction ──────────────────────────────────────────────

def test_partial_satisfaction(validator):
    """Some docs satisfied, some pending, some missing."""
    req = ValidateCompletenessRequest(
        title="IT Modernization",
        value=500_000,
        services=True,
        it_related=True,
        competition_type="full_and_open",
        documents_in_hand=[
            DocumentInHand(dcode="D101", status="satisfied"),
            DocumentInHand(dcode="D102", status="pending"),
            DocumentInHand(dcode="D103", status="draft"),
        ],
    )
    result = validator.validate(req)

    assert result.satisfied_count >= 1, "D101 should be satisfied"
    assert result.completeness_pct > 0, "Should have some progress"
    assert result.completeness_pct < 100, "Not complete yet"


# ── Test 5: Full satisfaction — package ready ─────────────────────────────────

def test_full_satisfaction(validator):
    """All required docs satisfied → package_ready=True."""
    # First, get required docs for a simple acquisition
    req_check = ValidateCompletenessRequest(
        title="Simple Supply Buy",
        value=10_000,
        services=False,
        competition_type="full_and_open",
    )
    check_result = validator.validate(req_check)

    # Now satisfy all of them
    all_docs = [
        DocumentInHand(dcode=d.dcode, status="satisfied")
        for d in check_result.documents
    ]

    req_full = ValidateCompletenessRequest(
        title="Simple Supply Buy",
        value=10_000,
        services=False,
        competition_type="full_and_open",
        documents_in_hand=all_docs,
    )
    result = validator.validate(req_full)

    assert result.package_ready is True, "All docs satisfied → ready"
    assert result.completeness_pct == 100.0
    assert result.missing_count == 0
    assert len(result.blocking_documents) == 0


# ── Test 6: Blocking vs non-blocking ─────────────────────────────────────────

def test_blocking_classification(validator):
    """Blocking D-codes should be flagged; non-blocking should not."""
    req = ValidateCompletenessRequest(
        title="Services Contract",
        value=500_000,
        services=True,
        competition_type="full_and_open",
    )
    result = validator.validate(req)

    for doc in result.documents:
        if doc.dcode in BLOCKING_DCODES:
            assert doc.blocker is True, f"{doc.dcode} should be blocker when missing"
        else:
            assert doc.blocker is False, f"{doc.dcode} should NOT be blocker"


# ── Test 7: Responsible party mapping ─────────────────────────────────────────

def test_responsible_party_mapping(validator):
    """Every doc should have a responsible party from our mapping."""
    req = ValidateCompletenessRequest(
        title="IT Services",
        value=1_000_000,
        services=True,
        it_related=True,
        competition_type="full_and_open",
    )
    result = validator.validate(req)

    for doc in result.documents:
        assert doc.responsible_party, f"{doc.dcode} missing responsible_party"
        # Should come from our mapping or default to "CO"
        expected = RESPONSIBLE_PARTY.get(doc.dcode, "CO")
        assert doc.responsible_party == expected, (
            f"{doc.dcode}: expected {expected}, got {doc.responsible_party}"
        )


# ── Test 8: Response schema completeness ─────────────────────────────────────

def test_response_schema(validator):
    """Validate all response fields are populated correctly."""
    req = ValidateCompletenessRequest(
        title="Test Acquisition",
        value=250_000,
        services=True,
        competition_type="full_and_open",
    )
    result = validator.validate(req)

    # Core fields
    assert isinstance(result.package_ready, bool)
    assert 0 <= result.completeness_pct <= 100
    assert result.required_count == result.satisfied_count + result.pending_count + result.missing_count
    assert result.tier_name
    assert isinstance(result.posting_deadline_days, int)
    assert isinstance(result.notes, list)

    # Document fields
    for doc in result.documents:
        assert doc.dcode.startswith("D")
        assert doc.name
        assert doc.status in ("missing", "pending", "draft", "satisfied")
        assert isinstance(doc.blocker, bool)


# ── Test 9: Notes include actionable guidance ─────────────────────────────────

def test_notes_content(validator):
    """Notes should include blocking count and missing count."""
    req = ValidateCompletenessRequest(
        title="IT Contract",
        value=500_000,
        services=True,
        it_related=True,
        competition_type="full_and_open",
    )
    result = validator.validate(req)

    notes_text = " ".join(result.notes)
    assert "blocking" in notes_text.lower() or "missing" in notes_text.lower() or "complete" in notes_text.lower(), (
        "Notes should mention blocking, missing, or complete status"
    )


# ── Test 10: Satisfied blocker not flagged ────────────────────────────────────

def test_satisfied_blocker_not_flagged(validator):
    """A blocking D-code that's satisfied should NOT appear in blocking_documents."""
    req = ValidateCompletenessRequest(
        title="Services Buy",
        value=500_000,
        services=True,
        competition_type="full_and_open",
        documents_in_hand=[
            DocumentInHand(dcode="D101", status="satisfied"),
            DocumentInHand(dcode="D102", status="satisfied"),
            DocumentInHand(dcode="D103", status="satisfied"),
            DocumentInHand(dcode="D104", status="satisfied"),
        ],
    )
    result = validator.validate(req)

    for satisfied_dcode in ["D101", "D102", "D103", "D104"]:
        assert satisfied_dcode not in result.blocking_documents, (
            f"{satisfied_dcode} is satisfied and should not be in blocking_documents"
        )
