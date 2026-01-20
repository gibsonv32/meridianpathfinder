from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.modes.mode_0 import Mode0Executor
from meridian.modes.mode_1 import Mode1Executor
from meridian.modes.mode_2 import Mode2Executor
from meridian.modes.mode_3 import Mode3Executor
from meridian.modes.mode_4 import Mode4Executor
from meridian.modes.mode_5 import Mode5Executor


def _make_dataset(path: Path) -> None:
    rng = np.random.default_rng(5)
    n = 300
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(2.0 * x1 - 1.0 * x2)))
    y = (p > 0.5).astype(int)
    pd.DataFrame({"x1": x1, "x2": x2, "target": y}).to_csv(path, index=False)


def test_mode5_requires_mode4_complete(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex5 = Mode5Executor(project=project, llm=None)
    with pytest.raises(RuntimeError):
        ex5.run(output_dir=project.project_path / "PROJECT", headless=True)


def test_mode5_writes_plan_and_project_scaffold(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Validate feasibility",
        hypotheses=["h1", "h2"],
        verdict=GateVerdict.GO,
        headless=True,
    )
    data = tmp_path / "d.csv"
    _make_dataset(data)
    Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    Mode3Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    Mode4Executor(project=project, llm=None).run(headless=True)

    out = project.project_path / "PROJECT"
    plan = Mode5Executor(project=project, llm=None).run(output_dir=out, headless=True)

    mode5_dir = project.project_path / ".meridian" / "artifacts" / "mode_5"
    plan_path = next(mode5_dir.glob(f"CodeGenerationPlan_{plan.artifact_id}.json"))
    assert plan.fingerprint_id == plan.artifact_id
    assert project.fingerprint_store.verify(plan.fingerprint_id, plan_path.read_bytes()) is True
    assert project.is_mode_complete(Mode.MODE_5) is True

    assert (out / "README.md").exists()
    assert (out / "src" / "pipeline.py").exists()
    assert (out / "tests" / "test_smoke.py").exists()
    assert (out / "config" / "plan.json").exists()

