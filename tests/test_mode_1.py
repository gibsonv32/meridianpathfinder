from __future__ import annotations

from pathlib import Path

import pytest

from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.modes.mode_0 import Mode0Executor
from meridian.modes.mode_1 import Mode1Executor


def _fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_data.csv"


def test_mode1_requires_mode0_complete(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex1 = Mode1Executor(project=project, llm=None)
    with pytest.raises(RuntimeError):
        ex1.run(business_kpi="Reduce churn", hypotheses=["h1", "h2"], headless=True)


def test_mode1_saves_artifact_and_fingerprint(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(_fixture_path(), headless=True)

    ex1 = Mode1Executor(project=project, llm=None)
    dip = ex1.run(
        business_kpi="Reduce churn rate",
        hypotheses=["Engagement drives churn", "Support issues drive churn"],
        verdict=GateVerdict.GO,
        headless=True,
    )

    mode1_dir = project.project_path / ".meridian" / "artifacts" / "mode_1"
    fpath = next(mode1_dir.glob(f"DecisionIntelProfile_{dip.artifact_id}.json"))
    assert dip.fingerprint_id == dip.artifact_id
    assert project.fingerprint_store.verify(dip.fingerprint_id, fpath.read_bytes()) is True
    assert project.is_mode_complete(Mode.MODE_1) is True

