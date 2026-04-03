"""
Tests for Requirements Elicitation Agent — Phase 24
====================================================
Comprehensive test coverage for guided intake, parameter derivation,
requirements generation, validation, legacy SOW import, and orchestration.

57 tests across 12 classes.
"""
import pytest
from backend.core.requirements_elicitation import (
    # Enums
    RequirementCategory, RequirementPriority, VerificationMethod,
    QuestionGroupID, IntakeStatus,
    # Constants
    INTAKE_QUESTIONS, QUESTION_INDEX, GROUP_ORDER, GROUP_NAMES,
    APPROVAL_CHAINS, SSA_APPOINTMENTS,
    # Data classes
    IntakeQuestion, Requirement, DeliverableSpec, PolicyDerivation,
    ValidationIssue, RequirementsPackage,
    # Engines
    IntakeEngine, ParameterDeriver, RequirementsGenerator,
    RequirementsValidator, LegacySOWImporter, RequirementsElicitationAgent,
    # Functions
    derive_approval_chain, derive_ssa, derive_posting_requirement,
    derive_estimated_timeline,
)


# ---------------------------------------------------------------------------
# Fixtures — Canonical $20M TSA IT Services Answers
# ---------------------------------------------------------------------------

def _canonical_answers() -> dict:
    """Full $20M TSA IT services answer set."""
    return {
        "BI-01": "TSA IT Infrastructure Support",
        "BI-02": 20_000_000,
        "BI-03": "services",
        "BI-04": True,
        "BI-05": "541512",
        "BI-06": "FFP",
        "BI-07": "recompete",
        "BI-08": "full_and_open",
        "SD-01": "Support TSA IT infrastructure and cybersecurity operations.",
        "SD-02": "Network management, help desk, cybersecurity monitoring, cloud services.",
        "SD-03": "mixed",
        "SD-04": "1 base + 4 option years",
        "SD-05": True,
        "TR-01": "Maintain 99.5% network availability; Respond to P1 tickets within 15 minutes",
        "TR-02": "SIEM, ServiceNow, AWS GovCloud, Active Directory",
        "TR-03": True,
        "TR-04": "99.5% availability, 24/7 monitoring",
        "MR-01": True,
        "MR-02": True,
        "MR-03": "monthly",
        "SR-01": "secret",
        "SR-02": True,
        "SR-03": True,
        "SR-04": True,
        "SR-05": True,
        "PR-01": "Program Manager, Senior Engineer, Help Desk Analyst",
        "PR-02": "PMP, CISSP, 10 years PM, 5 years senior",
        "DL-01": "Monthly Status Report; Incident Reports; Transition Plan",
        "DL-02": "5_business_days",
        "PS-01": "99.5% system availability; P1 tickets resolved within 4 hours; Monthly report within 5 business days",
        "PS-02": "payment_deductions",
        "TN-01": True,
        "TN-02": "90_days",
        "CN-01": False,
        "CN-02": False,
        "CN-03": True,
    }


def _minimal_answers() -> dict:
    """Minimal valid answer set — micro-purchase, no frills."""
    return {
        "BI-01": "Office Supplies",
        "BI-02": 5000,
        "BI-03": "supplies",
        "BI-04": False,
        "BI-06": "FFP",
        "BI-07": "new",
        "BI-08": "full_and_open",
        "SD-02": "Office supplies and furniture.",
    }


