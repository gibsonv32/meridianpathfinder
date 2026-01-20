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
from meridian.modes.mode_6 import Mode6Executor
from meridian.modes.mode_6_5 import Mode6_5Executor
from meridian.modes.mode_7 import Mode7Executor


def _make_dataset(path: Path) -> None:
    rng = np.random.default_rng(8)
    n = 250
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(1.0 * x1 - 0.5 * x2)))
    y = rng.binomial(1, p).astype(int)
    pd.DataFrame({"x1": x1, "x2": x2, "target": y}).to_csv(path, index=False)


def test_mode7_requires_mode6_5_complete(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex7 = Mode7Executor(project=project, llm=None)
    with pytest.raises(RuntimeError):
        ex7.run(headless=True)


def test_mode7_saves_delivery_manifest_and_deliverables(tmp_path: Path):
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
    Mode5Executor(project=project, llm=None).run(output_dir=out, headless=True)
    Mode6Executor(project=project, llm=None).run(project_dir=out, headless=True)
    Mode6_5Executor(project=project, llm=None).run(headless=True)

    mf = Mode7Executor(project=project, llm=None).run(headless=True)

    mode_dir = project.project_path / ".meridian" / "artifacts" / "mode_7"
    mf_path = next(mode_dir.glob(f"DeliveryManifest_{mf.artifact_id}.json"))
    assert mf.fingerprint_id == mf.artifact_id
    assert project.fingerprint_store.verify(mf.fingerprint_id, mf_path.read_bytes()) is True
    assert project.is_mode_complete(Mode.MODE_7) is True

    deliver_dir = project.project_path / ".meridian" / "deliverables"
    assert (deliver_dir / "ExecutiveSummary.md").exists()
    assert (deliver_dir / "TechnicalReport.md").exists()

