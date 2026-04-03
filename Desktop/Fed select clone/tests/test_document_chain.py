"""
Phase 27: Document Chain Integration Tests
============================================

Tests the DocumentChainOrchestrator that composes the base pipeline
with supporting document engines.

Author: Centurion Acquisitor / FedProcure
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.document_chain import (
    DocumentChainOrchestrator, ChainResult, SUPPORT_DOC_UCF_MAP,
)
from backend.core.document_engines import DOCUMENT_ENGINES, DocumentDraft
from backend.core.drafting_orchestrator import (
    PipelineStage, UCFSection, VersionStore,
)


def _canonical_params() -> dict:
    """$20M TSA IT services — canonical test fixture."""
    return {
        "estimated_value": 20_000_000,
        "services": True,
        "is_it": True,
        "it_related": True,
        "contract_type": "FFP",
        "competition_type": "full_and_open",
        "naics_code": "541512",
        "psc_code": "D311",
        "sub_agency": "TSA",
        "evaluation_type": "tradeoff",
        "pop_months": 60,
        "has_options": True,
        "sole_source": False,
        "classified": True,
        "clearance_required": True,
        "vendor_on_site": True,
        "on_site": True,
        "handles_ssi": True,
        "has_cui": True,
        "requirement_description": "IT systems support services",
        "contractor_name": "Acme Federal Services",
        # Fields needed by base pipeline
        "value": 20_000_000,
    }


# ========================================================================
# Test DocumentChainOrchestrator
# ========================================================================

class TestChainOrchestrator(unittest.TestCase):
    """Test the document chain orchestrator."""

    def setUp(self):
        self.chain = DocumentChainOrchestrator()

    def test_generate_supporting_only(self):
        """Skip base pipeline, generate only supporting docs."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        self.assertIsInstance(result, ChainResult)
        self.assertGreater(len(result.supporting_docs), 0)
        self.assertEqual(len(result.pipeline_result.documents), 0)

    def test_canonical_supporting_docs(self):
        """$20M FFP F&O should produce correct supporting docs."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        # Should have: bcm, ssp, eval_worksheet, award_notice, security, cor, sb_review
        self.assertIn("bcm", result.supporting_docs)
        self.assertIn("ssp", result.supporting_docs)
        self.assertIn("cor_nomination", result.supporting_docs)
        self.assertIn("sb_review", result.supporting_docs)
        self.assertIn("security_requirements", result.supporting_docs)
        # Should NOT have J&A (competitive) or AP (FFP under $50M)
        self.assertNotIn("ja", result.supporting_docs)
        self.assertNotIn("ap", result.supporting_docs)

    def test_specific_doc_types(self):
        """Generate only specified supporting doc types."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
            doc_types=["bcm", "ssp"],
        )
        self.assertEqual(len(result.supporting_docs), 2)
        self.assertIn("bcm", result.supporting_docs)
        self.assertIn("ssp", result.supporting_docs)

    def test_skip_supporting(self):
        """Skip supporting docs, run base pipeline only."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
            skip_supporting=True,
        )
        self.assertEqual(len(result.supporting_docs), 0)

    def test_ucf_assembly_includes_supporting(self):
        """Full UCF should include both base and supporting docs."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        ucf_types = [m.doc_type for m in result.full_ucf_assembly]
        # Supporting docs should be in UCF
        self.assertIn("bcm", ucf_types)
        self.assertIn("security_requirements", ucf_types)

    def test_ucf_ordering(self):
        """UCF assembly should be sorted by section order."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        section_order = list(UCFSection)
        for i in range(len(result.full_ucf_assembly) - 1):
            idx_a = section_order.index(result.full_ucf_assembly[i].ucf_section)
            idx_b = section_order.index(result.full_ucf_assembly[i + 1].ucf_section)
            self.assertLessEqual(idx_a, idx_b)

    def test_total_counts(self):
        """Verify total document and section counts."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        expected_docs = len(result.supporting_docs)
        self.assertEqual(result.total_documents, expected_docs)
        expected_sections = sum(len(d.sections) for d in result.supporting_docs.values())
        self.assertEqual(result.total_sections, expected_sections)

    def test_warnings_aggregated(self):
        """Warnings from all sources should be aggregated."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        # BCM over $500K should produce a warning
        self.assertTrue(any("$500K" in w for w in result.warnings))

    def test_generated_at(self):
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        self.assertIn("T", result.generated_at)


# ========================================================================
# Test Approval Summary
# ========================================================================

class TestApprovalSummary(unittest.TestCase):
    """Test approval chain derivation."""

    def setUp(self):
        self.chain = DocumentChainOrchestrator()

    def test_canonical_approval(self):
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        self.assertEqual(result.approval_summary["bcm_approver"], "DAA")
        self.assertEqual(result.approval_summary["ssa_appointment"], "DAA")
        # No J&A for competitive
        self.assertNotIn("ja_approver", result.approval_summary)

    def test_sole_source_approval(self):
        params = {**_canonical_params(), "sole_source": True, "competition_type": "sole_source"}
        result = self.chain.generate(
            "pkg-002", params,
            skip_base_pipeline=True,
        )
        self.assertIn("ja_approver", result.approval_summary)
        self.assertEqual(result.approval_summary["ja_approver"], "DHS CPO")  # $20M+


# ========================================================================
# Test Serialization
# ========================================================================

class TestSerialization(unittest.TestCase):
    """Test to_dict() serialization."""

    def test_chain_result_to_dict(self):
        chain = DocumentChainOrchestrator()
        result = chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        d = result.to_dict()
        self.assertIn("package_id", d)
        self.assertIn("supporting_docs", d)
        self.assertIn("full_ucf_assembly", d)
        self.assertIn("total_documents", d)
        self.assertIn("approval_summary", d)

    def test_supporting_docs_serializable(self):
        chain = DocumentChainOrchestrator()
        result = chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        d = result.to_dict()
        for doc_type, doc_dict in d["supporting_docs"].items():
            self.assertIn("doc_type", doc_dict)
            self.assertIn("sections", doc_dict)
            self.assertIn("generated_at", doc_dict)

    def test_ucf_assembly_serializable(self):
        chain = DocumentChainOrchestrator()
        result = chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        d = result.to_dict()
        for ucf in d["full_ucf_assembly"]:
            self.assertIn("ucf_section", ucf)
            self.assertIn("doc_type", ucf)
            self.assertIn("authority", ucf)


# ========================================================================
# Test Single Document Generation
# ========================================================================

class TestSingleDocument(unittest.TestCase):
    """Test generate_single() method."""

    def setUp(self):
        self.chain = DocumentChainOrchestrator()

    def test_generate_single_bcm(self):
        draft = self.chain.generate_single("bcm", {
            **_canonical_params(), "bcm_type": "pre_competitive"
        })
        self.assertIsInstance(draft, DocumentDraft)
        self.assertEqual(draft.doc_type, "bcm")

    def test_generate_single_ja(self):
        draft = self.chain.generate_single("ja", {
            **_canonical_params(), "justification_type": "sole_source"
        })
        self.assertEqual(draft.doc_type, "ja")
        self.assertEqual(len(draft.sections), 8)

    def test_generate_single_unknown(self):
        with self.assertRaises(ValueError):
            self.chain.generate_single("nonexistent", {})


# ========================================================================
# Test list_available_doc_types
# ========================================================================

class TestListDocTypes(unittest.TestCase):

    def test_returns_all_10(self):
        types = DocumentChainOrchestrator.list_available_doc_types()
        self.assertEqual(len(types), 10)

    def test_each_has_description(self):
        types = DocumentChainOrchestrator.list_available_doc_types()
        for t in types:
            self.assertIn("doc_type", t)
            self.assertIn("description", t)
            self.assertGreater(len(t["description"]), 10)


# ========================================================================
# Test UCF Map Coverage
# ========================================================================

class TestUCFMapCoverage(unittest.TestCase):

    def test_all_engines_mapped(self):
        """Every document engine should have a UCF mapping."""
        for dt in DOCUMENT_ENGINES:
            self.assertIn(dt, SUPPORT_DOC_UCF_MAP, f"{dt} missing from UCF map")

    def test_ucf_sections_valid(self):
        """All mapped UCF sections should be valid."""
        for dt, (section, auth) in SUPPORT_DOC_UCF_MAP.items():
            self.assertIsInstance(section, UCFSection)
            self.assertTrue(auth, f"{dt} missing authority")


# ========================================================================
# Test Version Store Integration
# ========================================================================

class TestVersionStoreIntegration(unittest.TestCase):

    def test_supporting_docs_versioned(self):
        """Supporting docs should be saved to version store."""
        vs = VersionStore()
        chain = DocumentChainOrchestrator(version_store=vs)
        result = chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
        )
        # Check that at least one version was saved
        count = vs.version_count("pkg-001", PipelineStage.PWS)
        self.assertGreater(count, 0)


# ========================================================================
# Test Edge Cases
# ========================================================================

class TestEdgeCases(unittest.TestCase):

    def setUp(self):
        self.chain = DocumentChainOrchestrator()

    def test_invalid_doc_type_in_list(self):
        """Invalid doc types in doc_types list should warn, not crash."""
        result = self.chain.generate(
            "pkg-001", _canonical_params(),
            skip_base_pipeline=True,
            doc_types=["bcm", "nonexistent_type"],
        )
        # bcm should succeed, nonexistent should produce warning
        self.assertIn("bcm", result.supporting_docs)
        self.assertNotIn("nonexistent_type", result.supporting_docs)

    def test_micro_purchase_chain(self):
        """Micro-purchase should produce minimal chain."""
        params = {
            "estimated_value": 10_000,
            "services": True,
            "is_it": False,
            "contract_type": "FFP",
            "competition_type": "full_and_open",
            "value": 10_000,
        }
        result = self.chain.generate(
            "pkg-micro", params,
            skip_base_pipeline=True,
        )
        # Should NOT have SB review (under $100K)
        self.assertNotIn("sb_review", result.supporting_docs)
        # Should still have BCM and SSP
        self.assertIn("bcm", result.supporting_docs)

    def test_empty_params(self):
        """Empty params should not crash."""
        result = self.chain.generate(
            "pkg-empty", {"estimated_value": 0, "value": 0},
            skip_base_pipeline=True,
        )
        self.assertIsInstance(result, ChainResult)


if __name__ == "__main__":
    unittest.main()
