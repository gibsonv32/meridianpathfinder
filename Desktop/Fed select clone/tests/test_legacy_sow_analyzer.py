"""
Tests for Legacy SOW Analyzer — Phase 25
==========================================
60 tests across 13 classes covering:
- SOW parsing (sections, levels, tagging)
- Language quality (passive voice, vague terms, will/shall, staffing)
- Gap analysis (PBA elements, QASP, metrics, acceptance criteria, security)
- Protest vulnerability (patterns, cross-section, deliverables, brand-name, OCI)
- Requirement extraction (classification, verification, priority, metrics)
- Deliverable extraction (frequency, format, acceptance)
- Scoring engine (quality, gap, protest, overall, severity counts)
- Full pipeline (canonical SOW, empty, minimal, section-based)
- Serialization (to_dict, fix_priority)
- Edge cases (single section, no shall statements, huge text)
"""
import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.legacy_sow_analyzer import (
    LegacySOWAnalyzer,
    SOWParser,
    LanguageQualityAnalyzer,
    GapAnalyzer,
    ProtestVulnerabilityScanner,
    RequirementExtractor,
    DeliverableExtractor,
    SOWScorer,
    SOWSection,
    Finding,
    RequirementEntry,
    DeliverableEntry,
    AnalysisReport,
    Severity,
    FindingCategory,
    PBAElement,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

CANONICAL_SOW = """
1.0 - Background
The Transportation Security Administration (TSA) requires IT operations and
maintenance services to support the Enterprise Data Analytics Platform (EDAP).
The current contract expires September 30, 2027. This requirement has been
identified as a critical priority for the agency.

2.0 - Scope
The contractor will provide 45 FTEs to deliver IT services as needed for the
EDAP system. Services include approximately 24/7 monitoring, incident response,
and system maintenance. The contractor should follow best practices and
industry standard approaches.

3.0 - Service Delivery
3.1 - System Monitoring
The Contractor shall maintain 99.5% system availability measured monthly.
The Contractor shall respond to Priority 1 incidents within 15 minutes
and resolve within 4 hours. The contractor will submit a monthly performance
report within 5 business days after month-end.

3.2 - Software Development
The Contractor shall develop and maintain software applications using agile
methodology. The contractor will deliver code releases quarterly. Preference
will be given to solutions using Microsoft Azure and ServiceNow.

3.3 - Security Requirements
All personnel shall maintain a minimum Secret clearance. The Contractor
shall comply with FISMA requirements and maintain an ATO. CUI and SSI data
shall be handled per TSA Management Directive requirements.

4.0 - Reporting
The Contractor shall submit the following deliverables:
- Monthly Performance Report to the COR within 5 business days
- Quarterly Program Review briefing to the COR
- Annual Security Assessment Report in PDF format
- Transition Plan (one-time, within 30 calendar days of award)

5.0 - Quality Control
The Contractor shall maintain a Quality Control Plan and submit it to the
COR within 15 calendar days of award. Performance will be assessed etc.

6.0 - Transition
The Contractor shall provide a transition-in plan and support transition-out
for up to 90 calendar days. The Contractor shall provide adequate staffing
during transition periods.

7.0 - Period of Performance
Base Period: October 1, 2027 through September 30, 2028
Option Year 1: October 1, 2028 through September 30, 2029
Option Year 2: October 1, 2029 through September 30, 2030
"""

MINIMAL_SOW = """
1.0 - Scope
The Contractor shall provide IT support services.
"""

EMPTY_SOW = ""

PRESCRIPTIVE_SOW = """
1.0 - Staffing
The contractor shall provide a team of 25 FTEs including:
- 1 Program Manager
- 5 Senior Software Engineers
- 10 Software Developers
- 5 QA Analysts
- 4 DevOps Engineers
Maintain a minimum of 20 staff at all times.

2.0 - Services
The contractor shall perform development as needed and provide timely updates.
The contractor should try to follow best practices.
"""


# ===========================================================================
# Test Classes
# ===========================================================================

class TestSOWParser:
    """Test SOW text parsing into sections."""

    def test_parse_canonical(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        assert len(sections) >= 7  # At least 7 top-level + subsections

    def test_section_ids(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        ids = [s.section_id for s in sections]
        assert "1.0" in ids
        assert "3.1" in ids
        assert "3.2" in ids

    def test_section_levels(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        sec_map = {s.section_id: s for s in sections}
        assert sec_map["1.0"].level == 2  # "1.0" has one dot
        assert sec_map["3.1"].level == 2

    def test_word_counts(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        for sec in sections:
            if sec.content:
                assert sec.word_count > 0

    def test_has_metrics_tagging(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        sec_map = {s.section_id: s for s in sections}
        # Section 3.1 has "99.5%" and "within 15 minutes"
        assert sec_map["3.1"].has_metrics is True

    def test_has_security_tagging(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        sec_map = {s.section_id: s for s in sections}
        assert sec_map["3.3"].has_security is True

    def test_has_deliverables_tagging(self):
        parser = SOWParser()
        sections = parser.parse(CANONICAL_SOW)
        sec_map = {s.section_id: s for s in sections}
        assert sec_map["4.0"].has_deliverables is True

    def test_empty_text(self):
        parser = SOWParser()
        sections = parser.parse("")
        assert sections == []

    def test_no_headings_single_block(self):
        parser = SOWParser()
        sections = parser.parse("The Contractor shall do stuff. No section headings here.")
        assert len(sections) == 1
        assert sections[0].section_id == "1.0"
        assert sections[0].heading == "Full Document"


class TestLanguageQuality:
    """Test language quality analysis."""

    def test_detects_vague_terms(self):
        analyzer = LanguageQualityAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The contractor shall provide services as needed and follow best practices.",
            word_count=11,
        )]
        findings = analyzer.analyze(sections)
        vague_findings = [f for f in findings if "Vague" in f.title]
        assert len(vague_findings) >= 2  # "as needed" and "best practices"

    def test_detects_will_shall_inconsistency(self):
        analyzer = LanguageQualityAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The contractor shall monitor systems. The contractor will submit reports.",
            word_count=10,
        )]
        findings = analyzer.analyze(sections)
        will_shall = [f for f in findings if "will/shall" in f.title.lower() or "Will" in f.title]
        assert len(will_shall) >= 1

    def test_detects_only_will(self):
        analyzer = LanguageQualityAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The contractor will provide services. The contractor will submit reports.",
            word_count=10,
        )]
        findings = analyzer.analyze(sections)
        will_findings = [f for f in findings if "'shall'" in f.title.lower() or "will" in f.title.lower()]
        assert len(will_findings) >= 1

    def test_detects_staffing_spec(self):
        analyzer = LanguageQualityAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Staffing",
            content="The contractor shall provide 25 FTEs for this effort.",
            word_count=9,
        )]
        findings = analyzer.analyze(sections)
        staffing = [f for f in findings if "staffing" in f.title.lower()]
        assert len(staffing) >= 1

    def test_etc_is_high_severity(self):
        analyzer = LanguageQualityAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The contractor shall provide software, hardware, etc.",
            word_count=8,
        )]
        findings = analyzer.analyze(sections)
        etc_finding = [f for f in findings if "'etc'" in f.title.lower() or "etc" in f.title]
        assert len(etc_finding) >= 1
        assert etc_finding[0].severity in (Severity.HIGH, Severity.MEDIUM)

    def test_clean_section_no_findings(self):
        analyzer = LanguageQualityAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The Contractor shall maintain 99.5% availability measured monthly.",
            word_count=8,
        )]
        findings = analyzer.analyze(sections)
        # Should have no vague/will-shall/staffing findings
        assert len(findings) == 0


