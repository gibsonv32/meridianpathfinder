from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: Literal["anthropic", "ollama", "openai"] = "anthropic"
    model: str = Field(default="claude-sonnet-4-20250514")
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7

