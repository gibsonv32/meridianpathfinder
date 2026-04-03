"""
Tests for Post-Award Management — MVP #7
Option tracking, mod routing, CPARS, cure notices, closeout
"""
import pytest
from datetime import date, timedelta
from backend.phase2.post_award import (
    PostAwardManager,
    OptionStatus,
    ModType,
    ModStatus,
    CPARSStatus,
    PerformanceAction,
    CloseoutStatus,
    Tier3PostAwardError,
    CLOSEOUT_CHECKLIST,
)


@pytest.fixture
def mgr():
    return PostAwardManager()


@pytest.fixture
def contract_with_options(mgr):
    """Contract with 4 option years."""
    today = date.today()
    options = [
        {
            "period_start": (today + timedelta(days=30)).isoformat(),
            "period_end": (today + timedelta(days=395)).isoformat(),
            "estimated_value": 5_000_000,
        },
        {
            "period_start": (today + timedelta(days=395)).isoformat(),
            "period_end": (today + timedelta(days=760)).isoformat(),
            "estimated_value": 5_200_000,
        },
    ]
    mgr.register_options("CTR-001", today.isoformat(), options, "co_smith")
    return "CTR-001"


# ---------------------------------------------------------------------------
# Option Tracking
# ---------------------------------------------------------------------------

class TestOptionTracking:
    def test_register_options(self, mgr):
        today = date.today()
        options = mgr.register_options("CTR-001", today.isoformat(), [
            {"period_start": (today + timedelta(days=60)).isoformat(),
             "period_end": (today + timedelta(days=425)).isoformat(),
             "estimated_value": 5_000_000},
        ], "co_smith")
        assert len(options) == 1
        assert options[0].option_number == 1
        assert options[0].status == OptionStatus.UPCOMING

    def test_option_decision_deadline(self, mgr):
        today = date.today()
        start = today + timedelta(days=120)
        options = mgr.register_options("CTR-002", today.isoformat(), [
            {"period_start": start.isoformat(), "period_end": (start + timedelta(days=365)).isoformat()},
        ], "co_smith")
        # Decision deadline = 60 days before start
        expected_deadline = (start - timedelta(days=60)).isoformat()
        assert options[0].decision_deadline == expected_deadline

    def test_option_preliminary_notice(self, mgr):
        today = date.today()
        start = today + timedelta(days=120)
        options = mgr.register_options("CTR-003", today.isoformat(), [
            {"period_start": start.isoformat(), "period_end": (start + timedelta(days=365)).isoformat()},
        ], "co_smith")
        # Preliminary notice = 90 days before start
        expected_prelim = (start - timedelta(days=90)).isoformat()
        assert options[0].preliminary_notice_date == expected_prelim

    def test_exercise_option(self, mgr, contract_with_options):
        options = mgr._options[contract_with_options]
        opt = mgr.exercise_option(
            contract_with_options, 1,
            rationale="Satisfactory performance and continued need for services",
            actor="co_smith",
        )
        assert opt.status == OptionStatus.EXERCISED
        assert opt.exercise_rationale is not None
        assert opt.exercised_by == "co_smith"

    def test_exercise_requires_rationale(self, mgr, contract_with_options):
        with pytest.raises(ValueError, match="rationale"):
            mgr.exercise_option(contract_with_options, 1, rationale="", actor="co_smith")

    def test_cannot_exercise_twice(self, mgr, contract_with_options):
        mgr.exercise_option(contract_with_options, 1,
                           rationale="Continued need for services and satisfactory performance",
                           actor="co_smith")
        with pytest.raises(ValueError, match="already exercised"):
            mgr.exercise_option(contract_with_options, 1,
                               rationale="Try again", actor="co_smith")

    def test_decline_option(self, mgr, contract_with_options):
        opt = mgr.decline_option(
            contract_with_options, 1,
            rationale="Recompete planned", actor="co_smith",
        )
        assert opt.status == OptionStatus.DECLINED

    def test_option_alerts_preliminary_notice(self, mgr):
        today = date.today()
        start = today + timedelta(days=80)  # 80 days out → prelim window (90 days) is open
        mgr.register_options("CTR-010", today.isoformat(), [
            {"period_start": start.isoformat(), "period_end": (start + timedelta(days=365)).isoformat()},
        ], "co_smith")
        alerts = mgr.get_option_alerts("CTR-010", today.isoformat())
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "preliminary_notice_due"

    def test_option_alerts_decision_overdue(self, mgr):
        today = date.today()
        start = today + timedelta(days=30)  # 30 days out → deadline (60 days) was 30 days ago
        mgr.register_options("CTR-011", today.isoformat(), [
            {"period_start": start.isoformat(), "period_end": (start + timedelta(days=365)).isoformat()},
        ], "co_smith")
        alerts = mgr.get_option_alerts("CTR-011", today.isoformat())
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "decision_overdue"

    def test_option_alerts_expired(self, mgr):
        today = date.today()
        start = today - timedelta(days=5)  # Already past start
        mgr.register_options("CTR-012", (today - timedelta(days=400)).isoformat(), [
            {"period_start": start.isoformat(), "period_end": (start + timedelta(days=365)).isoformat()},
        ], "co_smith")
        alerts = mgr.get_option_alerts("CTR-012", today.isoformat())
        assert any(a["alert_type"] == "expired" for a in alerts)

    def test_exercised_options_no_alerts(self, mgr, contract_with_options):
        mgr.exercise_option(contract_with_options, 1,
                           rationale="Satisfactory performance and continued requirement",
                           actor="co_smith")
        alerts = mgr.get_option_alerts(contract_with_options)
        option_1_alerts = [a for a in alerts if a["option_number"] == 1]
        assert len(option_1_alerts) == 0