def _mock_sow_analysis() -> dict:
    """Mock output from LegacySOWAnalyzer().analyze().to_dict()."""
    return {
        "sections": [
            {"section_id": "1.0", "title": "Background", "content": "TSA background...", "has_security": True},
            {"section_id": "3.0", "title": "Service Delivery", "content": "The contractor shall provide IT support.", "has_security": False},
        ],
        "requirements": [
            {
                "text": "The contractor shall maintain 99.5% uptime",
                "category": "technical",
                "priority": "critical",
                "verification_method": "analysis",
                "acceptance_criteria": "Verified via monthly uptime report",
                "metric_value": "99.5% uptime",
                "has_metric": True,
                "source_section": "3.0",
            },
            {
                "text": "The contractor shall submit monthly status reports",
                "category": "reporting",
                "priority": "standard",
                "verification_method": "inspection",
                "acceptance_criteria": "",
                "metric_value": "",
                "has_metric": False,
                "source_section": "4.0",
            },
        ],
        "deliverables": [
            {
                "name": "Monthly Status Report",
                "frequency": "monthly",
                "format_specified": True,
                "review_period": "5 business days",
                "approval_authority": "COR",
                "acceptance_criteria": "Covers all performance metrics",
                "source_section": "4.0",
            },
        ],
        "pba_elements": {
            "performance_standards": True,
            "measurable_outcomes": True,
            "quality_assurance": True,
            "performance_incentives": False,
            "work_requirements": True,
            "government_furnished": False,
            "deliverables": True,
            "period_of_performance": True,
        },
        "scores": {"quality": 65, "gap": 55, "protest_risk": 30, "overall": 55.5},
        "severity_counts": {"critical": 1, "high": 3, "medium": 2, "low": 1},
    }


# ===========================================================================
# Test Classes
# ===========================================================================


class TestIntakeQuestions:
    """Test question structure and indexing."""

    def test_question_count(self):
        assert len(INTAKE_QUESTIONS) == 36

    def test_all_groups_covered(self):
        groups = {q.group for q in INTAKE_QUESTIONS}
        for g in GROUP_ORDER:
            assert g in groups, f"Group {g.value} has no questions"

    def test_question_index_complete(self):
        assert len(QUESTION_INDEX) == 36
        for q in INTAKE_QUESTIONS:
            assert q.question_id in QUESTION_INDEX

    def test_unique_question_ids(self):
        ids = [q.question_id for q in INTAKE_QUESTIONS]
        assert len(ids) == len(set(ids)), "Duplicate question IDs"

    def test_group_order_has_10_groups(self):
        assert len(GROUP_ORDER) == 10

    def test_group_names_complete(self):
        for g in GROUP_ORDER:
            assert g in GROUP_NAMES


