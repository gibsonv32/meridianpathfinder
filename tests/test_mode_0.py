from __future__ import annotations

from pathlib import Path

from meridian.core.state import MeridianProject
from meridian.modes.mode_0 import Mode0Executor


def _fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_data.csv"


def test_mode0_generates_fingerprint(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    assert artifact.fingerprint_id is not None
    # FingerprintStore is keyed by artifact_id (and should match fingerprint_id)
    fpath = next((project.project_path / ".meridian" / "artifacts" / "mode_0").glob("Mode0GatePacket_*.json"))
    assert project.fingerprint_store.verify(artifact.fingerprint_id, fpath.read_bytes()) is True


def test_mode0_detects_missing_values(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    assert artifact.quality_assessment.missing_pct["spent_30d"] > 0


def test_mode0_detects_duplicates(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    assert artifact.quality_assessment.duplicate_rows >= 1


def test_mode0_distribution_stats_numeric(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    stats = artifact.distribution_summary["last_login_days"].stats
    assert "mean" in stats


def test_mode0_distribution_stats_categorical(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    stats = artifact.distribution_summary["segment"].stats
    assert "unique_count" in stats


def test_mode0_identifies_risks(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    assert len(artifact.risks) >= 1


def test_mode0_saves_artifact(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0Executor(project=project, llm=None)
    artifact = ex.run(_fixture_path(), headless=True)
    mode0_dir = project.project_path / ".meridian" / "artifacts" / "mode_0"
    assert any(p.name.endswith(f"{artifact.artifact_id}.json") for p in mode0_dir.glob("*.json"))

