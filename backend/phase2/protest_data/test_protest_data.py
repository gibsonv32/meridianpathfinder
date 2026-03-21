"""
Tests for Protest Data Pipeline — Phase 1
=========================================
Covers: TangoClient (mocked HTTP), canonical models, normalization,
ingestion pipeline with run logging.

Run: pytest phase2/protest_data/test_protest_data.py -v
"""
from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from .models import (
    EntityRole,
    IngestionRun,
    IngestionStatus,
    ProtestCase,
    ProtestEntity,
    ProtestGround,
    ProtestGroundType,
    ProtestOutcome,
    ProtestSignal,
    SignalSeverity,
)
from .normalization import (
    ProtestNormalizationService,
    classify_ground,
    normalize_agency,
    normalize_outcome,
    parse_date,
)
from .tango_client import (
    TangoAuthError,
    TangoClient,
    TangoConfig,
    TangoListResponse,
    TangoNotFoundError,
    TangoProtestRecord,
    TangoRateLimitError,
    TangoUnavailableError,
)
from .ingestion import ProtestDataStore, ProtestIngestionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TANGO_RECORD = {
    "id": "tango-001",
    "case_number": "B-421234",
    "filed_date": "2025-06-15",
    "decision_date": "2025-09-20",
    "outcome": "sustained",
    "protester": "Acme Federal Services LLC",
    "agency": "Department of Homeland Security",
    "solicitation_number": "70T02025R0001",
    "title": "IT Infrastructure Modernization",
    "value": 25000000.0,
    "grounds": [
        "Unreasonable technical evaluation",
        "Unequal treatment of offerors",
        "Improper cost realism analysis",
    ],
    "decision_url": "https://www.gao.gov/products/B-421234",
    "docket": [],
}

SAMPLE_TANGO_RECORD_2 = {
    "id": "tango-002",
    "case_number": "B-421999",
    "filed_date": "2025-11-03",
    "decision_date": "2026-01-15",
    "outcome": "denied",
    "protester": "SecureTech Inc.",
    "agency": "Transportation Security Administration",
    "solicitation_number": "HSTS02-25-R-0042",
    "title": "Checkpoint Screening Equipment",
    "value": 8500000.0,
    "grounds": ["Inadequate discussions"],
    "decision_url": "https://www.gao.gov/products/B-421999",
    "docket": [],
}

SAMPLE_CORRECTIVE_ACTION = {
    "id": "tango-003",
    "case_number": "B-422100",
    "filed_date": "2025-08-01",
    "decision_date": None,
    "outcome": "withdrawn - agency corrective action",
    "protester": "Global Defense Corp",
    "agency": "DOD",
    "solicitation_number": "W911QX-25-R-0003",
    "title": "Logistics Support Services",
    "value": 45000000.0,
    "grounds": ["Sole source justification inadequate", "Small business set-aside violation"],
    "decision_url": "",
    "docket": [],
}

# Real Tango API shape (as returned from production endpoint)
REAL_TANGO_RECORD = {
    "case_id": "5f1af05e-c2d0-50d7-83ce-46f6395b7364",
    "source_system": "gao",
    "case_number": "b-423306",
    "title": "Professional Information Systems, Inc. (80TECH24R0001)",
    "protester": "Professional Information Systems, Inc.",
    "agency": "Independent Government Entities : National Aeronautics and Space Administration",
    "solicitation_number": "80TECH24R0001",
    "case_type": "Bid Protest",
    "outcome": "Dismissed",
    "filed_date": "2026-02-20",
    "posted_date": "2026-03-19",
    "decision_date": "2026-03-19",
    "due_date": "2026-06-01",
    "docket_url": "https://www.gao.gov/docket/b-423306.15",
    "decision_url": None,
}


@pytest.fixture
def tango_record() -> TangoProtestRecord:
    return TangoClient._parse_protest_record(SAMPLE_TANGO_RECORD)


@pytest.fixture
def normalizer() -> ProtestNormalizationService:
    return ProtestNormalizationService()


@pytest.fixture
def store() -> ProtestDataStore:
    return ProtestDataStore()


