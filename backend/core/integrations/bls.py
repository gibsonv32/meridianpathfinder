from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BLSBenchmarkResult:
    wages: list[dict]
    used_fallback: bool


class BLSClient:
    async def get_wage_benchmarks(self, labor_categories: list[dict]) -> BLSBenchmarkResult:
        if not labor_categories:
            labor_categories = [
                {"title": "Cybersecurity Analyst", "estimated_hours": 2080, "location": "Washington-Arlington-Alexandria, DC-VA-MD-WV"},
                {"title": "Network Operations Specialist", "estimated_hours": 2080, "location": "Washington-Arlington-Alexandria, DC-VA-MD-WV"},
            ]
        wages = []
        for category in labor_categories:
            title = category["title"]
            if "cyber" in title.lower():
                wages.append({
                    "labor_category": title,
                    "bls_series": "15-1212",
                    "hourly_wage": 71.25,
                    "source": "BLS OEWS series 15-1212",
                })
            elif "network" in title.lower() or "noc" in title.lower():
                wages.append({
                    "labor_category": title,
                    "bls_series": "15-1244",
                    "hourly_wage": 58.4,
                    "source": "BLS OEWS series 15-1244",
                })
            else:
                wages.append({
                    "labor_category": title,
                    "bls_series": "13-1199",
                    "hourly_wage": 52.0,
                    "source": "BLS OEWS fallback series 13-1199",
                })
        return BLSBenchmarkResult(wages=wages, used_fallback=True)
