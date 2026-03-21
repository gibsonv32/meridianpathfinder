"""Pydantic schemas for Workflow Gate API endpoints."""
from __future__ import annotations
from pydantic import BaseModel, Field


class GateCheckRequest(BaseModel):
    """Request to check if a phase transition is allowed."""
    package_id: str


class GateCheckResponse(BaseModel):
    """Result of a gate check."""
    allowed: bool
    current_phase: str
    target_phase: str
    failed_requirements: list[dict] = Field(default_factory=list)
    passed_requirements: list[dict] = Field(default_factory=list)
    completeness_pct: float
    min_completeness_pct: float
    completeness_met: bool
    overridable: bool
    gate_description: str
    notes: list[str] = Field(default_factory=list)


class PhaseAdvanceRequest(BaseModel):
    """Request to advance a package to the next phase."""
    package_id: str
    override: bool = False
    override_rationale: str = ""
    actor: str = "CO"


class PhaseAdvanceResponse(BaseModel):
    """Result of a phase advance attempt."""
    success: bool
    previous_phase: str
    new_phase: str
    gate_check: GateCheckResponse
    override_used: bool = False
    override_rationale: str = ""


class PhaseRoadmapResponse(BaseModel):
    """Full phase roadmap with gate status for each phase."""
    package_id: str
    current_phase: str
    phases: list[dict]
