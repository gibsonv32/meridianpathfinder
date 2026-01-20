from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional

import numpy as np
import pandas as pd

from meridian.artifacts.schemas import (
    DatasetFingerprint,
    DistributionStats,
    Mode0GatePacket,
    QualityAssessment,
    Risk,
)
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode0Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_0

    def run(self, data_path: Path, headless: bool = False) -> Mode0GatePacket:
        t0 = perf_counter()
        data_path = data_path.expanduser().resolve()
        df = pd.read_csv(data_path)

        fp = self._dataset_fingerprint(df=df, data_path=data_path)
        qa = self._quality_assessment(df)
        dist = self._distribution_summary(df)
        risks = self._identify_risks(df, qa, dist)

        packet = Mode0GatePacket(
            dataset_fingerprint=fp,
            quality_assessment=qa,
            distribution_summary=dist,
            risks=risks,
        )

        # Ensure project directories exist
        mode_dir = self.project.artifact_store / "mode_0"
        mode_dir.mkdir(parents=True, exist_ok=True)

        # Gate + state update
        self.project.start_mode(Mode.MODE_0)

        # (Optional) LLM narrative hook — stored as a risk note for now.
        if (not headless) and self.llm is not None:
            try:
                narrative = self.llm.complete(
                    "Summarize this dataset EDA in 3 bullet points, then list top 3 risks.\n\n"
                    f"Rows: {fp.n_rows}, Cols: {fp.n_cols}\n"
                    f"Missing pct (top 5): {dict(sorted(qa.missing_pct.items(), key=lambda x: -x[1])[:5])}\n"
                    f"Duplicate rows: {qa.duplicate_rows}\n",
                    max_tokens=300,
                )
                if narrative:
                    packet.risks.append(
                        Risk(severity="LOW", description="LLM narrative summary attached.", mitigation=narrative)
                    )
            except Exception:
                # Never fail Mode 0 because the LLM is unavailable.
                pass

        # Save artifact
        artifact_path = mode_dir / f"Mode0GatePacket_{packet.artifact_id}.json"
        packet.to_file(artifact_path)

        # Fingerprint + persist (fingerprint_id refers to fingerprint record id)
        content = artifact_path.read_bytes()
        fp_rec = generate_fingerprint(
            artifact_type="Mode0GatePacket",
            content=content,
            parent_ids=[],
            mode="mode_0",
            input_paths=[data_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=packet.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp_rec)

        # Update artifact with fingerprint_id and re-save
        packet.fingerprint_id = fp_rec.artifact_id
        packet.to_file(artifact_path)

        verdict = GateVerdict.GO if not any(r.severity == "HIGH" for r in risks) else GateVerdict.CONDITIONAL
        self.project.complete_mode(Mode.MODE_0, verdict=verdict, artifact_ids=[packet.artifact_id])

        return packet

    def _dataset_fingerprint(self, *, df: pd.DataFrame, data_path: Path) -> DatasetFingerprint:
        mem_mb = float(df.memory_usage(deep=True).sum()) / (1024 * 1024)
        return DatasetFingerprint(
            n_rows=int(df.shape[0]),
            n_cols=int(df.shape[1]),
            column_types={c: str(df[c].dtype) for c in df.columns},
            memory_usage_mb=mem_mb,
            file_hash=_sha256_file(data_path),
        )

    def _quality_assessment(self, df: pd.DataFrame) -> QualityAssessment:
        missing_pct = {c: float(df[c].isna().mean()) for c in df.columns}
        duplicate_rows = int(df.duplicated().sum())

        constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
        high_card_cols = []
        for c in df.columns:
            if df[c].dtype == "object" or str(df[c].dtype).startswith("category"):
                if df[c].nunique(dropna=True) > 100:
                    high_card_cols.append(c)

        outlier_cols = []
        for c in df.select_dtypes(include=[np.number]).columns:
            series = df[c].dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            frac_out = float(((series < lower) | (series > upper)).mean())
            if frac_out > 0.01:
                outlier_cols.append(c)

        return QualityAssessment(
            missing_pct=missing_pct,
            duplicate_rows=duplicate_rows,
            constant_columns=constant_cols,
            high_cardinality_columns=high_card_cols,
            outlier_columns=outlier_cols,
        )

    def _distribution_summary(self, df: pd.DataFrame) -> dict[str, DistributionStats]:
        out: dict[str, DistributionStats] = {}
        for c in df.columns:
            col = df[c]
            if pd.api.types.is_numeric_dtype(col):
                s = col.dropna()
                stats = {
                    "count": int(s.shape[0]),
                    "mean": float(s.mean()) if not s.empty else None,
                    "std": float(s.std(ddof=1)) if s.shape[0] > 1 else None,
                    "min": float(s.min()) if not s.empty else None,
                    "q25": float(s.quantile(0.25)) if not s.empty else None,
                    "median": float(s.quantile(0.50)) if not s.empty else None,
                    "q75": float(s.quantile(0.75)) if not s.empty else None,
                    "max": float(s.max()) if not s.empty else None,
                    "skew": float(s.skew()) if s.shape[0] > 2 else None,
                    "kurtosis": float(s.kurtosis()) if s.shape[0] > 3 else None,
                }
            else:
                s = col.astype("string")
                vc = s.value_counts(dropna=True).head(5)
                stats = {
                    "unique_count": int(s.nunique(dropna=True)),
                    "top_values": {str(k): int(v) for k, v in vc.items()},
                }
            out[c] = DistributionStats(stats=stats)
        return out

    def _identify_risks(
        self, df: pd.DataFrame, qa: QualityAssessment, dist: dict[str, DistributionStats]
    ) -> list[Risk]:
        risks: list[Risk] = []
        for col, pct in qa.missing_pct.items():
            if pct > 0.30:
                risks.append(
                    Risk(
                        severity="HIGH",
                        description=f"Column '{col}' has {pct:.0%} missing values.",
                        mitigation="Consider dropping, imputing, or sourcing upstream fixes.",
                    )
                )
        for col in qa.high_cardinality_columns:
            risks.append(
                Risk(
                    severity="MEDIUM",
                    description=f"Column '{col}' has high cardinality (>100 unique).",
                    mitigation="Consider frequency/target encoding or hashing; validate leakage risk.",
                )
            )
        # Skew risk (low severity)
        for col, ds in dist.items():
            skew = ds.stats.get("skew")
            if isinstance(skew, (int, float)) and abs(float(skew)) > 2.0:
                risks.append(
                    Risk(
                        severity="LOW",
                        description=f"Column '{col}' is severely skewed (skew={skew:.2f}).",
                        mitigation="Consider transforms (log/Box-Cox) or robust models.",
                    )
                )
        if qa.duplicate_rows > 0:
            risks.append(
                Risk(
                    severity="MEDIUM",
                    description=f"Dataset contains {qa.duplicate_rows} duplicate rows.",
                    mitigation="Deduplicate by stable keys or investigate upstream joins.",
                )
            )
        return risks


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

