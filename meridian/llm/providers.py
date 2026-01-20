from __future__ import annotations

import os
from typing import Optional, Protocol, Type, TypeVar, cast

import httpx
from anthropic import Anthropic
from anthropic.types import ToolParam
from pydantic import BaseModel


class LLMProvider(Protocol):
    """LLM provider interface."""

    @property
    def model_name(self) -> str: ...

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str: ...

    def complete_structured(
        self, prompt: str, schema: Type[BaseModel], system: Optional[str] = None
    ) -> BaseModel: ...

    def test_connection(self) -> bool: ...


TModel = TypeVar("TModel", bound=BaseModel)


class AnthropicProvider:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model
        self._client = Anthropic(api_key=self._api_key) if self._api_key else None

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        if not self._client:
            raise RuntimeError("Anthropic API key not set (ANTHROPIC_API_KEY).")
        messages = [{"role": "user", "content": prompt}]
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        # anthropic SDK returns content blocks; join any text blocks
        parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(cast(str, block.text))
        return "\n".join(parts).strip()

    def complete_structured(self, prompt: str, schema: Type[TModel], system: Optional[str] = None) -> TModel:
        """
        Use Anthropic tool-use to extract structured JSON, then validate via Pydantic.
        """
        if not self._client:
            raise RuntimeError("Anthropic API key not set (ANTHROPIC_API_KEY).")

        tool: ToolParam = {
            "name": "emit_json",
            "description": "Return a JSON object matching the provided schema.",
            "input_schema": schema.model_json_schema(),
        }

        resp = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit_json"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "emit_json":
                # block.input is a dict
                return schema.model_validate(getattr(block, "input"))

        raise RuntimeError("Anthropic did not return tool_use output for emit_json.")

    def test_connection(self) -> bool:
        if not self._client:
            return False
        try:
            _ = self._client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.Client(base_url=self._base_url, timeout=20.0)

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        payload = {"model": self._model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        resp = self._client.post("/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("response", "")).strip()

    def complete_structured(self, prompt: str, schema: Type[TModel], system: Optional[str] = None) -> TModel:
        json_prompt = (
            prompt
            + "\n\nReturn ONLY valid JSON that matches this schema:\n"
            + schema.model_json_schema().__repr__()
        )
        text = self.complete(json_prompt, system=system, max_tokens=4096)
        return schema.model_validate_json(text)

    def test_connection(self) -> bool:
        try:
            resp = self._client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False


def get_provider(config: dict) -> LLMProvider:
    llm_cfg = config.get("llm") if isinstance(config.get("llm"), dict) else {}
    provider = (llm_cfg.get("provider") or "anthropic").lower()
    model = llm_cfg.get("model")

    if provider == "ollama":
        base_url = llm_cfg.get("base_url") or "http://localhost:11434"
        return OllamaProvider(base_url=base_url, model=model or "llama3.1")
    if provider == "anthropic":
        return AnthropicProvider(api_key=llm_cfg.get("api_key"), model=model or "claude-sonnet-4-20250514")

    raise ValueError(f"Unsupported LLM provider: {provider}")