class TestIntakeEngine:
    """Test IntakeEngine question management and validation."""

    def setup_method(self):
        self.engine = IntakeEngine()

    def test_get_questions_for_group(self):
        basic = self.engine.get_questions_for_group(QuestionGroupID.BASIC_INFO)
        assert len(basic) == 8  # BI-01 through BI-08

    def test_get_all_groups(self):
        groups = self.engine.get_all_groups()
        assert len(groups) == 10
        assert groups[0]["group_id"] == "basic_info"
        assert groups[0]["order"] == 0

    def test_get_next_group_none_completed(self):
        g = self.engine.get_next_group([])
        assert g == QuestionGroupID.BASIC_INFO

    def test_get_next_group_some_completed(self):
        g = self.engine.get_next_group(["basic_info", "scope_definition"])
        assert g == QuestionGroupID.TECHNICAL_REQUIREMENTS

    def test_get_next_group_all_completed(self):
        all_groups = [g.value for g in GROUP_ORDER]
        g = self.engine.get_next_group(all_groups)
        assert g is None

    def test_validate_answer_required_empty(self):
        ok, msg = self.engine.validate_answer("BI-01", "")
        assert not ok
        assert "required" in msg.lower()

    def test_validate_answer_required_none(self):
        ok, msg = self.engine.validate_answer("BI-01", None)
        assert not ok

    def test_validate_answer_valid_text(self):
        ok, msg = self.engine.validate_answer("BI-01", "IT Support")
        assert ok
        assert msg == ""

    def test_validate_answer_number_valid(self):
        ok, _ = self.engine.validate_answer("BI-02", 20000000)
        assert ok

    def test_validate_answer_number_invalid(self):
        ok, msg = self.engine.validate_answer("BI-02", "not a number")
        assert not ok
        assert "numeric" in msg.lower()

    def test_validate_answer_boolean(self):
        ok, _ = self.engine.validate_answer("BI-04", True)
        assert ok
        ok, msg = self.engine.validate_answer("BI-04", "yes")
        assert not ok
        assert "true/false" in msg.lower()

    def test_validate_answer_select_valid(self):
        ok, _ = self.engine.validate_answer("BI-03", "services")
        assert ok

    def test_validate_answer_select_invalid(self):
        ok, msg = self.engine.validate_answer("BI-03", "invalid_option")
        assert not ok
        assert "must be one of" in msg.lower()

    def test_validate_answer_regex(self):
        ok, _ = self.engine.validate_answer("BI-05", "541512")
        assert ok
        ok, msg = self.engine.validate_answer("BI-05", "ABC")
        assert not ok
        assert "format" in msg.lower()

    def test_validate_answer_unknown_question(self):
        ok, msg = self.engine.validate_answer("FAKE-99", "whatever")
        assert not ok
        assert "unknown" in msg.lower()

    def test_validate_optional_field_empty(self):
        # TR-04 is not required
        ok, _ = self.engine.validate_answer("TR-04", "")
        assert ok  # Optional fields can be empty

    def test_group_completeness_full(self):
        answers = _canonical_answers()
        pct = self.engine.compute_group_completeness(QuestionGroupID.BASIC_INFO, answers)
        assert pct == 100.0

    def test_group_completeness_partial(self):
        answers = {"BI-01": "Test", "BI-02": 1000}
        pct = self.engine.compute_group_completeness(QuestionGroupID.BASIC_INFO, answers)
        assert 0 < pct < 100

    def test_overall_completeness(self):
        answers = _canonical_answers()
        pct = self.engine.compute_overall_completeness(answers)
        assert pct > 80  # Canonical set is mostly complete


