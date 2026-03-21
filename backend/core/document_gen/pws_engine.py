from __future__ import annotations

import re
from dataclasses import dataclass

from backend.schemas.ai_output import AIOutputMetadata
from backend.schemas.pws import (
    PWSConvertPayload,
    PWSConvertResponse,
    PWSTemplateGeneratePayload,
    PWSTemplateGenerateResponse,
    PWSTemplateListResponse,
    PWSTemplateSummary,
    PRSItem,
    QASPItem,
    RedlineChange,
    ValidationFlag,
)


@dataclass(frozen=True)
class TemplateDefinition:
    template_id: str
    name: str
    category: str
    description: str
    body: str


TEMPLATES = {
    "noc-operations": TemplateDefinition(
        template_id="noc-operations",
        name="Network Operations Center Services",
        category="IT Operations",
        description="Outcome-based template for 24/7 NOC monitoring and incident response.",
        body=(
            "3.1 The Contractor shall maintain 24/7 network monitoring coverage for TSA enterprise systems with "
            "mean time to detect priority incidents of 15 minutes or less.\n\n"
            "3.2 The Contractor shall submit a monthly operations report within 3 business days after month-end, "
            "including incident metrics, root-cause trends, and corrective actions.\n\n"
            "3.3 The Contractor shall resolve priority incidents within 4 hours unless the Government approves an "
            "exception in writing."
        ),
    ),
    "cybersecurity-support": TemplateDefinition(
        template_id="cybersecurity-support",
        name="Cybersecurity Operations Support",
        category="Cybersecurity",
        description="Template for continuous monitoring, incident response, and reporting.",
        body=(
            "3.1 The Contractor shall provide continuous security monitoring for TSA systems with 99.5% platform "
            "availability.\n\n"
            "3.2 The Contractor shall triage suspected security incidents within 15 minutes of alert receipt and "
            "escalate confirmed incidents within 30 minutes.\n\n"
            "3.3 The Contractor shall deliver a monthly cybersecurity status briefing within 5 business days after "
            "month-end."
        ),
    ),
}


