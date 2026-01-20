from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import List, Optional, Tuple

import pandas as pd

from meridian.artifacts.schemas import Feature, FeatureRegistry, FeasibilityReport, ModelCandidate, ModelRecommendations
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode3Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_3

    def run(
        self,
        *,
        data_path: Path,
        target_col: str,
        headless: bool = False,
    ) -> Tuple[ModelRecommendations, FeatureRegistry]:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_3)

        # Load Mode 2 report as context (must exist due to gate, but we parse for rationale)
        m2_path = self.project.get_artifact("FeasibilityReport")
        if not m2_path:
            raise RuntimeError("Required artifact FeasibilityReport not found")
        feas = FeasibilityReport.from_file(m2_path)

        df = pd.read_csv(Path(data_path).expanduser().resolve())
        if target_col not in df.columns:
            raise ValueError(f"target_col '{target_col}' not in dataset")

        feature_registry = self._build_feature_registry(df=df, target_col=target_col)
        model_recs = self._recommend_models(feas)

        if (not headless) and self.llm is not None:
            try:
                model_recs.rationale = (
                    self.llm.complete(
                        "Given feasibility results, refine this model recommendation rationale in 2-3 sentences.\n"
                        f"Current rationale: {model_recs.rationale}\n"
                        f"Lift: {feas.signal_validation.lift:.4f}, baseline metric: {feas.baseline_results.metrics.get('primary')}\n",
                        max_tokens=200,
                    ).strip()
                    or model_recs.rationale
                )
            except Exception:
                pass

        # Save artifacts
        mode_dir = self.project.artifact_store / "mode_3"
        mode_dir.mkdir(parents=True, exist_ok=True)

        fr_path = mode_dir / f"FeatureRegistry_{feature_registry.artifact_id}.json"
        mr_path = mode_dir / f"ModelRecommendations_{model_recs.artifact_id}.json"
        feature_registry.to_file(fr_path)
        model_recs.to_file(mr_path)

        # Fingerprint both (artifact_id is the fingerprint key)
        data_path_resolved = Path(data_path).expanduser().resolve()

        fr_fp = generate_fingerprint(
            artifact_type="FeatureRegistry",
            content=fr_path.read_bytes(),
            parent_ids=[feas.artifact_id],
            mode="mode_3",
            input_paths=[data_path_resolved, m2_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=feature_registry.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fr_fp)
        feature_registry.fingerprint_id = fr_fp.artifact_id
        feature_registry.to_file(fr_path)

        mr_fp = generate_fingerprint(
            artifact_type="ModelRecommendations",
            content=mr_path.read_bytes(),
            parent_ids=[feas.artifact_id, feature_registry.artifact_id],
            mode="mode_3",
            input_paths=[data_path_resolved, m2_path, fr_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=model_recs.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(mr_fp)
        model_recs.fingerprint_id = mr_fp.artifact_id
        model_recs.to_file(mr_path)

        # Complete state (Mode 3 verdict is advisory here; keep GO if feas is GO else CONDITIONAL)
        verdict = GateVerdict.GO if feas.gate_verdict == GateVerdict.GO else GateVerdict.CONDITIONAL
        self.project.complete_mode(Mode.MODE_3, verdict=verdict, artifact_ids=[model_recs.artifact_id, feature_registry.artifact_id])

        return model_recs, feature_registry

    def _build_feature_registry(self, *, df: pd.DataFrame, target_col: str) -> FeatureRegistry:
        features: List[Feature] = []
        for col in df.columns:
            if col == target_col:
                continue
            features.append(
                Feature(
                    name=col,
                    derivation="raw_column",
                    source_columns=[col],
                    temporal_safe=True,
                    compute_cost="LOW",
                    importance_rank=None,
                )
            )
        return FeatureRegistry(features=features)

    def _recommend_models(self, feas: FeasibilityReport) -> ModelRecommendations:
        baseline = feas.baseline_results.model_type
        lift = float(feas.signal_validation.lift)
        candidates = [
            ModelCandidate(name="LogisticRegression", rationale="Strong, fast baseline for tabular classification."),
            ModelCandidate(name="RandomForestClassifier", rationale="Nonlinear baseline; good with interactions."),
        ]
        recommended = "RandomForestClassifier" if lift > 0.2 else baseline or "LogisticRegression"
        rationale = (
            f"Feasibility lift={lift:.3f}. Start with {baseline} as a reference, then compare against a nonlinear tree model "
            "to capture interactions. Select the best candidate under your constraints."
        )
        return ModelRecommendations(candidates=candidates, recommended=recommended, rationale=rationale)