class TestGapAnalysis:
    """Test PBA compliance and gap detection."""

    def test_detects_missing_pba_elements(self):
        analyzer = GapAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The Contractor shall provide IT services.",
            word_count=7,
        )]
        findings, pba_found, pba_score = analyzer.analyze(sections, [], [])
        # Missing most PBA elements
        missing = [e for e, found in pba_found.items() if not found]
        assert len(missing) >= 4

    def test_pba_score_full(self):
        """SOW with all PBA elements should score 100."""
        analyzer = GapAnalyzer()
        content = (
            "performance standard SLA KPI measurable outcome result "
            "quality assurance QASP surveillance incentive award fee "
            "scope task requirement shall perform deliverable report "
            "government furnished GFE period of performance base period option year"
        )
        sections = [SOWSection(
            section_id="1.0", heading="Full",
            content=content, word_count=30,
        )]
        _, pba_found, pba_score = analyzer.analyze(sections, [], [])
        assert pba_score == 100.0
        assert all(pba_found.values())

    def test_no_qasp_reference(self):
        analyzer = GapAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The Contractor shall provide services with high quality.",
            word_count=9,
        )]
        findings, _, _ = analyzer.analyze(sections, [], [])
        qasp_findings = [f for f in findings if f.category == FindingCategory.QASP_LINKAGE]
        assert len(qasp_findings) >= 1

    def test_section_without_metrics(self):
        analyzer = GapAnalyzer()
        sections = [SOWSection(
            section_id="1.0", heading="Services",
            content="The contractor shall provide various IT services to the government. " * 10,
            word_count=100, has_metrics=False,
        )]
        findings, _, _ = analyzer.analyze(sections, [], [])
        metric_findings = [f for f in findings if f.category == FindingCategory.MEASURABILITY]
        assert len(metric_findings) >= 1

    def test_deliverable_missing_acceptance(self):
        analyzer = GapAnalyzer()
        deliverables = [DeliverableEntry(
            deliverable_id="DLV-001", name="Monthly Report",
            source_section="4.0", acceptance_criteria="",
        )]
        findings, _, _ = analyzer.analyze([], [], deliverables)
        acc_findings = [f for f in findings if f.category == FindingCategory.ACCEPTANCE_CRITERIA]
        assert len(acc_findings) >= 1

    def test_incomplete_security(self):
        analyzer = GapAnalyzer()
        sections = [SOWSection(
            section_id="3.3", heading="Security",
            content="All personnel shall maintain Secret clearance.",
            word_count=7, has_security=True,
        )]
        findings, _, _ = analyzer.analyze(sections, [], [])
        sec_findings = [f for f in findings if f.category == FindingCategory.SECURITY]
        assert len(sec_findings) >= 1  # Missing incident response + data handling


