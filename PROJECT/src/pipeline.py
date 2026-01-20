from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split


@dataclass
class Prediction:
    probability: float
    label: int
    meta: Dict[str, Any]


def train(
    *,
    data_path: str,
    target_col: str = "target",
    artifacts_dir: str | Path = "artifacts",
    test_size: float = 0.25,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Train a minimal baseline model and persist it for inference.

    Outputs:
    - <artifacts_dir>/model.joblib   (sklearn model + feature list)
    - <artifacts_dir>/metrics.json  (basic evaluation)
    """
    data_path_p = Path(data_path).expanduser().resolve()
    if not data_path_p.exists():
        raise FileNotFoundError(f"data_path not found: {data_path_p}")

    df = pd.read_csv(data_path_p)
    if target_col not in df.columns:
        raise ValueError(f"target_col '{target_col}' not in dataset columns")

    y = df[target_col]
    X = df.drop(columns=[target_col])
    X = _prep_features(X)

    # split
    stratify = y if _is_binary(y) else None
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    model = LogisticRegression(max_iter=300)
    model.fit(X_train, y_train)

    # eval
    auc = None
    try:
        proba = model.predict_proba(X_val)[:, 1]
        auc = float(roc_auc_score(y_val, proba))
    except Exception:
        pass

    art_dir = Path(artifacts_dir)
    if not art_dir.is_absolute():
        art_dir = (Path(__file__).resolve().parents[1] / art_dir).resolve()
    art_dir.mkdir(parents=True, exist_ok=True)

    model_path = art_dir / "model.joblib"
    metrics_path = art_dir / "metrics.json"

    _save_model_bundle(model_path, model=model, feature_columns=list(X.columns))
    metrics = {
        "model_type": "LogisticRegression",
        "n_rows": int(df.shape[0]),
        "n_features": int(X.shape[1]),
        "target_col": target_col,
        "val_auc": auc,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "data_path": str(data_path_p),
        "artifacts_dir": str(art_dir),
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "metrics": metrics,
    }


def predict_row(
    row: Dict[str, Any],
    *,
    threshold: float = 0.5,
    model_path: Optional[str | Path] = None,
) -> Prediction:
    """
    Predict a single row using the persisted model bundle.
    If model_path is not provided, uses <PROJECT>/artifacts/model.joblib.
    """
    bundle_path = _default_model_path() if model_path is None else Path(model_path).expanduser().resolve()
    if not bundle_path.exists():
        # Untrained/default behavior: keep contract stable for smoke runs.
        p = 0.5
        return Prediction(
            probability=p,
            label=int(p >= float(threshold)),
            meta={"threshold": float(threshold), "model_path": str(bundle_path), "untrained": True},
        )

    model, feature_columns = _load_model_bundle(bundle_path)

    # Use a DataFrame to preserve feature names and avoid sklearn warnings.
    xdf = pd.DataFrame([{c: float(row.get(c, 0.0) or 0.0) for c in feature_columns}], columns=feature_columns)
    p = float(model.predict_proba(xdf)[0, 1])
    label = int(p >= float(threshold))
    return Prediction(
        probability=p,
        label=label,
        meta={"threshold": float(threshold), "model_path": str(bundle_path), "features_used": feature_columns},
    )


def health() -> Dict[str, Any]:
    """Tiny service-compatible health payload for the DeliveryManifest /health endpoint."""
    return {"status": "ok", "model_present": _default_model_path().exists()}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_model_path() -> Path:
    return (_project_root() / "artifacts" / "model.joblib").resolve()


def _prep_features(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for c in list(X.columns):
        if not pd.api.types.is_numeric_dtype(X[c]):
            X = X.drop(columns=[c])
    return X.fillna(0)


def _is_binary(y: pd.Series) -> bool:
    vals = y.dropna().unique()
    return bool(len(vals) <= 2)


def _save_model_bundle(path: Path, *, model: Any, feature_columns: list[str]) -> None:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": feature_columns}, path)


def _load_model_bundle(path: Path) -> tuple[Any, list[str]]:
    import joblib

    if not path.exists():
        raise FileNotFoundError(f"model bundle not found: {path}")
    obj = joblib.load(path)
    return obj["model"], list(obj["feature_columns"])
