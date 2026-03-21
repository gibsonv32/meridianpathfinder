"""Workflow Gate Engine
=====================
Deterministic state machine that controls acquisition package phase transitions.
Each phase has required D-codes that must be satisfied before the package can advance.
This is Tier 1 (deterministic) — no AI involved.

Phases follow the federal acquisition lifecycle:
  Intake → Requirements → Solicitation Prep → Solicitation → Evaluation → Award → Post-Award

Gate rules are per-phase and cumulative — earlier gates must remain satisfied.

Design principles:
- Accept / Modify / Override: CO can override any gate with written rationale (logged)
- All gate checks are logged to the audit trail
- Phase definitions carry effective_date for versioning
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


# ── Phase Definitions ─────────────────────────────────────────────────────────

class AcquisitionPhase(str, Enum):
    """Ordered acquisition lifecycle phases."""
    INTAKE = "Intake"
    REQUIREMENTS = "Requirements"
    SOLICITATION_PREP = "Solicitation Prep"
    SOLICITATION = "Solicitation"
    EVALUATION = "Evaluation"
    AWARD = "Award"
    POST_AWARD = "Post-Award"
    CLOSEOUT = "Closeout"


# Ordered list for transition validation
PHASE_ORDER = list(AcquisitionPhase)
PHASE_INDEX = {p: i for i, p in enumerate(PHASE_ORDER)}


@dataclass
class GateRequirement:
    """A single gate requirement for a phase transition."""
    dcode: str
    required_status: str = "satisfied"  # satisfied, pending (pending = at least started)
    description: str = ""
    waivable: bool = True  # Can CO override with rationale?
    authority: str = ""


@dataclass
class PhaseGate:
    """Gate definition for entering a specific phase."""
    target_phase: AcquisitionPhase
    requirements: list[GateRequirement] = field(default_factory=list)
    min_completeness_pct: float = 0.0  # Minimum overall completeness %
    description: str = ""
    effective_date: date = field(default_factory=lambda: date(2025, 10, 1))


# ── Gate Registry ─────────────────────────────────────────────────────────────
# Requirements to ENTER each phase (not to leave it)

PHASE_GATES: dict[AcquisitionPhase, PhaseGate] = {
    # Intake: No gate — this is the starting phase
    AcquisitionPhase.INTAKE: PhaseGate(
        target_phase=AcquisitionPhase.INTAKE,
        requirements=[],
        description="Starting phase — no gate requirements.",
    ),

    # Requirements: Need market research started and basic planning
    AcquisitionPhase.REQUIREMENTS: PhaseGate(
        target_phase=AcquisitionPhase.REQUIREMENTS,
        requirements=[
            GateRequirement("D101", "pending", "Market Research must be at least in progress", authority="FAR 10.002"),
        ],
        min_completeness_pct=0.0,
        description="Enter requirements development phase.",
    ),

    # Solicitation Prep: Core docs must be at least started
    AcquisitionPhase.SOLICITATION_PREP: PhaseGate(
        target_phase=AcquisitionPhase.SOLICITATION_PREP,
        requirements=[
            GateRequirement("D101", "satisfied", "Market Research must be complete", authority="FAR 10.002"),
            GateRequirement("D102", "pending", "PWS/SOW must be at least in progress", authority="FAR 37.602"),
            GateRequirement("D104", "pending", "IGCE must be at least in progress", authority="FAR 36.203"),
            GateRequirement("D115", "pending", "COR nomination must be at least in progress", authority="FAR 1.602-2(d)"),
        ],
        min_completeness_pct=15.0,
        description="Begin solicitation preparation — core docs must be underway.",
    ),

    # Solicitation: All blocking docs must be satisfied
    AcquisitionPhase.SOLICITATION: PhaseGate(
        target_phase=AcquisitionPhase.SOLICITATION,
        requirements=[
            GateRequirement("D101", "satisfied", "Market Research complete", authority="FAR 10.002"),
            GateRequirement("D102", "satisfied", "PWS/SOW complete", authority="FAR 37.602"),
            GateRequirement("D103", "satisfied", "CLIN structure finalized", authority="FAR 4.1001"),
            GateRequirement("D104", "satisfied", "IGCE complete", authority="FAR 36.203"),
            GateRequirement("D115", "satisfied", "COR nominated", authority="FAR 1.602-2(d)"),
            GateRequirement("D120", "satisfied", "Security requirements documented", authority="TSA MD 2810.1", waivable=False),
        ],
        min_completeness_pct=60.0,
        description="Issue solicitation — all blocking documents must be satisfied.",
    ),

    # Evaluation: Solicitation must be complete, eval plan ready
    AcquisitionPhase.EVALUATION: PhaseGate(
        target_phase=AcquisitionPhase.EVALUATION,
        requirements=[
            GateRequirement("D117", "satisfied", "Evaluation factors defined", authority="FAR 15.304"),
            GateRequirement("D118", "satisfied", "Past performance eval plan ready", authority="FAR 15.305(a)(2)"),
        ],
        min_completeness_pct=75.0,
        description="Begin proposal evaluation — eval criteria must be locked.",
    ),

    # Award: All docs satisfied, evaluation complete
    AcquisitionPhase.AWARD: PhaseGate(
        target_phase=AcquisitionPhase.AWARD,
        requirements=[],  # Dynamically checked — all required D-codes must be satisfied
        min_completeness_pct=100.0,
        description="Award decision — Tier 3 hard stop: only warranted CO can sign.",
    ),

    # Post-Award: Award must be executed
    AcquisitionPhase.POST_AWARD: PhaseGate(
        target_phase=AcquisitionPhase.POST_AWARD,
        requirements=[],
        min_completeness_pct=100.0,
        description="Post-award administration phase.",
    ),

    # Closeout: Post-award complete
    AcquisitionPhase.CLOSEOUT: PhaseGate(
        target_phase=AcquisitionPhase.CLOSEOUT,
        requirements=[],
        min_completeness_pct=100.0,
        description="Contract closeout phase.",
    ),
}


# ── Gate Check Results ────────────────────────────────────────────────────────

@dataclass
class GateCheckResult:
    """Result of checking whether a phase transition is allowed."""
    allowed: bool
    current_phase: str
    target_phase: str
    failed_requirements: list[dict[str, Any]] = field(default_factory=list)
    passed_requirements: list[dict[str, Any]] = field(default_factory=list)
    completeness_pct: float = 0.0
    min_completeness_pct: float = 0.0
    completeness_met: bool = True
    overridable: bool = True  # Can CO force-advance with rationale?
    gate_description: str = ""
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: list[str] = field(default_factory=list)


@dataclass
class PhaseAdvanceResult:
    """Result of attempting to advance a package's phase."""
    success: bool
    previous_phase: str
    new_phase: str
    gate_check: GateCheckResult
    override_used: bool = False
    override_rationale: str = ""
    advanced_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Workflow Gate Engine ──────────────────────────────────────────────────────

