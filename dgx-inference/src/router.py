"""
DGX Inference Router - Routes requests between Claude (coding) and SGLang (reasoning)

OpenAI-compatible API with automatic task detection and streaming support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal, Optional

import anthropic
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import Settings, TaskType, get_settings

# =============================================================================
# Logging Setup
# =============================================================================
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models (OpenAI-compatible)
# =============================================================================
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="auto", description="Model or routing hint")
    messages: list[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    # Custom field for explicit routing
    task_type: Optional[Literal["coding", "reasoning", "auto"]] = "auto"


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage


# =============================================================================
# Backend Clients
# =============================================================================
class ClaudeBackend:
    """Anthropic Claude API backend for coding tasks."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
    
    async def complete(
        self,
        messages: list[ChatMessage],
        max_tokens: int,
        temperature: float,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """Generate completion using Claude."""
        
        # Convert to Anthropic format
        system_msg = None
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        if stream:
            return self._stream_response(anthropic_messages, system_msg, max_tokens, temperature)
        else:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg or "",
                messages=anthropic_messages,
            )
            return response.content[0].text
    
    async def _stream_response(
        self,
        messages: list[dict],
        system: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream response from Claude."""
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def health_check(self) -> bool:
        """Check if Claude API is accessible."""
        try:
            # Simple validation - just check if client is configured
            return bool(self.settings.anthropic_api_key)
        except Exception:
            return False


class SGLangBackend:
    """SGLang server backend for reasoning tasks."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.sglang_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.request_timeout,
        )
    
    async def complete(
        self,
        messages: list[ChatMessage],
        max_tokens: int,
        temperature: float,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """Generate completion using SGLang."""
        
        payload = {
            "model": self.settings.deepseek_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        
        if stream:
            return self._stream_response(payload)
        else:
            response = await self.client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _stream_response(self, payload: dict) -> AsyncIterator[str]:
        """Stream response from SGLang."""
        async with self.client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    async def health_check(self) -> bool:
        """Check if SGLang server is healthy."""
        try:
            response = await self.client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"SGLang health check failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# =============================================================================
# Task Classifier
# =============================================================================
class TaskClassifier:
    """Classifies tasks as coding or reasoning based on prompt content."""
    
    def __init__(self, settings: Settings):
        self.coding_keywords = [k.lower() for k in settings.coding_keywords]
        self.reasoning_keywords = [k.lower() for k in settings.reasoning_keywords]
    
    def classify(self, messages: list[ChatMessage]) -> str:
        """
        Classify the task type based on message content.
        
        Returns: "coding" or "reasoning"
        """
        # Combine all message content
        full_text = " ".join(m.content.lower() for m in messages)
        
        # Count keyword matches
        coding_score = sum(1 for kw in self.coding_keywords if kw in full_text)
        reasoning_score = sum(1 for kw in self.reasoning_keywords if kw in full_text)
        
        # Weight recent messages more heavily
        if messages:
            last_msg = messages[-1].content.lower()
            coding_score += sum(2 for kw in self.coding_keywords if kw in last_msg)
            reasoning_score += sum(2 for kw in self.reasoning_keywords if kw in last_msg)
        
        logger.debug(f"Task classification - coding: {coding_score}, reasoning: {reasoning_score}")
        
        # Default to reasoning if tied (DeepSeek handles both well)
        if coding_score > reasoning_score:
            return TaskType.CODING
        return TaskType.REASONING


# =============================================================================
# Router Service
# =============================================================================
class InferenceRouter:
    """Routes inference requests to appropriate backend."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.claude = ClaudeBackend(settings)
        self.sglang = SGLangBackend(settings)
        self.classifier = TaskClassifier(settings)
        self._sglang_available = True
    
    async def route_request(
        self,
        request: ChatCompletionRequest,
    ) -> tuple[str, AsyncIterator[str] | str]:
        """
        Route request to appropriate backend.
        
        Returns: (backend_name, response)
        """
        # Determine task type
        if request.task_type == TaskType.AUTO or request.task_type is None:
            task_type = self.classifier.classify(request.messages)
        else:
            task_type = request.task_type
        
        # Check model hint in request
        model_lower = request.model.lower()
        if "claude" in model_lower or "coding" in model_lower:
            task_type = TaskType.CODING
        elif "deepseek" in model_lower or "reasoning" in model_lower:
            task_type = TaskType.REASONING
        
        max_tokens = request.max_tokens or self.settings.max_tokens_default
        temperature = request.temperature or 0.7
        
        # Route to appropriate backend
        if task_type == TaskType.CODING:
            logger.info(f"Routing to Claude (coding task)")
            backend_name = f"claude/{self.settings.claude_model}"
            response = await self.claude.complete(
                request.messages,
                max_tokens,
                temperature,
                request.stream,
            )
        else:
            # Try SGLang first, fallback to Claude if unavailable
            if self._sglang_available:
                try:
                    logger.info(f"Routing to SGLang/DeepSeek (reasoning task)")
                    backend_name = f"sglang/{self.settings.deepseek_model}"
                    response = await self.sglang.complete(
                        request.messages,
                        max_tokens,
                        temperature,
                        request.stream,
                    )
                except Exception as e:
                    logger.warning(f"SGLang request failed: {e}")
                    if self.settings.fallback_to_claude:
                        logger.info("Falling back to Claude")
                        self._sglang_available = False
                        backend_name = f"claude/{self.settings.claude_model}"
                        response = await self.claude.complete(
                            request.messages,
                            max_tokens,
                            temperature,
                            request.stream,
                        )
                    else:
                        raise
            else:
                # SGLang known unavailable, use Claude
                logger.info("SGLang unavailable, using Claude")
                backend_name = f"claude/{self.settings.claude_model}"
                response = await self.claude.complete(
                    request.messages,
                    max_tokens,
                    temperature,
                    request.stream,
                )
        
        return backend_name, response
    
    async def get_status(self) -> dict:
        """Get status of all backends."""
        claude_ok = await self.claude.health_check()
        sglang_ok = await self.sglang.health_check()
        self._sglang_available = sglang_ok
        
        return {
            "claude": {
                "status": "online" if claude_ok else "offline",
                "model": self.settings.claude_model,
            },
            "sglang": {
                "status": "online" if sglang_ok else "offline",
                "model": self.settings.deepseek_model,
                "url": self.settings.sglang_url,
            },
        }
    
    async def close(self):
        """Cleanup resources."""
        await self.sglang.close()


# =============================================================================
# FastAPI Application
# =============================================================================
router: Optional[InferenceRouter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global router
    logger.info("Starting DGX Inference Router...")
    
    settings = get_settings()
    router = InferenceRouter(settings)
    
    # Initial health check
    status = await router.get_status()
    logger.info(f"Backend status: {status}")
    
    yield
    
    logger.info("Shutting down...")
    if router:
        await router.close()


app = FastAPI(
    title="DGX Inference Router",
    description="Routes AI requests between Claude (coding) and DeepSeek (reasoning)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API Endpoints
# =============================================================================
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    settings = get_settings()
    return {
        "object": "list",
        "data": [
            {
                "id": "auto",
                "object": "model",
                "owned_by": "router",
                "description": "Auto-detect task type and route accordingly",
            },
            {
                "id": "coding",
                "object": "model",
                "owned_by": "anthropic",
                "description": f"Claude ({settings.claude_model}) for coding tasks",
            },
            {
                "id": "reasoning",
                "object": "model",
                "owned_by": "sglang",
                "description": f"DeepSeek ({settings.deepseek_model}) for reasoning tasks",
            },
        ],
    }


@app.get("/status")
async def get_status():
    """Get detailed status of all backends."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    return await router.get_status()


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    
    Routes to Claude for coding tasks, DeepSeek for reasoning.
    Set task_type explicitly or use model="coding"/"reasoning" to override auto-detection.
    """
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    start_time = time.time()
    
    try:
        backend_name, response = await router.route_request(request)
        
        if request.stream:
            # Streaming response
            async def generate_stream():
                async for chunk in response:
                    data = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": backend_name,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                # Final chunk
                final = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": backend_name,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }],
                }
                yield f"data: {json.dumps(final)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Backend": backend_name,
                },
            )
        else:
            # Non-streaming response
            elapsed = time.time() - start_time
            logger.info(f"Request completed in {elapsed:.2f}s via {backend_name}")
            
            return ChatCompletionResponse(
                id=f"chatcmpl-{int(time.time())}",
                created=int(time.time()),
                model=backend_name,
                choices=[
                    ChatCompletionChoice(
                        message=ChatMessage(role="assistant", content=response),
                    )
                ],
                usage=Usage(),  # Token counting not implemented
            )
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend HTTP error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        raise HTTPException(status_code=500, detail=f"Claude API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Development Server
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
