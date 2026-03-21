"""
Protected Evaluation Workspace — Phase 2 Feature
=================================================
Secure, role-based workspace for source selection evaluation.
Enforces separation of duties and produces immutable evaluation records.

Hard Stop Awareness:
- Source selection DECISION is Tier 3 (FAR 15.308, 7.503(b)(1)) — AI prohibited
- Evaluation SUPPORT (scoring worksheets, comparison matrices, summaries) is Tier 2 — AI assists, human decides

RBAC Roles:
- SSA: Source Selection Authority (reads final SSDD, signs)
- SSEB_CHAIR: Manages evaluation, assigns factors
- SSEB_MEMBER: Scores assigned factors only
- CO: Contracting officer, administers process
- ADVISOR: Read-only (legal, SB specialist)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class EvalRole(str, Enum):
    SSA = "ssa"
    SSEB_CHAIR = "sseb_chair"
    SSEB_MEMBER = "sseb_member"
    CO = "co"
    ADVISOR = "advisor"


class Rating(str, Enum):
    OUTSTANDING = "outstanding"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    MARGINAL = "marginal"
    UNACCEPTABLE = "unacceptable"


class EvalPhase(str, Enum):
    SETUP = "setup"
    INDIVIDUAL_EVAL = "individual_evaluation"
    CONSENSUS = "consensus"
    DISCUSSIONS = "discussions"
    FINAL_EVAL = "final_evaluation"
    DECISION = "decision"
    COMPLETE = "complete"


@dataclass
class EvalFactor:
    factor_id: str
    name: str
    weight: int  # relative weight (e.g., 40 = 40%)
    description: str
    subfactors: list[str] = field(default_factory=list)


@dataclass
class OfferorRecord:
    offeror_id: str
    name: str
    proposal_received: str  # ISO date
    in_competitive_range: bool = True
    excluded_reason: str | None = None


@dataclass
class IndividualScore:
    """Individual evaluator's score for one factor of one offeror."""
    score_id: str
    evaluator: str
    evaluator_role: EvalRole
    offeror_id: str
    factor_id: str
    rating: Rating
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    deficiencies: list[str] = field(default_factory=list)
    narrative: str = ""
    timestamp: str = ""


@dataclass
class ConsensusScore:
    """SSEB consensus score for one factor of one offeror."""
    factor_id: str
    offeror_id: str
    rating: Rating
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    deficiencies: list[str] = field(default_factory=list)
    narrative: str = ""
    individual_scores: list[IndividualScore] = field(default_factory=list)


@dataclass
class EvaluationRecord:
    """Complete evaluation workspace state."""
    workspace_id: str
    package_id: str
    title: str
    phase: EvalPhase
    factors: list[EvalFactor]
    offerors: list[OfferorRecord]
    individual_scores: list[IndividualScore]
    consensus_scores: list[ConsensusScore]
    audit_log: list[dict]
    created_at: str
    updated_at: str


# Permission matrix: which roles can perform which actions
PERMISSIONS: dict[str, set[EvalRole]] = {
    "create_workspace": {EvalRole.CO, EvalRole.SSEB_CHAIR},
    "add_offeror": {EvalRole.CO},
    "define_factors": {EvalRole.SSEB_CHAIR, EvalRole.CO},
    "submit_individual_score": {EvalRole.SSEB_MEMBER, EvalRole.SSEB_CHAIR},
    "submit_consensus_score": {EvalRole.SSEB_CHAIR},
    "advance_phase": {EvalRole.SSEB_CHAIR, EvalRole.CO},
    "view_all_scores": {EvalRole.SSEB_CHAIR, EvalRole.CO, EvalRole.SSA},
    "view_own_scores": {EvalRole.SSEB_MEMBER},
    "view_consensus": {EvalRole.SSA, EvalRole.SSEB_CHAIR, EvalRole.CO, EvalRole.ADVISOR},
    "make_award_decision": {EvalRole.SSA},  # Tier 3 — human only
    "read_only": {EvalRole.ADVISOR},
}