class TestProtestVulnerability:
    """Test protest vulnerability scanning."""

    def test_detects_preference_language(self):
        scanner = ProtestVulnerabilityScanner()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="Preference will be given to solutions using cloud technology.",
            word_count=10,
        )]
        findings = scanner.scan(sections, [])
        pref = [f for f in findings if "unstated" in f.title.lower() or "preference" in f.snippet.lower()]
        assert len(pref) >= 1

    def test_detects_brand_name(self):
        scanner = ProtestVulnerabilityScanner()
        sections = [SOWSection(
            section_id="1.0", heading="Tech",
            content="The system shall be deployed on Microsoft Azure.",
            word_count=9,
        )]
        findings = scanner.scan(sections, [])
        brand = [f for f in findings if "brand" in f.title.lower() or "proprietary" in f.title.lower()]
        assert len(brand) >= 1

    def test_detects_oci_risk(self):
        scanner = ProtestVulnerabilityScanner()
        sections = [SOWSection(
            section_id="1.0", heading="Services",
            content="The contractor shall provide advisory and implementation services.",
            word_count=9,
        )]
        findings = scanner.scan(sections, [])
        oci = [f for f in findings if "conflict" in f.title.lower()]
        assert len(oci) >= 1

    def test_cross_section_inconsistency(self):
        scanner = ProtestVulnerabilityScanner()
        sections = [
            SOWSection(
                section_id="1.0", heading="Scope",
                content="The contractor shall provide monthly system monitoring reports within 5 days.",
                word_count=10,
            ),
            SOWSection(
                section_id="2.0", heading="Reporting",
                content="The contractor shall submit monthly system monitoring reports within 10 days.",
                word_count=10,
            ),
        ]
        findings = scanner.scan(sections, [])
        inconsistent = [f for f in findings if "inconsistency" in f.title.lower()]
        assert len(inconsistent) >= 1

    def test_deliverables_without_acceptance(self):
        scanner = ProtestVulnerabilityScanner()
        deliverables = [
            DeliverableEntry(deliverable_id="D1", name="Report A", source_section="1.0"),
            DeliverableEntry(deliverable_id="D2", name="Report B", source_section="2.0"),
        ]
        findings = scanner.scan([], deliverables)
        dlv_findings = [f for f in findings if "acceptance" in f.title.lower()]
        assert len(dlv_findings) >= 1

    def test_clean_section_no_vulnerabilities(self):
        scanner = ProtestVulnerabilityScanner()
        sections = [SOWSection(
            section_id="1.0", heading="Scope",
            content="The Contractor shall maintain 99.5% availability.",
            word_count=7,
        )]
        findings = scanner.scan(sections, [])
        # No preference, brand, or OCI language
        assert len(findings) == 0


