"""Rules Engine Migration — Wire PolicyService into the live API.

Strategy: Keep the existing /rules/evaluate endpoint backward-compatible
(same response shape, same D-code names) while adding PolicyService
evaluation as an enriched section of the response.

New field: `policy_evaluation` contains Q-code trace, clause list,
corrected D-codes, posting rule detail, and full authority chain.

Also adds /rules/evaluate/v2 that returns the full PolicyService output
directly (for new consumers).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel

from backend.phase2.policy_engine import PolicyService, PolicyEvaluationResult


# ── Extended Response Schema ──────────────────────────────────────────────────

class QCodeTraceItem(BaseModel):
    code: str
    question: str
    answer: str
    triggered_dcodes: list[str]
    authority: str


class PolicyEvaluationSummary(BaseModel):
    """Enriched policy evaluation attached to the existing response."""
    tier_name: str
    corrected_dcodes: list[str]
    qcode_trace: list[QCodeTraceItem]
    nodes_evaluated: int
    terminal_node: str
    posting_rule: str
    posting_authority: str
    posting_days: int
    ja_approver: str
    ja_authority: str
    applicable_clauses: list[dict]
    thresholds_checked: dict[str, float]
    notes: list[str]


class EnrichedRulesEvaluationResponse(BaseModel):
    """V1 response + policy_evaluation enrichment."""
    # --- Backward-compatible fields (from old RulesEvaluationResponse) ---
    tier: dict  # ThresholdTierResponse as dict
    required_dcodes: list[str]
    q_codes_evaluated: list[str]
    approvers: dict[str, str]
    posting_deadline_days: int
    authority_chain: list[str]
    notes: list[str]
    # --- New: enriched policy evaluation ---
    policy_evaluation: PolicyEvaluationSummary | None = None


class PolicyV2Response(BaseModel):
    """Full PolicyService output for /rules/evaluate/v2."""
    tier_name: str
    docs_required: str
    competition: str
    required_dcodes: list[str]
    qcode_trace: list[QCodeTraceItem]
    nodes_evaluated: int
    terminal_node: str
    posting_deadline_days: int
    posting_rule: str
    posting_authority: str
    ja_approver: str
    ja_authority: str
    applicable_clauses: list[dict]
    thresholds_checked: dict[str, float]
    authority_chain: list[str]
    notes: list[str]


# ── PolicyService Singleton ───────────────────────────────────────────────────

_policy_service = PolicyService()


def run_policy_evaluation(params: dict[str, Any], as_of: date | None = None) -> PolicyEvaluationResult:
    """Run PolicyService evaluation. Called from router."""
    return _policy_service.evaluate(params, as_of)


def to_enrichment(result: PolicyEvaluationResult) -> PolicyEvaluationSummary:
    """Convert PolicyService result to the enrichment summary."""
    return PolicyEvaluationSummary(
        tier_name=result.tier.name,
        corrected_dcodes=result.required_dcodes,
        qcode_trace=[
            QCodeTraceItem(
                code=e.code, question=e.question, answer=e.answer,
                triggered_dcodes=e.triggered_dcodes, authority=e.authority,
            ) for e in result.qcode_trace
        ],
        nodes_evaluated=result.nodes_evaluated,
        terminal_node=result.terminal_node,
        posting_rule=result.posting_rule,
        posting_authority=result.posting_authority,
        posting_days=result.posting_deadline_days,
        ja_approver=result.ja_approver,
        ja_authority=result.ja_authority,
        applicable_clauses=result.applicable_clauses,
        thresholds_checked=result.thresholds_checked,
        notes=result.notes,
    )


def to_v2_response(result: PolicyEvaluationResult) -> PolicyV2Response:
    """Convert PolicyService result to the full V2 response."""
    return PolicyV2Response(
        tier_name=result.tier.name,
        docs_required=result.tier.docs_required,
        competition=result.tier.competition,
        required_dcodes=result.required_dcodes,
        qcode_trace=[
            QCodeTraceItem(
                code=e.code, question=e.question, answer=e.answer,
                triggered_dcodes=e.triggered_dcodes, authority=e.authority,
            ) for e in result.qcode_trace
        ],
        nodes_evaluated=result.nodes_evaluated,
        terminal_node=result.terminal_node,
        posting_deadline_days=result.posting_deadline_days,
        posting_rule=result.posting_rule,
        posting_authority=result.posting_authority,
        ja_approver=result.ja_approver,
        ja_authority=result.ja_authority,
        applicable_clauses=result.applicable_clauses,
        thresholds_checked=result.thresholds_checked,
        authority_chain=result.authority_chain,
        notes=result.notes,
    )
