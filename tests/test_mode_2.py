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


def _make_dataset(path: Path, *, leak: bool = False, random_labels: bool = False) -> None:
    rng = np.random.default_rng(0)
    n = 400
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    logits = 2.5 * x1 - 1.2 * x2
    p = 1 / (1 + np.exp(-logits))
    y = (p > 0.5).astype(int)
    if random_labels:
        y = rng.integers(0, 2, size=n)
    df = pd.DataFrame({"x1": x1, "x2": x2, "target": y})
    if leak:
        df["leak_feature"] = df["target"]
    df.to_csv(path, index=False)


def test_mode2_requires_mode1_complete(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    data = tmp_path / "d.csv"
    _make_dataset(data)
    ex2 = Mode2Executor(project=project, llm=None)
    with pytest.raises(RuntimeError):
        ex2.run(data_path=data, target_col="target", headless=True)


def test_baseline_trains_successfully(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    # satisfy gates with Mode 0 + Mode 1 artifacts
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Reduce churn", hypotheses=["h1", "h2"], verdict=GateVerdict.GO, headless=True
    )
    data = tmp_path / "d.csv"
    _make_dataset(data)

    report = Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    assert report.baseline_results.metrics["primary"] > 0.6


def test_label_shuffle_detects_real_signal(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Reduce churn", hypotheses=["h1", "h2"], verdict=GateVerdict.GO, headless=True
    )
    data = tmp_path / "d.csv"
    _make_dataset(data)
    report = Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    assert report.probe_results["label_shuffle"].status in ("PASS", "WARN")


def test_label_shuffle_fails_on_random_labels(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Reduce churn", hypotheses=["h1", "h2"], verdict=GateVerdict.GO, headless=True
    )
    data = tmp_path / "d.csv"
    _make_dataset(data, random_labels=True)
    report = Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    assert report.probe_results["label_shuffle"].status in ("FAIL", "WARN")


def test_future_feature_probe_detects_leakage(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Reduce churn", hypotheses=["h1", "h2"], verdict=GateVerdict.GO, headless=True
    )
    data = tmp_path / "d.csv"
    _make_dataset(data, leak=True)
    report = Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    assert report.probe_results["future_feature"].status == "FAIL"
    assert report.gate_verdict in (GateVerdict.NO_GO, GateVerdict.CONDITIONAL)


def test_signal_validation_calculates_lift(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Reduce churn", hypotheses=["h1", "h2"], verdict=GateVerdict.GO, headless=True
    )
    data = tmp_path / "d.csv"
    _make_dataset(data)
    report = Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)
    assert report.signal_validation.lift != 0


def test_mode2_saves_artifact_with_fingerprint(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    Mode0Executor(project=project, llm=None).run(Path(__file__).parent / "fixtures" / "sample_data.csv", headless=True)
    Mode1Executor(project=project, llm=None).run(
        business_kpi="Reduce churn", hypotheses=["h1", "h2"], verdict=GateVerdict.GO, headless=True
    )
    data = tmp_path / "d.csv"
    _make_dataset(data)
    report = Mode2Executor(project=project, llm=None).run(data_path=data, target_col="target", headless=True)

    mode2_dir = project.project_path / ".meridian" / "artifacts" / "mode_2"
    fpath = next(mode2_dir.glob(f"FeasibilityReport_{report.artifact_id}.json"))
    assert report.fingerprint_id == report.artifact_id
    assert project.fingerprint_store.verify(report.fingerprint_id, fpath.read_bytes()) is True
    assert project.is_mode_complete(Mode.MODE_2) is True

