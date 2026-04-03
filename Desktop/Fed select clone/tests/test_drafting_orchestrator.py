"""
Tests for Phase 26: Drafting Orchestrator — Agent-Callable Document Pipeline

Coverage:
- VersionStore (save, retrieve, history, rollback, diff, version count)
- EngineInput/EngineOutput contracts
- Individual engine adapters (PWS, IGCE, Section L, Section M, QASP)
- Pipeline execution (full, partial, custom stage list)
- Inter-engine data flow (requirements → PWS → QASP)
- UCF assembly (section mapping, ordering)
- Compliance integration (post-generation validation)
- PipelineResult serialization
- Edge cases (empty requirements, no stages, unknown stage)
- Canonical $20M TSA IT services scenario
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.drafting_orchestrator import (
    DraftingOrchestrator,
    VersionStore,
    VersionRecord,
    PipelineStage,
    PipelineContext,
    PipelineResult,
    EngineInput,
    EngineOutput,
    ComplianceResult,
    UCFSection,
    UCFMapping,
    assemble_ucf,
    run_pws,
    run_igce,
    run_section_l,
    run_section_m,
    run_qasp,
    run_requirements,
    run_compliance,
    DEFAULT_PIPELINE,
    COMPLIANCE_STAGES,
    UCF_STAGE_MAP,
)


# ─── Canonical Fixture ───────────────────────────────────────────────────────

def _canonical_params():
    """$20M TSA IT services — canonical test fixture."""
    return {
        "value": 20_000_000,
        "title": "TSA Cybersecurity Operations Support",
        "naics": "541512",
        "psc": "D302",
        "services": True,
        "it_related": True,
        "sole_source": False,
        "commercial_item": False,
        "competition_type": "tradeoff",
        "sub_agency": "TSA",
        "agency": "DHS",
    }


def _canonical_requirements():
    """Sample requirements from elicitation."""
    return [
        {
            "requirement_id": "REQ-001",
            "category": "TECHNICAL",
            "title": "24/7 SOC Monitoring",
            "description": "The contractor shall provide continuous security monitoring.",
            "far_reference": "FAR 37.602",
        },
        {
            "requirement_id": "REQ-002",
            "category": "REPORTING",
            "title": "Monthly Status Reports",
            "description": "Submit monthly status reports within 5 business days.",
            "far_reference": "FAR 37.602",
        },
    ]


def _canonical_eval_factors():
    return [
        {"factor_id": "F-01", "name": "Technical Approach", "far_authority": "FAR 15.304(c)(1)", "description": "Technical evaluation"},
        {"factor_id": "F-02", "name": "Past Performance", "far_authority": "FAR 15.304(c)(3)", "description": "Past performance evaluation"},
    ]


# ─── Version Store Tests ─────────────────────────────────────────────────────

class TestVersionStore:
    def test_save_and_retrieve(self):
        store = VersionStore()
        sections = [{"section_id": "3.1", "content": "Test", "heading": "Test"}]
        record = store.save("pkg-001", PipelineStage.PWS, sections)
        assert record.version == 1
        assert record.stage == PipelineStage.PWS
        assert record.sections == sections
        assert record.timestamp

    def test_get_latest(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v1"}])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v2"}])
        latest = store.get_latest("pkg-001", PipelineStage.PWS)
        assert latest.version == 2
        assert latest.sections[0]["content"] == "v2"

    def test_get_specific_version(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v1"}])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v2"}])
        v1 = store.get_version("pkg-001", PipelineStage.PWS, 1)
        assert v1.version == 1
        assert v1.sections[0]["content"] == "v1"

    def test_get_history(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v1"}])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v2"}])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v3"}])
        history = store.get_history("pkg-001", PipelineStage.PWS)
        assert len(history) == 3
        assert [h.version for h in history] == [1, 2, 3]

    def test_rollback(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v1"}])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v2"}])
        rolled = store.rollback("pkg-001", PipelineStage.PWS, 1)
        assert rolled.version == 3  # rollback creates a new version
        assert rolled.sections[0]["content"] == "v1"
        assert rolled.metadata["rollback_to"] == 1

    def test_rollback_nonexistent_version(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "v1"}])
        result = store.rollback("pkg-001", PipelineStage.PWS, 99)
        assert result is None

    def test_diff_between_versions(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "Original text"}])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "Modified text"}])
        diffs = store.diff("pkg-001", PipelineStage.PWS, 1, 2)
        assert len(diffs) == 1
        assert diffs[0]["change_type"] == "modified"
        assert len(diffs[0]["diff_lines"]) > 0

    def test_diff_added_section(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "Original"}])
        store.save("pkg-001", PipelineStage.PWS, [
            {"section_id": "3.1", "content": "Original"},
            {"section_id": "3.2", "content": "New section"},
        ])
        diffs = store.diff("pkg-001", PipelineStage.PWS, 1, 2)
        added = [d for d in diffs if d["change_type"] == "added"]
        assert len(added) == 1
        assert added[0]["section_id"] == "3.2"

    def test_diff_deleted_section(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [
            {"section_id": "3.1", "content": "Keep"},
            {"section_id": "3.2", "content": "Remove"},
        ])
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "Keep"}])
        diffs = store.diff("pkg-001", PipelineStage.PWS, 1, 2)
        deleted = [d for d in diffs if d["change_type"] == "deleted"]
        assert len(deleted) == 1

    def test_version_count(self):
        store = VersionStore()
        assert store.version_count("pkg-001", PipelineStage.PWS) == 0
        store.save("pkg-001", PipelineStage.PWS, [])
        store.save("pkg-001", PipelineStage.PWS, [])
        assert store.version_count("pkg-001", PipelineStage.PWS) == 2

    def test_separate_packages(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "A"}])
        store.save("pkg-002", PipelineStage.PWS, [{"section_id": "3.1", "content": "B"}])
        assert store.get_latest("pkg-001", PipelineStage.PWS).sections[0]["content"] == "A"
        assert store.get_latest("pkg-002", PipelineStage.PWS).sections[0]["content"] == "B"

    def test_separate_stages(self):
        store = VersionStore()
        store.save("pkg-001", PipelineStage.PWS, [{"section_id": "3.1", "content": "PWS"}])
        store.save("pkg-001", PipelineStage.IGCE, [{"section_id": "IGCE.1", "content": "IGCE"}])
        assert store.version_count("pkg-001", PipelineStage.PWS) == 1
        assert store.version_count("pkg-001", PipelineStage.IGCE) == 1

    def test_get_latest_empty(self):
        store = VersionStore()
        assert store.get_latest("pkg-001", PipelineStage.PWS) is None

    def test_metadata_preserved(self):
        store = VersionStore()
        record = store.save("pkg-001", PipelineStage.PWS, [], metadata={"author": "CO"})
        assert record.metadata["author"] == "CO"


# ─── Engine Adapter Tests ────────────────────────────────────────────────────

class TestEngineAdapters:
    def test_run_pws(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_pws(ei)
        assert output.stage == PipelineStage.PWS
        assert len(output.sections) > 0
        assert output.confidence > 0

    def test_run_igce(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_igce(ei)
        assert output.stage == PipelineStage.IGCE
        assert len(output.sections) >= 3  # methodology, labor, comparables + cost data at $20M

    def test_run_section_l(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_section_l(ei)
        assert output.stage == PipelineStage.SECTION_L
        assert len(output.sections) >= 6
        ids = [s["section_id"] for s in output.sections]
        assert "L.1" in ids

    def test_run_section_m(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_section_m(ei)
        assert output.stage == PipelineStage.SECTION_M
        assert len(output.sections) >= 4

    def test_run_qasp_with_pws(self):
        ei = EngineInput(
            package_id="test",
            acquisition_params=_canonical_params(),
            pws_sections=[
                {"section_id": "3.1", "heading": "Monitoring", "content": "24/7 monitoring with 99.5% uptime", "authority": "FAR 37.602"},
            ],
        )
        output = run_qasp(ei)
        assert output.stage == PipelineStage.QASP
        assert any("QASP" in s["section_id"] for s in output.sections)

    def test_run_requirements_passthrough(self):
        ei = EngineInput(
            package_id="test",
            acquisition_params=_canonical_params(),
            requirements=_canonical_requirements(),
        )
        output = run_requirements(ei)
        assert output.stage == PipelineStage.REQUIREMENTS
        assert len(output.sections) == 2

    def test_run_requirements_empty(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_requirements(ei)
        assert len(output.sections) == 0
        assert len(output.warnings) > 0

    def test_section_m_tradeoff_at_20m(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_section_m(ei)
        m1 = next(s for s in output.sections if s["section_id"] == "M.1")
        assert "tradeoff" in m1["content"].lower()
        assert "significantly more important" in m1["content"]

    def test_section_l_page_limits_20m(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_section_l(ei)
        l2 = next(s for s in output.sections if s["section_id"] == "L.2")
        assert "40" in l2["content"]  # 40 pages at $20M

    def test_igce_cost_data_section_at_20m(self):
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        output = run_igce(ei)
        assert len(output.sections) >= 4  # includes cost data section
        cost_sec = next((s for s in output.sections if "Cost Data" in s["heading"]), None)
        assert cost_sec is not None
        assert "$2.5M" in cost_sec["content"] or "2.5M" in cost_sec["content"]


# ─── Pipeline Execution Tests ────────────────────────────────────────────────

class TestPipelineExecution:
    def test_full_pipeline(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            requirements=_canonical_requirements(),
            skip_compliance=True,
        )
        assert isinstance(result, PipelineResult)
        assert result.package_id == "pkg-001"
        assert len(result.stages_completed) > 0
        assert result.overall_confidence > 0

    def test_documents_generated(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            skip_compliance=True,
        )
        # Should have PWS, IGCE, Section L, Section M, QASP at minimum
        doc_stages = set(result.documents.keys())
        assert "pws" in doc_stages
        assert "igce" in doc_stages
        assert "section_l" in doc_stages
        assert "section_m" in doc_stages
        assert "qasp" in doc_stages

    def test_custom_stage_list(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.IGCE],
        )
        assert set(result.documents.keys()) == {"pws", "igce"}
        assert PipelineStage.PWS in result.stages_completed
        assert PipelineStage.IGCE in result.stages_completed

    def test_version_store_populated(self):
        store = VersionStore()
        orch = DraftingOrchestrator(version_store=store)
        orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS],
        )
        assert store.version_count("pkg-001", PipelineStage.PWS) == 1
        latest = store.get_latest("pkg-001", PipelineStage.PWS)
        assert latest is not None
        assert len(latest.sections) > 0

    def test_pipeline_result_serialization(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.SECTION_L],
            skip_compliance=True,
        )
        d = result.to_dict()
        assert d["package_id"] == "pkg-001"
        assert "pws" in d["documents"]
        assert isinstance(d["ucf_assembly"], list)
        assert d["overall_confidence"] > 0
        assert d["generated_at"]

    def test_warnings_aggregated(self):
        orch = DraftingOrchestrator()
        params = _canonical_params()
        # Empty requirements should produce a warning
        result = orch.run(
            package_id="pkg-001",
            params=params,
            stages=[PipelineStage.REQUIREMENTS, PipelineStage.PWS],
        )
        # Requirements stage with no input generates a warning
        assert any("No requirements" in w for w in result.warnings)

    def test_provenance_deduplicated(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.SECTION_L],
            skip_compliance=True,
        )
        # Provenance should have no duplicates
        assert len(result.source_provenance) == len(set(result.source_provenance))

    def test_generated_at_timestamp(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS],
        )
        assert result.generated_at
        # Should be parseable ISO format
        datetime.fromisoformat(result.generated_at.replace("Z", "+00:00"))


# ─── Inter-Engine Data Flow Tests ────────────────────────────────────────────

class TestInterEngineDataFlow:
    def test_pws_feeds_qasp(self):
        """QASP should receive PWS sections from the pipeline context."""
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.QASP],
        )
        qasp_output = result.documents["qasp"]
        # QASP purpose section + surveillance items from PWS
        assert len(qasp_output.sections) >= 2
        assert qasp_output.sections[0]["section_id"] == "QASP.1"

    def test_requirements_feed_downstream(self):
        """Requirements should flow into the pipeline context."""
        orch = DraftingOrchestrator()
        reqs = _canonical_requirements()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            requirements=reqs,
            stages=[PipelineStage.REQUIREMENTS, PipelineStage.PWS],
        )
        req_output = result.documents["requirements"]
        assert len(req_output.sections) == 2

    def test_eval_factors_feed_section_m(self):
        """Eval factors should be available to Section M engine."""
        orch = DraftingOrchestrator()
        factors = _canonical_eval_factors()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            eval_factors=factors,
            stages=[PipelineStage.FACTOR_DERIVATION, PipelineStage.SECTION_M],
        )
        assert "factor_derivation" in result.documents
        assert "section_m" in result.documents


# ─── UCF Assembly Tests ──────────────────────────────────────────────────────

class TestUCFAssembly:
    def test_ucf_mapping(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.SECTION_L, PipelineStage.SECTION_M,
                    PipelineStage.QASP, PipelineStage.UCF_ASSEMBLY],
            skip_compliance=True,
        )
        ucf_sections = {m.ucf_section for m in result.ucf_assembly}
        assert UCFSection.C in ucf_sections    # PWS → Section C
        assert UCFSection.L in ucf_sections    # Section L
        assert UCFSection.M in ucf_sections    # Section M
        assert UCFSection.J in ucf_sections    # QASP → Attachments

    def test_ucf_ordering(self):
        """UCF sections should be in alphabetical order (A through M)."""
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.SECTION_L, PipelineStage.SECTION_M,
                    PipelineStage.QASP, PipelineStage.UCF_ASSEMBLY],
            skip_compliance=True,
        )
        ucf_values = [m.ucf_section.value for m in result.ucf_assembly]
        assert ucf_values == sorted(ucf_values)

    def test_ucf_authorities(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.SECTION_L, PipelineStage.UCF_ASSEMBLY],
            skip_compliance=True,
        )
        for m in result.ucf_assembly:
            assert m.authority.startswith("FAR")

    def test_ucf_stage_map_complete(self):
        """All document stages should have UCF mappings."""
        for stage in [PipelineStage.PWS, PipelineStage.SECTION_L,
                      PipelineStage.SECTION_M, PipelineStage.QASP, PipelineStage.IGCE]:
            assert stage in UCF_STAGE_MAP

    def test_ucf_serialization(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.UCF_ASSEMBLY],
            skip_compliance=True,
        )
        d = result.to_dict()
        assert len(d["ucf_assembly"]) > 0
        for entry in d["ucf_assembly"]:
            assert "ucf_section" in entry
            assert "authority" in entry
            assert "section_count" in entry


# ─── Compliance Integration Tests ────────────────────────────────────────────

class TestComplianceIntegration:
    def test_compliance_result_structure(self):
        cr = ComplianceResult(doc_type="PWS", overall_score=85.0, passed=True)
        assert cr.doc_type == "PWS"
        assert cr.overall_score == 85.0
        assert cr.passed is True

    def test_compliance_stages_defined(self):
        assert "PWS" in COMPLIANCE_STAGES.values()
        assert "Section_L" in COMPLIANCE_STAGES.values()
        assert "Section_M" in COMPLIANCE_STAGES.values()
        assert "QASP" in COMPLIANCE_STAGES.values()
        assert "IGCE" in COMPLIANCE_STAGES.values()

    def test_compliance_fallback_on_import_error(self):
        """Compliance should gracefully degrade if module not available."""
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        # This should not raise even if compliance module has issues
        result = run_compliance(ei, "PWS", [{"section_id": "3.1", "content": "Test"}])
        assert isinstance(result, ComplianceResult)

    def test_compliance_in_pipeline(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.COMPLIANCE],
            skip_compliance=False,
        )
        # Compliance should have run on PWS
        assert PipelineStage.COMPLIANCE in result.stages_completed


# ─── Pipeline Context Tests ──────────────────────────────────────────────────

class TestPipelineContext:
    def test_context_initialization(self):
        ctx = PipelineContext(
            package_id="pkg-001",
            acquisition_params=_canonical_params(),
        )
        assert ctx.package_id == "pkg-001"
        assert ctx.pws_sections is None
        assert ctx.market_research is None

    def test_context_accumulates(self):
        """Running pipeline should populate context progressively."""
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS, PipelineStage.QASP],
        )
        # QASP should have received PWS sections (evidenced by surveillance items)
        qasp = result.documents["qasp"]
        assert len(qasp.sections) > 1  # Purpose + at least 1 surveillance item


# ─── Edge Cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_stage_list(self):
        orch = DraftingOrchestrator()
        result = orch.run(package_id="pkg-001", params=_canonical_params(), stages=[])
        assert len(result.stages_completed) == 0
        assert len(result.documents) == 0

    def test_single_stage(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params=_canonical_params(),
            stages=[PipelineStage.PWS],
        )
        assert len(result.documents) == 1
        assert "pws" in result.documents

    def test_minimal_params(self):
        orch = DraftingOrchestrator()
        result = orch.run(
            package_id="pkg-001",
            params={"value": 100_000, "title": "Simple Purchase"},
            stages=[PipelineStage.PWS],
        )
        assert len(result.documents["pws"].sections) > 0

    def test_multiple_runs_accumulate_versions(self):
        store = VersionStore()
        orch = DraftingOrchestrator(version_store=store)
        orch.run(package_id="pkg-001", params=_canonical_params(), stages=[PipelineStage.PWS])
        orch.run(package_id="pkg-001", params=_canonical_params(), stages=[PipelineStage.PWS])
        assert store.version_count("pkg-001", PipelineStage.PWS) == 2

    def test_version_diff_between_runs(self):
        store = VersionStore()
        orch = DraftingOrchestrator(version_store=store)
        orch.run(package_id="pkg-001", params=_canonical_params(), stages=[PipelineStage.PWS])
        # Modify params slightly for different output
        params2 = _canonical_params()
        params2["title"] = "Modified Title"
        orch.run(package_id="pkg-001", params=params2, stages=[PipelineStage.PWS])
        diffs = store.diff("pkg-001", PipelineStage.PWS, 1, 2)
        # Should have at least one modified section (background mentions title)
        assert len(diffs) > 0

    def test_default_pipeline_stages(self):
        assert PipelineStage.MARKET_RESEARCH in DEFAULT_PIPELINE
        assert PipelineStage.PWS in DEFAULT_PIPELINE
        assert PipelineStage.UCF_ASSEMBLY in DEFAULT_PIPELINE
        assert len(DEFAULT_PIPELINE) == 10

    def test_run_stage_unknown(self):
        orch = DraftingOrchestrator()
        ei = EngineInput(package_id="test", acquisition_params=_canonical_params())
        # COMPLIANCE and UCF_ASSEMBLY don't have runners — should return fallback
        output = orch.run_stage(PipelineStage.COMPLIANCE, ei)
        assert len(output.warnings) > 0

    def test_diff_nonexistent_versions(self):
        store = VersionStore()
        diffs = store.diff("pkg-001", PipelineStage.PWS, 1, 2)
        assert diffs == []
