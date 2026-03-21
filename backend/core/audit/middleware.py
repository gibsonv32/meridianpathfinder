from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.audit.audit_service import audit_service


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if self._should_skip(request):
            return await call_next(request)

        raw_body = await request.body()
        request._body = raw_body
        before_state = self._parse_json(raw_body)

        response = await call_next(request)

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        after_state = self._parse_json(response_body)

        if response.status_code < 500:
            await audit_service.append_event(
                actor=self._infer_actor(request),
                action_type=self._infer_action_type(request.method),
                target_type=self._infer_target_type(request.url.path),
                target_id=self._infer_target_id(request.url.path, before_state, after_state),
                package_id=self._infer_package_id(request.url.path, before_state, after_state),
                before_state=jsonable_encoder(before_state) if before_state is not None else None,
                after_state=jsonable_encoder(after_state) if after_state is not None else None,
                source_provenance=[f"HTTP {request.method} {request.url.path}"],
                rationale=None,
            )

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    def _should_skip(self, request: Request) -> bool:
        return request.method == "GET" or request.url.path == "/api/v1/health"

    def _parse_json(self, body: bytes) -> dict[str, Any] | list[Any] | None:
        if not body:
            return None
        try:
            return json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _infer_actor(self, request: Request) -> str:
        return request.headers.get("x-actor") or request.headers.get("x-user") or "system"

    def _infer_action_type(self, method: str) -> str:
        return {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "override",
        }.get(method, "review")

    def _infer_target_type(self, path: str) -> str:
        segments = [segment for segment in path.split("/") if segment]
        if "packages" in segments:
            return "package"
        if "documents" in segments:
            return "document"
        if "rules" in segments:
            return "threshold" if "thresholds" in segments else "rule"
        if "igce" in segments:
            return "igce"
        if "pws" in segments:
            return "pws"
        return "rule"

    def _infer_target_id(self, path: str, before_state: Any, after_state: Any) -> str:
        segments = [segment for segment in path.split("/") if segment]
        if isinstance(after_state, dict):
            for key in ("package_id", "document_id", "igce_id", "id", "name"):
                value = after_state.get(key)
                if isinstance(value, str):
                    return value
        if isinstance(before_state, dict):
            for key in ("package_id", "document_id", "igce_id", "name"):
                value = before_state.get(key)
                if isinstance(value, str):
                    return value
        if "documents" in segments:
            idx = segments.index("documents")
            if len(segments) > idx + 1:
                return segments[idx + 1]
        if "packages" in segments:
            idx = segments.index("packages")
            if len(segments) > idx + 1 and segments[idx + 1] != "packages":
                return segments[idx + 1]
        if segments:
            return segments[-1]
        return "unknown"

    def _infer_package_id(self, path: str, before_state: Any, after_state: Any) -> str | None:
        if isinstance(after_state, dict) and isinstance(after_state.get("package_id"), str):
            return after_state["package_id"]
        if isinstance(before_state, dict) and isinstance(before_state.get("package_id"), str):
            return before_state["package_id"]
        segments = [segment for segment in path.split("/") if segment]
        if "packages" in segments:
            idx = segments.index("packages")
            if len(segments) > idx + 1:
                return segments[idx + 1]
        return None
