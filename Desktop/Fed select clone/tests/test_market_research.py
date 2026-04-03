"""Tests for Market Research Agent (Phase 23a).

Coverage:
- Section generators (6 sections)
- Canonical $20M TSA IT scenario
- Report assembly and serialization
- Edge cases (no data, micro-purchase, sole source)
- PIL pricing benchmarks
- Protest context integration
- Small business rule-of-two logic
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.market_research_agent import (
    MarketResearchAgent,
    MarketResearchRequest,
    SetAsideRecommendation,
    generate_comparable_awards,
    generate_active_market_scan,
    generate_small_business_availability,
    generate_commercial_assessment,
    generate_pricing_intelligence,
    generate_protest_context,
    report_to_dict,
    PIL_RATES,
    PROTEST_RATES_BY_VALUE,
    PROTEST_RATES_BY_AGENCY,
    _value_bracket,
)


# ─── Sample Data ─────────────────────────────────────────────────────────────

SAMPLE_AWARDS = [
    {"piid": "70T01024C0001", "recipient_name": "Acme Corp", "total_obligation": 15_000_000,
     "agency": "DHS", "sub_agency": "TSA", "naics_code": "541512", "psc_code": "D302",
     "start_date": "2024-01-15", "competition_type": "full_and_open",
     "set_aside_type": "Total Small Business"},
    {"piid": "70T01024C0002", "recipient_name": "Beta LLC", "total_obligation": 22_000_000,
     "agency": "DHS", "sub_agency": "TSA", "naics_code": "541512", "psc_code": "D302",
     "start_date": "2024-06-01", "competition_type": "full_and_open",
     "set_aside_type": None},
    {"piid": "70T01024C0003", "recipient_name": "Gamma Inc", "total_obligation": 8_000_000,
     "agency": "DHS", "sub_agency": "CBP", "naics_code": "541511", "psc_code": "D301",
     "start_date": "2023-09-01", "competition_type": "full_and_open",
     "set_aside_type": "8(a) Sole Source"},
    {"piid": "70T01024C0004", "recipient_name": "Delta Services", "total_obligation": 18_000_000,
     "agency": "DHS", "sub_agency": "TSA", "naics_code": "541512", "psc_code": "D302",
     "start_date": "2025-01-10", "competition_type": "full_and_open",
     "set_aside_type": "Total Small Business"},
    {"piid": "70T01024C0005", "recipient_name": "Epsilon Tech", "total_obligation": 25_000_000,
     "agency": "DHS", "sub_agency": "TSA", "naics_code": "541512", "psc_code": "D302",
     "start_date": "2025-03-01", "competition_type": "not_competed",
     "set_aside_type": "8(a) Sole Source"},
]

SAMPLE_OPPS = [
    {"notice_id": "SAM-001", "title": "TSA IT Support", "agency": "DHS/TSA",
     "naics_code": "541512", "set_aside": "Total Small Business",
     "posted_date": "2026-02-01", "response_deadline": "2026-03-01",
     "estimated_value": 15_000_000, "status": "active"},
    {"notice_id": "SAM-002", "title": "CBP Cyber Services", "agency": "DHS/CBP",
     "naics_code": "541512", "set_aside": None,
     "posted_date": "2026-01-15", "response_deadline": "2026-02-15",
     "estimated_value": 30_000_000, "status": "active"},
]

SAMPLE_PROTESTS = [
    {"file_number": "B-420441", "company_name": "CACI", "sub_agency": "TSA",
     "outcome": "Sustained", "estimated_value": 200_000_000},
    {"file_number": "B-417840", "company_name": "SecureTech", "sub_agency": "TSA",
     "outcome": "Denied", "estimated_value": 50_000_000},
    {"file_number": "B-418642", "company_name": "Credco", "sub_agency": "TSA",
     "outcome": "Denied", "estimated_value": 30_000_000},
]

TSA_20M_REQ = MarketResearchRequest(
    naics_code="541512",
    estimated_value=20_000_000,
    agency="DHS",
    sub_agency="TSA",
    psc_code="D302",
    services=True,
    it_related=True,
)


# ─── Test Value Bracket ──────────────────────────────────────────────────────

class TestValueBracket:
    def test_under_sat(self):
        assert _value_bracket(10_000) == "under_sat"

    def test_sat_to_5m(self):
        assert _value_bracket(1_000_000) == "sat_to_5.5m"

    def test_5m_to_50m(self):
        assert _value_bracket(20_000_000) == "5.5m_to_50m"

    def test_50m_to_100m(self):
        assert _value_bracket(75_000_000) == "50m_to_100m"

    def test_100m_plus(self):
        assert _value_bracket(200_000_000) == "100m_plus"


# ─── Test Section 1: Comparable Awards ───────────────────────────────────────

class TestComparableAwards:
    def test_finds_matching_awards(self):
        section = generate_comparable_awards(TSA_20M_REQ, SAMPLE_AWARDS)
        assert section.section_number == 1
        assert section.content["total_matches"] > 0

    def test_relevance_scoring(self):
        section = generate_comparable_awards(TSA_20M_REQ, SAMPLE_AWARDS)
        awards = section.content["comparable_awards"]
        # TSA + NAICS 5415 awards should have highest relevance
        assert all(a["relevance"] >= 0.3 for a in awards)

    def test_price_statistics(self):
        section = generate_comparable_awards(TSA_20M_REQ, SAMPLE_AWARDS)
        stats = section.content["price_statistics"]
        assert "min" in stats
        assert "max" in stats
        assert stats["min"] > 0

    def test_empty_store(self):
        section = generate_comparable_awards(TSA_20M_REQ, [])
        assert section.content["total_matches"] == 0
        assert section.confidence < 0.5

    def test_far_authority(self):
        section = generate_comparable_awards(TSA_20M_REQ, SAMPLE_AWARDS)
        assert "FAR 10.002" in section.far_authority


# ─── Test Section 2: Active Market Scan ──────────────────────────────────────

class TestActiveMarketScan:
    def test_finds_matching_opps(self):
        section = generate_active_market_scan(TSA_20M_REQ, SAMPLE_OPPS)
        assert section.content["total_found"] > 0

    def test_empty_opps(self):
        section = generate_active_market_scan(TSA_20M_REQ, [])
        assert section.content["total_found"] == 0
        assert section.confidence < 0.5


# ─── Test Section 3: Small Business ──────────────────────────────────────────

class TestSmallBusiness:
    def test_rule_of_two(self):
        """Rule of two: need >= 2 SB firms for set-aside viability."""
        section = generate_small_business_availability(TSA_20M_REQ, SAMPLE_AWARDS)
        profiles = section.content["profiles"]
        # We have Acme + Delta as Total Small Business = viable
        sb = [p for p in profiles if p["category"] == "total_small_business"]
        assert len(sb) == 1
        assert sb[0]["viable"] is True
        assert sb[0]["count"] >= 2

    def test_set_aside_recommendation(self):
        section = generate_small_business_availability(TSA_20M_REQ, SAMPLE_AWARDS)
        rec = section.content["set_aside_recommendation"]
        assert rec in [e.value for e in SetAsideRecommendation]

    def test_empty_awards(self):
        section = generate_small_business_availability(TSA_20M_REQ, [])
        rec = section.content["set_aside_recommendation"]
        assert rec == "full_and_open"


# ─── Test Section 4: Commercial Assessment ───────────────────────────────────

class TestCommercialAssessment:
    def test_it_services_commercial(self):
        section = generate_commercial_assessment(TSA_20M_REQ)
        assert section.content["is_commercial"] is True

    def test_below_commercial_sap(self):
        req = MarketResearchRequest(
            naics_code="541512", estimated_value=5_000_000,
            services=True, it_related=True,
        )
        section = generate_commercial_assessment(req)
        assert section.content["is_commercial"] is True
        assert any("SAP" in f or "13.5" in f for f in section.findings)


# ─── Test Section 5: Pricing Intelligence ────────────────────────────────────

class TestPricingIntelligence:
    def test_pil_rates_loaded(self):
        assert len(PIL_RATES) == 15

    def test_it_benchmarks(self):
        section = generate_pricing_intelligence(TSA_20M_REQ)
        benchmarks = section.content["benchmarks"]
        assert len(benchmarks) > 5  # IT should have many categories
        categories = [b["category"] for b in benchmarks]
        assert "Senior Software Developer" in categories

    def test_fte_estimate(self):
        section = generate_pricing_intelligence(TSA_20M_REQ)
        fte = section.content["estimated_fte"]
        assert fte > 0
        # $20M / (~$135/hr * 1920 hrs) ≈ 77 FTE
        assert 30 < fte < 200  # Sanity range

    def test_average_rate(self):
        section = generate_pricing_intelligence(TSA_20M_REQ)
        avg = section.content["average_rate"]
        assert 80 < avg < 200  # DHS PIL range


# ─── Test Section 6: Protest Context ─────────────────────────────────────────

class TestProtestContext:
    def test_protest_rates(self):
        section = generate_protest_context(TSA_20M_REQ, SAMPLE_PROTESTS)
        content = section.content
        assert content["value_bracket_rate"] == PROTEST_RATES_BY_VALUE["5.5m_to_50m"]
        assert content["agency_rate"] == PROTEST_RATES_BY_AGENCY["TSA"]

    def test_comparable_protests_found(self):
        section = generate_protest_context(TSA_20M_REQ, SAMPLE_PROTESTS)
        assert len(section.content["comparable_protests"]) > 0

    def test_mitigations_present(self):
        section = generate_protest_context(TSA_20M_REQ, SAMPLE_PROTESTS)
        assert len(section.content["mitigations"]) > 0

    def test_high_value_warnings(self):
        req = MarketResearchRequest(
            naics_code="541512", estimated_value=75_000_000,
            sub_agency="TSA",
        )
        section = generate_protest_context(req)
        risks = section.content["risk_factors"]
        assert any("$50M" in r for r in risks)

    def test_empty_protests(self):
        section = generate_protest_context(TSA_20M_REQ, [])
        assert section.content["overall_protest_rate"] > 0  # Still has rate tables


# ─── Test Full Report Assembly ───────────────────────────────────────────────

class TestReportAssembly:
    def test_six_sections(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ, SAMPLE_AWARDS, SAMPLE_OPPS, SAMPLE_PROTESTS)
        assert len(report.sections) == 6

    def test_section_numbering(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ)
        numbers = [s.section_number for s in report.sections]
        assert numbers == [1, 2, 3, 4, 5, 6]

    def test_executive_summary(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ, SAMPLE_AWARDS)
        assert "TSA" in report.executive_summary
        assert "541512" in report.executive_summary

    def test_requires_acceptance(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ)
        assert report.requires_acceptance is True  # Tier 2

    def test_overall_confidence(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ, SAMPLE_AWARDS, SAMPLE_OPPS)
        assert 0 < report.overall_confidence <= 1.0

    def test_serialization(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ, SAMPLE_AWARDS, SAMPLE_OPPS, SAMPLE_PROTESTS)
        d = report_to_dict(report)
        assert d["request"]["naics_code"] == "541512"
        assert len(d["sections"]) == 6
        assert "executive_summary" in d
        assert "set_aside_recommendation" in d

    def test_set_aside_recommendation_from_data(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ, SAMPLE_AWARDS)
        # With sample data having 2 total SB vendors, should recommend SB
        assert report.set_aside_recommendation == SetAsideRecommendation.TOTAL_SMALL_BUSINESS


# ─── Test Edge Cases ─────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_micro_purchase(self):
        req = MarketResearchRequest(
            naics_code="541512", estimated_value=5_000,
        )
        agent = MarketResearchAgent()
        report = agent.generate_report(req)
        assert len(report.sections) == 6

    def test_no_data_stores(self):
        agent = MarketResearchAgent()
        report = agent.generate_report(TSA_20M_REQ)
        # Should still produce all 6 sections with reduced confidence
        assert len(report.sections) == 6
        assert report.overall_confidence < 0.8

    def test_100m_plus(self):
        req = MarketResearchRequest(
            naics_code="541512", estimated_value=150_000_000,
            sub_agency="USCIS",
        )
        section = generate_protest_context(req)
        risks = section.content["risk_factors"]
        assert any("$100M" in r for r in risks)

    def test_non_it_services(self):
        req = MarketResearchRequest(
            naics_code="561210", estimated_value=2_000_000,
            services=True, it_related=False,
        )
        section = generate_pricing_intelligence(req)
        benchmarks = section.content["benchmarks"]
        categories = [b["category"] for b in benchmarks]
        assert "Program Manager" in categories


# ─── Test Rate Tables ────────────────────────────────────────────────────────

class TestRateTables:
    def test_protest_value_rates_complete(self):
        assert len(PROTEST_RATES_BY_VALUE) == 5
        for k, v in PROTEST_RATES_BY_VALUE.items():
            assert 0 <= v <= 100

    def test_protest_agency_rates_complete(self):
        assert "TSA" in PROTEST_RATES_BY_AGENCY
        assert "CBP" in PROTEST_RATES_BY_AGENCY
        assert len(PROTEST_RATES_BY_AGENCY) >= 8

    def test_pil_rates_have_min_max_avg(self):
        for cat, rates in PIL_RATES.items():
            assert rates["min"] < rates["max"]
            assert rates["min"] <= rates["avg"] <= rates["max"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