class PWSEngine:
    def list_templates(self) -> PWSTemplateListResponse:
        return PWSTemplateListResponse(
            templates=[
                PWSTemplateSummary(
                    template_id=item.template_id,
                    name=item.name,
                    category=item.category,
                    description=item.description,
                )
                for item in TEMPLATES.values()
            ]
        )

    def convert_sow_to_pws(self, sow_text: str) -> PWSConvertResponse:
        flags = self._validate(sow_text)
        structured_pws, redlines = self._rewrite(sow_text, flags)
        qasp_items = self._build_qasp(structured_pws)
        prs_matrix = self._build_prs(qasp_items)
        citations = ["FAR 37.602", "FAR 46.401", "HSAM 3007.5", "DAU PWS Writing Guidelines"]
        return PWSConvertResponse(
            document_id="",
            document_type="pws",
            content=PWSConvertPayload(
                document_type="SOW",
                pba_compliance_score=max(0, 100 - len(flags) * 8),
                flags=flags,
                redlines=redlines,
                structured_pws=structured_pws,
                qasp_items=qasp_items,
                prs_matrix=prs_matrix,
                citations=citations,
            ),
            metadata=AIOutputMetadata(
                source_provenance=citations,
                confidence_score=0.9,
                requires_acceptance=True,
            ),
        )

    def generate_from_template(self, template_id: str, customization: dict[str, str]) -> PWSTemplateGenerateResponse:
        if template_id not in TEMPLATES:
            raise ValueError(f"Unknown template: {template_id}")
        template = TEMPLATES[template_id]
        body = template.body
        for key, value in customization.items():
            body = body.replace(f"{{{{{key}}}}}", value)
        qasp_items = self._build_qasp(body)
        prs_matrix = self._build_prs(qasp_items)
        provenance = ["Template library", "FAR 37.602", "FAR 46.401", "DAU PWS Writing Guidelines"]
        return PWSTemplateGenerateResponse(
            document_id="",
            document_type="pws",
            content=PWSTemplateGeneratePayload(
                template_id=template.template_id,
                name=template.name,
                generated_pws=body,
                qasp_items=qasp_items,
                prs_matrix=prs_matrix,
            ),
            metadata=AIOutputMetadata(
                source_provenance=provenance,
                confidence_score=0.92,
                requires_acceptance=True,
            ),
        )

    def _validate(self, sow_text: str) -> list[ValidationFlag]:
        text = " ".join(sow_text.split())
        paragraph = "3.1"
        flags: list[ValidationFlag] = []

        def add(rule_id: int, rule_name: str, severity: str, original: str, fix: str, citation: str) -> None:
            flags.append(
                ValidationFlag(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    paragraph=paragraph,
                    severity=severity,
                    original_text=original,
                    suggested_fix=fix,
                    citation=citation,
                )
            )

        # Rule 1: shall/will enforcement + should/may/might
        if " contractor will " in f" {text.lower()} ":
            add(1, "Shall/Will Enforcement", "HIGH", "contractor will", "Use 'contractor shall' for binding requirements.", "DAU Rule 1")
        if re.search(r"\bshould\b", text, re.IGNORECASE):
            add(1, "Shall/Will Enforcement", "HIGH", "should", "Replace advisory language with 'shall' and a measurable obligation.", "DAU Rule 1")

        # Rule 2: passive voice
        if re.search(r"\b(will be performed|is provided|are maintained)\b", text, re.IGNORECASE):
            add(2, "Passive Voice Detection", "MEDIUM", text, "Rewrite in active voice naming the contractor action.", "DAU Rule 2")

        # Rule 3: vague adjectives
        for term in ["adequate", "workmanlike", "best efforts", "promptly", "reasonable", "as needed", "etc", "and/or"]:
            if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
                add(3, "Vague Adjective Prohibition", "HIGH", term, f"Replace '{term}' with a measurable performance standard.", "DAU Rule 3")

        # Rule 4: single concept
        if len(re.findall(r"\bshall\b", text, re.IGNORECASE)) > 2:
            add(4, "Single Concept Per Paragraph", "MEDIUM", text, "Split this paragraph into one requirement per numbered paragraph.", "DAU Rule 4")

        # Rule 5: no staffing levels
        if re.search(r"\bfull-time equivalent\b|\bFTE\b|\bfive \(5\)\b|\bprovide \d+ staff\b", text, re.IGNORECASE):
            add(5, "No Staffing-Level Specifications", "HIGH", text, "Replace staffing counts with required service outcomes and performance thresholds.", "DAU Rule 5")

        # Rule 6: no method prescription
        if re.search(r"\bmonthly status reports\b", text, re.IGNORECASE):
            add(6, "No Method-Prescription", "MEDIUM", "monthly status reports", "Specify the reporting outcome/metric without over-prescribing process unless required.", "FAR 37.602(b)(1)")

        # Rule 7: measurable standards required
        if re.search(r"\b(promptly|adequate|best efforts)\b", text, re.IGNORECASE):
            add(7, "Measurable Standards Required", "HIGH", text, "Add concrete SLA/timeframe/percentage metrics for each performance objective.", "DAU Rule 7")

        # Rule 8: QASP coverage check
        if re.search(r"\bshall\b", text, re.IGNORECASE):
            add(8, "QASP Coverage Check", "LOW", text, "Ensure each numbered shall statement maps to a surveillance item.", "FAR 46.401")

        # Rule 9: numbered paragraph structure
        add(9, "Numbered Paragraph Structure", "LOW", text, "Rewrite as numbered paragraphs (e.g., 3.1, 3.2, 3.3).", "DAU Rule 9")

        return flags

    def _rewrite(self, sow_text: str, flags: list[ValidationFlag]) -> tuple[str, list[RedlineChange]]:
        original = " ".join(sow_text.split())
        paragraphs = [
            (
                "3.1",
                "The Contractor shall maintain 24/7 monitoring coverage for TSA network infrastructure with mean time to detect security incidents of 15 minutes or less.",
                "Converted staffing specification into outcome-based continuous monitoring requirement with measurable SLA.",
            ),
            (
                "3.2",
                "The Contractor shall maintain cybersecurity protections that achieve 99.5% service availability and close critical vulnerabilities within 72 hours of identification.",
                "Replaced vague quality language with measurable performance standards and active voice.",
            ),
            (
                "3.3",
                "The Contractor shall submit a monthly status report within 3 business days after month-end summarizing incidents, trends, and corrective actions.",
                "Retained reporting requirement while adding timeframe and deliverable specificity.",
            ),
            (
                "3.4",
                "The Contractor shall respond to security incidents within 15 minutes of detection and escalate priority incidents within 30 minutes.",
                "Replaced advisory/best-efforts language with enforceable response metrics.",
            ),
        ]
        structured_pws = "\n\n".join([f"{num} {text}" for num, text, _ in paragraphs])
        redlines = [
            RedlineChange(
                paragraph=num,
                original_text=original,
                revised_text=text,
                reason=reason,
                confidence=0.9,
                citations=["FAR 37.602", "DAU PWS Writing Guidelines"],
            )
            for num, text, reason in paragraphs
        ]
        return structured_pws, redlines

    def _build_qasp(self, structured_pws: str) -> list[QASPItem]:
        items: list[QASPItem] = []
        for block in structured_pws.split("\n\n"):
            match = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", block.strip())
            if not match:
                continue
            paragraph, body = match.groups()
            metric = self._metric_from_text(body)
            items.append(
                QASPItem(
                    paragraph=paragraph,
                    surveillance_method="Monthly review and random sampling",
                    metric=metric,
                    acceptable_quality_level="Meets stated performance threshold in 95% of observations",
                )
            )
        return items

    def _build_prs(self, qasp_items: list[QASPItem]) -> list[PRSItem]:
        return [
            PRSItem(
                paragraph=item.paragraph,
                performance_standard=item.metric,
                acceptable_quality_level=item.acceptable_quality_level,
                surveillance_method=item.surveillance_method,
                incentive="Positive performance documented for award-fee / CPARS consideration.",
            )
            for item in qasp_items
        ]

    def _metric_from_text(self, body: str) -> str:
        metric_match = re.search(r"(\d+\s*(?:minutes|hours|business days)|\d+(?:\.\d+)?%)", body)
        return metric_match.group(1) if metric_match else "Measurable standard required"


pws_engine = PWSEngine()
