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


def _make_dataset(path: Path) -> None:
    rng = np.random.default_rng(1)
    n = 400
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(2.5 * x1 - 1.2 * x2)))
    y = (p > 0.5).astype(int)
    pd.DataFrame({"x1": x1, "x2": x2, "target": y}).to_csv(path, index=False)


def test_mode3_requires_mode2_complete(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    data = tmp_path / "d.csv"
    _make_dataset(data)
    ex3 = Mode3Executor(project=project, llm=None)
    with pytest.raises(RuntimeError):
        ex3.run(data_path=data, target_col="target", headless=True)


def test_mode3_saves_both_artifacts_and_fingerprints(tmp_path: Path):
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

    mr, fr = Mode3Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)

    mode3_dir = project.project_path / ".meridian" / "artifacts" / "mode_3"
    mr_path = next(mode3_dir.glob(f"ModelRecommendations_{mr.artifact_id}.json"))
    fr_path = next(mode3_dir.glob(f"FeatureRegistry_{fr.artifact_id}.json"))
    assert mr.fingerprint_id == mr.artifact_id
    assert fr.fingerprint_id == fr.artifact_id
    assert project.fingerprint_store.verify(mr.fingerprint_id, mr_path.read_bytes()) is True
    assert project.fingerprint_store.verify(fr.fingerprint_id, fr_path.read_bytes()) is True
    assert project.is_mode_complete(Mode.MODE_3) is True