class EvaluationWorkspace:
    """
    Protected evaluation workspace with RBAC and immutable logging.

    All actions are logged. Scores cannot be modified after consensus — only superseded.
    The SSA award decision is a Tier 3 hard stop — this workspace facilitates but never makes that decision.
    """

    def __init__(self):
        self._workspaces: dict[str, EvaluationRecord] = {}

    def _check_permission(self, action: str, role: EvalRole) -> None:
        allowed = PERMISSIONS.get(action, set())
        if role not in allowed:
            raise PermissionError(f"Role '{role.value}' cannot perform '{action}'. Allowed: {[r.value for r in allowed]}")

    def _log(self, workspace: EvaluationRecord, action: str, actor: str, role: str, details: str = "") -> None:
        workspace.audit_log.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "actor": actor,
            "role": role,
            "details": details,
        })
        workspace.updated_at = datetime.now(UTC).isoformat()

    def create_workspace(
        self,
        *,
        package_id: str,
        title: str,
        actor: str,
        role: EvalRole,
        factors: list[dict],
    ) -> EvaluationRecord:
        self._check_permission("create_workspace", role)
        workspace_id = f"eval_{uuid4().hex[:8]}"
        eval_factors = [
            EvalFactor(
                factor_id=f"F{i+1:02d}",
                name=f.get("name", f"Factor {i+1}"),
                weight=f.get("weight", 0),
                description=f.get("description", ""),
                subfactors=f.get("subfactors", []),
            )
            for i, f in enumerate(factors)
        ]
        now = datetime.now(UTC).isoformat()
        workspace = EvaluationRecord(
            workspace_id=workspace_id,
            package_id=package_id,
            title=title,
            phase=EvalPhase.SETUP,
            factors=eval_factors,
            offerors=[],
            individual_scores=[],
            consensus_scores=[],
            audit_log=[],
            created_at=now,
            updated_at=now,
        )
        self._log(workspace, "create_workspace", actor, role.value, f"Created with {len(eval_factors)} factors")
        self._workspaces[workspace_id] = workspace
        return workspace

    def add_offeror(
        self,
        workspace_id: str,
        *,
        name: str,
        proposal_received: str,
        actor: str,
        role: EvalRole,
    ) -> OfferorRecord:
        self._check_permission("add_offeror", role)
        workspace = self._get_workspace(workspace_id)
        offeror = OfferorRecord(
            offeror_id=f"off_{uuid4().hex[:6]}",
            name=name,
            proposal_received=proposal_received,
        )
        workspace.offerors.append(offeror)
        self._log(workspace, "add_offeror", actor, role.value, f"Added offeror: {name}")
        return offeror

    def submit_individual_score(
        self,
        workspace_id: str,
        *,
        evaluator: str,
        role: EvalRole,
        offeror_id: str,
        factor_id: str,
        rating: Rating,
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        deficiencies: list[str] | None = None,
        narrative: str = "",
    ) -> IndividualScore:
        self._check_permission("submit_individual_score", role)
        workspace = self._get_workspace(workspace_id)
        if workspace.phase not in (EvalPhase.SETUP, EvalPhase.INDIVIDUAL_EVAL):
            raise ValueError(f"Cannot submit individual scores in phase '{workspace.phase.value}'")

        score = IndividualScore(
            score_id=f"score_{uuid4().hex[:6]}",
            evaluator=evaluator,
            evaluator_role=role,
            offeror_id=offeror_id,
            factor_id=factor_id,
            rating=rating,
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            deficiencies=deficiencies or [],
            narrative=narrative,
            timestamp=datetime.now(UTC).isoformat(),
        )
        workspace.individual_scores.append(score)
        self._log(workspace, "submit_score", evaluator, role.value, f"Scored {offeror_id}/{factor_id}: {rating.value}")
        return score

    def submit_consensus_score(
        self,
        workspace_id: str,
        *,
        actor: str,
        role: EvalRole,
        offeror_id: str,
        factor_id: str,
        rating: Rating,
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        deficiencies: list[str] | None = None,
        narrative: str = "",
    ) -> ConsensusScore:
        self._check_permission("submit_consensus_score", role)
        workspace = self._get_workspace(workspace_id)

        # Gather individual scores for this factor/offeror
        indiv = [s for s in workspace.individual_scores if s.offeror_id == offeror_id and s.factor_id == factor_id]

        consensus = ConsensusScore(
            factor_id=factor_id,
            offeror_id=offeror_id,
            rating=rating,
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            deficiencies=deficiencies or [],
            narrative=narrative,
            individual_scores=indiv,
        )
        workspace.consensus_scores.append(consensus)
        self._log(workspace, "consensus_score", actor, role.value, f"Consensus {offeror_id}/{factor_id}: {rating.value}")
        return consensus

    def advance_phase(self, workspace_id: str, *, actor: str, role: EvalRole) -> EvalPhase:
        self._check_permission("advance_phase", role)
        workspace = self._get_workspace(workspace_id)
        phase_order = list(EvalPhase)
        current_idx = phase_order.index(workspace.phase)
        if current_idx >= len(phase_order) - 1:
            raise ValueError("Evaluation already complete")

        # Decision phase is Tier 3 — log but don't automate
        next_phase = phase_order[current_idx + 1]
        if next_phase == EvalPhase.DECISION:
            self._log(workspace, "advance_phase", actor, role.value,
                      "ENTERING DECISION PHASE — Tier 3 hard stop. SSA must make independent award decision per FAR 15.308.")

        workspace.phase = next_phase
        self._log(workspace, "advance_phase", actor, role.value, f"Advanced to {next_phase.value}")
        return next_phase

    def get_workspace(self, workspace_id: str) -> EvaluationRecord:
        return self._get_workspace(workspace_id)

    def get_comparison_matrix(self, workspace_id: str, *, actor: str, role: EvalRole) -> dict:
        """Generate side-by-side comparison matrix from consensus scores."""
        self._check_permission("view_consensus", role)
        workspace = self._get_workspace(workspace_id)

        matrix: dict[str, dict[str, str]] = {}
        for offeror in workspace.offerors:
            matrix[offeror.name] = {}
            for factor in workspace.factors:
                consensus = next(
                    (c for c in workspace.consensus_scores if c.offeror_id == offeror.offeror_id and c.factor_id == factor.factor_id),
                    None,
                )
                matrix[offeror.name][factor.name] = consensus.rating.value if consensus else "not_scored"

        self._log(workspace, "view_matrix", actor, role.value, "Generated comparison matrix")
        return {
            "workspace_id": workspace_id,
            "phase": workspace.phase.value,
            "matrix": matrix,
            "factors": [{"id": f.factor_id, "name": f.name, "weight": f.weight} for f in workspace.factors],
            "offerors": [{"id": o.offeror_id, "name": o.name} for o in workspace.offerors],
        }

    def _get_workspace(self, workspace_id: str) -> EvaluationRecord:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            raise ValueError(f"Unknown workspace: {workspace_id}")
        return ws


evaluation_workspace = EvaluationWorkspace()
