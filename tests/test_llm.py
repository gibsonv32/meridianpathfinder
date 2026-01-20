from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from pydantic import BaseModel

from meridian.llm.providers import AnthropicProvider, OllamaProvider, get_provider


class ExampleSchema(BaseModel):
    foo: str
    bar: int


class _FakeTextBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class _FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, name: str, input: Dict[str, Any]):
        self.name = name
        self.input = input


@dataclass
class _FakeMessageResponse:
    content: List[Any]


class _FakeAnthropicMessages:
    def __init__(self, *, tool_output: Optional[Dict[str, Any]] = None, should_fail: bool = False):
        self._tool_output = tool_output
        self._should_fail = should_fail

    def create(self, **_: Any) -> _FakeMessageResponse:
        if self._should_fail:
            raise RuntimeError("boom")
        blocks: List[Any] = []
        if self._tool_output is not None:
            blocks.append(_FakeToolUseBlock("emit_json", self._tool_output))
        else:
            blocks.append(_FakeTextBlock("hello"))
        return _FakeMessageResponse(content=blocks)


class _FakeAnthropicClient:
    def __init__(self, *, tool_output: Optional[Dict[str, Any]] = None, should_fail: bool = False):
        self.messages = _FakeAnthropicMessages(tool_output=tool_output, should_fail=should_fail)


def test_anthropic_provider_complete(monkeypatch: pytest.MonkeyPatch):
    p = AnthropicProvider(api_key="x", model="m")
    p._client = _FakeAnthropicClient(tool_output=None, should_fail=False)  # type: ignore[attr-defined]
    # complete() should join text blocks
    assert p.complete("ping").strip() == "hello"


def test_structured_output_validates(monkeypatch: pytest.MonkeyPatch):
    p = AnthropicProvider(api_key="x", model="m")
    p._client = _FakeAnthropicClient(tool_output={"foo": "ok", "bar": 1}, should_fail=False)  # type: ignore[attr-defined]
    model = p.complete_structured("give json", ExampleSchema)
    assert isinstance(model, ExampleSchema)
    assert model.foo == "ok"
    assert model.bar == 1


def test_connection_failure_handling():
    p = AnthropicProvider(api_key="x", model="m")
    p._client = _FakeAnthropicClient(tool_output=None, should_fail=True)  # type: ignore[attr-defined]
    assert p.test_connection() is False


class _FakeHTTPXResponse:
    def __init__(self, status_code: int, json_data: Optional[dict] = None):
        self.status_code = status_code
        self._json = json_data or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self) -> dict:
        return self._json


class _FakeHTTPXClient:
    def __init__(self):
        self.calls: list[tuple[str, str, Optional[dict]]] = []

    def post(self, path: str, json: dict) -> _FakeHTTPXResponse:  # noqa: A002
        self.calls.append(("POST", path, json))
        return _FakeHTTPXResponse(200, {"response": "{\"foo\":\"ok\",\"bar\":2}"})

    def get(self, path: str) -> _FakeHTTPXResponse:
        self.calls.append(("GET", path, None))
        return _FakeHTTPXResponse(200, {"models": []})


def test_ollama_provider_complete(monkeypatch: pytest.MonkeyPatch):
    p = OllamaProvider(base_url="http://localhost:11434", model="llama3.1")
    p._client = _FakeHTTPXClient()  # type: ignore[attr-defined]
    out = p.complete("hi")
    assert out == "{\"foo\":\"ok\",\"bar\":2}"


def test_get_provider_from_config():
    p = get_provider({"llm": {"provider": "ollama", "model": "llama3.1", "base_url": "http://localhost:11434"}})
    assert p.model_name == "llama3.1"

