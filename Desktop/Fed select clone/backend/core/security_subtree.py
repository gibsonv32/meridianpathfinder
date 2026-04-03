"""
Security Sub-Tree Expansion (Pattern 2)
Expands D120 (Security Requirements) into 8 conditional sub-codes.

D120 is currently a single blocking gate in the completeness validator
that tells the CO nothing actionable. This module expands it into
granular, condition-driven sub-codes so the CO knows exactly which
security artifacts to pursue.

Architecture:
- Pure deterministic (Tier 1) — no AI, no Q-code changes
- PolicyService calls expand_security_subcodes() after D120 triggers
- Sub-codes appear as additional required D-codes in completeness response
- D142 (FedRAMP) aliases to D120.03 for backward compatibility
- Non-waivable sub-codes block at Solicitation gate (consistent with D120)

References:
- FedProcure_Phase24_26_Spec.md, Pattern 2
- CLAUDE.md Phase 4 D-code definitions (D101-D145)
- FAR 4.13, FISMA, FedRAMP, 49 CFR 1572, NIST 800-53
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


# ─── Sub-Code Definitions ────────────────────────────────────────────────────

@dataclass(frozen=True)
class SecuritySubCode:
    """A conditional security sub-code under D120."""
    code: str                    # e.g. "D120.01"
    name: str                    # Human-readable name
    trigger_conditions: dict     # param_name -> required_value (all must match)
    responsible_party: str       # CO, COR, Contractor, Security Officer
    far_authorities: list[str]   # Governing regulations
    blocking: bool               # If True, non-waivable at Solicitation gate
    description: str             # What artifact/action is required
    ucf_section: str = "H"      # Default UCF section for security items
    effective_date: date = field(default_factory=lambda: date(2025, 10, 1))
    expiration_date: date | None = None


# The 8 sub-codes from Pattern 2 spec
SECURITY_SUBCODES: list[SecuritySubCode] = [
    SecuritySubCode(
        code="D120.01",
        name="Personnel Security & Clearances",
        trigger_conditions={"on_site": True},
        # Also triggers if classified=True, handled via _check_trigger
        responsible_party="CO / Contractor",
        far_authorities=["FAR 4.13", "HSAR 3004.72", "TSA MD 300.9"],
        blocking=True,
        description="Personnel security clearance requirements: background investigations, "
                    "suitability determinations, and position sensitivity designations.",
    ),
    SecuritySubCode(
        code="D120.02",
        name="FISMA/SSP & ATO",
        trigger_conditions={"is_it": True, "cloud_only": False},
        responsible_party="Contractor / COR",
        far_authorities=["FAR 39.105", "FISMA", "NIST 800-53", "HSAM 3052.204-71"],
        blocking=True,
        description="Federal Information Security Management Act compliance: System Security Plan, "
                    "Authority to Operate (ATO), NIST 800-53 security control baseline.",
    ),
    SecuritySubCode(
        code="D120.03",
        name="FedRAMP Authorization",
        trigger_conditions={"is_it": True, "cloud": True},
        responsible_party="Contractor",
        far_authorities=["OMB A-130", "FedRAMP.gov", "NIST 800-53"],
        blocking=False,  # Can proceed without FedRAMP if using on-prem alternative
        description="FedRAMP authorization for cloud service offerings: JAB P-ATO or "
                    "Agency ATO at appropriate impact level (Low/Moderate/High).",
    ),
    SecuritySubCode(
        code="D120.04",
        name="TSA Facility Access & TWIC",
        trigger_conditions={"on_site": True, "tsa_facilities": True},
        responsible_party="Contractor / COR",
        far_authorities=["6 U.S.C. §1520a", "49 CFR 1572", "TSA TWIC SOP"],
        blocking=True,
        description="Transportation Worker Identification Credential requirements: "
                    "TWIC enrollment, TSA badge/access credentialing plan, escort procedures.",
    ),
    SecuritySubCode(
        code="D120.05",
        name="Sensitive Security Information (SSI)",
        trigger_conditions={"is_tsa": True, "handles_security_info": True},
        responsible_party="CO / Contractor",
        far_authorities=["49 U.S.C. §114(r)", "49 CFR Part 1520", "HSAM 3052.204-71"],
        blocking=True,
        description="SSI handling requirements: access controls, marking requirements, "
                    "storage/transmission standards, non-disclosure agreements.",
    ),
    SecuritySubCode(
        code="D120.06",
        name="Incident Response & Breach Notification",
        trigger_conditions={"is_it": True},
        # Also triggers if handles_pii=True, handled via _check_trigger
        responsible_party="Contractor / COR",
        far_authorities=["OMB A-130", "FISMA", "FAR 52.239-1"],
        blocking=False,
        description="Incident response plan requirements: breach notification timelines, "
                    "POC identification, reporting chain, remediation procedures.",
    ),
    SecuritySubCode(
        code="D120.07",
        name="Data Classification & Marking",
        trigger_conditions={"has_cui": True},
        # Also triggers if classified=True, handled via _check_trigger
        responsible_party="CO / Contractor",
        far_authorities=["NIST 800-60", "OMB A-130", "32 CFR Part 2002"],
        blocking=False,
        description="Data classification and marking requirements: CUI categories, "
                    "marking standards, handling/destruction procedures.",
    ),
    SecuritySubCode(
        code="D120.08",
        name="Contractor Cybersecurity Posture",
        trigger_conditions={"is_it": True, "integrates_federal_network": True},
        responsible_party="Contractor",
        far_authorities=["NIST CSF", "CISA BOD 22-01", "HSAR 3052.204-72"],
        blocking=False,
        description="Contractor cybersecurity posture assessment: NIST CSF alignment, "
                    "supply chain risk management, vulnerability disclosure program.",
    ),
]

# D142 alias — existing D142 (FedRAMP Authorization) resolves to D120.03
D142_ALIAS = "D120.03"

# Non-waivable sub-codes at Solicitation gate
NON_WAIVABLE_SUBCODES = frozenset(
    sc.code for sc in SECURITY_SUBCODES if sc.blocking
)
# Should be: D120.01, D120.02, D120.04, D120.05


# ─── Trigger Evaluation ──────────────────────────────────────────────────────

def _check_trigger(subcode: SecuritySubCode, params: dict[str, Any]) -> bool:
    """Check whether a security sub-code triggers for given acquisition params.

    Each sub-code has a dict of trigger_conditions. All must match for the
    sub-code to fire. Some sub-codes have additional OR conditions (e.g.,
    D120.01 triggers if on_site=True OR classified=True).
    """
    # Special OR-condition handling per sub-code
    if subcode.code == "D120.01":
        # Personnel security: on_site OR classified
        return params.get("on_site", False) or params.get("classified", False)

    if subcode.code == "D120.06":
        # Incident response: is_it OR handles_pii
        return params.get("is_it", False) or params.get("handles_pii", False)

    if subcode.code == "D120.07":
        # Data classification: has_cui OR classified
        return params.get("has_cui", False) or params.get("classified", False)

    if subcode.code == "D120.08":
        # Cyber posture: is_it AND integrates_federal_network AND value > $5.5M
        return (
            params.get("is_it", False)
            and params.get("integrates_federal_network", False)
            and params.get("estimated_value", 0) > 5_500_000
        )

    # Default: all trigger_conditions must match
    for param_name, required_value in subcode.trigger_conditions.items():
        actual = params.get(param_name, None)
        if actual is None:
            return False
        if isinstance(required_value, bool):
            if bool(actual) != required_value:
                return False
        elif actual != required_value:
            return False
    return True


def expand_security_subcodes(
    params: dict[str, Any],
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    """Expand D120 into applicable security sub-codes based on acquisition params.

    Args:
        params: Acquisition parameters including:
            - is_it: bool — IT-related acquisition
            - on_site: bool — Contractor works on government site
            - tsa_facilities: bool — Work at TSA facilities
            - is_tsa: bool — TSA acquisition (auto-inferred from sub_agency)
            - cloud: bool — Cloud services involved
            - cloud_only: bool — Pure cloud (no on-prem)
            - classified: bool — Involves classified information
            - has_cui: bool — Involves CUI
            - handles_pii: bool — Handles PII
            - handles_security_info: bool — Handles SSI
            - integrates_federal_network: bool — Connects to federal network
            - estimated_value: float — Contract value
        as_of: Date for effective-date filtering (default: today)

    Returns:
        List of triggered sub-code dicts, each with:
            code, name, responsible_party, far_authorities, blocking,
            description, ucf_section
    """
    if as_of is None:
        as_of = date.today()

    # Auto-infer is_tsa from sub_agency if not explicitly set
    if not params.get("is_tsa"):
        sub = (params.get("sub_agency") or "").upper()
        if sub in ("TSA", "TRANSPORTATION SECURITY ADMINISTRATION"):
            params = {**params, "is_tsa": True}

    # Auto-infer handles_security_info for TSA IT
    if params.get("is_tsa") and params.get("is_it"):
        if "handles_security_info" not in params:
            params = {**params, "handles_security_info": True}

    triggered = []
    for sc in SECURITY_SUBCODES:
        # Effective date check
        if sc.effective_date > as_of:
            continue
        if sc.expiration_date and sc.expiration_date <= as_of:
            continue

        if _check_trigger(sc, params):
            triggered.append({
                "code": sc.code,
                "name": sc.name,
                "responsible_party": sc.responsible_party,
                "far_authorities": sc.far_authorities,
                "blocking": sc.blocking,
                "description": sc.description,
                "ucf_section": sc.ucf_section,
                "status": "missing",  # Default — completeness validator updates
            })

    return triggered


def resolve_d142_alias() -> str:
    """D142 (FedRAMP Authorization) is aliased to D120.03.
    Queries for D142 should resolve to D120.03."""
    return D142_ALIAS


def get_non_waivable_subcodes() -> frozenset[str]:
    """Return set of sub-codes that cannot be waived at Solicitation gate."""
    return NON_WAIVABLE_SUBCODES


def get_all_subcodes() -> list[dict[str, Any]]:
    """Return metadata for all 8 sub-codes (for docs/UI display)."""
    return [
        {
            "code": sc.code,
            "name": sc.name,
            "trigger_conditions": sc.trigger_conditions,
            "responsible_party": sc.responsible_party,
            "far_authorities": sc.far_authorities,
            "blocking": sc.blocking,
            "description": sc.description,
        }
        for sc in SECURITY_SUBCODES
    ]


# ─── Integration with PolicyService ─────────────────────────────────────────

def enrich_completeness_with_security(
    completeness_result: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Post-process completeness validator output to inject security sub-codes.

    When D120 appears in the required D-codes, expand it into applicable
    sub-codes. The original D120 entry is preserved (parent), and sub-codes
    appear as additional entries in the documents list.

    Args:
        completeness_result: Output from CompletenessValidator.validate()
        params: Acquisition parameters (same as expand_security_subcodes)

    Returns:
        Enriched completeness result with security_subcodes field and
        expanded document list.
    """
    # Check if D120 is in the required docs
    docs = completeness_result.get("documents", [])
    has_d120 = any(d.get("dcode") == "D120" for d in docs)

    if not has_d120:
        completeness_result["security_subcodes"] = []
        return completeness_result

    # Expand sub-codes
    subcodes = expand_security_subcodes(params)
    completeness_result["security_subcodes"] = subcodes

    # Check which sub-codes are satisfied by docs_in_hand
    docs_in_hand = set()
    for d in docs:
        if d.get("status") in ("satisfied", "pending"):
            # Check if any sub-code-specific doc is present
            dcode = d.get("dcode", "")
            if dcode.startswith("D120."):
                docs_in_hand.add(dcode)

    # Inject sub-code entries into document list
    for sc in subcodes:
        sc_doc = {
            "dcode": sc["code"],
            "document_type": f"Security: {sc['name']}",
            "status": "satisfied" if sc["code"] in docs_in_hand else "missing",
            "responsible_party": sc["responsible_party"],
            "far_authority": ", ".join(sc["far_authorities"]),
            "ucf_section": sc["ucf_section"],
            "blocking": sc["blocking"],
            "notes": sc["description"],
            "parent_dcode": "D120",
        }
        docs.append(sc_doc)

    # Update counts
    total_subcodes = len(subcodes)
    satisfied_subcodes = sum(1 for sc in subcodes if sc["code"] in docs_in_hand)
    blocking_missing = sum(
        1 for sc in subcodes
        if sc["blocking"] and sc["code"] not in docs_in_hand
    )

    completeness_result["security_summary"] = {
        "total_subcodes": total_subcodes,
        "satisfied": satisfied_subcodes,
        "missing": total_subcodes - satisfied_subcodes,
        "blocking_missing": blocking_missing,
        "non_waivable_codes": sorted(NON_WAIVABLE_SUBCODES & {s["code"] for s in subcodes}),
        "package_ready_override": blocking_missing == 0,
    }

    # If any blocking sub-codes are missing, package is not ready
    if blocking_missing > 0:
        completeness_result["package_ready"] = False

    return completeness_result
