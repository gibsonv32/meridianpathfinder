from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional

from meridian.artifacts.schemas import (
    APIEndpoint,
    CodeGenerationPlan,
    DeliveryManifest,
    InterpretationPackage,
    OutputSpec,
)
from meridian.core.fingerprint import generate_fingerprint
from meridian.core.gates import GateVerdict
from meridian.core.modes import Mode
from meridian.core.state import MeridianProject
from meridian.llm.providers import LLMProvider


@dataclass
class Mode7Executor:
    project: MeridianProject
    llm: Optional[LLMProvider] = None

    mode: Mode = Mode.MODE_7

    def run(self, *, headless: bool = False) -> DeliveryManifest:
        t0 = perf_counter()
        self.project.start_mode(Mode.MODE_7)

        ip_path = self.project.get_artifact("InterpretationPackage")
        if not ip_path:
            raise RuntimeError("Required artifact InterpretationPackage not found")
        ip = InterpretationPackage.from_file(ip_path)

        plan_path = self.project.get_artifact("CodeGenerationPlan")
        plan = CodeGenerationPlan.from_file(plan_path) if plan_path else None

        deliver_dir = self.project.project_path / ".meridian" / "deliverables"
        deliver_dir.mkdir(parents=True, exist_ok=True)
        exec_md = deliver_dir / "ExecutiveSummary.md"
        tech_md = deliver_dir / "TechnicalReport.md"

        exec_md.write_text(
            "# Executive Summary\n\n"
            f"{ip.audience_versions.get('executive', '').strip()}\n\n"
            f"- InterpretationPackage: `{ip.artifact_id}`\n",
            encoding="utf-8",
        )
        tech_md.write_text(
            "# Technical Report\n\n"
            f"{ip.audience_versions.get('technical', '').strip()}\n\n"
            f"- InterpretationPackage: `{ip.artifact_id}`\n",
            encoding="utf-8",
        )

        outputs = [
            OutputSpec(name="ExecutiveSummary.md", path=str(exec_md)),
            OutputSpec(name="TechnicalReport.md", path=str(tech_md)),
        ]
        if plan is not None:
            outputs.append(OutputSpec(name="PROJECT", path=str(Path(plan.output_path))))

        api_endpoints = [
            APIEndpoint(method="GET", path="/health"),
            APIEndpoint(method="POST", path="/predict"),
            APIEndpoint(method="GET", path="/metrics"),
        ]
        manifest = DeliveryManifest(
            outputs=outputs,
            api_endpoints=api_endpoints,
            distribution_channels=["api", "internal-dashboard", "slack"],
        )

        # Optional LLM polish: rewrite executive summary file (best-effort)
        if (not headless) and self.llm is not None:
            try:
                polished = self.llm.complete(
                    "Rewrite this as a crisp executive summary (max 120 words).\n"
                    f"{exec_md.read_text(encoding='utf-8')}\n",
                    max_tokens=200,
                ).strip()
                if polished:
                    exec_md.write_text(polished + "\n", encoding="utf-8")
            except Exception:
                pass

        mode_dir = self.project.artifact_store / "mode_7"
        mode_dir.mkdir(parents=True, exist_ok=True)
        mf_path = mode_dir / f"DeliveryManifest_{manifest.artifact_id}.json"
        manifest.to_file(mf_path)

        # Fingerprint: include key deliverables as inputs (files only).
        input_paths: list[Path] = [ip_path, exec_md, tech_md]
        if plan_path and plan_path.exists():
            input_paths.append(plan_path)

        fp = generate_fingerprint(
            artifact_type="DeliveryManifest",
            content=mf_path.read_bytes(),
            parent_ids=[ip.artifact_id],
            mode="mode_7",
            input_paths=input_paths,
            config_path=self.project.project_path / "meridian.yaml",
            artifact_id=manifest.artifact_id,
            execution_duration_ms=int((perf_counter() - t0) * 1000),
            created_by=f"meridian-cli:{self.project.meridian_version}",
            meridian_version=self.project.meridian_version,
        )
        self.project.fingerprint_store.save(fp)
        manifest.fingerprint_id = fp.artifact_id
        manifest.to_file(mf_path)

        pred = self.project.get_gate_verdict(Mode.MODE_6_5) or GateVerdict.GO
        verdict = GateVerdict.GO if pred == GateVerdict.GO else GateVerdict.CONDITIONAL
        self.project.complete_mode(Mode.MODE_7, verdict=verdict, artifact_ids=[manifest.artifact_id])
        return manifest