# ---------------------------------------------------------------------------
# TangoClient tests
# ---------------------------------------------------------------------------

class TestTangoConfig:
    def test_from_env_defaults(self):
        with patch.dict("os.environ", {}, clear=True):
            config = TangoConfig.from_env()
            assert config.api_key == ""
            assert "makegov" in config.base_url
            assert config.timeout == 30.0
            assert config.rate_limit == 2
            assert config.max_retries == 3

    def test_from_env_custom(self):
        with patch.dict("os.environ", {
            "TANGO_API_KEY": "test-key-123",
            "TANGO_TIMEOUT": "60",
            "TANGO_RATE_LIMIT": "5",
        }):
            config = TangoConfig.from_env()
            assert config.api_key == "test-key-123"
            assert config.timeout == 60.0
            assert config.rate_limit == 5.0


class TestTangoRecordParsing:
    def test_parse_standard_record(self):
        record = TangoClient._parse_protest_record(SAMPLE_TANGO_RECORD)
        assert record.tango_id == "tango-001"
        assert record.case_number == "B-421234"
        assert record.outcome == "sustained"
        assert record.agency == "Department of Homeland Security"
        assert record.value == 25000000.0
        assert len(record.grounds) == 3
        assert record.raw_payload == SAMPLE_TANGO_RECORD

    def test_parse_alternative_field_names(self):
        """Tango API may use alternative field names — client handles both."""
        alt = {
            "tango_id": "alt-001",
            "b_number": "B-999999",
            "date_filed": "2025-01-01",
            "date_decided": "2025-04-01",
            "status": "denied",
            "protestant": "Test Corp",
            "contracting_agency": "GSA",
            "solicitation_no": "GS-00F-0001",
            "description": "Test procurement",
            "contract_value": 1000000.0,
            "protest_grounds": ["evaluation error"],
            "url": "https://example.com",
        }
        record = TangoClient._parse_protest_record(alt)
        assert record.tango_id == "alt-001"
        assert record.case_number == "B-999999"
        assert record.filed_date == "2025-01-01"
        assert record.outcome == "denied"
        assert record.protester == "Test Corp"
        assert record.agency == "GSA"
        assert record.value == 1000000.0
        assert len(record.grounds) == 1

    def test_parse_real_tango_shape(self):
        """Parse a record matching the real Tango API production shape."""
        record = TangoClient._parse_protest_record(REAL_TANGO_RECORD)
        assert record.tango_id == "5f1af05e-c2d0-50d7-83ce-46f6395b7364"
        assert record.case_number == "b-423306"
        assert record.outcome == "Dismissed"
        assert record.protester == "Professional Information Systems, Inc."
        assert "National Aeronautics" in record.agency
        assert record.case_type == "Bid Protest"
        assert record.posted_date == "2026-03-19"
        assert record.docket_url == "https://www.gao.gov/docket/b-423306.15"
        assert record.decision_url is None

    def test_parse_missing_optional_fields(self):
        minimal = {"id": "min-001", "case_number": "B-000001"}
        record = TangoClient._parse_protest_record(minimal)
        assert record.tango_id == "min-001"
        assert record.case_number == "B-000001"
        assert record.outcome is None
        assert record.protester is None
        assert record.value is None
        assert record.grounds == []


class TestTangoClientAuth:
    def test_no_api_key_raises(self):
        config = TangoConfig(api_key="")
        client = TangoClient(config)
        with pytest.raises(TangoAuthError, match="TANGO_API_KEY not set"):
            client._get_client()


# ---------------------------------------------------------------------------
# Canonical model tests
# ---------------------------------------------------------------------------

class TestProtestCase:
    def test_fiscal_year_oct_through_dec(self):
        """Cases filed Oct–Dec belong to next calendar year's FY."""
        case = ProtestCase(case_number="B-100", filed_date=date(2025, 10, 15))
        assert case.fiscal_year == 2026

    def test_fiscal_year_jan_through_sep(self):
        """Cases filed Jan–Sep belong to current calendar year's FY."""
        case = ProtestCase(case_number="B-101", filed_date=date(2025, 6, 1))
        assert case.fiscal_year == 2025

    def test_fiscal_year_none_without_date(self):
        case = ProtestCase(case_number="B-102")
        assert case.fiscal_year is None

    def test_default_uuid_ids(self):
        c1 = ProtestCase(case_number="B-200")
        c2 = ProtestCase(case_number="B-201")
        assert c1.id != c2.id
        assert len(c1.id) == 36  # UUID format


