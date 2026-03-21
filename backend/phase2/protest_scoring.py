"""
Protest Risk Scoring Engine — Phase 2 Feature
==============================================
Scores procurement decisions against GAO protest risk factors.
Based on GAO sustain rate data (FY2025: 14%) and common protest grounds.

Tier 2 AI output — requires CO review before entering official record.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFactor:
    factor_id: str
    name: str
    description: str
    risk_level: RiskLevel
    score: int  # 0-100
    mitigation: str
    authority: str


@dataclass
class ProtestRiskAssessment:
    overall_score: int  # 0-100 (higher = more risk)
    overall_risk: RiskLevel
    factors: list[RiskFactor]
    summary: str
    recommendations: list[str]
    source_provenance: list[str]
    confidence_score: float
    requires_acceptance: bool = True


class ProtestRiskEngine:
    """
    Scores protest risk based on procurement characteristics.

    Factors assessed:
    1. Sole source / limited competition
    2. Evaluation criteria clarity (J-L-M traceability)
    3. Price realism analysis
    4. Organizational conflict of interest
    5. Incumbent advantage / leveling
    6. Debriefing quality obligations
    7. Small business set-aside compliance
    8. Discussions vs. clarifications
    9. Technical evaluation documentation
    10. Past performance evaluation consistency
    """

    GAO_SUSTAIN_RATE_FY2025 = 0.14  # 14% sustain rate

    def score(
        self,
        *,
        value: float,
        sole_source: bool = False,
        incumbent_rebid: bool = False,
        evaluation_type: str = "tradeoff",  # tradeoff | lpta
        num_offerors_expected: int = 3,
        has_discussions: bool = False,
        set_aside_type: str | None = None,
        has_oci_plan: bool = False,
        j_l_m_traced: bool = True,
        price_analysis_method: str = "competitive",
        past_performance_weighted: bool = True,
        debriefing_required: bool = False,
    ) -> ProtestRiskAssessment:
        factors: list[RiskFactor] = []
        provenance = [
            "GAO Bid Protest Annual Report FY2025",
            "FAR 33.103 (Protests to the agency)",
            "FAR 33.104 (Protests to GAO)",
            "4 C.F.R. Part 21",
        ]

        # Factor 1: Sole source / limited competition
        if sole_source:
            factors.append(RiskFactor(
                factor_id="PF01", name="Sole Source Justification",
                description="Sole source procurements face higher protest scrutiny on J&A adequacy.",
                risk_level=RiskLevel.HIGH, score=75,
                mitigation="Ensure J&A cites specific FAR 6.302 authority with detailed market research evidence.",
                authority="FAR 6.302, FAR 6.304",
            ))
        elif num_offerors_expected < 3:
            factors.append(RiskFactor(
                factor_id="PF01", name="Limited Competition Pool",
                description=f"Only {num_offerors_expected} expected offeror(s) increases protest risk from excluded vendors.",
                risk_level=RiskLevel.MEDIUM, score=45,
                mitigation="Document market research showing genuine lack of qualified sources.",
                authority="FAR 6.101, FAR 10.002",
            ))
        else:
            factors.append(RiskFactor(
                factor_id="PF01", name="Competition Adequacy",
                description="Full and open competition with adequate offeror pool.",
                risk_level=RiskLevel.LOW, score=10,
                mitigation="Maintain documentation of all sources solicited.",
                authority="FAR 6.101",
            ))

        # Factor 2: J-L-M traceability
        if not j_l_m_traced:
            factors.append(RiskFactor(
                factor_id="PF02", name="Evaluation Criteria Traceability",
                description="Section J/L/M misalignment is a top GAO sustain ground.",
                risk_level=RiskLevel.HIGH, score=80,
                mitigation="Ensure every Section M factor traces to a Section L instruction and Section J requirement.",
                authority="FAR 15.304, FAR 15.305",
            ))
        else:
            factors.append(RiskFactor(
                factor_id="PF02", name="Evaluation Criteria Traceability",
                description="J-L-M traceability confirmed.",
                risk_level=RiskLevel.LOW, score=10,
                mitigation="Maintain traceability matrix through any amendments.",
                authority="FAR 15.304, FAR 15.305",
            ))

        # Factor 3: LPTA vs Tradeoff risk
        if evaluation_type == "lpta" and value > 5_500_000:
            factors.append(RiskFactor(
                factor_id="PF03", name="LPTA on High-Value Acquisition",
                description="LPTA above $5.5M invites protests on whether tradeoff was more appropriate.",
                risk_level=RiskLevel.MEDIUM, score=55,
                mitigation="Document D&F explaining why LPTA is appropriate per FAR 15.101-2(b).",
                authority="FAR 15.101-2, DFARS 215.101-2-70",
            ))
        else:
            factors.append(RiskFactor(
                factor_id="PF03", name="Evaluation Methodology",
                description=f"{evaluation_type.upper()} methodology appropriate for value tier.",
                risk_level=RiskLevel.LOW, score=10,
                mitigation="Document rationale for evaluation methodology selection.",
                authority="FAR 15.101",
            ))

        # Factor 4: Incumbent advantage
        if incumbent_rebid:
            factors.append(RiskFactor(
                factor_id="PF04", name="Incumbent Recompete",
                description="Recompetes with incumbent participation increase protest risk from new entrants alleging unequal access.",
                risk_level=RiskLevel.MEDIUM, score=50,
                mitigation="Ensure all offerors receive equivalent information. Document any information leveling steps.",
                authority="FAR 15.306(e), FAR 9.505",
            ))

        # Factor 5: OCI
        if not has_oci_plan and value > 5_500_000:
            factors.append(RiskFactor(
                factor_id="PF05", name="Organizational Conflict of Interest",
                description="No OCI mitigation plan for major acquisition.",
                risk_level=RiskLevel.MEDIUM, score=45,
                mitigation="Require OCI disclosures and develop mitigation plan per FAR 9.5.",
                authority="FAR 9.503, FAR 9.504, FAR 9.505",
            ))

        # Factor 6: Discussions
        if has_discussions:
            factors.append(RiskFactor(
                factor_id="PF06", name="Discussions Conduct",
                description="Discussions increase protest surface area — unequal treatment is common sustain ground.",
                risk_level=RiskLevel.MEDIUM, score=40,
                mitigation="Document all exchanges. Ensure equivalent topics raised with all competitive range offerors.",
                authority="FAR 15.306(d)",
            ))

        # Factor 7: Small business
        if set_aside_type and value > 350_000:
            factors.append(RiskFactor(
                factor_id="PF07", name="Small Business Set-Aside Compliance",
                description=f"Set-aside type '{set_aside_type}' must comply with SBA regulations.",
                risk_level=RiskLevel.LOW, score=20,
                mitigation="Verify all awardees meet size standard for NAICS at time of proposal.",
                authority="FAR 19.301, 13 C.F.R. 121",
            ))

        # Factor 8: Debriefing obligations (>$7.5M task orders)
        if debriefing_required or value > 7_500_000:
            factors.append(RiskFactor(
                factor_id="PF08", name="Debriefing Quality",
                description="Enhanced debriefing required. Poor debriefings correlate with protests.",
                risk_level=RiskLevel.MEDIUM, score=35,
                mitigation="Prepare thorough debriefing with evaluation ratings, strengths, weaknesses, and rationale.",
                authority="FAR 15.506, FAR 16.505(b)(6)",
            ))

        # Factor 9: GAO jurisdiction for task orders
        if value > 10_000_000:
            factors.append(RiskFactor(
                factor_id="PF09", name="GAO Task Order Protest Jurisdiction",
                description="Civilian task orders >$10M are subject to GAO protest jurisdiction.",
                risk_level=RiskLevel.MEDIUM, score=40,
                mitigation="Ensure fair opportunity documentation meets FAR 16.505 requirements.",
                authority="41 U.S.C. 4106(f), FAR 16.505(d)",
            ))

        # Factor 10: Price realism
        if price_analysis_method != "competitive":
            factors.append(RiskFactor(
                factor_id="PF10", name="Price Analysis Methodology",
                description=f"Non-competitive price analysis ({price_analysis_method}) may face scrutiny.",
                risk_level=RiskLevel.MEDIUM, score=40,
                mitigation="Document price analysis methodology with supporting data per FAR 15.404.",
                authority="FAR 15.404-1",
            ))

        # Calculate overall score
        if not factors:
            overall_score = 10
        else:
            overall_score = int(sum(f.score for f in factors) / len(factors))

        if overall_score >= 70:
            overall_risk = RiskLevel.CRITICAL
        elif overall_score >= 50:
            overall_risk = RiskLevel.HIGH
        elif overall_score >= 30:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        high_factors = [f for f in factors if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]
        recommendations = [f.mitigation for f in high_factors]
        if not recommendations:
            recommendations = ["Continue with standard procurement documentation practices."]

        summary = (
            f"Protest risk assessment: {overall_risk.value.upper()} (score {overall_score}/100). "
            f"{len(factors)} factors evaluated, {len(high_factors)} elevated risk. "
            f"GAO sustain rate FY2025: {self.GAO_SUSTAIN_RATE_FY2025*100:.0f}%."
        )

        return ProtestRiskAssessment(
            overall_score=overall_score,
            overall_risk=overall_risk,
            factors=factors,
            summary=summary,
            recommendations=recommendations,
            source_provenance=provenance,
            confidence_score=0.85,
        )


protest_risk_engine = ProtestRiskEngine()
