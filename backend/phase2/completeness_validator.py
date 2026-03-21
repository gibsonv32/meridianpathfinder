"""PR Package Completeness Validator
====================================
Dedicated endpoint that:
1. Takes acquisition params + list of documents already in hand
2. Runs PolicyService to determine required D-codes
3. Compares required vs provided
4. Returns gap analysis with responsible parties and authorities

This is MVP Priority #2 from the FedProcure roadmap.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from backend.phase2.policy_engine import (
    PolicyService,
    get_dcode_registry,
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class DocumentInHand(BaseModel):
    """A document the user already has."""
    dcode: str
    status: str = Field(default="satisfied", description="satisfied|pending|draft")


class ValidateCompletenessRequest(BaseModel):
    """Request to validate package completeness before creation."""
    title: str = ""
    value: float = 0
    naics: str = ""
    psc: str = ""
    services: bool = False
    it_related: bool = False
    sole_source: bool = False
    commercial_item: bool = False
    emergency: bool = False
    vendor_on_site: bool = False
    competition_type: str = "full_and_open"
    documents_in_hand: list[DocumentInHand] = Field(default_factory=list)
    phase: str | None = Field(default=None, description="Current acquisition phase for branch-aware D-code resolution")


class DocumentGap(BaseModel):
    """A required document that is missing or incomplete."""
    dcode: str
    name: str
    description: str
    responsible_party: str
    authority: str
    status: str = Field(description="missing|pending|draft|satisfied")
    ucf_section: str | None = None
    blocker: bool = Field(description="True if this blocks package submission")


class CompletenessValidationResponse(BaseModel):
    """Result of the completeness validation."""
    package_ready: bool = Field(description="True if all required docs are satisfied")
    completeness_pct: float = Field(description="0-100 percentage")
    required_count: int
    satisfied_count: int
    pending_count: int
    missing_count: int
    documents: list[DocumentGap]
    blocking_documents: list[str] = Field(description="D-codes that block submission")
    tier_name: str
    posting_deadline_days: int
    notes: list[str] = Field(default_factory=list)


# ── Responsible Party Defaults ────────────────────────────────────────────────

RESPONSIBLE_PARTY: dict[str, str] = {
    "D101": "CO/CS",
    "D102": "COR/Program Office",
    "D103": "CO",
    "D104": "COR/Program Office",
    "D105": "COR",
    "D106": "CO",
    "D107": "CO/SB Specialist",
    "D108": "CO",
    "D109": "CO",
    "D110": "CO/SB Specialist",
    "D111": "CO",
    "D112": "CO",
    "D113": "CO",
    "D114": "CIO/ISSO",
    "D115": "Program Office",
    "D116": "CO",
    "D117": "CO/SSEB Chair",
    "D118": "CO/SSEB Chair",
    "D119": "CO/Legal",
    "D120": "Security Officer",
    "D121": "CO",
    "D122": "CO",
    "D123": "CO",
    "D124": "CO",
    "D125": "COR/Program Office",
    "D126": "COR/Property Officer",
    "D127": "COR/Program Office",
    "D128": "Security Officer",
    "D129": "CO",
    "D130": "CO",
    "D131": "CO",
    "D132": "CO/Price Analyst",
    "D133": "CO",
    "D134": "CO",
    "D135": "CO",
    "D136": "SSA",
    "D137": "CO/Legal",
    "D138": "CO/Legal",
    "D139": "CO/SB Specialist",
    "D140": "CO",
    "D141": "CO",
    "D142": "CIO/ISSO",
    "D143": "CO",
    "D144": "COR",
    "D145": "CO",
}

# D-codes that block submission if missing (vs advisory)
BLOCKING_DCODES = {
    "D101", "D102", "D103", "D104", "D106", "D108", "D115", "D120",
    "D131", "D132", "D136",  # Award phase blockers
}


# ── Validator Service ─────────────────────────────────────────────────────────

class CompletenessValidator:
    """Validates PR package completeness against PolicyService requirements."""

    def __init__(self):
        self._policy = PolicyService()

    def validate(self, request: ValidateCompletenessRequest) -> CompletenessValidationResponse:
        """Run full completeness check."""
        params = {
            "title": request.title,
            "value": request.value,
            "naics": request.naics,
            "psc": request.psc,
            "services": request.services,
            "it_related": request.it_related,
            "sole_source": request.sole_source,
            "commercial_item": request.commercial_item,
            "emergency": request.emergency,
            "vendor_on_site": request.vendor_on_site,
            "competition_type": request.competition_type,
        }

        # Get policy evaluation (phase-aware: includes branch-specific D-codes)
        policy_result = self._policy.evaluate(params, phase=request.phase)
        required_dcodes = set(policy_result.required_dcodes)

        # Build lookup of documents in hand
        in_hand = {d.dcode: d.status for d in request.documents_in_hand}

        # Get D-code registry for names/descriptions
        registry = get_dcode_registry()

        # Build document gap analysis
        documents: list[DocumentGap] = []
        satisfied = 0
        pending = 0
        missing = 0

        for dcode in sorted(required_dcodes):
            defn = registry.get(dcode)
            status = in_hand.get(dcode, "missing")
            is_blocker = dcode in BLOCKING_DCODES and status != "satisfied"

            if status == "satisfied":
                satisfied += 1
            elif status in ("pending", "draft"):
                pending += 1
            else:
                missing += 1

            documents.append(DocumentGap(
                dcode=dcode,
                name=defn.name if defn else dcode,
                description=defn.description if defn else "",
                responsible_party=RESPONSIBLE_PARTY.get(dcode, "CO"),
                authority=defn.authority if defn else "",
                status=status,
                ucf_section=defn.ucf_section if defn else None,
                blocker=is_blocker,
            ))

        total = len(documents)
        pct = (satisfied / total * 100) if total > 0 else 100.0
        blocking = [d.dcode for d in documents if d.blocker]

        notes = list(policy_result.notes)
        if blocking:
            notes.insert(0, f"{len(blocking)} blocking document(s) must be resolved before submission.")
        if missing > 0:
            notes.append(f"{missing} document(s) not yet started.")
        if pct == 100:
            notes.append("Package is complete and ready for CO review.")

        return CompletenessValidationResponse(
            package_ready=(missing == 0 and len(blocking) == 0),
            completeness_pct=round(pct, 1),
            required_count=total,
            satisfied_count=satisfied,
            pending_count=pending,
            missing_count=missing,
            documents=documents,
            blocking_documents=blocking,
            tier_name=policy_result.tier.name,
            posting_deadline_days=policy_result.posting_deadline_days,
            notes=notes,
        )


# Singleton
completeness_validator = CompletenessValidator()