class TestIngestionRun:
    def test_complete_success(self):
        run = IngestionRun(provider_name="tango", records_fetched=10, records_normalized=10)
        run.complete()
        assert run.status == IngestionStatus.COMPLETED
        assert run.completed_at is not None

    def test_complete_partial(self):
        run = IngestionRun(provider_name="tango", records_fetched=10, records_normalized=7, records_failed=3)
        run.complete()
        assert run.status == IngestionStatus.PARTIAL

    def test_complete_failed(self):
        run = IngestionRun(provider_name="tango", records_fetched=10, records_normalized=0, records_failed=10)
        run.complete()
        assert run.status == IngestionStatus.FAILED

    def test_duration(self):
        run = IngestionRun(provider_name="tango")
        assert run.duration_seconds is None
        run.complete()
        assert run.duration_seconds is not None
        assert run.duration_seconds >= 0

    def test_summary(self):
        run = IngestionRun(provider_name="tango", records_fetched=5, records_normalized=4, records_failed=1)
        run.complete()
        s = run.to_summary()
        assert s["provider"] == "tango"
        assert s["fetched"] == 5
        assert s["normalized"] == 4
        assert s["failed"] == 1
        assert s["status"] == "partial"


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------

class TestOutcomeNormalization:
    @pytest.mark.parametrize("raw,expected", [
        ("sustained", ProtestOutcome.SUSTAINED),
        ("Sustained", ProtestOutcome.SUSTAINED),
        ("SUSTAINED", ProtestOutcome.SUSTAINED),
        ("denied", ProtestOutcome.DENIED),
        ("Denied", ProtestOutcome.DENIED),
        ("dismissed", ProtestOutcome.DISMISSED),
        ("Dismissed", ProtestOutcome.DISMISSED),
        ("withdrawn", ProtestOutcome.WITHDRAWN),
        ("Withdrawn", ProtestOutcome.WITHDRAWN),
        ("corrective action", ProtestOutcome.CORRECTIVE_ACTION),
        ("corrective_action", ProtestOutcome.CORRECTIVE_ACTION),
        ("withdrawn - agency corrective action", ProtestOutcome.CORRECTIVE_ACTION),
        ("partially sustained", ProtestOutcome.MIXED),
        ("mixed", ProtestOutcome.MIXED),
        ("unknown_value", ProtestOutcome.UNKNOWN),
        (None, ProtestOutcome.UNKNOWN),
        ("", ProtestOutcome.UNKNOWN),
    ])
    def test_outcome_mapping(self, raw, expected):
        assert normalize_outcome(raw) == expected


class TestAgencyNormalization:
    @pytest.mark.parametrize("raw,expected_abbrev", [
        ("Department of Homeland Security", "DHS"),
        ("DHS", "DHS"),
        ("Transportation Security Administration", "TSA"),
        ("TSA", "TSA"),
        ("Department of Defense", "DOD"),
        ("DOD", "DOD"),
        ("General Services Administration", "GSA"),
        ("NASA", "NASA"),
        ("Environmental Protection Agency", "EPA"),
    ])
    def test_agency_abbreviation(self, raw, expected_abbrev):
        _, abbrev = normalize_agency(raw)
        assert abbrev == expected_abbrev

    def test_unknown_agency(self):
        full, abbrev = normalize_agency("Ministry of Magic")
        assert full == "Ministry of Magic"
        assert abbrev == ""

    def test_none_agency(self):
        full, abbrev = normalize_agency(None)
        assert full == ""
        assert abbrev == ""

    def test_substring_match(self):
        """Agency names containing a known substring should still match."""
        _, abbrev = normalize_agency("U.S. Customs and Border Protection - Field Office")
        assert abbrev == "CBP"

    def test_colon_separated_format(self):
        """Tango API returns 'Parent : Sub-agency' — should resolve sub-agency."""
        _, abbrev = normalize_agency("Department of Homeland Security : Transportation Security Administration")
        assert abbrev == "TSA"

    def test_colon_separated_nasa(self):
        _, abbrev = normalize_agency("Independent Government Entities : National Aeronautics and Space Administration")
        assert abbrev == "NASA"

    def test_colon_separated_dod_sub(self):
        _, abbrev = normalize_agency("Department of Defense : Defense Logistics Agency")
        assert abbrev == "DOD"


