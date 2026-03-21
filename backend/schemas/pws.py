from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.ai_output import AIGeneratedDocument, AIOutputMetadata


Severity = Literal["HIGH", "MEDIUM", "LOW"]


class ValidationFlag(BaseModel):
    rule_id: int
    rule_name: str
    paragraph: str
    severity: Severity
    original_text: str
    suggested_fix: str
    citation: str
    confidence_score: float = Field(default=0.9, ge=0, le=1)


class RedlineChange(BaseModel):
    paragraph: str
    original_text: str
    revised_text: str
    reason: str
    confidence: float = Field(ge=0, le=1)
    citations: list[str]


class QASPItem(BaseModel):
    paragraph: str
    surveillance_method: str
    metric: str
    acceptable_quality_level: str


class PRSItem(BaseModel):
    paragraph: str
    performance_standard: str
    acceptable_quality_level: str
    surveillance_method: str
    incentive: str


class PWSConvertRequest(BaseModel):
    sow_text: str
    package_id: str | None = None


class PWSConvertPayload(BaseModel):
    document_type: str
    pba_compliance_score: int
    flags: list[ValidationFlag]
    redlines: list[RedlineChange]
    structured_pws: str
    qasp_items: list[QASPItem]
    prs_matrix: list[PRSItem]
    citations: list[str]


class PWSConvertResponse(AIGeneratedDocument):
    content: PWSConvertPayload
    metadata: AIOutputMetadata


class PWSTemplateSummary(BaseModel):
    template_id: str
    name: str
    category: str
    description: str


class PWSTemplateListResponse(BaseModel):
    templates: list[PWSTemplateSummary]


class PWSTemplateGenerateRequest(BaseModel):
    template_id: str
    customization: dict[str, str] = Field(default_factory=dict)
    package_id: str | None = None


class PWSTemplateGeneratePayload(BaseModel):
    template_id: str
    name: str
    generated_pws: str
    qasp_items: list[QASPItem]
    prs_matrix: list[PRSItem]


class PWSTemplateGenerateResponse(AIGeneratedDocument):
    content: PWSTemplateGeneratePayload
    metadata: AIOutputMetadata
