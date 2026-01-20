from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional

from meridian.artifacts.schemas import (
    Explanation,
    ExecutionOpsScorecard,
    InterpretationPackage,
)
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode6_5Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_6_5

    def run(self, *, headless: bool = False) -> InterpretationPackage:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_6_5)

        sc_path = self.project.get_artifact("ExecutionOpsScorecard")
        if not sc_path:
            raise RuntimeError("Required artifact ExecutionOpsScorecard not found")
        scorecard = ExecutionOpsScorecard.from_file(sc_path)

        compliance = scorecard.compliance_status.status
        pytest_rc = int(scorecard.runtime_metrics.metrics.get("pytest_returncode", 1))
        duration_ms = int(scorecard.runtime_metrics.metrics.get("pytest_duration_ms", 0))

        confidence: str = "HIGH" if (compliance == "ok" and pytest_rc == 0) else "MEDIUM"

        ip = InterpretationPackage(
            explanations={
                "execution_summary": Explanation(
                    text=(
                        f"Execution validation completed. PROJECT smoke tests returncode={pytest_rc} "
                        f"({duration_ms}ms). Compliance status: {compliance}."
                    ),
                    confidence=confidence,  # type: ignore[arg-type]
                ),
                "risk_notes": Explanation(
                    text=(
                        "Risks are provisional at this stage. If tests fail or runtimes spike, treat results as CONDITIONAL "
                        "and address pipeline reliability before delivery."
                    ),
                    confidence="MEDIUM",  # type: ignore[arg-type]
                ),
            },
            audience_versions={
                "executive": (
                    f"Ops check: {('PASS' if compliance == 'ok' else 'ATTENTION NEEDED')}. "
                    f"Smoke tests {'passed' if pytest_rc == 0 else 'failed'}."
                ),
                "technical": (
                    f"pytest_returncode={pytest_rc}, pytest_duration_ms={duration_ms}, compliance_status={compliance}. "
                    "See ExecutionOpsScorecard.runtime_metrics for stdout/stderr excerpts."
                ),
            },
        )

        if (not headless) and self.llm is not None:
            # Best-effort rewrites (keep deterministic fallbacks)
            try:
                ip.audience_versions["executive"] = (
                    self.llm.complete(
                        "Rewrite this for an executive stakeholder in 1-2 sentences.\n"
                        f"Text: {ip.audience_versions['executive']}\n",
                        max_tokens=120,
                    ).strip()
                    or ip.audience_versions["executive"]
                )
            except Exception:
                pass

        mode_dir = self.project.artifact_store / "mode_6_5"
        mode_dir.mkdir(parents=True, exist_ok=True)
        ip_path = mode_dir / f"InterpretationPackage_{ip.artifact_id}.json"
        ip.to_file(ip_path)

        fp = generate_fingerprint(
            artifact_type="InterpretationPackage",
            content=ip_path.read_bytes(),
            parent_ids=[scorecard.artifact_id],
            mode="mode_6_5",
            input_paths=[sc_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=ip.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp)
        ip.fingerprint_id = fp.artifact_id
        ip.to_file(ip_path)

        verdict = GateVerdict.GO if compliance == "ok" and pytest_rc == 0 else GateVerdict.CONDITIONAL
        self.project.complete_mode(Mode.MODE_6_5, verdict=verdict, artifact_ids=[ip.artifact_id])
        return ip