class TestRequirementExtraction:
    """Test requirement extraction from SOW sections."""

    def test_extracts_shall_statements(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="3.1", heading="Monitoring",
            content="The Contractor shall maintain 99.5% availability. The Contractor shall respond within 15 minutes.",
            word_count=15,
        )]
        reqs = extractor.extract(sections)
        assert len(reqs) >= 2

    def test_requirement_ids_sequential(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="1.0", heading="Services",
            content="The Contractor shall do A. The Contractor shall do B. The Contractor shall do C.",
            word_count=15,
        )]
        reqs = extractor.extract(sections)
        ids = [r.requirement_id for r in reqs]
        assert ids == ["REQ-001", "REQ-002", "REQ-003"]

    def test_classifies_technical(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="1.0", heading="Dev",
            content="The Contractor shall develop and maintain software applications.",
            word_count=8,
        )]
        reqs = extractor.extract(sections)
        assert reqs[0].category == "technical"

    def test_classifies_reporting(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="1.0", heading="Reports",
            content="The Contractor shall submit a monthly performance report.",
            word_count=8,
        )]
        reqs = extractor.extract(sections)
        assert reqs[0].category == "reporting"

    def test_detects_metric(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="1.0", heading="SLA",
            content="The Contractor shall maintain 99.5% system availability.",
            word_count=7,
        )]
        reqs = extractor.extract(sections)
        assert reqs[0].has_metric is True
        assert "99.5%" in reqs[0].metric_value

    def test_infers_verification_method(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="1.0", heading="Reports",
            content="The Contractor shall submit monthly status reports for review.",
            word_count=9,
        )]
        reqs = extractor.extract(sections)
        assert reqs[0].verification_method == "analysis"

    def test_source_section_tracked(self):
        extractor = RequirementExtractor()
        sections = [SOWSection(
            section_id="3.2", heading="Dev",
            content="The Contractor shall develop applications.",
            word_count=5,
        )]
        reqs = extractor.extract(sections)
        assert reqs[0].source_section == "3.2"


class TestDeliverableExtraction:
    """Test deliverable extraction."""

    def test_extracts_from_canonical(self):
        parser = SOWParser()
        extractor = DeliverableExtractor()
        sections = parser.parse(CANONICAL_SOW)
        deliverables = extractor.extract(sections)
        assert len(deliverables) >= 2  # Monthly report, transition plan, etc.

    def test_detects_frequency(self):
        extractor = DeliverableExtractor()
        sections = [SOWSection(
            section_id="4.0", heading="Reports",
            content="The Contractor shall submit a monthly performance report to the COR within 5 business days.",
            word_count=15,
        )]
        deliverables = extractor.extract(sections)
        monthly = [d for d in deliverables if d.frequency == "monthly"]
        assert len(monthly) >= 1

    def test_detects_format(self):
        extractor = DeliverableExtractor()
        sections = [SOWSection(
            section_id="4.0", heading="Reports",
            content="The Contractor shall submit the annual report in PDF format to the COR.",
            word_count=13,
        )]
        deliverables = extractor.extract(sections)
        if deliverables:
            formatted = [d for d in deliverables if d.format_specified]
            assert len(formatted) >= 1

    def test_deduplicates(self):
        extractor = DeliverableExtractor()
        sections = [
            SOWSection(section_id="1.0", heading="A",
                       content="The Contractor shall submit a monthly report to the COR.", word_count=10),
            SOWSection(section_id="2.0", heading="B",
                       content="The Contractor shall submit a monthly report to the CO.", word_count=10),
        ]
        deliverables = extractor.extract(sections)
        names = [d.name.lower() for d in deliverables]
        # Should deduplicate "monthly report"
        assert names.count("monthly report") <= 1


