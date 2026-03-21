from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import delete, func, select

from backend.core.rules_engine.seeds import APPROVAL_LADDERS, DCODES, QCODE_NODES, THRESHOLDS
from backend.database.db import AsyncSessionLocal
from backend.database.models import ApprovalLadder, AcquisitionPackage, DCode, PackageDocument, QCodeNode, Threshold

RESPONSIBLE_PARTY_BY_DCODE = {
    "D101": "Program Office",
    "D102": "COR",
    "D104": "Program Office",
    "D106": "CO",
    "D107": "Small Business Specialist",
    "D108": "CO",
    "D109": "Program Office",
    "D110": "Offeror",
    "D114": "CIO",
    "D116": "CO",
}

SOURCE_ATTRIBUTION_BY_DCODE = {
    "D101": "Generated from market research inputs and rules engine thresholds.",
    "D102": "Required because services path triggers COR workflow.",
    "D104": "Generated from acquisition package value and estimate inputs.",
    "D106": "Triggered by FAR 7.105 / TSA MD 300.25 acquisition-plan threshold.",
    "D107": "Triggered by SAT small-business review rule.",
    "D108": "Triggered by sole-source / J&A routing.",
    "D109": "Derived from requirement narrative / PWS workflow.",
    "D110": "Triggered by subcontracting-plan threshold.",
    "D114": "Triggered by IT/CIO review rule.",
    "D116": "Triggered by commercial-item path.",
}

DEMO_ROWS = [
    {
        "package_id": "demo-001",
        "title": "Checked Baggage Screening Engineering Support",
        "value": 20000000,
        "phase": "PR Validation",
        "status": "blocked",
        "deadline": "2026-03-21",
        "blocking_reason": "D114 CIO approval missing",
        "required_dcodes": ["D101", "D102", "D104", "D106", "D107", "D109", "D110", "D114"],
        "satisfied": ["D101", "D102", "D104", "D106", "D107"],
    },
    {
        "package_id": "demo-002",
        "title": "Airport Credentialing Help Desk",
        "value": 4800000,
        "phase": "CO Review",
        "status": "action",
        "deadline": "2026-03-24",
        "blocking_reason": "D109 needs revision",
        "required_dcodes": ["D101", "D102", "D104", "D107", "D109"],
        "satisfied": ["D101", "D104", "D107"],
    },
    {
        "package_id": "demo-003",
        "title": "TSA Cloud FinOps Support",
        "value": 9500000,
        "phase": "Acquisition Planning",
        "status": "blocked",
        "deadline": "2026-03-22",
        "blocking_reason": "D106 acquisition plan not accepted",
        "required_dcodes": ["D101", "D102", "D104", "D106", "D107", "D109", "D110", "D114"],
        "satisfied": ["D101", "D102", "D104", "D107", "D109"],
    },
    {
        "package_id": "demo-004",
        "title": "Canine Training Logistics Services",
        "value": 240000,
        "phase": "PR Validation",
        "status": "ready",
        "deadline": "2026-03-28",
        "blocking_reason": None,
        "required_dcodes": ["D101", "D104", "D109"],
        "satisfied": ["D101", "D104", "D109"],
    },
    {
        "package_id": "demo-005",
        "title": "Surface Transportation Threat Intel Support",
        "value": 12000000,
        "phase": "CO Review",
        "status": "action",
        "deadline": "2026-03-25",
        "blocking_reason": "Awaiting subcontracting plan from vendor",
        "required_dcodes": ["D101", "D102", "D104", "D106", "D107", "D109", "D110", "D114"],
        "satisfied": ["D101", "D102", "D104", "D107", "D109", "D114"],
    },
    {
        "package_id": "demo-006",
        "title": "Exit Lane Monitoring Hardware Refresh",
        "value": 3200000,
        "phase": "Routing",
        "status": "ready",
        "deadline": "2026-03-29",
        "blocking_reason": None,
        "required_dcodes": ["D101", "D104", "D107", "D109"],
        "satisfied": ["D101", "D104", "D107", "D109"],
    },
    {
        "package_id": "demo-007",
        "title": "TSA SOC Surge Operations",
        "value": 65000000,
        "phase": "Executive Review",
        "status": "blocked",
        "deadline": "2026-03-20",
        "blocking_reason": "HCA review package incomplete",
        "required_dcodes": ["D101", "D102", "D104", "D106", "D107", "D109", "D110", "D114"],
        "satisfied": ["D101", "D102", "D104", "D106", "D107", "D109", "D110"],
    },
]


async def seed_database() -> None:
    async with AsyncSessionLocal() as session:
        threshold_count = await session.scalar(select(func.count()).select_from(Threshold))
        if threshold_count and threshold_count > 0:
            return

        session.add_all([Threshold(**item) for item in THRESHOLDS])
        session.add_all([ApprovalLadder(**item) for item in APPROVAL_LADDERS])
        session.add_all([
            QCodeNode(
                code=item["code"],
                question_text=item["question_text"],
                branch_logic_json=json.dumps({}),
                triggered_dcodes=json.dumps(item["triggered_dcodes"]),
                system_behavior=item["system_behavior"],
                authority=item["authority"],
                confidence_level="high",
            )
            for item in QCODE_NODES
        ])
        session.add_all([
            DCode(
                code=code,
                name=name,
                description=name,
                template_id=None,
                always_required=code in {"D101", "D104", "D109"},
                condition_text=f"Generated by rules engine for {code}",
            )
            for code, name in DCODES.items()
        ])

        now = datetime.now(UTC)
        for row in DEMO_ROWS:
            package = AcquisitionPackage(
                id=row["package_id"],
                title=row["title"],
                value=row["value"],
                naics="541512",
                psc="D323",
                services=True,
                it_related=("IT" in row["title"] or "SOC" in row["title"] or "Cloud" in row["title"] or "Credentialing" in row["title"] or "Baggage" in row["title"]),
                sole_source=False,
                commercial_item=False,
                emergency=False,
                vendor_on_site=False,
                competition_type="full_and_open",
                phase=row["phase"],
                status=row["status"],
                blocking_reason=row["blocking_reason"],
                deadline=row["deadline"],
                posting_deadline_days=30 if row["value"] > 350000 else 0,
                created_at=now,
                updated_at=now,
            )
            session.add(package)
            for dcode in row["required_dcodes"]:
                session.add(
                    PackageDocument(
                        package_id=row["package_id"],
                        dcode=dcode,
                        status="satisfied" if dcode in row["satisfied"] else "missing",
                        responsible_party=RESPONSIBLE_PARTY_BY_DCODE.get(dcode, "CO"),
                        source_attribution=SOURCE_ATTRIBUTION_BY_DCODE.get(dcode),
                    )
                )

        await session.commit()