class TestGroundClassification:
    @pytest.mark.parametrize("text,expected", [
        ("Unreasonable technical evaluation", ProtestGroundType.EVALUATION_ERROR),
        ("Unequal treatment of offerors", ProtestGroundType.UNEQUAL_TREATMENT),
        ("Improper cost realism analysis", ProtestGroundType.COST_PRICE_ANALYSIS),
        ("Inadequate discussions", ProtestGroundType.DISCUSSIONS_CLARIFICATIONS),
        ("Sole source justification inadequate", ProtestGroundType.SOLE_SOURCE_JA),
        ("Small business set-aside violation", ProtestGroundType.SMALL_BUSINESS_SET_ASIDE),
        ("Organizational conflict of interest", ProtestGroundType.ORGANIZATIONAL_CONFLICT),
        ("Ambiguous solicitation terms", ProtestGroundType.SOLICITATION_DEFICIENCY),
        ("Best value tradeoff analysis flawed", ProtestGroundType.BEST_VALUE_TRADEOFF),
        ("Past performance rating inconsistent", ProtestGroundType.PAST_PERFORMANCE),
        ("Debriefing was inadequate", ProtestGroundType.DEBRIEFING),
        ("Random unrelated text", ProtestGroundType.OTHER),
    ])
    def test_ground_classification(self, text, expected):
        assert classify_ground(text) == expected


class TestDateParsing:
    @pytest.mark.parametrize("raw,expected", [
        ("2025-06-15", date(2025, 6, 15)),
        ("06/15/2025", date(2025, 6, 15)),
        ("06-15-2025", date(2025, 6, 15)),
        ("June 15, 2025", date(2025, 6, 15)),
        ("Jun 15, 2025", date(2025, 6, 15)),
        ("20250615", date(2025, 6, 15)),
        (None, None),
        ("", None),
        ("not-a-date", None),
    ])
    def test_date_parsing(self, raw, expected):
        assert parse_date(raw) == expected