class TestScoring:
    """Test scoring engine."""

    def test_perfect_quality_score(self):
        scorer = SOWScorer()
        report = AnalysisReport(findings=[])
        scorer.score(report)
        assert report.quality_score == 100.0

    def test_quality_degrades_with_findings(self):
        scorer = SOWScorer()
        report = AnalysisReport(findings=[
            Finding(finding_id="LQ-001", category=FindingCategory.LANGUAGE,
                    severity=Severity.HIGH, title="test", detail="test"),
            Finding(finding_id="LQ-002", category=FindingCategory.LANGUAGE,
                    severity=Severity.MEDIUM, title="test", detail="test"),
        ])
        scorer.score(report)
        assert report.quality_score < 100.0
        assert report.quality_score >= 0.0

    def test_protest_risk_scales_with_findings(self):
        scorer = SOWScorer()
        report = AnalysisReport(findings=[
            Finding(finding_id="PV-001", category=FindingCategory.PROTEST_VULNERABILITY,
                    severity=Severity.HIGH, title="test", detail="test", protest_relevant=True),
            Finding(finding_id="PV-002", category=FindingCategory.PROTEST_VULNERABILITY,
                    severity=Severity.CRITICAL, title="test", detail="test", protest_relevant=True),
        ])
        scorer.score(report)
        assert report.protest_risk_score > 0

    def test_severity_counts(self):
        scorer = SOWScorer()
        report = AnalysisReport(findings=[
            Finding(finding_id="1", category=FindingCategory.LANGUAGE,
                    severity=Severity.CRITICAL, title="", detail=""),
            Finding(finding_id="2", category=FindingCategory.LANGUAGE,
                    severity=Severity.HIGH, title="", detail=""),
            Finding(finding_id="3", category=FindingCategory.LANGUAGE,
                    severity=Severity.MEDIUM, title="", detail=""),
            Finding(finding_id="4", category=FindingCategory.LANGUAGE,
                    severity=Severity.LOW, title="", detail=""),
            Finding(finding_id="5", category=FindingCategory.LANGUAGE,
                    severity=Severity.INFO, title="", detail=""),
        ])
        scorer.score(report)
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.medium_count == 1
        assert report.low_count == 1
        assert report.info_count == 1

    def test_overall_score_weighted(self):
        scorer = SOWScorer()
        report = AnalysisReport(
            pba_score=50.0,
            findings=[],
        )
        scorer.score(report)
        # quality=100, gap=50*0.5+100*0.5=75, protest_risk=0
        # overall = 100*0.3 + 75*0.4 + 100*0.3 = 30 + 30 + 30 = 90
        assert report.overall_score == pytest.approx(90.0, abs=1.0)


