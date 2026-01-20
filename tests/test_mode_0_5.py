from __future__ import annotations

from pathlib import Path

import pytest

from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.modes.mode_0_5 import Mode0_5Executor


def test_mode0_5_is_entry_mode(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0_5Executor(project=project, llm=None)
    backlog, brief = ex.run(problem_statement="Reduce churn", target_entity="customer", headless=True)
    assert backlog.fingerprint_id == backlog.artifact_id
    assert brief.fingerprint_id == brief.artifact_id
    assert project.is_mode_complete(Mode.MODE_0_5) is True


def test_mode0_5_saves_artifacts_and_fingerprints(tmp_path: Path):
    project = MeridianProject.create(tmp_path / "proj", name="proj", config={})
    ex = Mode0_5Executor(project=project, llm=None)
    backlog, brief = ex.run(
        problem_statement="Reduce churn",
        target_entity="customer",
        candidates=["prediction:Predict churn risk", "detection:Detect service incidents"],
        select_id="opp_2",
        data_requirements=["events", "billing"],
        headless=True,
    )

    mode_dir = project.project_path / ".meridian" / "artifacts" / "mode_0_5"
    backlog_path = next(mode_dir.glob(f"OpportunityBacklog_{backlog.artifact_id}.json"))
    brief_path = next(mode_dir.glob(f"OpportunityBrief_{brief.artifact_id}.json"))

    assert project.fingerprint_store.verify(backlog.fingerprint_id, backlog_path.read_bytes()) is True
    assert project.fingerprint_store.verify(brief.fingerprint_id, brief_path.read_bytes()) is True
    assert brief.selected_opportunity_id == "opp_2"
    assert "events" in brief.data_requirements

