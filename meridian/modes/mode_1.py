from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import List, Optional

from meridian.artifacts.schemas import DecisionIntelProfile, Hypothesis, KPITrace, Mode0GatePacket
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode1Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_1

    def run(
        self,
        *,
        business_kpi: str,
        hypotheses: List[str],
        verdict: GateVerdict = GateVerdict.GO,
        headless: bool = False,
    ) -> DecisionIntelProfile:
        t0 = perf_counter()

        # Gate check + start
        self.project.start_mode(Mode.MODE_1)

        # Load Mode 0 gate packet as context
        mode0_path = self.project.get_artifact("Mode0GatePacket")
        if not mode0_path:
            raise RuntimeError("Required artifact Mode0GatePacket not found")
        mode0 = Mode0GatePacket.from_file(mode0_path)

        # Build hypotheses list (min 2 enforced by schema)
        hyp_models = [Hypothesis(statement=h) for h in hypotheses]

        dip = DecisionIntelProfile(
            kpi_trace=KPITrace(business_kpi=business_kpi),
            hypotheses=hyp_models,
            gate_verdict=verdict,
            # keep these empty for now; Mode 1 will be extended later
            constraint_matrix={},
            definitions_of_done={},
            assumptions=[],
        )

        # Optional LLM enrichment: rewrite KPI in clearer language
        if (not headless) and self.llm is not None:
            try:
                improved = self.llm.complete(
                    "Rewrite this business KPI as a crisp, measurable objective (one sentence).\n"
                    f"KPI: {business_kpi}\n"
                    f"Dataset rows: {mode0.dataset_fingerprint.n_rows}, cols: {mode0.dataset_fingerprint.n_cols}\n",
                    max_tokens=120,
                ).strip()
                if improved:
                    dip.kpi_trace.business_kpi = improved
            except Exception:
                pass

        # Save artifact
        mode_dir = self.project.artifact_store / "mode_1"
        mode_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = mode_dir / f"DecisionIntelProfile_{dip.artifact_id}.json"
        dip.to_file(artifact_path)

        # Fingerprint (use artifact_id as fingerprint key)
        content = artifact_path.read_bytes()
        fp = generate_fingerprint(
            artifact_type="DecisionIntelProfile",
            content=content,
            parent_ids=[mode0.artifact_id],
            mode="mode_1",
            input_paths=[mode0_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=dip.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp)

        dip.fingerprint_id = fp.artifact_id
        dip.to_file(artifact_path)

        # Complete state
        self.project.complete_mode(Mode.MODE_1, verdict=verdict, artifact_ids=[dip.artifact_id])
        return dip

