from __future__ import annotations

import json
import os
from contextlib import contextmanager
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


class OpenAIProvider:
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        base_url: str = "https://api.openai.com/v1", 
        model: str = "gpt-4",
        temperature: float = 0.3
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY") or "not-needed"
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._client: Optional[httpx.Client] = None

    @property
    def model_name(self) -> str:
        return self._model

    @contextmanager
    def _get_client(self):
        """Context manager for httpx client to ensure proper cleanup."""
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client = httpx.Client(
            base_url=self._base_url, 
            headers=headers, 
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
        try:
            yield client
        finally:
            client.close()

    def complete(
        self, 
        prompt: str, 
        system: Optional[str] = None, 
        max_tokens: int = 4096,
        temperature: Optional[float] = None
    ) -> str:
        """Complete a prompt with optional system message."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature or self._temperature,
            "stream": False
        }
        
        try:
            with self._get_client() as client:
                resp = client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                if "choices" not in data or not data["choices"]:
                    raise ValueError("Invalid response: no choices returned")
                
                return str(data["choices"][0]["message"]["content"]).strip()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError("Invalid API key for OpenAI provider") from e
            elif e.response.status_code == 429:
                raise RuntimeError("Rate limit exceeded for OpenAI API") from e
            elif e.response.status_code == 404:
                raise RuntimeError(f"Model {self._model} not found") from e
            else:
                raise RuntimeError(f"OpenAI API error: {e.response.text}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Connection error to {self._base_url}: {str(e)}") from e

    def complete_structured(
        self, 
        prompt: str, 
        schema: Type[TModel], 
        system: Optional[str] = None
    ) -> TModel:
        """Complete with structured output using JSON mode."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        
        # Enhanced prompt with schema
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        enhanced_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond with valid JSON that matches this exact schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Respond ONLY with the JSON object, no additional text."
        )
        messages.append({"role": "user", "content": enhanced_prompt})
        
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.1,  # Lower temperature for structured output
            "response_format": {"type": "json_object"}  # Enable JSON mode if supported
        }
        
        try:
            with self._get_client() as client:
                resp = client.post("/chat/completions", json=payload)
                
                # Fallback if JSON mode not supported (e.g., local models)
                if resp.status_code == 400 and "response_format" in resp.text:
                    del payload["response_format"]
                    resp = client.post("/chat/completions", json=payload)
                
                resp.raise_for_status()
                data = resp.json()
                
                content = data["choices"][0]["message"]["content"].strip()
                
                # Try to extract JSON if wrapped in markdown
                if "```json" in content:
                    start = content.index("```json") + 7
                    end = content.index("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.index("```") + 3
                    end = content.index("```", start)
                    content = content[start:end].strip()
                
                # Validate and parse
                try:
                    return schema.model_validate_json(content)
                except Exception as e:
                    # Try to parse as dict first, then validate
                    try:
                        data_dict = json.loads(content)
                        return schema.model_validate(data_dict)
                    except:
                        raise ValueError(f"Failed to parse structured output: {e}") from e
                        
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"OpenAI API error during structured completion: {e.response.text}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Connection error during structured completion: {str(e)}") from e

    def test_connection(self) -> bool:
        """Test if the connection to the OpenAI API is working."""
        try:
            with self._get_client() as client:
                # Try listing models first (standard OpenAI endpoint)
                try:
                    resp = client.get("/models")
                    if resp.status_code == 200:
                        return True
                except:
                    pass
                
                # Fallback: try a minimal completion
                resp = client.post(
                    "/chat/completions",
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    }
                )
                return resp.status_code == 200
        except Exception:
            return False

    def __del__(self):
        """Ensure client is closed on deletion."""
        if self._client:
            self._client.close()


def get_provider(config: dict, project_path: Optional["Path"] = None) -> LLMProvider:
    from pathlib import Path
    
    llm_cfg = config.get("llm") if isinstance(config.get("llm"), dict) else {}
    provider = (llm_cfg.get("provider") or "anthropic").lower()
    model = llm_cfg.get("model")

    # Create base provider
    if provider == "dgx":
        # Use DGX router for dual-model routing
        try:
            from meridian.llm.router import get_dgx_provider
            return get_dgx_provider(
                fast_port=llm_cfg.get("fast_port", 30001),
                reasoning_port=llm_cfg.get("reasoning_port", 30002),
                host=llm_cfg.get("host", "localhost"),
            )
        except ImportError:
            raise ValueError("DGX router not available. Copy deploy/llm_router.py to meridian/llm/router.py")
    elif provider == "ollama":
        base_url = llm_cfg.get("base_url") or "http://localhost:11434"
        base_provider = OllamaProvider(base_url=base_url, model=model or "llama3.1")
    elif provider == "openai":
        base_url = llm_cfg.get("base_url") or "https://api.openai.com/v1"
        temperature = llm_cfg.get("temperature", 0.3)
        base_provider = OpenAIProvider(
            api_key=llm_cfg.get("api_key"), 
            base_url=base_url, 
            model=model or "gpt-4",
            temperature=temperature
        )
    elif provider == "anthropic":
        base_provider = AnthropicProvider(api_key=llm_cfg.get("api_key"), model=model or "claude-sonnet-4-20250514")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    # Check if enhanced intelligence is enabled
    intelligence_cfg = llm_cfg.get("intelligence", {})
    if intelligence_cfg.get("enabled", False) and project_path:
        from meridian.llm.intelligence import EnhancedLLMProvider
        return EnhancedLLMProvider(
            base_provider=base_provider,
            project_path=project_path,
            enable_memory=intelligence_cfg.get("memory", True),
            enable_few_shot=intelligence_cfg.get("few_shot", True),
            enable_optimization=intelligence_cfg.get("optimization", True)
        )
    
    return base_provider
