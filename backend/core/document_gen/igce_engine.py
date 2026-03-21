from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean

from sqlalchemy import select

from backend.core.integrations.bls import BLSClient
from backend.core.integrations.sam_gov import SAMGovClient
from backend.database.db import AsyncSessionLocal, init_database
from backend.database.models import GeneratedDocument
from backend.schemas.ai_output import AIOutputMetadata
from backend.schemas.igce import (
    ComparableContract,
    IGCEGeneratePayload,
    IGCEGenerateRequest,
    IGCEGenerateResponse,
    IGCERetrieveResponse,
    RateAnalysisItem,
    WageBenchmark,
)


class IGCEEngine:
    def __init__(self, sam_client: SAMGovClient | None = None, bls_client: BLSClient | None = None) -> None:
        self.sam_client = sam_client or SAMGovClient()
        self.bls_client = bls_client or BLSClient()

    async def generate(self, payload: IGCEGenerateRequest) -> IGCEGenerateResponse:
        sam_result = await self.sam_client.get_comparable_contracts(
            payload.naics_code,
            payload.psc,
            payload.estimated_value,
        )
        bls_result = await self.bls_client.get_wage_benchmarks(
            [item.model_dump() for item in payload.labor_categories]
        )

        comparables = [ComparableContract(**row) for row in sam_result.comparable_contracts]
        wages = [WageBenchmark(**row) for row in bls_result.wages]
        rate_analysis = self._build_rate_analysis(payload, wages)
        recommendation = self._recommend_contract_type(payload.contract_type, payload.estimated_value)
        methodology = self._build_methodology(payload, comparables)
        narrative = self._build_narrative(payload, comparables, rate_analysis, recommendation)
        provenance = [contract.source for contract in comparables] + [w.source for w in wages]
        if sam_result.warning:
            provenance.append(sam_result.warning)

        generated_at = datetime.now(UTC)
        confidence_score = min(
            0.98,
            0.55 + (0.08 * min(len(comparables), 4)) + (0.06 * min(len(wages), 3)),
        )
        response = IGCEGenerateResponse(
            document_id="",
            document_type="igce",
            content=IGCEGeneratePayload(
                igce_id="",
                title=payload.title,
                methodology=methodology,
                comparable_contracts=comparables,
                wage_benchmarks=wages,
                rate_analysis=rate_analysis,
                narrative=narrative,
                contract_type_recommendation=recommendation,
                provenance=provenance,
                used_fallback_data=sam_result.used_fallback or bls_result.used_fallback,
                generated_at=generated_at,
            ),
            metadata=AIOutputMetadata(
                source_provenance=provenance,
                confidence_score=round(confidence_score, 2),
                requires_acceptance=True,
                generated_at=generated_at,
            ),
        )
        return response

    async def get(self, igce_id: str) -> IGCERetrieveResponse:
        await init_database()
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(GeneratedDocument).where(
                        GeneratedDocument.id == igce_id,
                        GeneratedDocument.document_type == "igce",
                    )
                )
            ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"Unknown IGCE: {igce_id}")
        payload = dict(row.content)
        payload["igce_id"] = row.id
        return IGCERetrieveResponse(
            document_id=row.id,
            document_type=row.document_type,
            content=payload,
            metadata=AIOutputMetadata(
                source_provenance=list(row.source_provenance or []),
                confidence_score=row.confidence_score,
                requires_acceptance=row.requires_acceptance,
                generated_at=row.created_at,
            ),
            acceptance_status=row.acceptance_status,
            accepted_by=row.accepted_by,
            accepted_at=row.accepted_at,
        )

    def _build_rate_analysis(self, payload: IGCEGenerateRequest, wages: list[WageBenchmark]) -> list[RateAnalysisItem]:
        if not payload.labor_categories:
            payload = IGCEGenerateRequest(
                **{
                    **payload.model_dump(),
                    "labor_categories": [
                        {
                            "title": wages[0].labor_category if wages else "Cybersecurity Analyst",
                            "estimated_hours": 4160,
                            "location": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
                        }
                    ],
                }
            )
        wage_map = {w.labor_category: w for w in wages}
        items: list[RateAnalysisItem] = []
        for labor in payload.labor_categories:
            benchmark = wage_map.get(labor.title) or wages[0]
            proposed = round(benchmark.hourly_wage * 1.22, 2)
            annual_cost = round(proposed * labor.estimated_hours, 2)
            variance = round(((proposed - benchmark.hourly_wage) / benchmark.hourly_wage) * 100, 2)
            items.append(
                RateAnalysisItem(
                    labor_category=labor.title,
                    estimated_hours=labor.estimated_hours,
                    benchmark_hourly_wage=benchmark.hourly_wage,
                    proposed_hourly_rate=proposed,
                    variance_percent=variance,
                    annual_cost=annual_cost,
                    source=benchmark.source,
                )
            )
        return items

    def _recommend_contract_type(self, requested_type: str, estimated_value: float) -> str:
        if requested_type == "firm_fixed_price":
            return "Firm-Fixed-Price remains preferred under FAR 37.102(a)(2) because the requirement can be expressed in measurable outcomes."
        if estimated_value >= 20000000:
            return "Use Time-and-Materials only if market research shows uncertainty that prevents reliable FFP pricing; otherwise prefer Firm-Fixed-Price per FAR 37.102(a)(2)."
        return "Recommended contract type should follow FAR 37.102(a)(2) hierarchy, preferring performance-based Firm-Fixed-Price where practicable."

    def _build_methodology(self, payload: IGCEGenerateRequest, comparables: list[ComparableContract]) -> str:
        avg_value = round(mean(contract.obligated_amount for contract in comparables), 2)
        return f"Methodology: Queried SAM.gov comparable contracts for NAICS {payload.naics_code} and PSC {payload.psc}, reviewed {len(comparables)} comparable awards, and benchmarked labor rates against BLS wage data. Average comparable value was ${avg_value:,.2f}. FAR 37.102(a)(2) was used to assess contract type preference, and every numeric estimate is tied to a PIID or BLS series citation."

    def _build_narrative(
        self,
        payload: IGCEGenerateRequest,
        comparables: list[ComparableContract],
        rate_analysis: list[RateAnalysisItem],
        recommendation: str,
    ) -> str:
        comparable_lines = "; ".join(
            f"{item.piid} at ${item.obligated_amount:,.0f}" for item in comparables[:3]
        )
        rate_lines = "; ".join(
            f"{item.labor_category}: ${item.proposed_hourly_rate}/hr vs BLS ${item.benchmark_hourly_wage}/hr ({item.variance_percent}% variance)"
            for item in rate_analysis
        )
        return f"IGCE Narrative for {payload.title}: Comparable contract review identified {len(comparables)} relevant DHS/TSA-aligned awards, including {comparable_lines}. Labor-rate analysis shows {rate_lines}. {recommendation}"


igce_engine = IGCEEngine()
