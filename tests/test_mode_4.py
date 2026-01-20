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


def _make_dataset(path: Path) -> None:
    rng = np.random.default_rng(2)
    n = 400
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(2.5 * x1 - 1.2 * x2)))
    y = (p > 0.5).astype(int)
    pd.DataFrame({"x1": x1, "x2": x2, "target": y}).to_csv(path, index=False)


def test_mode4_requires_mode3_complete(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex4 = Mode4Executor(project=project, llm=None)
    with pytest.raises(RuntimeError):
        ex4.run(headless=True)


def test_mode4_saves_scorecard_and_thresholds(tmp_path: Path):
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

    sc, tf = Mode4Executor(project=project, llm=None).run(headless=True)

    mode4_dir = project.project_path / ".meridian" / "artifacts" / "mode_4"
    sc_path = next(mode4_dir.glob(f"BusinessCaseScorecard_{sc.artifact_id}.json"))
    tf_path = next(mode4_dir.glob(f"ThresholdFramework_{tf.artifact_id}.json"))
    assert sc.fingerprint_id == sc.artifact_id
    assert tf.fingerprint_id == tf.artifact_id
    assert project.fingerprint_store.verify(sc.fingerprint_id, sc_path.read_bytes()) is True
    assert project.fingerprint_store.verify(tf.fingerprint_id, tf_path.read_bytes()) is True
    assert project.is_mode_complete(Mode.MODE_4) is True