class TestNormalizationService:
    def test_full_normalization(self, tango_record, normalizer):
        case = normalizer.normalize(tango_record)

        assert case.case_number == "B-421234"
        assert case.outcome == ProtestOutcome.SUSTAINED
        assert case.agency_abbreviation == "DHS"
        assert case.protester == "Acme Federal Services LLC"
        assert case.value == 25000000.0
        assert case.filed_date == date(2025, 6, 15)
        assert case.decision_date == date(2025, 9, 20)
        assert case.fiscal_year == 2025
        assert case.provider_name == "tango"
        assert case.provider_id == "tango-001"
        assert case.normalized_at is not None

    def test_grounds_populated(self, tango_record, normalizer):
        case = normalizer.normalize(tango_record)
        assert len(case.grounds) == 3
        ground_types = {g.ground_type for g in case.grounds}
        assert ProtestGroundType.EVALUATION_ERROR in ground_types
        assert ProtestGroundType.UNEQUAL_TREATMENT in ground_types
        assert ProtestGroundType.COST_PRICE_ANALYSIS in ground_types

    def test_entities_populated(self, tango_record, normalizer):
        case = normalizer.normalize(tango_record)
        assert len(case.entities) == 2
        roles = {e.role for e in case.entities}
        assert EntityRole.PROTESTER in roles
        assert EntityRole.AGENCY in roles

    def test_signals_derived(self, tango_record, normalizer):
        case = normalizer.normalize(tango_record)
        assert len(case.signals) > 0
        # Sustained case should produce HIGH severity signals
        for signal in case.signals:
            assert signal.severity == SignalSeverity.HIGH
            assert signal.confidence == 0.9

    def test_real_tango_record_normalization(self, normalizer):
        """End-to-end normalization of a real Tango API record."""
        record = TangoClient._parse_protest_record(REAL_TANGO_RECORD)
        case = normalizer.normalize(record)
        assert case.case_number == "b-423306"
        assert case.outcome == ProtestOutcome.DISMISSED
        assert case.agency_abbreviation == "NASA"
        assert case.protester == "Professional Information Systems, Inc."
        assert case.filed_date == date(2026, 2, 20)
        assert case.decision_date == date(2026, 3, 19)
        assert case.fiscal_year == 2026
        assert case.provider_id == "5f1af05e-c2d0-50d7-83ce-46f6395b7364"

    def test_corrective_action_normalization(self, normalizer):
        record = TangoClient._parse_protest_record(SAMPLE_CORRECTIVE_ACTION)
        case = normalizer.normalize(record)
        assert case.outcome == ProtestOutcome.CORRECTIVE_ACTION
        assert case.agency_abbreviation == "DOD"
        # Corrective action = MEDIUM severity signals
        for signal in case.signals:
            assert signal.severity == SignalSeverity.MEDIUM
            assert signal.confidence == 0.7

    def test_batch_normalization(self, normalizer):
        records = [
            TangoClient._parse_protest_record(SAMPLE_TANGO_RECORD),
            TangoClient._parse_protest_record(SAMPLE_TANGO_RECORD_2),
            TangoClient._parse_protest_record(SAMPLE_CORRECTIVE_ACTION),
        ]
        successes, failures = normalizer.normalize_batch(records)
        assert len(successes) == 3
        assert len(failures) == 0

    def test_batch_with_failure(self, normalizer):
        """Batch normalization isolates failures — other records still succeed."""
        good = TangoClient._parse_protest_record(SAMPLE_TANGO_RECORD)
        bad = TangoProtestRecord(tango_id="bad", case_number="")
        # Patch normalize to raise on the bad record
        original = normalizer.normalize

        def side_effect(record):
            if record.tango_id == "bad":
                raise ValueError("intentional test failure")
            return original(record)

        normalizer.normalize = side_effect
        successes, failures = normalizer.normalize_batch([good, bad])
        assert len(successes) == 1
        assert len(failures) == 1
        assert "intentional" in failures[0][1]


# ---------------------------------------------------------------------------
# Data store tests
# ---------------------------------------------------------------------------

class TestProtestDataStore:
    def test_upsert_new(self, store):
        case = ProtestCase(case_number="B-100")
        is_new = store.upsert_case(case)
        assert is_new is True
        assert store.total_cases == 1

    def test_upsert_existing(self, store):
        case1 = ProtestCase(case_number="B-100", title="Original")
        case2 = ProtestCase(case_number="B-100", title="Updated")
        store.upsert_case(case1)
        is_new = store.upsert_case(case2)
        assert is_new is False
        assert store.total_cases == 1
        retrieved = store.get_case("B-100")
        assert retrieved.title == "Updated"

    def test_get_cases_by_agency(self, store):
        store.upsert_case(ProtestCase(case_number="B-1", agency_abbreviation="DHS"))
        store.upsert_case(ProtestCase(case_number="B-2", agency_abbreviation="DHS"))
        store.upsert_case(ProtestCase(case_number="B-3", agency_abbreviation="DOD"))
        dhs = store.get_cases_by_agency("DHS")
        assert len(dhs) == 2

    def test_get_sustained(self, store):
        store.upsert_case(ProtestCase(case_number="B-1", outcome=ProtestOutcome.SUSTAINED))
        store.upsert_case(ProtestCase(case_number="B-2", outcome=ProtestOutcome.DENIED))
        sustained = store.get_sustained_cases()
        assert len(sustained) == 1

    def test_raw_payload_storage(self, store):
        store.store_raw("t-001", {"test": True})
        assert "t-001" in store.raw_payloads

    def test_summary(self, store):
        store.upsert_case(ProtestCase(case_number="B-1", outcome=ProtestOutcome.SUSTAINED))
        store.upsert_case(ProtestCase(case_number="B-2", outcome=ProtestOutcome.DENIED))
        s = store.summary()
        assert s["total_cases"] == 2
        assert s["outcomes"]["sustained"] == 1
        assert s["outcomes"]["denied"] == 1


