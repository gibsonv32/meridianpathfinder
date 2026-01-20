from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Optional, Tuple

from meridian.artifacts.schemas import (
    BusinessCaseScorecard,
    BusinessRule,
    CostModel,
    FeasibilityReport,
    ModelRecommendations,
    Option,
    Scenarios,
    ThresholdFramework,
    ValueModel,
)
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode4Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_4

    def run(self, *, headless: bool = False) -> Tuple[BusinessCaseScorecard, ThresholdFramework]:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_4)

        # Inputs (enforced by gate, but read for content)
        mr_path = self.project.get_artifact("ModelRecommendations")
        if not mr_path:
            raise RuntimeError("Required artifact ModelRecommendations not found")
        recs = ModelRecommendations.from_file(mr_path)

        feas_path = self.project.get_artifact("FeasibilityReport")
        feas = FeasibilityReport.from_file(feas_path) if feas_path else None
        lift = float(feas.signal_validation.lift) if feas else 0.0

        # Threshold framework (simple defaults for MVP)
        tf = ThresholdFramework(
            prediction_thresholds={"primary_threshold": 0.5},
            operational_thresholds={"latency_p99_ms": 100.0, "error_rate_pct": 1.0},
            governance_thresholds={"feature_psi_warn": 0.10, "feature_psi_alert": 0.20},
            business_rules=[
                BusinessRule(rule_id="BR001", condition="score >= 0.7", action="high_touch_intervention"),
                BusinessRule(rule_id="BR002", condition="0.4 <= score < 0.7", action="automated_campaign"),
            ],
        )

        # Business case scorecard (placeholder economics, baseline-anchored narrative)
        options = [
            Option(name="BaselineOnly", description="Ship nothing; use baseline decisions."),
            Option(name=recs.recommended, description="Ship recommended model + rules."),
        ]
        scenarios = Scenarios(
            downside={"lift": max(lift * 0.5, 0.0)},
            base={"lift": lift},
            upside={"lift": lift * 1.25},
        )
        recommendation = "PROCEED" if lift > 0.1 and (feas is None or feas.gate_verdict != GateVerdict.NO_GO) else "DO_NOT_PROCEED"
        verdict = GateVerdict.GO if recommendation == "PROCEED" else GateVerdict.NO_GO

        scorecard = BusinessCaseScorecard(
            options=options,
            cost_model=CostModel(notes="MVP placeholder cost model; extend with Mode 4 finance bundle later."),
            value_model=ValueModel(notes="Baseline-anchored value uses Mode 2 lift as proxy."),
            scenarios=scenarios,
            recommendation=recommendation,
            gate_verdict=verdict,
        )

        # Optional LLM: refine recommendation text
        if (not headless) and self.llm is not None:
            try:
                scorecard.recommendation = (
                    self.llm.complete(
                        "Rewrite this business recommendation as a crisp decision sentence.\n"
                        f"Current: {scorecard.recommendation}\n"
                        f"Lift: {lift:.3f}\n"
                        f"Recommended model: {recs.recommended}\n",
                        max_tokens=120,
                    ).strip()
                    or scorecard.recommendation
                )
            except Exception:
                pass

        # Save artifacts
        mode_dir = self.project.artifact_store / "mode_4"
        mode_dir.mkdir(parents=True, exist_ok=True)
        sc_path = mode_dir / f"BusinessCaseScorecard_{scorecard.artifact_id}.json"
        tf_path = mode_dir / f"ThresholdFramework_{tf.artifact_id}.json"
        scorecard.to_file(sc_path)
        tf.to_file(tf_path)

        # Fingerprint both
        sc_fp = generate_fingerprint(
            artifact_type="BusinessCaseScorecard",
            content=sc_path.read_bytes(),
            parent_ids=[recs.artifact_id, (feas.artifact_id if feas else "")],
            mode="mode_4",
            input_paths=[mr_path, *( [feas_path] if feas_path else [] )],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=scorecard.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(sc_fp)
        scorecard.fingerprint_id = sc_fp.artifact_id
        scorecard.to_file(sc_path)

        tf_fp = generate_fingerprint(
            artifact_type="ThresholdFramework",
            content=tf_path.read_bytes(),
            parent_ids=[recs.artifact_id],
            mode="mode_4",
            input_paths=[mr_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=tf.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(tf_fp)
        tf.fingerprint_id = tf_fp.artifact_id
        tf.to_file(tf_path)

        self.project.complete_mode(Mode.MODE_4, verdict=verdict, artifact_ids=[scorecard.artifact_id, tf.artifact_id])
        return scorecard, tf

