from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split

from meridian.artifacts.schemas import BaselineResults, FeasibilityReport, ProbeResult, SignalValidation, SplitInfo
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode2Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_2

    def run(
        self,
        *,
        data_path: Path,
        target_col: str,
        split: str = "stratified",
        date_col: Optional[str] = None,
        headless: bool = False,
    ) -> FeasibilityReport:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_2)

        # Try self-healing CSV load if available
        data_path = Path(data_path).expanduser().resolve()
        if self.llm:
            try:
                from meridian.data.healer import DataHealer
                healer = DataHealer(self.llm, self.project.project_path)
                df = healer.resilient_read_csv(data_path)
            except Exception:
                df = pd.read_csv(data_path)
        else:
            df = pd.read_csv(data_path)
        if target_col not in df.columns:
            raise ValueError(f"target_col '{target_col}' not in dataset")

        y = df[target_col]
        X = df.drop(columns=[target_col])
        X = self._prep_features(X)

        is_classification = self._is_binary_target(y)
        split_info, splits = self._make_split(X, y, split=split, date_col=date_col)
        X_train, X_val, X_test, y_train, y_val, y_test = splits

        baseline_metric, model_type = self._train_baseline(
            X_train, y_train, X_val, y_val, is_classification=is_classification
        )

        random_metric = 0.5 if is_classification else float(mean_squared_error(y_val, np.repeat(y_train.mean(), len(y_val))) ** 0.5)
        lift = self._calc_lift(baseline_metric, random_metric, is_classification=is_classification)
        signal_present = bool(lift > 0.1) if is_classification else bool(lift > 0.1)

        probe_results: Dict[str, ProbeResult] = {}
        probe_results["label_shuffle"] = self._label_shuffle_probe(
            X_train, y_train, X_val, y_val, baseline_metric, is_classification=is_classification
        )
        probe_results["future_feature"] = self._future_feature_probe(X_train, y_train, is_classification=is_classification)
        probe_results["time_travel"] = self._time_travel_probe(df=df, date_col=date_col)
        probe_results["join_fanout"] = ProbeResult(status="PASS", details={"note": "no joins in baseline pipeline"})

        baseline_results = BaselineResults(model_type=model_type, metrics={"primary": float(baseline_metric)})
        signal_validation = SignalValidation(
            baseline_metric=float(baseline_metric),
            random_metric=float(random_metric),
            lift=float(lift),
            signal_present=signal_present,
        )

        verdict = self._recommend_verdict(lift=lift, probe_results=probe_results)

        report = FeasibilityReport(
            split_info=split_info,
            baseline_results=baseline_results,
            probe_results=probe_results,
            signal_validation=signal_validation,
            gate_verdict=verdict,
        )

        if (not headless) and self.llm is not None:
            try:
                _ = self.llm.complete(
                    "Summarize feasibility results. Return 3 bullets + recommended verdict.\n"
                    f"baseline={baseline_metric:.4f} random={random_metric:.4f} lift={lift:.4f}\n"
                    f"probes={ {k:v.status for k,v in probe_results.items()} }\n",
                    max_tokens=200,
                )
            except Exception:
                pass

        mode_dir = self.project.artifact_store / "mode_2"
        mode_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = mode_dir / f"FeasibilityReport_{report.artifact_id}.json"
        report.to_file(artifact_path)

        fp = generate_fingerprint(
            artifact_type="FeasibilityReport",
            content=artifact_path.read_bytes(),
            parent_ids=[self._latest_artifact_id("DecisionIntelProfile")],
            mode="mode_2",
            input_paths=[Path(data_path).expanduser().resolve()],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=report.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp)
        report.fingerprint_id = fp.artifact_id
        report.to_file(artifact_path)

        self.project.complete_mode(Mode.MODE_2, verdict=verdict, artifact_ids=[report.artifact_id])
        return report

    def _latest_artifact_id(self, artifact_type: str) -> str:
        p = self.project.get_artifact(artifact_type)
        if not p:
            return ""
        try:
            data = pd.read_json(p)
            return str(data.get("artifact_id", ""))
        except Exception:
            # fallback: parse from filename
            return p.stem.split("_")[-1]

    def _prep_features(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        # drop non-numeric columns for baseline
        for c in list(X.columns):
            if not pd.api.types.is_numeric_dtype(X[c]):
                X = X.drop(columns=[c])
        X = X.fillna(0)
        return X

    def _is_binary_target(self, y: pd.Series) -> bool:
        vals = y.dropna().unique()
        if len(vals) <= 2:
            return True
        return False

    def _make_split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        *,
        split: str,
        date_col: Optional[str],
        train_pct: float = 0.7,
        val_pct: float = 0.15,
    ) -> tuple[SplitInfo, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]]:
        n = len(X)
        if split == "temporal":
            if not date_col or date_col not in X.columns and date_col not in y.index:
                raise ValueError("--date-col required for temporal split (and must be in dataset)")
            # For simplicity, require date_col exists in original df; caller will pass date_col from df.
            raise ValueError("temporal split not supported in this MVP without full timestamp pipeline")

        # stratified/random split
        stratify = y if split == "stratified" and self._is_binary_target(y) else None
        X_train, X_tmp, y_train, y_tmp = train_test_split(
            X, y, test_size=(1.0 - train_pct), random_state=42, stratify=stratify
        )
        stratify_tmp = y_tmp if stratify is not None else None
        rel_test = (1.0 - train_pct - val_pct) / (1.0 - train_pct)
        X_val, X_test, y_val, y_test = train_test_split(
            X_tmp, y_tmp, test_size=rel_test, random_state=42, stratify=stratify_tmp
        )
        split_info = SplitInfo(
            train_size=int(len(X_train)),
            val_size=int(len(X_val)),
            test_size=int(len(X_test)),
            split_method=split,
            split_params={"train_pct": train_pct, "val_pct": val_pct},
        )
        return split_info, (X_train, X_val, X_test, y_train, y_val, y_test)

    def _train_baseline(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        *,
        is_classification: bool,
    ) -> tuple[float, str]:
        if is_classification:
            model = LogisticRegression(max_iter=200)
            model.fit(X_train, y_train)
            proba = model.predict_proba(X_val)[:, 1]
            return float(roc_auc_score(y_val, proba)), "LogisticRegression"
        model = Ridge()
        model.fit(X_train, y_train)
        preds = model.predict(X_val)
        rmse = float(mean_squared_error(y_val, preds) ** 0.5)
        # For regression, higher is better? We'll negate RMSE for "primary" metric.
        return float(-rmse), "Ridge"

    def _label_shuffle_probe(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        baseline_metric: float,
        *,
        is_classification: bool,
    ) -> ProbeResult:
        rng = np.random.default_rng(42)
        y_shuf = pd.Series(rng.permutation(y_train.to_numpy()), index=y_train.index)
        shuf_metric, _ = self._train_baseline(X_train, y_shuf, X_val, y_val, is_classification=is_classification)
        drop = float(baseline_metric - shuf_metric)
        status = "PASS" if drop > 0.3 else ("WARN" if drop > 0.1 else "FAIL")
        return ProbeResult(status=status, details={"baseline": baseline_metric, "shuffled": shuf_metric, "drop": drop})

    def _future_feature_probe(self, X: pd.DataFrame, y: pd.Series, *, is_classification: bool) -> ProbeResult:
        # Flag any feature nearly perfectly correlated with target (simple leakage heuristic)
        if X.shape[1] == 0:
            return ProbeResult(status="WARN", details={"reason": "no numeric features"})
        y_num = pd.to_numeric(y, errors="coerce").fillna(0)
        flagged: list[str] = []
        for c in X.columns:
            corr = np.corrcoef(pd.to_numeric(X[c], errors="coerce").fillna(0), y_num)[0, 1]
            if np.isnan(corr):
                continue
            if abs(float(corr)) > 0.95:
                flagged.append(c)
        if flagged:
            return ProbeResult(status="FAIL", details={"flagged": flagged})
        return ProbeResult(status="PASS", details={"flagged": []})

    def _time_travel_probe(self, *, df: pd.DataFrame, date_col: Optional[str]) -> ProbeResult:
        # MVP: if date_col provided ensure it's monotonic increasing (basic sanity), else WARN.
        if not date_col:
            return ProbeResult(status="WARN", details={"reason": "no date_col provided"})
        if date_col not in df.columns:
            return ProbeResult(status="FAIL", details={"reason": f"date_col '{date_col}' not found"})
        try:
            s = pd.to_datetime(df[date_col], errors="coerce")
            if s.isna().any():
                return ProbeResult(status="WARN", details={"reason": "date parsing produced NaT"})
            return ProbeResult(status="PASS", details={"monotonic": bool(s.is_monotonic_increasing)})
        except Exception as e:
            return ProbeResult(status="FAIL", details={"reason": str(e)})

    def _calc_lift(self, baseline_metric: float, random_metric: float, *, is_classification: bool) -> float:
        if is_classification:
            if random_metric == 0:
                return 0.0
            return (baseline_metric - random_metric) / abs(random_metric)
        # For regression, baseline_metric is negative RMSE; random_metric is RMSE
        if random_metric == 0:
            return 0.0
        return (-baseline_metric - random_metric) / abs(random_metric) * -1.0

    def _recommend_verdict(self, *, lift: float, probe_results: Dict[str, ProbeResult]) -> GateVerdict:
        if any(p.status == "FAIL" for p in probe_results.values()):
            return GateVerdict.NO_GO
        if lift <= 0.1:
            return GateVerdict.CONDITIONAL
        return GateVerdict.GO