class WorkflowGateEngine:
    """Deterministic gate engine for acquisition phase transitions.

    Tier 1 — no AI. Pure rules.
    """

    def check_gate(
        self,
        current_phase: str,
        target_phase: str,
        documents: dict[str, str],  # {dcode: status}
        required_dcodes: set[str] | None = None,
    ) -> GateCheckResult:
        """Check if a phase transition is allowed.

        Args:
            current_phase: Current package phase name
            target_phase: Desired target phase name
            documents: Dict of {dcode: status} for all package documents
            required_dcodes: Set of all D-codes required for this package
                             (used for completeness % calc and Award gate)
        """
        # Resolve phases
        try:
            current = AcquisitionPhase(current_phase)
        except ValueError:
            return GateCheckResult(
                allowed=False,
                current_phase=current_phase,
                target_phase=target_phase,
                notes=[f"Unknown current phase: {current_phase}"],
            )

        try:
            target = AcquisitionPhase(target_phase)
        except ValueError:
            return GateCheckResult(
                allowed=False,
                current_phase=current_phase,
                target_phase=target_phase,
                notes=[f"Unknown target phase: {target_phase}"],
            )

        # Validate ordering — can only advance forward (no skipping allowed either, for now)
        current_idx = PHASE_INDEX[current]
        target_idx = PHASE_INDEX[target]

        if target_idx <= current_idx:
            return GateCheckResult(
                allowed=False,
                current_phase=current_phase,
                target_phase=target_phase,
                notes=[f"Cannot move backward or stay in same phase. Current: {current.value} (#{current_idx}), Target: {target.value} (#{target_idx})"],
            )

        if target_idx > current_idx + 1:
            return GateCheckResult(
                allowed=False,
                current_phase=current_phase,
                target_phase=target_phase,
                notes=[f"Cannot skip phases. Must advance one phase at a time. Next phase is: {PHASE_ORDER[current_idx + 1].value}"],
            )

        # Get gate definition
        gate = PHASE_GATES.get(target)
        if gate is None:
            return GateCheckResult(
                allowed=False,
                current_phase=current_phase,
                target_phase=target_phase,
                notes=[f"No gate definition for phase: {target_phase}"],
            )

        # Calculate completeness
        required = required_dcodes or set(documents.keys())
        total = len(required)
        satisfied = sum(1 for dc in required if documents.get(dc) == "satisfied")
        completeness_pct = (satisfied / total * 100) if total > 0 else 100.0

        # Check document requirements
        passed = []
        failed = []
        all_overridable = True

        for req in gate.requirements:
            doc_status = documents.get(req.dcode, "missing")
            meets_requirement = self._status_meets(doc_status, req.required_status)

            entry = {
                "dcode": req.dcode,
                "required_status": req.required_status,
                "actual_status": doc_status,
                "description": req.description,
                "authority": req.authority,
                "waivable": req.waivable,
            }

            if meets_requirement:
                passed.append(entry)
            else:
                failed.append(entry)
                if not req.waivable:
                    all_overridable = False

        # Check completeness threshold
        completeness_met = completeness_pct >= gate.min_completeness_pct

        # Build notes
        notes = []
        if failed:
            notes.append(f"{len(failed)} requirement(s) not met for {target.value}.")
        if not completeness_met:
            notes.append(
                f"Completeness {completeness_pct:.1f}% is below minimum {gate.min_completeness_pct:.0f}% "
                f"for {target.value}."
            )
        if not failed and completeness_met:
            notes.append(f"All gate requirements met for {target.value}.")

        allowed = len(failed) == 0 and completeness_met

        return GateCheckResult(
            allowed=allowed,
            current_phase=current_phase,
            target_phase=target_phase,
            failed_requirements=failed,
            passed_requirements=passed,
            completeness_pct=round(completeness_pct, 1),
            min_completeness_pct=gate.min_completeness_pct,
            completeness_met=completeness_met,
            overridable=all_overridable,
            gate_description=gate.description,
            notes=notes,
        )

    def advance(
        self,
        current_phase: str,
        target_phase: str,
        documents: dict[str, str],
        required_dcodes: set[str] | None = None,
        override: bool = False,
        override_rationale: str = "",
        actor: str = "system",
    ) -> PhaseAdvanceResult:
        """Attempt to advance a package to the next phase.

        If override=True and the gate is overridable, the CO can force-advance
        with a written rationale (logged to audit trail).
        """
        gate_check = self.check_gate(current_phase, target_phase, documents, required_dcodes)

        if gate_check.allowed:
            return PhaseAdvanceResult(
                success=True,
                previous_phase=current_phase,
                new_phase=target_phase,
                gate_check=gate_check,
            )

        # Not allowed — check if override is requested and permitted
        if override:
            if not gate_check.overridable:
                gate_check.notes.append(
                    "Override DENIED: one or more requirements are non-waivable "
                    "(e.g., security requirements per TSA MD 2810.1)."
                )
                return PhaseAdvanceResult(
                    success=False,
                    previous_phase=current_phase,
                    new_phase=current_phase,
                    gate_check=gate_check,
                    override_used=True,
                    override_rationale=override_rationale,
                )

            if not override_rationale.strip():
                gate_check.notes.append(
                    "Override DENIED: CO must provide written rationale for gate override."
                )
                return PhaseAdvanceResult(
                    success=False,
                    previous_phase=current_phase,
                    new_phase=current_phase,
                    gate_check=gate_check,
                    override_used=True,
                )

            # Override approved with rationale
            gate_check.notes.append(
                f"Gate OVERRIDDEN by {actor}. Rationale: {override_rationale}"
            )
            return PhaseAdvanceResult(
                success=True,
                previous_phase=current_phase,
                new_phase=target_phase,
                gate_check=gate_check,
                override_used=True,
                override_rationale=override_rationale,
            )

        # Not allowed and no override
        return PhaseAdvanceResult(
            success=False,
            previous_phase=current_phase,
            new_phase=current_phase,
            gate_check=gate_check,
        )

    def get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase in sequence, or None if at the end."""
        try:
            current = AcquisitionPhase(current_phase)
        except ValueError:
            return None
        idx = PHASE_INDEX[current]
        if idx + 1 >= len(PHASE_ORDER):
            return None
        return PHASE_ORDER[idx + 1].value

    def get_phase_roadmap(self, current_phase: str, documents: dict[str, str], required_dcodes: set[str] | None = None) -> list[dict]:
        """Get the full phase roadmap with gate status for each phase."""
        try:
            current = AcquisitionPhase(current_phase)
        except ValueError:
            return []

        current_idx = PHASE_INDEX[current]
        roadmap = []

        for i, phase in enumerate(PHASE_ORDER):
            gate = PHASE_GATES.get(phase)
            if i <= current_idx:
                status = "completed" if i < current_idx else "current"
            elif i == current_idx + 1:
                check = self.check_gate(current_phase, phase.value, documents, required_dcodes)
                status = "ready" if check.allowed else "blocked"
            else:
                status = "future"

            roadmap.append({
                "phase": phase.value,
                "index": i,
                "status": status,
                "description": gate.description if gate else "",
                "min_completeness_pct": gate.min_completeness_pct if gate else 0,
                "requirement_count": len(gate.requirements) if gate else 0,
            })

        return roadmap

    @staticmethod
    def _status_meets(actual: str, required: str) -> bool:
        """Check if actual status meets or exceeds the required status.

        Status hierarchy: missing < pending/draft < satisfied
        """
        HIERARCHY = {"missing": 0, "draft": 1, "pending": 1, "satisfied": 2}
        actual_level = HIERARCHY.get(actual, 0)
        required_level = HIERARCHY.get(required, 2)
        return actual_level >= required_level


# Singleton
workflow_gate_engine = WorkflowGateEngine()
