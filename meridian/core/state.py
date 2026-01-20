from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from meridian import __version__
from meridian.config import _read_yaml, _write_yaml
from meridian.core.fingerprint import FingerprintStore
from meridian.core.gates import GateVerdict
from meridian.core.gates import GateEnforcer
from meridian.core.modes import Mode


@dataclass
class ModeState:
    mode: Mode
    status: Literal["not_started", "in_progress", "complete"]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    gate_verdict: Optional[GateVerdict] = None
    artifact_ids: List[str] = None  # type: ignore[assignment]


class ProjectState(BaseModel):
    project_name: str
    created_at: datetime
    current_mode: Optional[Mode] = None
    mode_states: Dict[Mode, ModeState]
    config_hash: str


class MeridianProject:
    """Project container with persisted state and artifacts."""

    def __init__(self, project_path: Path):
        self.project_path = project_path.resolve()
        self._config_path = self.project_path / "meridian.yaml"
        self._state_path = self.project_path / ".meridian" / "state.json"
        self.artifact_store = self.project_path / ".meridian" / "artifacts"
        self.fingerprint_store = FingerprintStore(self.project_path / ".meridian" / "fingerprints.db")

        self.config: Dict[str, Any] = _read_yaml(self._config_path)
        self.state: ProjectState = self._load_state()

    @staticmethod
    def _resolve_project_root(start: Path) -> Path:
        """
        Allow running CLI from subdirectories (e.g. ./PROJECT).
        We treat a directory as a MERIDIAN project root if it contains either:
        - meridian.yaml
        - .meridian/state.json
        """
        p = start.resolve()
        for candidate in [p, *p.parents]:
            if (candidate / "meridian.yaml").exists():
                return candidate
            if (candidate / ".meridian" / "state.json").exists():
                return candidate
        return p

    @classmethod
    def create(cls, path: Path, name: str, config: dict) -> "MeridianProject":
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        (path / ".meridian").mkdir(parents=True, exist_ok=True)
        (path / "data").mkdir(parents=True, exist_ok=True)
        (path / "data" / "raw").mkdir(parents=True, exist_ok=True)
        (path / "data" / "processed").mkdir(parents=True, exist_ok=True)
        (path / ".meridian" / "artifacts").mkdir(parents=True, exist_ok=True)

        cfg_path = path / "meridian.yaml"
        _write_yaml(cfg_path, dict(config))
        cfg_bytes = cfg_path.read_bytes() if cfg_path.exists() else b""
        cfg_hash = sha256(cfg_bytes).hexdigest()

        mode_states = {m: ModeState(mode=m, status="not_started", artifact_ids=[]) for m in Mode}
        state = ProjectState(
            project_name=name,
            created_at=datetime.now(timezone.utc),
            current_mode=None,
            mode_states=mode_states,
            config_hash=cfg_hash,
        )
        state_path = path / ".meridian" / "state.json"
        state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return cls(path)

    @classmethod
    def load(cls, path: Path) -> "MeridianProject":
        return cls(cls._resolve_project_root(path))

    def save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def _load_state(self) -> ProjectState:
        if not self._state_path.exists():
            # Create minimal default state if missing.
            cfg_bytes = self._config_path.read_bytes() if self._config_path.exists() else b""
            cfg_hash = sha256(cfg_bytes).hexdigest()
            mode_states = {m: ModeState(mode=m, status="not_started", artifact_ids=[]) for m in Mode}
            return ProjectState(
                project_name=self.project_path.name,
                created_at=datetime.now(timezone.utc),
                current_mode=None,
                mode_states=mode_states,
                config_hash=cfg_hash,
            )
        return ProjectState.model_validate_json(self._state_path.read_text(encoding="utf-8"))

    def is_mode_complete(self, mode: Mode) -> bool:
        return self.state.mode_states[mode].status == "complete"

    def get_gate_verdict(self, mode: Mode) -> Optional[GateVerdict]:
        return self.state.mode_states[mode].gate_verdict

    def get_current_mode(self) -> Optional[Mode]:
        return self.state.current_mode

    def start_mode(self, mode: Mode) -> None:
        enforcer = GateEnforcer(self)
        result = enforcer.can_enter_mode(mode)
        if not result.allowed:
            raise RuntimeError(f"Gate blocked: {result.reason}")

        ms = self.state.mode_states[mode]
        ms.status = "in_progress"
        ms.started_at = datetime.now(timezone.utc)
        self.state.current_mode = mode
        self.save()

    def complete_mode(self, mode: Mode, verdict: GateVerdict, artifact_ids: List[str]) -> None:
        ms = self.state.mode_states[mode]
        ms.status = "complete"
        ms.completed_at = datetime.now(timezone.utc)
        ms.gate_verdict = verdict
        ms.artifact_ids = list(artifact_ids)
        self.state.current_mode = None
        self.save()

    def get_artifact(self, artifact_type: str) -> Optional[Path]:
        """
        Return path to the most recent artifact file matching `artifact_type`
        by filename convention.
        """
        if not self.artifact_store.exists():
            return None
        matches: list[Path] = []
        for p in self.artifact_store.rglob("*.json"):
            if artifact_type in p.name:
                matches.append(p)
        if not matches:
            return None
        return sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    @property
    def meridian_version(self) -> str:
        return __version__

