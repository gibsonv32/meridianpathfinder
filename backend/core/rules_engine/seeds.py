from __future__ import annotations

from datetime import date

THRESHOLDS = [
    {
        "name": "sat",
        "value": 350000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 2.101",
        "overlay_level": 0,
    },
    {
        "name": "micro_purchase",
        "value": 15000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 2.101",
        "overlay_level": 0,
    },
    {
        "name": "commercial_sap",
        "value": 9000000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 13.5",
        "overlay_level": 0,
    },
    {
        "name": "cost_data",
        "value": 2500000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 15.403",
        "overlay_level": 0,
    },
    {
        "name": "subcontracting_plan",
        "value": 900000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 19.702",
        "overlay_level": 0,
    },
    {
        "name": "acquisition_plan",
        "value": 5500000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 7.105/TSA MD 300.25",
        "overlay_level": 3,
    },
    {
        "name": "ssac_encouraged",
        "value": 50000000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 15.308",
        "overlay_level": 0,
    },
    {
        "name": "ssac_required",
        "value": 100000000,
        "unit": "USD",
        "effective_date": date(2025, 10, 1),
        "expiration_date": None,
        "authority": "FAR 15.308",
        "overlay_level": 0,
    },
]

APPROVAL_LADDERS = [
    {
        "document_type": "J&A",
        "min_value": 0,
        "max_value": 800000,
        "approver_role": "CO",
        "authority": "FAR 6.304(a)(1)",
        "effective_date": date(2025, 10, 1),
    },
    {
        "document_type": "J&A",
        "min_value": 800000,
        "max_value": 15500000,
        "approver_role": "Competition Advocate",
        "authority": "FAR 6.304(a)(2)",
        "effective_date": date(2025, 10, 1),
    },
    {
        "document_type": "J&A",
        "min_value": 15500000,
        "max_value": 100000000,
        "approver_role": "HCA",
        "authority": "FAR 6.304(a)(3)",
        "effective_date": date(2025, 10, 1),
    },
    {
        "document_type": "J&A",
        "min_value": 100000000,
        "max_value": None,
        "approver_role": "Senior Procurement Executive",
        "authority": "FAR 6.304(a)(4)",
        "effective_date": date(2025, 10, 1),
    },
]

QCODE_NODES = [
    {"code": "Q1", "question_text": "New requirement?", "authority": "FedProcure Q-code tree", "triggered_dcodes": [], "system_behavior": "route_intake"},
    {"code": "Q2", "question_text": "Exceeds SAT?", "authority": "FAR 2.101", "triggered_dcodes": ["D101", "D102", "D104", "D107", "D109"], "system_behavior": "check_sat"},
    {"code": "Q4", "question_text": "Sole source?", "authority": "FAR 6.302 / 6.304", "triggered_dcodes": ["D108"], "system_behavior": "check_ja"},
    {"code": "Q5", "question_text": "Includes services?", "authority": "FAR Part 37", "triggered_dcodes": ["D102", "D109"], "system_behavior": "check_services"},
    {"code": "Q6", "question_text": "Vendor on site?", "authority": "FAR 37.104", "triggered_dcodes": [], "system_behavior": "check_personal_services"},
    {"code": "Q7", "question_text": "IT-related?", "authority": "TSA CIO / ITAR control", "triggered_dcodes": ["D114"], "system_behavior": "check_it"},
    {"code": "Q8", "question_text": "Emergency/urgency?", "authority": "FAR 6.302-2", "triggered_dcodes": [], "system_behavior": "check_urgency"},
    {"code": "Q9", "question_text": "Commercial item?", "authority": "FAR Part 12", "triggered_dcodes": ["D116"], "system_behavior": "check_commercial"},
    {"code": "Q10", "question_text": "SB set-aside feasible?", "authority": "FAR Part 19", "triggered_dcodes": ["D107", "D110"], "system_behavior": "check_sb"},
]

DCODES = {
    "D101": "Market Research",
    "D102": "COR Nomination",
    "D104": "IGCE",
    "D106": "Acquisition Plan",
    "D107": "SB Review 700-22",
    "D108": "J&A",
    "D109": "PWS/SOW/SOO",
    "D110": "Subcontracting Plan 700-23",
    "D114": "CIO/ITAR Approval",
    "D116": "Commercial D&F",
}