# ---------------------------------------------------------------------------
# Ingestion pipeline tests (mocked client)
# ---------------------------------------------------------------------------

class TestIngestionService:
    def _make_mock_client(self, records: list[dict]) -> TangoClient:
        """Create a mock client that returns the given records."""
        client = MagicMock(spec=TangoClient)
        parsed = [TangoClient._parse_protest_record(r) for r in records]
        client.list_protests.return_value = TangoListResponse(
            records=parsed,
            total_count=len(parsed),
            page=1,
            page_size=50,
            has_next=False,
        )
        return client

    def test_successful_ingestion(self):
        client = self._make_mock_client([SAMPLE_TANGO_RECORD, SAMPLE_TANGO_RECORD_2])
        service = ProtestIngestionService(client=client)
        run = service.ingest(agency="DHS")

        assert run.status == IngestionStatus.COMPLETED
        assert run.records_fetched == 2
        assert run.records_normalized == 2
        assert run.records_failed == 0
        assert len(run.errors) == 0
        assert service.store.total_cases == 2
        assert len(service.store.raw_payloads) == 2

    def test_ingestion_with_normalization_failure(self):
        client = self._make_mock_client([SAMPLE_TANGO_RECORD])
        normalizer = MagicMock(spec=ProtestNormalizationService)
        record = TangoClient._parse_protest_record(SAMPLE_TANGO_RECORD)
        normalizer.normalize_batch.return_value = ([], [(record, "test error")])

        service = ProtestIngestionService(client=client, normalizer=normalizer)
        run = service.ingest()

        assert run.status == IngestionStatus.FAILED
        assert run.records_fetched == 1
        assert run.records_normalized == 0
        assert run.records_failed == 1

    def test_ingestion_api_failure(self):
        client = MagicMock(spec=TangoClient)
        client.list_protests.side_effect = TangoUnavailableError("Connection refused")

        service = ProtestIngestionService(client=client)
        run = service.ingest()

        assert run.status in (IngestionStatus.FAILED, IngestionStatus.COMPLETED)
        assert len(run.errors) > 0
        assert "Connection refused" in run.errors[0]

    def test_ingestion_run_stored(self):
        client = self._make_mock_client([SAMPLE_TANGO_RECORD])
        service = ProtestIngestionService(client=client)
        service.ingest()
        assert service.store.total_runs == 1

    def test_ingestion_parameters_logged(self):
        client = self._make_mock_client([])
        service = ProtestIngestionService(client=client)
        run = service.ingest(agency="TSA", outcome="sustained")
        assert run.parameters["agency"] == "TSA"
        assert run.parameters["outcome"] == "sustained"

    def test_deduplication_on_reingest(self):
        client = self._make_mock_client([SAMPLE_TANGO_RECORD])
        service = ProtestIngestionService(client=client)

        run1 = service.ingest()
        run2 = service.ingest()

        assert service.store.total_cases == 1  # not 2
        assert service.store.total_runs == 2

    def test_ingest_single(self):
        record_data = SAMPLE_TANGO_RECORD
        client = MagicMock(spec=TangoClient)
        client.get_protest.return_value = TangoClient._parse_protest_record(record_data)

        service = ProtestIngestionService(client=client)
        case = service.ingest_single("tango-001")

        assert case is not None
        assert case.case_number == "B-421234"
        assert service.store.total_cases == 1

    def test_ingest_single_failure(self):
        client = MagicMock(spec=TangoClient)
        client.get_protest.side_effect = TangoNotFoundError("Not found")

        service = ProtestIngestionService(client=client)
        case = service.ingest_single("nonexistent")
        assert case is None
