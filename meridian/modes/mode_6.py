from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional

from meridian.artifacts.schemas import (
    CodeGenerationPlan,
    ComplianceStatus,
    DriftReport,
    ExecutionOpsScorecard,
    Incident,
    RuntimeMetrics,
)
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode6Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_6

    def run(self, *, project_dir: Optional[Path] = None, headless: bool = False) -> ExecutionOpsScorecard:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_6)

        plan_path = self.project.get_artifact("CodeGenerationPlan")
        if not plan_path:
            raise RuntimeError("Required artifact CodeGenerationPlan not found")
        plan = CodeGenerationPlan.from_file(plan_path)

        # Determine where the generated PROJECT scaffold lives.
        proj = Path(project_dir or plan.output_path).expanduser().resolve()
        if not proj.exists():
            raise FileNotFoundError(f"--project '{proj}' does not exist (from plan.output_path or CLI override)")

        # Run smoke tests in the generated scaffold.
        test_t0 = perf_counter()
        pytest_result = self._run_pytest(proj)
        test_ms = int((perf_counter() - test_t0) * 1000)

        incidents = []
        compliance = "ok" if pytest_result.returncode == 0 else "failed"
        if pytest_result.returncode != 0:
            incidents.append(
                Incident(
                    id="INC001",
                    severity="SEV1",
                    description="PROJECT smoke tests failed; see runtime_metrics.pytest_stderr / pytest_stdout.",
                )
            )

        metrics = RuntimeMetrics(
            metrics={
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
                "project_dir": str(proj),
                "pytest_returncode": int(pytest_result.returncode),
                "pytest_duration_ms": test_ms,
                "pytest_stdout": pytest_result.stdout[-4000:] if pytest_result.stdout else "",
                "pytest_stderr": pytest_result.stderr[-4000:] if pytest_result.stderr else "",
            }
        )

        scorecard = ExecutionOpsScorecard(
            runtime_metrics=metrics,
            compliance_status=ComplianceStatus(status=compliance),
            drift_report=DriftReport(psi={}),
            incidents=incidents,
        )

        # Optional LLM summarization (best-effort)
        if (not headless) and self.llm is not None:
            try:
                _ = self.llm.complete(
                    "Summarize this execution scorecard in 3 bullets.\n"
                    f"status={scorecard.compliance_status.status}\n"
                    f"pytest_returncode={pytest_result.returncode}\n",
                    max_tokens=150,
                )
            except Exception:
                pass

        # Save artifact
        mode_dir = self.project.artifact_store / "mode_6"
        mode_dir.mkdir(parents=True, exist_ok=True)
        sc_path = mode_dir / f"ExecutionOpsScorecard_{scorecard.artifact_id}.json"
        scorecard.to_file(sc_path)

        # Fingerprint
        proj_inputs: list[Path] = []
        for rel in ["config/plan.json", "src/pipeline.py", "tests/test_smoke.py"]:
            p = proj / rel
            if p.exists() and p.is_file():
                proj_inputs.append(p)

        fp = generate_fingerprint(
            artifact_type="ExecutionOpsScorecard",
            content=sc_path.read_bytes(),
            parent_ids=[plan.artifact_id],
            mode="mode_6",
            input_paths=[plan_path, *proj_inputs],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=scorecard.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp)
        scorecard.fingerprint_id = fp.artifact_id
        scorecard.to_file(sc_path)

        verdict = GateVerdict.GO if pytest_result.returncode == 0 else GateVerdict.CONDITIONAL
        self.project.complete_mode(Mode.MODE_6, verdict=verdict, artifact_ids=[scorecard.artifact_id])
        return scorecard

    def _run_pytest(self, project_dir: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        # Avoid user-installed pytest plugins from breaking generated scaffold.
        env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        cmd = [sys.executable, "-m", "pytest", "-q"]
        return subprocess.run(
            cmd,
            cwd=str(project_dir),
            env=env,
            text=True,
            capture_output=True,
            timeout=300,
            check=False,
        )

