from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from meridian.core.fingerprint import FingerprintStore
from meridian.core.modes import Mode


class GateVerdict(str, Enum):
    GO = "go"
    CONDITIONAL = "conditional"
    NO_GO = "no_go"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: str
    verdict: Optional[GateVerdict] = None
    override_permitted: bool = True


class GateEnforcer:
    """Hard enforcement of mode transitions."""

    def __init__(self, project: "MeridianProject"):
        self.project = project

    def can_enter_mode(self, target: Mode) -> GateResult:
        """
        Returns GateResult with allowed=True/False and reason.
        This is NOT advisory—execution should halt if allowed=False.
        """
        predecessor = MODE_DEPENDENCIES.get(target)
        if predecessor is not None:
            if not bool(getattr(self.project, "is_mode_complete")(predecessor)):
                return GateResult(
                    allowed=False,
                    reason=f"Mode {predecessor.value} not complete",
                    verdict=GateVerdict.BLOCKED,
                )

        required_artifact = REQUIRED_ARTIFACTS.get(target)
        if required_artifact:
            artifact = getattr(self.project, "get_artifact")(required_artifact)
            if not artifact:
                return GateResult(
                    allowed=False,
                    reason=f"Required artifact {required_artifact} not found",
                    verdict=GateVerdict.BLOCKED,
                )
            if not _artifact_validates(artifact):
                return GateResult(
                    allowed=False,
                    reason=f"Artifact {required_artifact} fails schema validation",
                    verdict=GateVerdict.BLOCKED,
                )

        if predecessor is not None:
            verdict = getattr(self.project, "get_gate_verdict")(predecessor)
            if verdict == GateVerdict.BLOCKED:
                return GateResult(
                    allowed=False,
                    reason=f"Mode {predecessor.value} verdict is BLOCKED",
                    verdict=GateVerdict.BLOCKED,
                    override_permitted=False,
                )
            if verdict == GateVerdict.NO_GO:
                return GateResult(
                    allowed=False,
                    reason=f"Mode {predecessor.value} verdict is NO_GO",
                    verdict=GateVerdict.NO_GO,
                    override_permitted=True,
                )
            if verdict == GateVerdict.CONDITIONAL:
                return GateResult(
                    allowed=True,
                    reason=f"Mode {predecessor.value} verdict is CONDITIONAL",
                    verdict=GateVerdict.CONDITIONAL,
                    override_permitted=True,
                )

        return GateResult(allowed=True, reason="All prerequisites met", verdict=GateVerdict.GO, override_permitted=True)

    def log_override(self, mode: Mode, reason: str, fingerprint_id: str) -> None:
        store: Any = getattr(self.project, "fingerprint_store", None)
        if isinstance(store, FingerprintStore):
            store.log_override(mode=mode.value, reason=reason, fingerprint_id=fingerprint_id)


def _artifact_validates(artifact: Any) -> bool:
    # Prefer explicit validator methods if present.
    validates = getattr(artifact, "validates", None)
    if callable(validates):
        return bool(validates())
    validate_schema = getattr(artifact, "validate_schema", None)
    if callable(validate_schema):
        return bool(validate_schema())
    # As a last resort: consider it present and "valid".
    return True


MODE_DEPENDENCIES: dict[Mode, Optional[Mode]] = {
    Mode.MODE_0: None,
    Mode.MODE_0_5: None,
    Mode.MODE_1: Mode.MODE_0,
    Mode.MODE_2: Mode.MODE_1,
    Mode.MODE_3: Mode.MODE_2,
    Mode.MODE_4: Mode.MODE_3,
    Mode.MODE_5: Mode.MODE_4,
    Mode.MODE_6: Mode.MODE_5,
    Mode.MODE_6_5: Mode.MODE_6,
    Mode.MODE_7: Mode.MODE_6_5,
}


REQUIRED_ARTIFACTS: dict[Mode, Optional[str]] = {
    Mode.MODE_0: None,
    Mode.MODE_0_5: None,
    Mode.MODE_1: "Mode0GatePacket",
    Mode.MODE_2: "DecisionIntelProfile",
    Mode.MODE_3: "FeasibilityReport",
    Mode.MODE_4: "ModelRecommendations",
    Mode.MODE_5: "BusinessCaseScorecard",
    Mode.MODE_6: "CodeGenerationPlan",
    Mode.MODE_6_5: "ExecutionOpsScorecard",
    Mode.MODE_7: "InterpretationPackage",
}
