from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional

from meridian.artifacts.schemas import (
    BusinessCaseScorecard,
    CodeGenerationPlan,
    ConfigSpec,
    PipelineSpec,
    TestSpec,
    ThresholdFramework,
)
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode5Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_5

    def run(self, *, output_dir: Optional[Path] = None, headless: bool = False) -> CodeGenerationPlan:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_5)

        # Inputs (gate enforces scorecard exists + Mode 4 completion)
        sc_path = self.project.get_artifact("BusinessCaseScorecard")
        if not sc_path:
            raise RuntimeError("Required artifact BusinessCaseScorecard not found")
        scorecard = BusinessCaseScorecard.from_file(sc_path)

        tf_path = self.project.get_artifact("ThresholdFramework")
        tf = ThresholdFramework.from_file(tf_path) if tf_path else None

        # Plan + scaffold destination
        out = (output_dir or (self.project.project_path / "PROJECT")).resolve()
        out.mkdir(parents=True, exist_ok=True)

        plan = self._build_plan(scorecard=scorecard, thresholds=tf, output_path=out)

        if (not headless) and self.llm is not None:
            # Optional LLM expansion for human-readability (best-effort).
            try:
                extra = self.llm.complete(
                    "Expand this code generation plan into 6-10 crisp steps (bullets). Keep it practical.\n"
                    f"Current steps: {plan.pipeline_spec.steps}\n",
                    max_tokens=220,
                ).strip()
                if extra:
                    plan.pipeline_spec.steps = plan.pipeline_spec.steps + [s.strip("- ").strip() for s in extra.splitlines() if s.strip()]
            except Exception:
                pass

        self._write_scaffold(out, plan=plan)

        # Save artifact
        mode_dir = self.project.artifact_store / "mode_5"
        mode_dir.mkdir(parents=True, exist_ok=True)
        plan_path = mode_dir / f"CodeGenerationPlan_{plan.artifact_id}.json"
        plan.to_file(plan_path)

        # Fingerprint plan (use Mode 4 artifacts as provenance)
        parent_ids = [scorecard.artifact_id]
        input_paths: list[Path] = [sc_path]
        if tf is not None and tf_path is not None:
            parent_ids.append(tf.artifact_id)
            input_paths.append(tf_path)

        fp = generate_fingerprint(
            artifact_type="CodeGenerationPlan",
            content=plan_path.read_bytes(),
            parent_ids=parent_ids,
            mode="mode_5",
            input_paths=input_paths,
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=plan.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp)
        plan.fingerprint_id = fp.artifact_id
        plan.to_file(plan_path)

        # Mode 5 verdict inherits predecessor stance.
        pred = self.project.get_gate_verdict(Mode.MODE_4) or GateVerdict.GO
        verdict = GateVerdict.GO if pred == GateVerdict.GO else GateVerdict.CONDITIONAL
        self.project.complete_mode(Mode.MODE_5, verdict=verdict, artifact_ids=[plan.artifact_id])
        return plan

    def _build_plan(
        self,
        *,
        scorecard: BusinessCaseScorecard,
        thresholds: Optional[ThresholdFramework],
        output_path: Path,
    ) -> CodeGenerationPlan:
        steps = [
            "Create a clean project package with src/ + tests/ layout",
            "Implement data loading + schema checks",
            "Implement feature prep consistent with Mode 3 FeatureRegistry (raw columns for MVP)",
            "Train a baseline model and persist as a versioned artifact",
            "Add evaluation script + metrics report",
            "Implement predict() API (batch + single-row) with thresholding rules",
            "Add smoke tests + deterministic run config",
        ]
        if thresholds is not None and thresholds.business_rules:
            steps.append("Encode business rules / routing from ThresholdFramework into prediction post-processing")

        config_entries = {
            "schema_version": scorecard.schema_version,
            "recommended_action": scorecard.recommendation,
            "gate_verdict_mode4": str(scorecard.gate_verdict.value),
            "prediction_thresholds": (thresholds.prediction_thresholds if thresholds else {"primary_threshold": 0.5}),
        }

        return CodeGenerationPlan(
            pipeline_spec=PipelineSpec(steps=steps),
            test_spec=TestSpec(tests=["test_smoke_pipeline_runs", "test_predict_returns_probability_and_label"]),
            config_spec=ConfigSpec(entries=config_entries),
            output_path=str(output_path),
        )

    def _write_scaffold(self, out: Path, *, plan: CodeGenerationPlan) -> None:
        """
        Create a minimal runnable skeleton. We keep it dependency-light and safe:
        no network calls, no installs, no secrets.
        """
        (out / "src").mkdir(parents=True, exist_ok=True)
        (out / "tests").mkdir(parents=True, exist_ok=True)
        (out / "config").mkdir(parents=True, exist_ok=True)

        (out / "src" / "__init__.py").write_text("", encoding="utf-8")

        (out / "README.md").write_text(
            "# PROJECT (generated by MERIDIAN Mode 5)\n\n"
            "This folder is a starter scaffold produced by Mode 5.\n\n"
            "## Next\n"
            "- Implement the pipeline in `src/pipeline.py`\n"
            "- Run tests in `tests/`\n",
            encoding="utf-8",
        )

        (out / "config" / "plan.json").write_text(plan.to_json(), encoding="utf-8")

        (out / "src" / "pipeline.py").write_text(
            "from __future__ import annotations\n\n"
            "import json\n"
            "from dataclasses import dataclass\n"
            "from pathlib import Path\n"
            "from typing import Any, Dict, Optional\n\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.linear_model import LogisticRegression\n"
            "from sklearn.metrics import roc_auc_score\n"
            "from sklearn.model_selection import train_test_split\n\n\n"
            "@dataclass\n"
            "class Prediction:\n"
            "    probability: float\n"
            "    label: int\n"
            "    meta: Dict[str, Any]\n\n\n"
            "def train(\n"
            "    *,\n"
            "    data_path: str,\n"
            "    target_col: str = \"target\",\n"
            "    artifacts_dir: str | Path = \"artifacts\",\n"
            "    test_size: float = 0.25,\n"
            "    random_state: int = 42,\n"
            ") -> Dict[str, Any]:\n"
            "    \"\"\"Train a minimal baseline model and persist it for inference.\"\"\"\n"
            "    data_path_p = Path(data_path).expanduser().resolve()\n"
            "    if not data_path_p.exists():\n"
            "        raise FileNotFoundError(f\"data_path not found: {data_path_p}\")\n"
            "    df = pd.read_csv(data_path_p)\n"
            "    if target_col not in df.columns:\n"
            "        raise ValueError(f\"target_col '{target_col}' not in dataset columns\")\n"
            "    y = df[target_col]\n"
            "    X = df.drop(columns=[target_col])\n"
            "    X = _prep_features(X)\n"
            "    stratify = y if _is_binary(y) else None\n"
            "    X_train, X_val, y_train, y_val = train_test_split(\n"
            "        X, y, test_size=test_size, random_state=random_state, stratify=stratify\n"
            "    )\n"
            "    model = LogisticRegression(max_iter=300)\n"
            "    model.fit(X_train, y_train)\n"
            "    auc = None\n"
            "    try:\n"
            "        proba = model.predict_proba(X_val)[:, 1]\n"
            "        auc = float(roc_auc_score(y_val, proba))\n"
            "    except Exception:\n"
            "        pass\n"
            "    art_dir = Path(artifacts_dir)\n"
            "    if not art_dir.is_absolute():\n"
            "        art_dir = (Path(__file__).resolve().parents[1] / art_dir).resolve()\n"
            "    art_dir.mkdir(parents=True, exist_ok=True)\n"
            "    model_path = art_dir / \"model.joblib\"\n"
            "    metrics_path = art_dir / \"metrics.json\"\n"
            "    _save_model_bundle(model_path, model=model, feature_columns=list(X.columns))\n"
            "    metrics = {\n"
            "        \"model_type\": \"LogisticRegression\",\n"
            "        \"n_rows\": int(df.shape[0]),\n"
            "        \"n_features\": int(X.shape[1]),\n"
            "        \"target_col\": target_col,\n"
            "        \"val_auc\": auc,\n"
            "    }\n"
            "    metrics_path.write_text(json.dumps(metrics, indent=2), encoding=\"utf-8\")\n"
            "    return {\n"
            "        \"status\": \"ok\",\n"
            "        \"data_path\": str(data_path_p),\n"
            "        \"artifacts_dir\": str(art_dir),\n"
            "        \"model_path\": str(model_path),\n"
            "        \"metrics_path\": str(metrics_path),\n"
            "        \"metrics\": metrics,\n"
            "    }\n\n\n"
            "def predict_row(\n"
            "    row: Dict[str, Any],\n"
            "    *,\n"
            "    threshold: float = 0.5,\n"
            "    model_path: Optional[str | Path] = None,\n"
            ") -> Prediction:\n"
            "    \"\"\"Predict a single row using the persisted model bundle.\"\"\"\n"
            "    bundle_path = _default_model_path() if model_path is None else Path(model_path).expanduser().resolve()\n"
            "    if not bundle_path.exists():\n"
            "        p = 0.5\n"
            "        return Prediction(\n"
            "            probability=p,\n"
            "            label=int(p >= float(threshold)),\n"
            "            meta={\"threshold\": float(threshold), \"model_path\": str(bundle_path), \"untrained\": True},\n"
            "        )\n"
            "    model, feature_columns = _load_model_bundle(bundle_path)\n"
            "    xdf = pd.DataFrame([{c: float(row.get(c, 0.0) or 0.0) for c in feature_columns}], columns=feature_columns)\n"
            "    p = float(model.predict_proba(xdf)[0, 1])\n"
            "    label = int(p >= float(threshold))\n"
            "    return Prediction(\n"
            "        probability=p,\n"
            "        label=label,\n"
            "        meta={\"threshold\": float(threshold), \"model_path\": str(bundle_path), \"features_used\": feature_columns},\n"
            "    )\n\n\n"
            "def health() -> Dict[str, Any]:\n"
            "    return {\"status\": \"ok\", \"model_present\": _default_model_path().exists()}\n\n\n"
            "def _project_root() -> Path:\n"
            "    return Path(__file__).resolve().parents[1]\n\n\n"
            "def _default_model_path() -> Path:\n"
            "    return (_project_root() / \"artifacts\" / \"model.joblib\").resolve()\n\n\n"
            "def _prep_features(X: pd.DataFrame) -> pd.DataFrame:\n"
            "    X = X.copy()\n"
            "    for c in list(X.columns):\n"
            "        if not pd.api.types.is_numeric_dtype(X[c]):\n"
            "            X = X.drop(columns=[c])\n"
            "    return X.fillna(0)\n\n\n"
            "def _is_binary(y: pd.Series) -> bool:\n"
            "    vals = y.dropna().unique()\n"
            "    return bool(len(vals) <= 2)\n\n\n"
            "def _save_model_bundle(path: Path, *, model: Any, feature_columns: list[str]) -> None:\n"
            "    import joblib\n"
            "    path.parent.mkdir(parents=True, exist_ok=True)\n"
            "    joblib.dump({\"model\": model, \"feature_columns\": feature_columns}, path)\n\n\n"
            "def _load_model_bundle(path: Path) -> tuple[Any, list[str]]:\n"
            "    import joblib\n"
            "    if not path.exists():\n"
            "        raise FileNotFoundError(f\"model bundle not found: {path}\")\n"
            "    obj = joblib.load(path)\n"
            "    return obj[\"model\"], list(obj[\"feature_columns\"])\n",
            encoding="utf-8",
        )

        (out / "tests" / "test_smoke.py").write_text(
            "from __future__ import annotations\n\n"
            "import importlib.util\n"
            "from pathlib import Path\n\n\n"
            "def _load_pipeline_module():\n"
            "    here = Path(__file__).resolve()\n"
            "    project_root = here.parents[1]\n"
            "    pipeline_path = project_root / 'src' / 'pipeline.py'\n"
            "    spec = importlib.util.spec_from_file_location('pipeline', pipeline_path)\n"
            "    assert spec and spec.loader\n"
            "    mod = importlib.util.module_from_spec(spec)\n"
            "    # Python 3.13 dataclasses + string annotations expect the module\n"
            "    # to be present in sys.modules during exec_module().\n"
            "    import sys\n"
            "    sys.modules[spec.name] = mod\n"
            "    spec.loader.exec_module(mod)\n"
            "    return mod\n\n\n"
            "def test_predict_row_contract():\n"
            "    pipeline = _load_pipeline_module()\n"
            "    pred = pipeline.predict_row({\"x1\": 0.1, \"x2\": -0.2})\n"
            "    assert 0.0 <= pred.probability <= 1.0\n"
            "    assert pred.label in (0, 1)\n",
            encoding="utf-8",
        )

        (out / "demo.py").write_text(
            "from __future__ import annotations\n\n"
            "import argparse\n"
            "import json\n\n"
            "from src.pipeline import predict_row, train\n\n\n"
            "def main() -> None:\n"
            "    ap = argparse.ArgumentParser(description='Single-command demo: train + predict')\n"
            "    ap.add_argument('--data', required=True, help='Path to CSV dataset')\n"
            "    ap.add_argument('--target', default='target', help='Target column name')\n"
            "    ap.add_argument('--row', required=True, help='JSON dict for a single row')\n"
            "    args = ap.parse_args()\n"
            "    result = train(data_path=args.data, target_col=args.target)\n"
            "    print('TRAIN:', json.dumps(result['metrics'], indent=2))\n"
            "    row = json.loads(args.row)\n"
            "    pred = predict_row(row)\n"
            "    print('PREDICT:', json.dumps({'probability': pred.probability, 'label': pred.label, 'meta': pred.meta}, indent=2))\n\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n",
            encoding="utf-8",
        )