# ---------------------------------------------------------------------------
# Modification Routing
# ---------------------------------------------------------------------------

class TestModificationRouting:
    def test_create_bilateral_mod(self, mgr):
        mod = mgr.create_modification(
            "CTR-001", mod_type=ModType.BILATERAL,
            title="Add CLIN 0005", description="Additional monitoring",
            estimated_value_change=250_000, actor="co_smith",
        )
        assert mod.mod_number.startswith("P")
        assert mod.mod_type == ModType.BILATERAL
        assert mod.status == ModStatus.DRAFTED
        assert "D129" in mod.documents

    def test_create_unilateral_mod(self, mgr):
        mod = mgr.create_modification(
            "CTR-001", mod_type=ModType.UNILATERAL,
            title="Admin change", description="Update COR designation",
            actor="co_smith",
        )
        assert mod.mod_number.startswith("A")
        assert "FAR 43.103(b)" in mod.authority

    def test_scope_change_requires_janda(self, mgr):
        mod = mgr.create_modification(
            "CTR-001", mod_type=ModType.BILATERAL,
            title="New scope", description="Adding cybersecurity assessment",
            scope_impact="outside_scope", actor="co_smith",
        )
        assert mod.requires_janda is True
        assert "D106" in mod.documents

    def test_advance_mod_workflow(self, mgr):
        mod = mgr.create_modification(
            "CTR-001", mod_type=ModType.BILATERAL,
            title="Test mod", description="Test", actor="co_smith",
        )
        mgr.advance_modification("CTR-001", mod.mod_id,
                                 new_status=ModStatus.UNDER_REVIEW, actor="co_smith")
        mgr.advance_modification("CTR-001", mod.mod_id,
                                 new_status=ModStatus.APPROVED, actor="co_jones")
        mgr.advance_modification("CTR-001", mod.mod_id,
                                 new_status=ModStatus.EXECUTED, actor="co_jones")
        assert mod.status == ModStatus.EXECUTED
        assert mod.executed_date is not None

    def test_invalid_transition(self, mgr):
        mod = mgr.create_modification(
            "CTR-001", mod_type=ModType.BILATERAL,
            title="Test", description="Test", actor="co_smith",
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            mgr.advance_modification("CTR-001", mod.mod_id,
                                     new_status=ModStatus.EXECUTED, actor="co_smith")

    def test_pending_modifications(self, mgr):
        mgr.create_modification("CTR-001", mod_type=ModType.BILATERAL,
                               title="Mod 1", description="A", actor="co_smith")
        mod2 = mgr.create_modification("CTR-001", mod_type=ModType.BILATERAL,
                                       title="Mod 2", description="B", actor="co_smith")
        mgr.advance_modification("CTR-001", mod2.mod_id,
                                 new_status=ModStatus.UNDER_REVIEW, actor="co_smith")
        mgr.advance_modification("CTR-001", mod2.mod_id,
                                 new_status=ModStatus.REJECTED, actor="co_jones")

        pending = mgr.get_pending_modifications("CTR-001")
        assert len(pending) == 1  # Only mod 1 (drafted); mod 2 is rejected

    def test_mod_numbering_sequential(self, mgr):
        m1 = mgr.create_modification("CTR-001", mod_type=ModType.BILATERAL,
                                     title="M1", description="A", actor="co_smith")
        m2 = mgr.create_modification("CTR-001", mod_type=ModType.BILATERAL,
                                     title="M2", description="B", actor="co_smith")
        assert m1.mod_number == "P00001"
        assert m2.mod_number == "P00002"


# ---------------------------------------------------------------------------
# CPARS Tracking
# ---------------------------------------------------------------------------

class TestCPARSTracking:
    def test_schedule_cpars(self, mgr):
        evals = mgr.schedule_cpars("CTR-001", periods=[
            {"period_type": "interim", "period_start": "2026-04-01", "period_end": "2026-09-30"},
            {"period_type": "final", "period_start": "2026-10-01", "period_end": "2027-03-31"},
        ], actor="co_smith")
        assert len(evals) == 2
        assert evals[0].period_type == "interim"
        assert evals[1].period_type == "final"

    def test_cpars_due_date_default(self, mgr):
        evals = mgr.schedule_cpars("CTR-002", periods=[
            {"period_type": "interim", "period_start": "2026-04-01", "period_end": "2026-09-30"},
        ], actor="co_smith")
        # Default due date = period_end + 60 days
        expected = (date(2026, 9, 30) + timedelta(days=60)).isoformat()
        assert evals[0].due_date == expected

    def test_cpars_alert_due_soon(self, mgr):
        today = date.today()
        due = today + timedelta(days=15)
        mgr.schedule_cpars("CTR-003", periods=[
            {"period_type": "interim",
             "period_start": (today - timedelta(days=180)).isoformat(),
             "period_end": (today - timedelta(days=1)).isoformat(),
             "due_date": due.isoformat()},
        ], actor="co_smith")
        alerts = mgr.get_cpars_alerts("CTR-003", today.isoformat())
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "due_soon"

    def test_cpars_alert_overdue(self, mgr):
        today = date.today()
        due = today - timedelta(days=10)
        mgr.schedule_cpars("CTR-004", periods=[
            {"period_type": "final",
             "period_start": (today - timedelta(days=400)).isoformat(),
             "period_end": (today - timedelta(days=70)).isoformat(),
             "due_date": due.isoformat()},
        ], actor="co_smith")
        alerts = mgr.get_cpars_alerts("CTR-004", today.isoformat())
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "overdue"
        assert alerts[0]["days_overdue"] == 10

    def test_submit_cpars(self, mgr):
        evals = mgr.schedule_cpars("CTR-005", periods=[
            {"period_type": "interim", "period_start": "2026-01-01", "period_end": "2026-06-30"},
        ], actor="co_smith")
        ev = mgr.submit_cpars(
            "CTR-005", evals[0].eval_id,
            ratings={"quality": "satisfactory", "schedule": "very_good",
                     "management": "satisfactory"},
            narrative="Contractor met all key performance indicators.",
            actor="co_smith",
        )
        assert ev.status == CPARSStatus.SUBMITTED
        assert ev.quality_rating == "satisfactory"


# ---------------------------------------------------------------------------
# Performance Issues & Cure Notices
# ---------------------------------------------------------------------------

class TestPerformanceIssues:
    def test_report_issue(self, mgr):
        issue = mgr.report_issue(
            "CTR-001", title="Missed SLA", description="Detection SLA exceeded 15 minutes",
            pws_reference="3.1", qasp_reference="QASP.2", severity="major", actor="cor_jones",
        )
        assert issue.severity == "major"
        assert issue.resolved is False

    def test_escalate_to_cure_notice(self, mgr):
        issue = mgr.report_issue(
            "CTR-001", title="Repeated SLA miss", description="Third violation",
            severity="major", actor="cor_jones",
        )
        escalated = mgr.escalate_issue(
            "CTR-001", issue.issue_id,
            action=PerformanceAction.CURE_NOTICE, actor="co_smith",
        )
        assert escalated.action_taken == PerformanceAction.CURE_NOTICE
        assert escalated.cure_notice_date is not None
        assert escalated.cure_deadline is not None
        # Check audit log mentions FAR authority
        log_text = " ".join(e["details"] for e in escalated.audit_log)
        assert "FAR 49.402-3" in log_text

    def test_escalate_to_show_cause(self, mgr):
        issue = mgr.report_issue(
            "CTR-001", title="Critical failure", description="System down 48 hours",
            severity="critical", actor="cor_jones",
        )
        escalated = mgr.escalate_issue(
            "CTR-001", issue.issue_id,
            action=PerformanceAction.SHOW_CAUSE, actor="co_smith",
        )
        assert escalated.action_taken == PerformanceAction.SHOW_CAUSE

    def test_resolve_issue(self, mgr):
        issue = mgr.report_issue(
            "CTR-001", title="Minor issue", description="Late report",
            severity="minor", actor="cor_jones",
        )
        resolved = mgr.resolve_issue("CTR-001", issue.issue_id, actor="cor_jones")
        assert resolved.resolved is True
        assert resolved.resolved_date is not None

    def test_custom_cure_period(self, mgr):
        issue = mgr.report_issue(
            "CTR-001", title="Test", description="Test", severity="minor", actor="cor_jones",
        )
        escalated = mgr.escalate_issue(
            "CTR-001", issue.issue_id,
            action=PerformanceAction.CURE_NOTICE, actor="co_smith",
            cure_period_days=30,
        )
        assert escalated.cure_period_days == 30


# ---------------------------------------------------------------------------
# Tier 3 Hard Stops
# ---------------------------------------------------------------------------

class TestTier3PostAward:
    def test_terminate_for_default_always_refuses(self, mgr):
        with pytest.raises(Tier3PostAwardError, match="TIER 3"):
            mgr.terminate_for_default("CTR-001")

    def test_terminate_cites_authority(self, mgr):
        try:
            mgr.terminate_for_default("CTR-001")
        except Tier3PostAwardError as e:
            msg = str(e)
            assert "FAR 49" in msg
            assert "FAR 7.503" in msg

    def test_ratify_always_refuses(self, mgr):
        with pytest.raises(Tier3PostAwardError, match="TIER 3"):
            mgr.ratify_unauthorized_commitment()

    def test_ratify_cites_authority(self, mgr):
        try:
            mgr.ratify_unauthorized_commitment()
        except Tier3PostAwardError as e:
            assert "FAR 1.602-3" in str(e)


# ---------------------------------------------------------------------------
# Contract Closeout
# ---------------------------------------------------------------------------

class TestCloseout:
    def test_initiate_closeout(self, mgr):
        closeout = mgr.initiate_closeout("CTR-001", pop_end_date="2027-03-31", actor="co_smith")
        assert closeout.status == CloseoutStatus.NOT_STARTED
        assert len(closeout.checklist) == len(CLOSEOUT_CHECKLIST)
        assert all(v is False for v in closeout.checklist.values())

    def test_update_checklist_item(self, mgr):
        mgr.initiate_closeout("CTR-001", pop_end_date="2027-03-31", actor="co_smith")
        closeout = mgr.update_closeout_item(
            "CTR-001", item_key="pop_complete", completed=True, actor="co_smith",
        )
        assert closeout.checklist["pop_complete"] is True
        assert closeout.status == CloseoutStatus.IN_PROGRESS

    def test_complete_all_checklist(self, mgr):
        mgr.initiate_closeout("CTR-001", pop_end_date="2027-03-31", actor="co_smith")
        for key in CLOSEOUT_CHECKLIST:
            mgr.update_closeout_item("CTR-001", item_key=key, completed=True, actor="co_smith")
        closeout = mgr._closeouts["CTR-001"]
        assert closeout.status == CloseoutStatus.COMPLETE
        assert closeout.closeout_date is not None

    def test_closeout_status_report(self, mgr):
        mgr.initiate_closeout("CTR-001", pop_end_date="2027-03-31", actor="co_smith")
        mgr.update_closeout_item("CTR-001", item_key="pop_complete", completed=True, actor="co_smith")
        mgr.update_closeout_item("CTR-001", item_key="final_delivery_accepted", completed=True, actor="co_smith")

        status = mgr.get_closeout_status("CTR-001")
        assert status["progress"] == "2/10"
        assert status["progress_pct"] == 20.0
        assert len(status["blocking"]) == 8

    def test_invalid_checklist_item(self, mgr):
        mgr.initiate_closeout("CTR-001", pop_end_date="2027-03-31", actor="co_smith")
        with pytest.raises(ValueError, match="Unknown checklist item"):
            mgr.update_closeout_item("CTR-001", item_key="nonexistent", completed=True, actor="co_smith")

    def test_checklist_has_all_far_items(self):
        """Verify CLOSEOUT_CHECKLIST covers FAR 4.804 requirements."""
        assert "pop_complete" in CLOSEOUT_CHECKLIST
        assert "release_of_claims" in CLOSEOUT_CHECKLIST
        assert "final_cpars" in CLOSEOUT_CHECKLIST
        assert "files_archived" in CLOSEOUT_CHECKLIST
        assert len(CLOSEOUT_CHECKLIST) == 10


# ---------------------------------------------------------------------------
# Aggregated Alerts
# ---------------------------------------------------------------------------

class TestAggregatedAlerts:
    def test_get_contract_alerts(self, mgr, contract_with_options):
        today = date.today()
        # Add a CPARS period due soon
        mgr.schedule_cpars(contract_with_options, periods=[
            {"period_type": "interim",
             "period_start": (today - timedelta(days=180)).isoformat(),
             "period_end": (today - timedelta(days=1)).isoformat(),
             "due_date": (today + timedelta(days=15)).isoformat()},
        ], actor="co_smith")
        # Add an open issue
        mgr.report_issue(contract_with_options, title="SLA miss",
                         description="Detection exceeded threshold",
                         severity="major", actor="cor_jones")
        # Add a pending mod
        mgr.create_modification(contract_with_options, mod_type=ModType.BILATERAL,
                               title="Add services", description="Expand SOC coverage",
                               actor="co_smith")

        alerts = mgr.get_contract_alerts(contract_with_options, today.isoformat())
        assert alerts["contract_id"] == contract_with_options
        assert alerts["total_alerts"] >= 3  # at least: CPARS + issue + mod
        assert len(alerts["cpars_alerts"]) >= 1
        assert len(alerts["open_issues"]) == 1
        assert len(alerts["pending_modifications"]) == 1

    def test_alerts_empty_contract(self, mgr):
        alerts = mgr.get_contract_alerts("CTR-EMPTY")
        assert alerts["total_alerts"] == 0
        assert alerts["option_alerts"] == []
        assert alerts["cpars_alerts"] == []


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_unknown_option_number(self, mgr, contract_with_options):
        with pytest.raises(ValueError, match="No option"):
            mgr.exercise_option(contract_with_options, 99,
                               rationale="This option does not exist",
                               actor="co_smith")

    def test_unknown_mod_id(self, mgr):
        with pytest.raises(ValueError, match="Unknown modification"):
            mgr.advance_modification("CTR-001", "nonexistent",
                                     new_status=ModStatus.APPROVED, actor="co_smith")

    def test_unknown_cpars_eval(self, mgr):
        with pytest.raises(ValueError, match="Unknown CPARS"):
            mgr.submit_cpars("CTR-001", "nonexistent",
                            ratings={}, narrative="", actor="co_smith")

    def test_unknown_issue(self, mgr):
        with pytest.raises(ValueError, match="Unknown issue"):
            mgr.escalate_issue("CTR-001", "nonexistent",
                              action=PerformanceAction.CURE_NOTICE, actor="co_smith")

    def test_no_closeout_record(self, mgr):
        with pytest.raises(ValueError, match="No closeout"):
            mgr.get_closeout_status("CTR-NONE")
