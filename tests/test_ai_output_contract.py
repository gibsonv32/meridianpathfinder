from __future__ import annotations

from backend.schemas.ai_output import AIOutputMetadata


def test_ai_output_requires_acceptance_defaults_true() -> None:
    metadata = AIOutputMetadata(source_provenance=["FAR 37.602"], confidence_score=0.9)
    assert metadata.requires_acceptance is True