class TestParameterDeriver:
    """Test answer-to-parameter mapping."""

    def setup_method(self):
        self.deriver = ParameterDeriver()

    def test_canonical_params(self):
        params = self.deriver.derive(_canonical_answers())
        assert params["value"] == 20_000_000
        assert params["services"] is True
        assert params["it_related"] is True
        assert params["sole_source"] is False
        assert params["commercial_item"] is False
        assert params["vendor_on_site"] is True  # mixed → True
        assert params["classified"] is True  # secret
        assert params["has_options"] is True  # "option" in POP text
        assert params["sub_agency"] == "TSA"

    def test_sole_source_flag(self):
        answers = _canonical_answers()
        answers["BI-08"] = "sole_source"
        params = self.deriver.derive(answers)
        assert params["sole_source"] is True

    def test_supplies_not_services(self):
        answers = _minimal_answers()
        params = self.deriver.derive(answers)
        assert params["services"] is False

    def test_remote_not_on_site(self):
        answers = _canonical_answers()
        answers["SD-03"] = "remote"
        params = self.deriver.derive(answers)
        assert params["vendor_on_site"] is False
        assert params["on_site"] is False

    def test_security_flags(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        assert params["handles_ssi"] is True
        assert params["has_cui"] is True
        assert params["requires_fedramp"] is True
        assert params["requires_badge"] is True

    def test_invalid_value_defaults_zero(self):
        answers = {"BI-02": "not_a_number"}
        params = self.deriver.derive(answers)
        assert params["value"] == 0


class TestRequirementsGenerator:
    """Test requirement generation from answers."""

    def setup_method(self):
        self.gen = RequirementsGenerator()
        self.deriver = ParameterDeriver()

    def test_canonical_generates_requirements(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        assert len(reqs) >= 8  # Technical + system + integration + availability + personnel + reporting + security + transition + QCP + GFE

    def test_sequential_ids(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        ids = [r.requirement_id for r in reqs]
        for i, rid in enumerate(ids):
            assert rid == f"REQ-{i+1:03d}"

    def test_technical_outcomes_split(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        tech_reqs = [r for r in reqs if "Technical Outcome" in r.title]
        assert len(tech_reqs) == 2  # Two semicolon-separated outcomes

    def test_system_support_generated(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        system_reqs = [r for r in reqs if "System Support" in r.title]
        assert len(system_reqs) == 1
        assert "SIEM" in system_reqs[0].description

    def test_integration_requirement(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        integration = [r for r in reqs if "Integration" in r.title]
        assert len(integration) == 1

    def test_security_clearance_requirement(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        security = [r for r in reqs if r.category == RequirementCategory.SECURITY]
        assert len(security) >= 3  # Clearance + SSI + FISMA

    def test_transition_requirements(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        transition = [r for r in reqs if r.category == RequirementCategory.TRANSITION]
        assert len(transition) == 2  # Transition-in + transition-out

    def test_qcp_generated_for_services(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        qcp = [r for r in reqs if "Quality Control Plan" in r.title]
        assert len(qcp) == 1
        assert qcp[0].far_reference == "FAR 46.2"

    def test_gfe_requirement(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        gfe = [r for r in reqs if "Government Furnished" in r.title]
        assert len(gfe) == 1
        assert gfe[0].far_reference == "FAR Part 45"

    def test_no_qcp_for_supplies(self):
        answers = _minimal_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        qcp = [r for r in reqs if "Quality Control Plan" in r.title]
        assert len(qcp) == 0

    def test_reporting_always_generated(self):
        answers = _minimal_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        reporting = [r for r in reqs if r.category == RequirementCategory.REPORTING]
        assert len(reporting) >= 1

    def test_performance_standard_sla_split(self):
        answers = _canonical_answers()
        params = self.deriver.derive(answers)
        reqs = self.gen.generate(answers, params)
        sla_reqs = [r for r in reqs if "Performance Standard" in r.title]
        assert len(sla_reqs) == 3  # Three semicolon-separated SLAs


class TestDeliverableGeneration:
    """Test deliverable generation."""

    def setup_method(self):
        self.gen = RequirementsGenerator()

    def test_canonical_deliverables(self):
        dlvs = self.gen.generate_deliverables(_canonical_answers())
        assert len(dlvs) >= 4  # Status + QCP + Transition + custom

    def test_status_report_always_generated(self):
        dlvs = self.gen.generate_deliverables(_minimal_answers())
        status = [d for d in dlvs if "Status Report" in d.name]
        assert len(status) >= 1

    def test_transition_plan_when_incumbent(self):
        dlvs = self.gen.generate_deliverables(_canonical_answers())
        transition = [d for d in dlvs if d.name == "Transition-In Plan"]
        assert len(transition) == 1
        assert transition[0].frequency == "one_time"

    def test_custom_deliverables_parsed(self):
        dlvs = self.gen.generate_deliverables(_canonical_answers())
        custom = [d for d in dlvs if d.source == "DL-01"]
        assert len(custom) >= 2  # "Incident Reports" and "Transition Plan" from DL-01

    def test_frequency_inference(self):
        gen = RequirementsGenerator()
        assert gen._infer_frequency("Monthly Status Report") == "monthly"
        assert gen._infer_frequency("Weekly Dashboard") == "weekly"
        assert gen._infer_frequency("Final Report") == "as_needed"
        assert gen._infer_frequency("Quarterly Review") == "quarterly"
        assert gen._infer_frequency("Annual Assessment") == "annually"


class TestRequirementsValidator:
    """Test validation checks."""

    def setup_method(self):
        self.agent = RequirementsElicitationAgent()

    def test_canonical_no_critical_issues(self):
        package = self.agent.process_answers(_canonical_answers())
        critical = [v for v in package.validation_issues if v.severity == "critical"]
        assert len(critical) == 0

    def test_missing_scope_triggers_critical(self):
        answers = _canonical_answers()
        del answers["SD-02"]
        package = self.agent.process_answers(answers)
        critical = [v for v in package.validation_issues if v.severity == "critical"]
        titles = [v.title for v in critical]
        assert any("No specific services" in t for t in titles)

    def test_key_personnel_warning_20m(self):
        answers = _canonical_answers()
        answers["MR-01"] = False
        package = self.agent.process_answers(answers)
        kp_issues = [v for v in package.validation_issues if "key personnel" in v.title.lower()]
        assert len(kp_issues) == 1

    def test_tm_high_value_warning(self):
        answers = _canonical_answers()
        answers["BI-06"] = "T&M"
        package = self.agent.process_answers(answers)
        tm_issues = [v for v in package.validation_issues if "T&M" in v.title]
        assert len(tm_issues) == 1
        assert tm_issues[0].far_reference == "FAR 16.601(d)"

    def test_services_without_slas(self):
        answers = _canonical_answers()
        del answers["PS-01"]
        package = self.agent.process_answers(answers)
        sla_issues = [v for v in package.validation_issues if "performance standards" in v.title.lower()]
        assert len(sla_issues) == 1

    def test_it_without_fisma(self):
        answers = _canonical_answers()
        answers["SR-04"] = False
        package = self.agent.process_answers(answers)
        fisma_issues = [v for v in package.validation_issues if "FISMA" in v.title]
        assert len(fisma_issues) == 1

    def test_sole_source_ja_warning(self):
        answers = _canonical_answers()
        answers["BI-08"] = "sole_source"
        package = self.agent.process_answers(answers)
        ja_issues = [v for v in package.validation_issues if "J&A" in v.title]
        assert len(ja_issues) == 1

    def test_recompete_without_transition(self):
        answers = _canonical_answers()
        answers["TN-01"] = False
        package = self.agent.process_answers(answers)
        transition = [v for v in package.validation_issues if "recompete" in v.title.lower()]
        assert len(transition) == 1

    def test_clearance_without_badge(self):
        answers = _canonical_answers()
        answers["SR-05"] = False
        package = self.agent.process_answers(answers)
        badge = [v for v in package.validation_issues if "badge" in v.title.lower()]
        assert len(badge) == 1


class TestApprovalChains:
    """Test approval chain and SSA derivation."""

    def test_under_500k(self):
        assert derive_approval_chain(250_000) == "CO approves"

    def test_at_5m(self):
        assert derive_approval_chain(3_000_000) == "CS → CO → BC approves"

    def test_at_20m(self):
        chain = derive_approval_chain(20_000_000)
        assert "DD → DAA" in chain

    def test_over_50m(self):
        chain = derive_approval_chain(75_000_000)
        assert "HCA" in chain

    def test_ssa_under_2_5m(self):
        assert derive_ssa(1_000_000) == "CO is SSA"

    def test_ssa_at_20m(self):
        ssa = derive_ssa(20_000_000)
        assert "DAA" in ssa  # $20M < $50M threshold → DAA

    def test_posting_micro(self):
        post = derive_posting_requirement(5000, False)
        assert "micro" in post.lower()

    def test_posting_sole_source(self):
        post = derive_posting_requirement(20_000_000, True)
        assert "award notice" in post.lower()

    def test_posting_competitive_above_sat(self):
        post = derive_posting_requirement(20_000_000, False)
        assert "30-day" in post

    def test_timeline_micro(self):
        t = derive_estimated_timeline(5000, False)
        assert "6-12 weeks" in t

    def test_timeline_major(self):
        t = derive_estimated_timeline(75_000_000, False)
        assert "12-18" in t


class TestLegacySOWImporter:
    """Test Phase 25 integration."""

    def setup_method(self):
        self.importer = LegacySOWImporter()

    def test_import_requirements(self):
        report = _mock_sow_analysis()
        answers, reqs, dlvs = self.importer.import_from_analysis(report, {})
        assert len(reqs) == 2
        assert reqs[0].requirement_id == "SOW-REQ-001"
        assert reqs[0].category == RequirementCategory.TECHNICAL
        assert reqs[0].priority == RequirementPriority.MUST  # "critical" → MUST

    def test_import_deliverables(self):
        report = _mock_sow_analysis()
        _, _, dlvs = self.importer.import_from_analysis(report, {})
        assert len(dlvs) == 1
        assert dlvs[0].deliverable_id == "SOW-DLV-001"
        assert dlvs[0].format == "PDF"

    def test_pre_populate_answers(self):
        report = _mock_sow_analysis()
        answers, _, _ = self.importer.import_from_analysis(report, {})
        assert answers["BI-03"] == "services"
        assert answers.get("SD-04") == "See legacy SOW"
        assert answers.get("SR-01") == "public_trust"  # Security inference

    def test_no_overwrite_existing_answers(self):
        report = _mock_sow_analysis()
        existing = {"BI-03": "supplies", "SR-01": "secret"}
        answers, _, _ = self.importer.import_from_analysis(report, existing)
        assert answers["BI-03"] == "supplies"  # Not overwritten
        assert answers["SR-01"] == "secret"    # Not overwritten

    def test_metrics_populate_ps01(self):
        report = _mock_sow_analysis()
        answers, _, _ = self.importer.import_from_analysis(report, {})
        assert "99.5% uptime" in answers.get("PS-01", "")

    def test_category_mapping(self):
        assert self.importer._map_category("technical") == RequirementCategory.TECHNICAL
        assert self.importer._map_category("security") == RequirementCategory.SECURITY
        assert self.importer._map_category("unknown") == RequirementCategory.GENERAL

    def test_priority_mapping(self):
        assert self.importer._map_priority("critical") == RequirementPriority.MUST
        assert self.importer._map_priority("standard") == RequirementPriority.SHOULD
        assert self.importer._map_priority("desirable") == RequirementPriority.COULD
        assert self.importer._map_priority("unknown") == RequirementPriority.SHOULD


class TestRequirementsElicitationAgent:
    """Test main orchestrator."""

    def setup_method(self):
        self.agent = RequirementsElicitationAgent()

    def test_process_canonical(self):
        package = self.agent.process_answers(_canonical_answers())
        assert package.status in (IntakeStatus.COMPLETE, IntakeStatus.IN_PROGRESS)
        assert len(package.requirements) >= 8
        assert len(package.deliverables) >= 3
        assert package.acquisition_params["value"] == 20_000_000
        assert package.policy.approval_chain != ""
        assert package.completeness_pct > 80

    def test_process_minimal(self):
        package = self.agent.process_answers(_minimal_answers())
        assert package.status == IntakeStatus.IN_PROGRESS  # Low completeness
        assert len(package.requirements) >= 1  # At least reporting

    def test_title_from_bi01(self):
        package = self.agent.process_answers(_canonical_answers())
        assert package.title == "TSA IT Infrastructure Support"

    def test_policy_derivation(self):
        package = self.agent.process_answers(_canonical_answers())
        assert "DAA" in package.policy.approval_chain
        assert "30-day" in package.policy.posting_requirement
        assert package.policy.estimated_timeline != ""

    def test_contract_type_notes_tm(self):
        answers = _canonical_answers()
        answers["BI-06"] = "T&M"
        package = self.agent.process_answers(answers)
        assert "D&F" in package.policy.contract_type_notes

    def test_contract_type_notes_cpaf(self):
        answers = _canonical_answers()
        answers["BI-06"] = "CPAF"
        package = self.agent.process_answers(answers)
        assert "award fee" in package.policy.contract_type_notes.lower()

    def test_import_legacy_sow(self):
        report = _mock_sow_analysis()
        package = self.agent.import_legacy_sow(report)
        assert package.legacy_sow_imported is True
        assert package.legacy_sow_score == 55.5
        assert package.legacy_findings_count == 7  # 1+3+2+1
        # SOW requirements prepended
        sow_reqs = [r for r in package.requirements if r.requirement_id.startswith("SOW-")]
        assert len(sow_reqs) == 2

    def test_import_legacy_sow_with_existing_answers(self):
        report = _mock_sow_analysis()
        existing = {"BI-01": "Existing Title", "BI-02": 20_000_000}
        package = self.agent.import_legacy_sow(report, existing)
        assert package.title == "Existing Title"

    def test_import_legacy_dedup_deliverables(self):
        report = _mock_sow_analysis()
        # SOW has "Monthly Status Report", generator also creates one
        package = self.agent.import_legacy_sow(report)
        status_dlvs = [d for d in package.deliverables if "status report" in d.name.lower()]
        # Should be deduplicated — only 1 instance
        assert len(status_dlvs) == 1

    def test_get_intake_groups(self):
        groups = self.agent.get_intake_groups()
        assert len(groups) == 10
        assert groups[0]["group_id"] == "basic_info"

    def test_get_questions(self):
        questions = self.agent.get_questions(QuestionGroupID.BASIC_INFO)
        assert len(questions) == 8
        assert questions[0]["question_id"] == "BI-01"

    def test_get_next_group(self):
        result = self.agent.get_next_group([])
        assert result is not None
        assert result["group_id"] == "basic_info"

    def test_get_next_group_all_done(self):
        all_groups = [g.value for g in GROUP_ORDER]
        result = self.agent.get_next_group(all_groups)
        assert result is None

    def test_status_complete_when_high_completeness(self):
        package = self.agent.process_answers(_canonical_answers())
        # Canonical answers cover all required fields
        assert package.completeness_pct > 80

    def test_status_in_progress_when_critical_issues(self):
        # No scope = critical issue
        answers = _canonical_answers()
        del answers["SD-02"]
        package = self.agent.process_answers(answers)
        assert package.status == IntakeStatus.IN_PROGRESS


class TestSerialization:
    """Test to_dict() output."""

    def test_to_dict_structure(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        d = package.to_dict()
        assert "package_id" in d
        assert "requirements" in d
        assert "deliverables" in d
        assert "policy" in d
        assert "validation_issues" in d
        assert "completeness_pct" in d
        assert isinstance(d["completeness_pct"], (int, float))

    def test_requirements_serialized(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        d = package.to_dict()
        for req in d["requirements"]:
            assert "requirement_id" in req
            assert "category" in req
            assert "priority" in req
            assert "verification_method" in req

    def test_policy_serialized(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        d = package.to_dict()
        policy = d["policy"]
        assert "required_dcodes" in policy
        assert "approval_chain" in policy
        assert "posting_requirement" in policy

    def test_status_is_string(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        d = package.to_dict()
        assert isinstance(d["status"], str)

    def test_source_provenance(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        d = package.to_dict()
        assert len(d["source_provenance"]) == 4
        assert any("FAR 7.105" in s for s in d["source_provenance"])


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_answers(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers({})
        assert package.status == IntakeStatus.IN_PROGRESS
        critical = [v for v in package.validation_issues if v.severity == "critical"]
        assert len(critical) >= 1  # At least "no requirements" + "no scope"

    def test_zero_value(self):
        answers = _minimal_answers()
        answers["BI-02"] = 0
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(answers)
        assert package.acquisition_params["value"] == 0
        assert "micro" in package.policy.posting_requirement.lower()

    def test_requires_acceptance_flag(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        assert package.requires_acceptance is True

    def test_generated_at_populated(self):
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(_canonical_answers())
        assert package.generated_at != ""
        assert "T" in package.generated_at  # ISO format

    def test_no_clearance_no_security_reqs(self):
        answers = _minimal_answers()
        answers["SR-01"] = "none"
        agent = RequirementsElicitationAgent()
        package = agent.process_answers(answers)
        security = [r for r in package.requirements if r.category == RequirementCategory.SECURITY]
        assert len(security) == 0
