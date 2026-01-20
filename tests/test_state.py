from __future__ import annotations

from pathlib import Path

import pytest

from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject


def test_create_project(tmp_path: Path):
    p = MeridianProject.create(tmp_path / "proj", name="proj", config={"llm": {"provider": "anthropic"}})
    assert (p.project_path / "meridian.yaml").exists()
    assert (p.project_path / ".meridian" / "state.json").exists()
    assert (p.project_path / ".meridian" / "fingerprints.db").exists()


def test_load_project(tmp_path: Path):
    root = tmp_path / "proj"
    MeridianProject.create(root, name="proj", config={})
    p = MeridianProject.load(root)
    assert p.state.project_name == "proj"


def test_mode_progression(tmp_path: Path):
    p = MeridianProject.create(tmp_path / "proj", name="proj", config={})

    # Mode 0 is entry mode
    p.start_mode(Mode.MODE_0)
    assert p.get_current_mode() == Mode.MODE_0
    p.complete_mode(Mode.MODE_0, GateVerdict.GO, artifact_ids=["a1"])
    assert p.is_mode_complete(Mode.MODE_0)


def test_cannot_start_mode_without_gate_approval(tmp_path: Path):
    p = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    with pytest.raises(RuntimeError):
        p.start_mode(Mode.MODE_2)  # requires Mode 1 complete


def test_complete_mode_updates_state(tmp_path: Path):
    p = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    p.start_mode(Mode.MODE_0)
    p.complete_mode(Mode.MODE_0, GateVerdict.CONDITIONAL, artifact_ids=["x", "y"])
    ms = p.state.mode_states[Mode.MODE_0]
    assert ms.status == "complete"
    assert ms.gate_verdict == GateVerdict.CONDITIONAL
    assert ms.artifact_ids == ["x", "y"]


def test_state_persists_across_loads(tmp_path: Path):
    root = tmp_path / "proj"
    p = MeridianProject.create(root, name="proj", config={})
    p.start_mode(Mode.MODE_0)
    p.complete_mode(Mode.MODE_0, GateVerdict.GO, artifact_ids=["id1"])

    p2 = MeridianProject.load(root)
    assert p2.is_mode_complete(Mode.MODE_0)
    assert p2.state.mode_states[Mode.MODE_0].artifact_ids == ["id1"]