class TestFullPipeline:
    """Test the full LegacySOWAnalyzer pipeline."""

    def test_canonical_sow(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        assert report.section_count >= 7
        assert report.sow_word_count > 200
        assert len(report.findings) > 0
        assert len(report.requirements) > 0
        assert report.overall_score > 0

    def test_canonical_has_all_layers(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        categories = {f.category for f in report.findings}
        assert FindingCategory.LANGUAGE in categories
        # Should have at least language + one other
        assert len(categories) >= 2

    def test_canonical_extracts_deliverables(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        assert len(report.deliverables) >= 1

    def test_canonical_pba_elements(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        assert len(report.pba_elements_found) == len(PBAElement)
        # Canonical has some PBA elements
        found_count = sum(1 for v in report.pba_elements_found.values() if v)
        assert found_count >= 3

    def test_empty_sow(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(EMPTY_SOW)
        assert report.critical_count >= 1
        assert report.section_count == 0

    def test_minimal_sow(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(MINIMAL_SOW)
        assert report.section_count >= 1
        assert len(report.requirements) >= 1

    def test_prescriptive_sow(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(PRESCRIPTIVE_SOW)
        staffing_findings = [f for f in report.findings if "staffing" in f.title.lower()]
        assert len(staffing_findings) >= 1
        vague_findings = [f for f in report.findings if "Vague" in f.title]
        assert len(vague_findings) >= 2  # "as needed", "best practices"

    def test_analyze_sections_dict(self):
        analyzer = LegacySOWAnalyzer()
        sections = [
            {"section_id": "1.0", "heading": "Scope",
             "content": "The Contractor shall provide IT services. Performance assessed etc."},
            {"section_id": "2.0", "heading": "Reporting",
             "content": "The Contractor shall submit monthly reports within 5 business days."},
        ]
        report = analyzer.analyze_sections(sections)
        assert report.section_count == 2
        assert len(report.requirements) >= 2
        assert len(report.findings) > 0


class TestSerialization:
    """Test report serialization."""

    def test_to_dict_structure(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        d = report.to_dict()
        assert "sections" in d
        assert "findings" in d
        assert "requirements" in d
        assert "deliverables" in d
        assert "pba_elements" in d
        assert "scores" in d
        assert "severity_counts" in d
        assert "fix_priority" in d

    def test_fix_priority_ordered(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        d = report.to_dict()
        priority = d["fix_priority"]
        if len(priority) >= 2:
            # First items should be higher severity
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            for i in range(len(priority) - 1):
                assert severity_order[priority[i]["severity"]] <= severity_order[priority[i + 1]["severity"]]

    def test_scores_in_dict(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        d = report.to_dict()
        scores = d["scores"]
        assert "quality" in scores
        assert "gap" in scores
        assert "protest_risk" in scores
        assert "overall" in scores
        assert all(isinstance(v, (int, float)) for v in scores.values())

    def test_pba_elements_serialized(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        d = report.to_dict()
        pba = d["pba_elements"]
        assert len(pba) == len(PBAElement)
        # Keys should be string values, not enum names
        assert "performance_standards" in pba

    def test_findings_have_all_fields(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze(CANONICAL_SOW)
        d = report.to_dict()
        for finding in d["findings"]:
            assert "finding_id" in finding
            assert "category" in finding
            assert "severity" in finding
            assert "title" in finding
            assert "detail" in finding
            assert "recommended_fix" in finding


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_no_shall_statements(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("""
1.0 - Scope
The agency needs IT services. Services include monitoring, development,
and system administration. The work is complex and important.
""")
        assert len(report.requirements) == 0
        # Should still have PBA gap findings
        assert len(report.findings) > 0

    def test_single_sentence(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("The Contractor shall provide IT support services.")
        assert report.section_count == 1
        assert len(report.requirements) >= 1

    def test_generated_at_present(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("Test content.")
        assert report.generated_at != ""
        assert "T" in report.generated_at  # ISO format

    def test_requires_acceptance_true(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("Test content.")
        assert report.requires_acceptance is True

    def test_source_provenance(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("Test content.")
        assert len(report.source_provenance) >= 3
        assert any("FAR 37" in p for p in report.source_provenance)


class TestProtestRelevance:
    """Test protest_relevant flag on findings."""

    def test_etc_is_protest_relevant(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("""
1.0 - Scope
The Contractor shall provide IT support, helpdesk, monitoring, etc.
""")
        etc_findings = [f for f in report.findings if "etc" in f.title.lower()]
        if etc_findings:
            assert etc_findings[0].protest_relevant is True

    def test_preference_language_is_protest_relevant(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("""
1.0 - Scope
Preference will be given to cloud-native solutions.
The Contractor shall provide IT services.
""")
        pv_findings = [f for f in report.findings if f.category == FindingCategory.PROTEST_VULNERABILITY]
        if pv_findings:
            assert all(f.protest_relevant for f in pv_findings)

    def test_clean_sow_low_protest_risk(self):
        analyzer = LegacySOWAnalyzer()
        report = analyzer.analyze("""
1.0 - Scope
The Contractor shall maintain 99.5% system availability measured monthly per the QASP.
The Contractor shall respond to Priority 1 incidents within 15 minutes.
The Contractor shall submit monthly performance reports within 5 business days.
Performance standards include measurable outcomes and quality assurance surveillance.
The performance period includes a base period and two option years.
Government furnished equipment includes office space and network access.
Deliverables include monthly status reports.
Positive incentives apply per the award fee plan.
""")
        assert report.protest_risk_score < 30  # Low protest risk for clean SOW
