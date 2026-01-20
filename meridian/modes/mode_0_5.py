from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import List, Optional, Tuple

from meridian.artifacts.schemas import Opportunity, OpportunityBacklog, OpportunityBrief
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode0_5Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_0_5

    def run(
        self,
        *,
        problem_statement: str,
        target_entity: str = "customer",
        candidates: Optional[List[str]] = None,
        select_id: Optional[str] = None,
        stakeholder_brief: str = "",
        data_requirements: Optional[List[str]] = None,
        headless: bool = False,
    ) -> Tuple[OpportunityBacklog, OpportunityBrief]:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_0_5)

        backlog = self._build_backlog(
            problem_statement=problem_statement,
            target_entity=target_entity,
            candidates=candidates or [],
        )
        chosen = self._select_opportunity(backlog, select_id=select_id)
        brief = OpportunityBrief(
            selected_opportunity_id=chosen.id,
            problem_statement=problem_statement,
            stakeholder_brief=stakeholder_brief or f"Primary stakeholders: owners of {target_entity} outcomes; consumers of decisions.",
            data_requirements=list(data_requirements or []),
        )

        # Optional LLM: refine descriptions (best-effort)
        if (not headless) and self.llm is not None:
            try:
                backlog.metadata["llm_note"] = self.llm.complete(
                    "Given this problem statement, rewrite each opportunity description in 1 sentence.\n"
                    f"Problem: {problem_statement}\n"
                    f"Opportunities: {[o.description for o in backlog.opportunities]}\n",
                    max_tokens=200,
                ).strip()
            except Exception:
                pass

        mode_dir = self.project.artifact_store / "mode_0_5"
        mode_dir.mkdir(parents=True, exist_ok=True)
        backlog_path = mode_dir / f"OpportunityBacklog_{backlog.artifact_id}.json"
        brief_path = mode_dir / f"OpportunityBrief_{brief.artifact_id}.json"
        backlog.to_file(backlog_path)
        brief.to_file(brief_path)

        # Fingerprint backlog
        bl_fp = generate_fingerprint(
            artifact_type="OpportunityBacklog",
            content=backlog_path.read_bytes(),
            parent_ids=[],
            mode="mode_0_5",
            input_paths=[],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=backlog.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(bl_fp)
        backlog.fingerprint_id = bl_fp.artifact_id
        backlog.to_file(backlog_path)

        # Fingerprint brief (tie it to the backlog as input + parent)
        br_fp = generate_fingerprint(
            artifact_type="OpportunityBrief",
            content=brief_path.read_bytes(),
            parent_ids=[backlog.artifact_id],
            mode="mode_0_5",
            input_paths=[backlog_path],
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=brief.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(br_fp)
        brief.fingerprint_id = br_fp.artifact_id
        brief.to_file(brief_path)

        self.project.complete_mode(
            Mode.MODE_0_5, verdict=GateVerdict.GO, artifact_ids=[backlog.artifact_id, brief.artifact_id]
        )
        return backlog, brief

    def _build_backlog(self, *, problem_statement: str, target_entity: str, candidates: List[str]) -> OpportunityBacklog:
        if candidates:
            ops: list[Opportunity] = []
            for i, raw in enumerate(candidates, start=1):
                # Format: "type:description" (type optional)
                otype = "prediction"
                desc = raw.strip()
                if ":" in raw:
                    left, right = raw.split(":", 1)
                    if left.strip() in {"prediction", "detection", "segmentation", "optimization", "explanation"}:
                        otype = left.strip()
                        desc = right.strip()
                ops.append(
                    Opportunity(
                        id=f"opp_{i}",
                        type=otype,  # type: ignore[arg-type]
                        description=desc,
                        target_entity=target_entity,
                        feasibility_score=max(10, 80 - (i - 1) * 10),
                        business_value=("HIGH" if i == 1 else ("MEDIUM" if i == 2 else "LOW")),  # type: ignore[arg-type]
                    )
                )
            return OpportunityBacklog(opportunities=ops, metadata={"source": "cli:candidates"})

        # Default backlog (MVP heuristics)
        ops = [
            Opportunity(
                id="opp_1",
                type="prediction",
                description=f"Predict next best action to improve {target_entity} outcome for: {problem_statement}",
                target_entity=target_entity,
                feasibility_score=70,
                business_value="HIGH",
            ),
            Opportunity(
                id="opp_2",
                type="detection",
                description=f"Detect risk conditions early for {target_entity}: {problem_statement}",
                target_entity=target_entity,
                feasibility_score=60,
                business_value="MEDIUM",
            ),
            Opportunity(
                id="opp_3",
                type="segmentation",
                description=f"Segment {target_entity} cohorts to target interventions for: {problem_statement}",
                target_entity=target_entity,
                feasibility_score=50,
                business_value="MEDIUM",
            ),
        ]
        return OpportunityBacklog(opportunities=ops, metadata={"source": "mvp-defaults"})

    def _select_opportunity(self, backlog: OpportunityBacklog, *, select_id: Optional[str]) -> Opportunity:
        if select_id:
            for o in backlog.opportunities:
                if o.id == select_id:
                    return o
        return sorted(backlog.opportunities, key=lambda o: o.feasibility_score, reverse=True)[0]

