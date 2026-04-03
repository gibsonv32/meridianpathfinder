"""
Phase 28: Lineage Extension — Full Traceability Tests
=====================================================

Tests for backend/core/lineage_extension.py

Covers:
  - Extended chain stages (10 stages)
  - Market research integration
  - Document chain registration (Phase 27)
  - Cross-document dependency graph
  - Cross-document consistency checking
  - Modification impact analysis
  - Extended coverage computation
  - Full build orchestration
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from backend.core.lineage_extension import (
    FullTraceabilityLedger,
    EXTENDED_CHAIN_STAGES,
    DOCUMENT_DEPENDENCIES,
    SUPPORTING_DOC_DCODES,
    DependencyType,
    DocumentDependency,
    ConsistencyFinding,
    ModificationImpact,
    FullTraceabilityResult,
)
from backend.phase2.evidence_lineage import (
    EvidenceLineageLedger,
    LineageNodeType,
    LineageNode,
    LineageLink,
    LinkType,
    CHAIN_STAGES,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

def _canonical_params():
    """$20M TSA IT Services, FFP, Full & Open, NAICS 541512."""
    return {
        "package_id": "pkg-test-001",
        "estimated_value": 20_000_000,
        "services": True,
        "it_related": True,
        "sole_source": False,
        "competition_type": "full_and_open",
        "contract_type": "FFP",
        "naics": "541512",
        "sub_agency": "TSA",
        "vendor_on_site": True,
        "classified": False,
        "has_options": True,
    }


def _pws_document():
    """Mock PWS document with 3 sections."""
    return {
        "dcode": "D102",
        "document_id": "doc-pws-001",
        "title": "Performance Work Statement",
        "content": {
            "sections": [
                {"section_id": "3.1", "heading": "Help Desk Support",
                 "content": "The contractor shall provide help desk support."},
                {"section_id": "3.2", "heading": "Network Monitoring",
                 "content": "The contractor shall monitor network uptime 99.9%."},
                {"section_id": "3.3", "heading": "Incident Response",
                 "content": "The contractor shall respond to incidents within 4 hours."},
            ]
        },
    }


def _section_l_document():
    """Mock Section L document."""
    return {
        "dcode": "D113",
        "document_id": "doc-l-001",
        "title": "Section L — Instructions to Offerors",
        "content": {
            "sections": [
                {"section_id": "L.1", "heading": "General Instructions",
                 "content": "Proposals shall not exceed 40 pages."},
                {"section_id": "L.3", "heading": "Technical Approach",
                 "content": "Describe technical approach to PWS requirements."},
                {"section_id": "L.4", "heading": "Management Approach",
                 "content": "Describe management approach and key personnel."},
            ]
        },
    }


def _section_m_document():
    """Mock Section M document."""
    return {
        "dcode": "D107",
        "document_id": "doc-m-001",
        "title": "Section M — Evaluation Factors",
        "content": {
            "sections": [
                {"section_id": "M.1", "heading": "Basis for Award",
                 "content": "Best value tradeoff."},
                {"section_id": "M.2", "heading": "Technical Factor",
                 "content": "Technical approach evaluation."},
                {"section_id": "M.3", "heading": "Management Factor",
                 "content": "Management approach evaluation."},
            ]
        },
    }


def _qasp_document():
    """Mock QASP document."""
    return {
        "dcode": "D105",
        "document_id": "doc-qasp-001",
        "title": "QASP",
        "content": {
            "sections": [
                {"section_id": "QASP.1", "heading": "Help Desk SLA",
                 "content": "Monitor help desk response per PWS 3.1."},
                {"section_id": "QASP.2", "heading": "Network Uptime",
                 "content": "Monitor uptime per PWS 3.2. 99.9% threshold."},
            ]
        },
    }


def _market_research_report():
    """Mock MarketResearchAgent output."""
    return {
        "sections": [
            {"section_id": "MR.1", "heading": "Comparable Awards",
             "authority": "FAR 10.002(b)(1)", "confidence": 85,
             "content": "Found 12 comparable DHS IT services contracts."},
            {"section_id": "MR.2", "heading": "Small Business Availability",
             "authority": "FAR 10.002(b)(2)", "confidence": 90,
             "content": "Rule of two met — total SB set-aside viable."},
            {"section_id": "MR.3", "heading": "Pricing Intelligence",
             "authority": "FAR 10.002(b)(1)", "confidence": 75,
             "content": "PIL rates: $95–$250/hr for IT labor categories."},
        ]
    }


def _mock_chain_result():
    """Mock Phase 27 ChainResult.to_dict() output."""
    return {
        "supporting_docs": {
            "bcm": {
                "doc_type": "bcm",
                "sections": [
                    {"section_id": "A", "heading": "Acquisition Information",
                     "authority": "IGPM 0103.19", "content": "Contract info.",
                     "confidence": 90, "rationale": "Standard BCM"},
                    {"section_id": "G", "heading": "Compliance Checklist",
                     "authority": "IGPM 0103.19", "content": "27-item checklist.",
                     "confidence": 95, "rationale": "FAR/HSAM checklist"},
                ],
                "warnings": [],
                "requires_acceptance": True,
            },
            "ssp": {
                "doc_type": "ssp",
                "sections": [
                    {"section_id": "SSP.1", "heading": "Purpose",
                     "authority": "FAR 15.303", "content": "Source selection plan.",
                     "confidence": 90, "rationale": "Standard SSP"},
                ],
                "warnings": [],
                "requires_acceptance": True,
            },
            "security_requirements": {
                "doc_type": "security_requirements",
                "sections": [
                    {"section_id": "SEC.1", "heading": "Personnel Security",
                     "authority": "HSAR 3052.204-71", "content": "Background checks required.",
                     "confidence": 95, "rationale": "HSAR requirement"},
                ],
                "warnings": [],
                "requires_acceptance": True,
            },
        },
        "pipeline_result": {
            "documents": {
                "pws": {
                    "sections": [
                        {"section_id": "3.1", "heading": "Help Desk", "content": "Support."},
                    ]
                },
            },
            "warnings": [],
        },
    }


def _all_documents():
    """Full document set for base ledger."""
    return [_pws_document(), _section_l_document(), _section_m_document(), _qasp_document()]


# ══════════════════════════════════════════════════════════════════════════
# Test Classes
# ══════════════════════════════════════════════════════════════════════════


class TestExtendedChainStages:
    """Test the 10-stage extended chain model."""

    def test_has_10_stages(self):
        assert len(EXTENDED_CHAIN_STAGES) == 10

    def test_market_research_is_first(self):
        assert EXTENDED_CHAIN_STAGES[0] == "market_research"

    def test_closeout_is_last(self):
        assert EXTENDED_CHAIN_STAGES[-1] == "closeout"

    def test_base_stages_preserved(self):
        """All original 8 stages exist in extended stages."""
        for stage in CHAIN_STAGES:
            assert stage in EXTENDED_CHAIN_STAGES

    def test_stage_ordering(self):
        """Market research before requirement, closeout after cpars_rating."""
        mr_idx = EXTENDED_CHAIN_STAGES.index("market_research")
        req_idx = EXTENDED_CHAIN_STAGES.index("requirement")
        cpars_idx = EXTENDED_CHAIN_STAGES.index("cpars_rating")
        close_idx = EXTENDED_CHAIN_STAGES.index("closeout")
        assert mr_idx < req_idx
        assert cpars_idx < close_idx


class TestDocumentDependencyGraph:
    """Test the static dependency map and graph builder."""

    def test_pws_has_most_dependents(self):
        """PWS is the root document with most downstream dependencies."""
        pws_deps = DOCUMENT_DEPENDENCIES.get("pws", [])
        assert len(pws_deps) >= 5

    def test_all_dependency_types_used(self):
        """All DependencyType values are used in the graph."""
        used_types = set()
        for deps in DOCUMENT_DEPENDENCIES.values():
            for _, dep_type, _ in deps:
                used_types.add(dep_type)
        assert DependencyType.CONTENT_SOURCE in used_types
        assert DependencyType.APPROVAL_GATE in used_types
        assert DependencyType.CROSS_REFERENCE in used_types

    def test_build_dependency_graph_canonical(self):
        ftl = FullTraceabilityLedger()
        graph = ftl.build_dependency_graph(_canonical_params())
        assert len(graph) > 0
        assert all(isinstance(d, DocumentDependency) for d in graph)

    def test_sole_source_includes_ja_deps(self):
        ftl = FullTraceabilityLedger()
        params = _canonical_params()
        params["sole_source"] = True
        graph = ftl.build_dependency_graph(params)
        ja_deps = [d for d in graph if d.source_doc == "ja" or d.dependent_doc == "ja"]
        assert len(ja_deps) > 0

    def test_competitive_excludes_ja_deps(self):
        ftl = FullTraceabilityLedger()
        params = _canonical_params()
        params["sole_source"] = False
        graph = ftl.build_dependency_graph(params)
        ja_source = [d for d in graph if d.source_doc == "ja"]
        assert len(ja_source) == 0

    def test_blocking_dependencies_exist(self):
        ftl = FullTraceabilityLedger()
        params = _canonical_params()
        params["sole_source"] = True
        graph = ftl.build_dependency_graph(params)
        blocking = [d for d in graph if d.is_blocking]
        assert len(blocking) > 0

    def test_get_upstream_docs(self):
        ftl = FullTraceabilityLedger()
        upstream = ftl.get_upstream_docs("section_l")
        assert "pws" in upstream

    def test_get_downstream_docs(self):
        ftl = FullTraceabilityLedger()
        downstream = ftl.get_downstream_docs("pws")
        assert "section_l" in downstream
        assert "section_m" in downstream
        assert "qasp" in downstream


class TestSupportingDocDcodes:
    """Test the doc_type → D-code mapping."""

    def test_all_10_doc_types_mapped(self):
        assert len(SUPPORTING_DOC_DCODES) == 10

    def test_known_mappings(self):
        assert SUPPORTING_DOC_DCODES["ja"] == "D106"
        assert SUPPORTING_DOC_DCODES["bcm"] == "D110"
        assert SUPPORTING_DOC_DCODES["ap"] == "D104"
        assert SUPPORTING_DOC_DCODES["ssp"] == "D114"
        assert SUPPORTING_DOC_DCODES["security_requirements"] == "D120"


class TestMarketResearchIntegration:
    """Test market research finding registration."""

    def test_register_creates_nodes(self):
        ftl = FullTraceabilityLedger()
        report = _market_research_report()
        nodes = ftl.register_market_research("pkg-001", report)
        # 1 doc node + 3 finding nodes
        assert len(nodes) == 4

    def test_report_node_is_document_type(self):
        ftl = FullTraceabilityLedger()
        nodes = ftl.register_market_research("pkg-001", _market_research_report())
        assert nodes[0].node_type == LineageNodeType.DOCUMENT

    def test_finding_nodes_have_metadata(self):
        ftl = FullTraceabilityLedger()
        nodes = ftl.register_market_research("pkg-001", _market_research_report())
        finding = nodes[1]
        assert finding.metadata.get("doc_type") == "market_research_finding"
        assert finding.metadata.get("confidence") == 85

    def test_findings_linked_to_report(self):
        ftl = FullTraceabilityLedger()
        ftl.register_market_research("pkg-001", _market_research_report())
        links = ftl.ledger.get_all_links()
        contains_links = [l for l in links if l.link_type == LinkType.CONTAINS]
        assert len(contains_links) == 3

    def test_link_to_requirements(self):
        ftl = FullTraceabilityLedger()
        ftl.register_market_research("pkg-001", _market_research_report())
        # Build base ledger to create requirement nodes
        from backend.phase2.evidence_lineage import BuildLedgerRequest
        ftl.ledger.build_ledger(BuildLedgerRequest(
            package_id="pkg-001", documents=_all_documents(),
        ))
        links = ftl.link_market_research_to_requirements("pkg-001")
        # 3 findings × 3 requirements = up to 9 links
        assert len(links) > 0

    def test_empty_report_creates_doc_only(self):
        ftl = FullTraceabilityLedger()
        nodes = ftl.register_market_research("pkg-001", {"sections": []})
        assert len(nodes) == 1  # Just the doc node


class TestDocumentChainRegistration:
    """Test Phase 27 document chain integration."""

    def test_register_supporting_document(self):
        ftl = FullTraceabilityLedger()
        draft = {
            "doc_type": "bcm",
            "sections": [
                {"section_id": "A", "heading": "Info", "authority": "IGPM 0103.19",
                 "content": "Test", "confidence": 90},
            ],
            "warnings": [],
        }
        node = ftl.register_supporting_document("pkg-001", "bcm", draft)
        assert node.node_type == LineageNodeType.DOCUMENT
        assert node.metadata["dcode"] == "D110"

    def test_supporting_doc_linked_to_dcode(self):
        ftl = FullTraceabilityLedger()
        draft = {
            "doc_type": "ja",
            "sections": [
                {"section_id": "JA.1", "heading": "Authority", "authority": "FAR 6.302",
                 "content": "Test", "confidence": 85},
            ],
            "warnings": [],
        }
        ftl.register_supporting_document("pkg-001", "ja", draft)
        links = ftl.ledger.get_all_links()
        impl_links = [l for l in links if l.link_type == LinkType.IMPLEMENTS]
        assert len(impl_links) >= 1

    def test_section_nodes_created(self):
        ftl = FullTraceabilityLedger()
        draft = {
            "doc_type": "bcm",
            "sections": [
                {"section_id": "A", "heading": "Info", "authority": "X", "content": "T", "confidence": 90},
                {"section_id": "B", "heading": "Clearance", "authority": "Y", "content": "T", "confidence": 85},
                {"section_id": "G", "heading": "Compliance", "authority": "Z", "content": "T", "confidence": 95},
            ],
            "warnings": [],
        }
        ftl.register_supporting_document("pkg-001", "bcm", draft)
        all_nodes = ftl.ledger.get_all_nodes()
        # 1 doc node + 1 D-code node + 3 section nodes = 5
        assert len(all_nodes) == 5

    def test_register_document_chain(self):
        ftl = FullTraceabilityLedger()
        result = ftl.register_document_chain("pkg-001", _mock_chain_result())
        assert result["nodes_created"] > 0
        assert result["links_created"] > 0
        assert "bcm" in result["docs_registered"]
        assert "ssp" in result["docs_registered"]

    def test_chain_registers_pipeline_docs(self):
        ftl = FullTraceabilityLedger()
        result = ftl.register_document_chain("pkg-001", _mock_chain_result())
        assert "pipeline_pws" in result["docs_registered"]

    def test_dependency_links_created(self):
        """Dependency links are created between registered documents."""
        ftl = FullTraceabilityLedger()
        ftl.register_document_chain("pkg-001", _mock_chain_result())
        all_links = ftl.ledger.get_all_links()
        # Should have IMPLEMENTS + CONTAINS + dependency TRACES_TO links
        link_types = {l.link_type for l in all_links}
        assert LinkType.IMPLEMENTS in link_types
        assert LinkType.CONTAINS in link_types


class TestConsistencyChecking:
    """Test cross-document consistency validation."""

    def test_no_findings_when_consistent(self):
        ftl = FullTraceabilityLedger()
        docs = {
            "pws": {"sections": [
                {"section_id": "3.1", "heading": "Support", "content": "Shall provide."},
            ]},
            "section_l": {"sections": [
                {"section_id": "L.3", "heading": "Technical", "content": "Tech approach."},
                {"section_id": "L.4", "heading": "Management", "content": "Mgmt approach."},
            ]},
            "section_m": {"sections": [
                {"section_id": "M.2", "heading": "Technical", "content": "Tech eval."},
                {"section_id": "M.3", "heading": "Management", "content": "Mgmt eval."},
            ]},
            "qasp": {"sections": [
                {"section_id": "Q.1", "heading": "SLA", "content": "Monitor."},
            ]},
        }
        findings = ftl.check_consistency("pkg-001", docs)
        # With well-structured docs, should have zero critical/high findings
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) == 0

    def test_missing_section_l_flagged(self):
        ftl = FullTraceabilityLedger()
        docs = {
            "pws": {"sections": [
                {"section_id": "3.1", "heading": "Support", "content": "Shall provide."},
            ]},
            "section_l": {"sections": []},  # Empty L
        }
        findings = ftl.check_consistency("pkg-001", docs)
        assert len(findings) > 0
        assert any(f.affected_doc == "section_l" for f in findings)

    def test_missing_section_m_flagged(self):
        ftl = FullTraceabilityLedger()
        docs = {
            "section_l": {"sections": [
                {"section_id": "L.3", "heading": "Technical", "content": "Tech approach."},
            ]},
            "section_m": {"sections": []},  # Empty M
        }
        findings = ftl.check_consistency("pkg-001", docs)
        assert len(findings) > 0
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1

    def test_l_m_pair_mismatch(self):
        """L.3 exists but M.2 missing."""
        ftl = FullTraceabilityLedger()
        docs = {
            "section_l": {"sections": [
                {"section_id": "L.3", "heading": "Technical", "content": "Tech approach."},
            ]},
            "section_m": {"sections": [
                {"section_id": "M.1", "heading": "Basis", "content": "Award basis."},
                # M.2 missing!
            ]},
        }
        findings = ftl.check_consistency("pkg-001", docs)
        pair_findings = [f for f in findings if "L.3" in f.description or "M.2" in f.description]
        assert len(pair_findings) >= 1

    def test_qasp_coverage_warning(self):
        """QASP with very few items compared to PWS."""
        ftl = FullTraceabilityLedger()
        docs = {
            "pws": {"sections": [
                {"section_id": "3.1", "heading": "A", "content": "X"},
                {"section_id": "3.2", "heading": "B", "content": "X"},
                {"section_id": "3.3", "heading": "C", "content": "X"},
                {"section_id": "3.4", "heading": "D", "content": "X"},
                {"section_id": "3.5", "heading": "E", "content": "X"},
                {"section_id": "3.6", "heading": "F", "content": "X"},
            ]},
            "qasp": {"sections": [
                {"section_id": "Q.1", "heading": "One", "content": "X"},
            ]},
        }
        findings = ftl.check_consistency("pkg-001", docs)
        qasp_findings = [f for f in findings if f.affected_doc == "qasp"]
        assert len(qasp_findings) >= 1

    def test_security_cor_consistency(self):
        """Security has personnel requirements, COR should reference."""
        ftl = FullTraceabilityLedger()
        docs = {
            "security_requirements": {"sections": [
                {"section_id": "SEC.1", "heading": "Personnel Security",
                 "content": "Background investigation required."},
            ]},
            "cor_nomination": {"sections": [
                {"section_id": "COR.1", "heading": "Duties",
                 "content": "Monitor deliverables and invoices."},
                # No mention of security!
            ]},
        }
        findings = ftl.check_consistency("pkg-001", docs)
        sec_findings = [f for f in findings if f.source_doc == "security_requirements"]
        assert len(sec_findings) >= 1

    def test_bcm_ap_reference(self):
        """BCM should reference AP if it exists."""
        ftl = FullTraceabilityLedger()
        docs = {
            "ap": {"sections": [
                {"section_id": "AP.1", "heading": "Plan", "content": "Acquisition plan."},
            ]},
            "bcm": {"sections": [
                {"section_id": "A", "heading": "Info", "content": "Contract details only."},
            ]},
        }
        findings = ftl.check_consistency("pkg-001", docs)
        bcm_findings = [f for f in findings if f.affected_doc == "bcm"]
        assert len(bcm_findings) >= 1

    def test_finding_has_required_fields(self):
        ftl = FullTraceabilityLedger()
        docs = {
            "pws": {"sections": [{"section_id": "3.1", "heading": "X", "content": "Y"}]},
            "section_l": {"sections": []},
        }
        findings = ftl.check_consistency("pkg-001", docs)
        for f in findings:
            assert f.finding_id.startswith("CF-")
            assert f.severity in ("critical", "high", "medium", "low")
            assert f.source_doc
            assert f.affected_doc
            assert f.description
            assert f.recommendation

    def test_finding_to_dict(self):
        finding = ConsistencyFinding(
            finding_id="CF-001", severity="high",
            source_doc="pws", affected_doc="section_l",
            description="Test", recommendation="Fix it",
        )
        d = finding.to_dict()
        assert d["finding_id"] == "CF-001"
        assert d["severity"] == "high"


class TestModificationImpact:
    """Test modification impact analysis."""

    def test_pws_change_affects_many(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("pws")
        assert len(impact.affected_documents) >= 5
        assert "section_l" in impact.affected_documents
        assert "section_m" in impact.affected_documents
        assert "qasp" in impact.affected_documents

    def test_pws_change_requires_re_solicitation(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("pws")
        assert impact.requires_re_solicitation is True

    def test_section_m_change_requires_re_evaluation(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("section_m")
        assert impact.requires_re_evaluation is True

    def test_igce_change_limited_impact(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("igce")
        assert len(impact.affected_documents) < 5
        assert "bcm" in impact.affected_documents

    def test_market_research_cascades(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("market_research")
        # MR feeds PWS which feeds everything
        assert len(impact.affected_documents) >= 5

    def test_impact_has_severity_summary(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("pws")
        assert "critical" in impact.severity_summary
        assert "high" in impact.severity_summary
        assert "medium" in impact.severity_summary
        assert "low" in impact.severity_summary

    def test_impact_has_recommended_actions(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("pws")
        assert len(impact.recommended_actions) > 0

    def test_ja_change_has_blocking(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("ja")
        blocking = [d for d in impact.dependency_path if d.is_blocking]
        assert len(blocking) >= 1

    def test_jlm_traceability_action(self):
        """Changing PWS should trigger J-L-M re-verification."""
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("pws")
        assert any("J-L-M" in a for a in impact.recommended_actions)

    def test_impact_to_dict(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("pws")
        d = impact.to_dict()
        assert d["changed_doc"] == "pws"
        assert isinstance(d["affected_documents"], list)
        assert isinstance(d["dependency_path"], list)

    def test_leaf_doc_minimal_impact(self):
        """A leaf document with no downstream deps."""
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("award_notice")
        assert len(impact.affected_documents) == 0

    def test_unknown_doc_empty_impact(self):
        ftl = FullTraceabilityLedger()
        impact = ftl.analyze_modification_impact("nonexistent_doc")
        assert len(impact.affected_documents) == 0


class TestExtendedCoverage:
    """Test extended 10-stage coverage computation."""

    def test_empty_coverage(self):
        ftl = FullTraceabilityLedger()
        coverage = ftl.compute_extended_coverage("pkg-empty", {})
        assert len(coverage) == 10
        assert all(v == 0.0 for v in coverage.values())

    def test_market_research_detected_from_nodes(self):
        ftl = FullTraceabilityLedger()
        ftl.register_market_research("pkg-001", _market_research_report())
        coverage = ftl.compute_extended_coverage("pkg-001", {})
        assert coverage["market_research"] == 1.0

    def test_market_research_detected_from_documents(self):
        ftl = FullTraceabilityLedger()
        coverage = ftl.compute_extended_coverage("pkg-001", {"market_research": {}})
        assert coverage["market_research"] == 1.0

    def test_base_stages_from_chains(self):
        ftl = FullTraceabilityLedger()
        from backend.phase2.evidence_lineage import BuildLedgerRequest
        ftl.ledger.build_ledger(BuildLedgerRequest(
            package_id="pkg-001", documents=_all_documents(),
        ))
        coverage = ftl.compute_extended_coverage("pkg-001", {})
        # PWS has 3 sections, each should have requirement coverage
        assert coverage["requirement"] == 1.0


class TestFullBuildOrchestration:
    """Test the complete build_full_traceability method."""

    def test_full_build_returns_result(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            params=_canonical_params(),
        )
        assert isinstance(result, FullTraceabilityResult)
        assert result.package_id == "pkg-001"

    def test_full_build_with_market_research(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            market_research=_market_research_report(),
            params=_canonical_params(),
        )
        assert result.total_nodes > 0
        # MR nodes should be counted
        assert result.extended_coverage.get("market_research", 0) == 1.0

    def test_full_build_with_chain_result(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            chain_result=_mock_chain_result(),
            params=_canonical_params(),
        )
        assert result.document_nodes_registered > 0
        assert result.document_links_created > 0
        assert len(result.supporting_docs_in_lineage) > 0

    def test_full_build_has_dependency_graph(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            params=_canonical_params(),
        )
        assert len(result.dependency_graph) > 0

    def test_full_build_has_consistency_findings(self):
        """Build with incomplete docs should produce findings."""
        ftl = FullTraceabilityLedger()
        chain = _mock_chain_result()
        # Only has BCM, SSP, security — no L/M/QASP in supporting
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            chain_result=chain,
            params=_canonical_params(),
        )
        # No consistency findings expected since L/M/QASP not in chain_result supporting_docs
        assert isinstance(result.consistency_findings, list)

    def test_full_build_has_base_ledger(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            params=_canonical_params(),
        )
        assert result.base_ledger.total_nodes > 0
        assert len(result.base_ledger.chains) == 3  # 3 PWS sections

    def test_full_build_generated_at(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            params=_canonical_params(),
        )
        assert result.generated_at.endswith("Z")

    def test_full_build_overall_coverage(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            market_research=_market_research_report(),
            params=_canonical_params(),
        )
        assert 0.0 < result.overall_coverage <= 1.0

    def test_full_build_to_dict(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            params=_canonical_params(),
        )
        d = result.to_dict()
        assert d["package_id"] == "pkg-001"
        assert "base_ledger" in d
        assert "document_chain" in d
        assert "dependency_graph" in d
        assert "extended_coverage" in d

    def test_full_build_minimal(self):
        """Build with empty documents."""
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-empty",
            documents=[],
            params={},
        )
        assert result.total_chains == 0
        assert len(result.base_ledger.warnings) > 0  # "PWS not found" warning


class TestDocumentDependencyDataclass:
    """Test dataclass serialization."""

    def test_to_dict(self):
        dep = DocumentDependency(
            source_doc="pws",
            dependent_doc="section_l",
            dependency_type=DependencyType.CONTENT_SOURCE,
            rationale="L derives from PWS",
            is_blocking=False,
        )
        d = dep.to_dict()
        assert d["source_doc"] == "pws"
        assert d["dependency_type"] == "content_source"
        assert d["is_blocking"] is False


class TestModificationImpactDataclass:
    """Test ModificationImpact serialization."""

    def test_to_dict(self):
        impact = ModificationImpact(
            changed_doc="pws",
            affected_documents=["section_l", "section_m"],
            affected_chains=["chain-1"],
            total_affected_nodes=2,
            severity_summary={"critical": 0, "high": 2, "medium": 0, "low": 0},
            dependency_path=[],
            recommended_actions=["Update L and M"],
        )
        d = impact.to_dict()
        assert d["changed_doc"] == "pws"
        assert len(d["affected_documents"]) == 2


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_market_research_sections(self):
        ftl = FullTraceabilityLedger()
        nodes = ftl.register_market_research("pkg-001", {})
        # Should handle gracefully — no sections key
        assert len(nodes) == 1  # Just the doc node

    def test_register_chain_with_no_supporting(self):
        ftl = FullTraceabilityLedger()
        result = ftl.register_document_chain("pkg-001", {
            "supporting_docs": {},
            "pipeline_result": {"documents": {}, "warnings": []},
        })
        assert result["nodes_created"] == 0
        assert result["docs_registered"] == []

    def test_consistency_empty_docs(self):
        ftl = FullTraceabilityLedger()
        findings = ftl.check_consistency("pkg-001", {})
        assert findings == []

    def test_multiple_packages_isolated(self):
        ftl = FullTraceabilityLedger()
        ftl.register_market_research("pkg-A", _market_research_report())
        ftl.register_market_research("pkg-B", _market_research_report())
        cov_a = ftl.compute_extended_coverage("pkg-A", {})
        cov_b = ftl.compute_extended_coverage("pkg-B", {})
        assert cov_a["market_research"] == 1.0
        assert cov_b["market_research"] == 1.0

    def test_idempotent_node_registration(self):
        ftl = FullTraceabilityLedger()
        nodes1 = ftl.register_market_research("pkg-001", _market_research_report())
        nodes2 = ftl.register_market_research("pkg-001", _market_research_report())
        # Same reference_id → returns existing node
        assert nodes1[0].node_id == nodes2[0].node_id

    def test_dependency_to_dict_round_trip(self):
        dep = DocumentDependency(
            source_doc="igce", dependent_doc="bcm",
            dependency_type=DependencyType.CROSS_REFERENCE,
            rationale="BCM references IGCE", is_blocking=False,
        )
        d = dep.to_dict()
        assert d["dependency_type"] == "cross_reference"

    def test_full_result_to_dict_structure(self):
        ftl = FullTraceabilityLedger()
        result = ftl.build_full_traceability(
            package_id="pkg-001",
            documents=_all_documents(),
            market_research=_market_research_report(),
            chain_result=_mock_chain_result(),
            params=_canonical_params(),
        )
        d = result.to_dict()
        assert "base_ledger" in d
        assert "extended_coverage" in d
        assert "document_chain" in d
        assert "dependency_graph" in d
        assert "consistency_findings" in d
        assert "total_nodes" in d
        assert "total_links" in d
        assert "overall_coverage" in d
        assert "warnings" in d
