"""
MERIDIAN LLM Router for DGX Spark Deployment

Routes requests to appropriate models based on mode complexity:
- Fast model (Qwen-14B): Modes 0, 0.5, 1, 7 (simple tasks)
- Reasoning model (DeepSeek-70B): Modes 2-6.5 (complex analysis)

Supports OpenAI-compatible endpoints (vLLM, SGLang, etc.)
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Type, TypeVar, Literal
from enum import Enum

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Model routing configuration
class ModelTier(str, Enum):
    FAST = "fast"           # Quick responses, simple tasks
    REASONING = "reasoning"  # Complex analysis, multi-step reasoning


# Mode to model tier mapping
MODE_ROUTING: dict[str, ModelTier] = {
    "0": ModelTier.FAST,      # EDA - straightforward data analysis
    "0.5": ModelTier.FAST,    # Opportunity Discovery - enumeration
    "1": ModelTier.FAST,      # Decision Intelligence - hypothesis formatting
    "2": ModelTier.REASONING, # Feasibility - complex data analysis
    "3": ModelTier.REASONING, # Strategy - model recommendations
    "4": ModelTier.REASONING, # Business Case - financial analysis
    "5": ModelTier.REASONING, # Code Generation - architecture planning
    "6": ModelTier.REASONING, # Execution/Ops - integration analysis
    "6.5": ModelTier.REASONING, # Interpretation - explain ML results
    "7": ModelTier.FAST,      # Delivery - packaging/manifest
}


class DGXModelConfig(BaseModel):
    """Configuration for a model endpoint on DGX"""
    name: str
    base_url: str
    port: int
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.3
    
    @property
    def endpoint(self) -> str:
        return f"{self.base_url}:{self.port}"


# Default DGX configuration
DGX_MODELS = {
    ModelTier.FAST: DGXModelConfig(
        name="qwen-14b",
        base_url="http://localhost",
        port=30001,
        model_id="Qwen/Qwen2.5-14B-Instruct",
        max_tokens=4096,
        temperature=0.3,
    ),
    ModelTier.REASONING: DGXModelConfig(
        name="deepseek-70b", 
        base_url="http://localhost",
        port=30002,
        model_id="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        max_tokens=8192,
        temperature=0.2,
    ),
}


TModel = TypeVar("TModel", bound=BaseModel)


class DGXRouterProvider:
    """
    LLM provider that routes to appropriate DGX models based on mode.
    
    Implements the MERIDIAN LLMProvider protocol.
    """
    
    def __init__(
        self,
        fast_config: Optional[DGXModelConfig] = None,
        reasoning_config: Optional[DGXModelConfig] = None,
        current_mode: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.fast_config = fast_config or DGX_MODELS[ModelTier.FAST]
        self.reasoning_config = reasoning_config or DGX_MODELS[ModelTier.REASONING]
        self.current_mode = current_mode
        self.timeout = timeout
        
        # Create HTTP clients for each endpoint
        self._fast_client = httpx.Client(
            base_url=self.fast_config.endpoint,
            timeout=timeout,
        )
        self._reasoning_client = httpx.Client(
            base_url=self.reasoning_config.endpoint,
            timeout=timeout * 2,  # Reasoning model gets more time
        )
        
        logger.info(f"DGX Router initialized: fast={self.fast_config.endpoint}, reasoning={self.reasoning_config.endpoint}")
    
    def set_mode(self, mode: str) -> None:
        """Set current mode for routing decisions"""
        self.current_mode = mode
        logger.debug(f"Mode set to {mode}, routing to {self._get_tier().value}")
    
    def _get_tier(self) -> ModelTier:
        """Determine which model tier to use"""
        if self.current_mode is None:
            return ModelTier.FAST
        return MODE_ROUTING.get(self.current_mode, ModelTier.REASONING)
    
    def _get_config(self) -> DGXModelConfig:
        """Get config for current tier"""
        tier = self._get_tier()
        return self.fast_config if tier == ModelTier.FAST else self.reasoning_config
    
    def _get_client(self) -> httpx.Client:
        """Get HTTP client for current tier"""
        tier = self._get_tier()
        return self._fast_client if tier == ModelTier.FAST else self._reasoning_client
    
    @property
    def model_name(self) -> str:
        return self._get_config().model_id
    
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str:
        """
        Complete a prompt using the appropriate model.
        Uses OpenAI-compatible chat completions API.
        """
        config = self._get_config()
        client = self._get_client()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": config.model_id,
            "messages": messages,
            "max_tokens": min(max_tokens, config.max_tokens),
            "temperature": config.temperature,
            "stream": False,
        }
        
        logger.debug(f"Sending request to {config.name} ({config.endpoint})")
        
        try:
            resp = client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            content = data["choices"][0]["message"]["content"]
            logger.debug(f"Received {len(content)} chars from {config.name}")
            return content.strip()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {config.name}: {e.response.status_code}")
            raise RuntimeError(f"LLM request failed: {e}")
        except Exception as e:
            logger.error(f"Error calling {config.name}: {e}")
            raise RuntimeError(f"LLM request failed: {e}")
    
    def complete_structured(
        self,
        prompt: str,
        schema: Type[TModel],
        system: Optional[str] = None,
    ) -> TModel:
        """
        Complete with structured JSON output.
        Uses JSON mode or schema guidance depending on model support.
        """
        config = self._get_config()
        client = self._get_client()
        
        # Build prompt with schema instruction
        schema_json = schema.model_json_schema()
        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond with ONLY valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any text before or after the JSON."
        )
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": structured_prompt})
        
        payload = {
            "model": config.model_id,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "stream": False,
        }
        
        # Try to use JSON mode if available
        # vLLM and SGLang support this via response_format
        payload["response_format"] = {"type": "json_object"}
        
        try:
            resp = client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            content = data["choices"][0]["message"]["content"]
            
            # Parse and validate JSON
            return schema.model_validate_json(content)
            
        except Exception as e:
            # Fallback: try without JSON mode
            logger.warning(f"JSON mode failed, retrying without: {e}")
            del payload["response_format"]
            
            resp = client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # Extract JSON from response (handle markdown code blocks)
            import json
            import re
            
            # Try to find JSON in code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if json_match:
                content = json_match.group(1)
            
            return schema.model_validate_json(content.strip())
    
    def test_connection(self) -> bool:
        """Test connectivity to both model endpoints"""
        results = {}
        
        for tier, config in [(ModelTier.FAST, self.fast_config), 
                             (ModelTier.REASONING, self.reasoning_config)]:
            client = self._fast_client if tier == ModelTier.FAST else self._reasoning_client
            try:
                resp = client.get("/v1/models")
                results[tier] = resp.status_code == 200
            except Exception as e:
                logger.warning(f"Connection test failed for {config.name}: {e}")
                results[tier] = False
        
        return all(results.values())
    
    def get_model_status(self) -> dict:
        """Get status of all configured models"""
        status = {}
        
        for tier, config in [(ModelTier.FAST, self.fast_config),
                             (ModelTier.REASONING, self.reasoning_config)]:
            client = self._fast_client if tier == ModelTier.FAST else self._reasoning_client
            try:
                resp = client.get("/v1/models")
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    status[tier.value] = {
                        "name": config.name,
                        "endpoint": config.endpoint,
                        "model_id": config.model_id,
                        "status": "online",
                        "available_models": [m.get("id") for m in models],
                    }
                else:
                    status[tier.value] = {
                        "name": config.name,
                        "endpoint": config.endpoint,
                        "status": "error",
                        "error": f"HTTP {resp.status_code}",
                    }
            except Exception as e:
                status[tier.value] = {
                    "name": config.name,
                    "endpoint": config.endpoint,
                    "status": "offline",
                    "error": str(e),
                }
        
        return status
    
    def close(self) -> None:
        """Close HTTP clients"""
        self._fast_client.close()
        self._reasoning_client.close()


def get_dgx_provider(
    mode: Optional[str] = None,
    fast_port: int = 30001,
    reasoning_port: int = 30002,
    host: str = "localhost",
) -> DGXRouterProvider:
    """
    Factory function to create a DGX router provider.
    
    Can be configured via environment variables:
    - DGX_FAST_PORT: Port for fast model (default: 30001)
    - DGX_REASONING_PORT: Port for reasoning model (default: 30002)  
    - DGX_HOST: Host for model endpoints (default: localhost)
    - DGX_FAST_MODEL: Model ID for fast tier
    - DGX_REASONING_MODEL: Model ID for reasoning tier
    """
    fast_port = int(os.getenv("DGX_FAST_PORT", fast_port))
    reasoning_port = int(os.getenv("DGX_REASONING_PORT", reasoning_port))
    host = os.getenv("DGX_HOST", host)
    
    fast_config = DGXModelConfig(
        name="qwen-14b",
        base_url=f"http://{host}",
        port=fast_port,
        model_id=os.getenv("DGX_FAST_MODEL", "Qwen/Qwen2.5-14B-Instruct"),
    )
    
    reasoning_config = DGXModelConfig(
        name="deepseek-70b",
        base_url=f"http://{host}",
        port=reasoning_port,
        model_id=os.getenv("DGX_REASONING_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"),
    )
    
    return DGXRouterProvider(
        fast_config=fast_config,
        reasoning_config=reasoning_config,
        current_mode=mode,
    )


# Integration with MERIDIAN's get_provider function
def get_provider(config: dict, project_path: Optional["Path"] = None):
    """
    Drop-in replacement for meridian.llm.providers.get_provider
    that uses the DGX router when provider is set to 'dgx'.
    """
    from pathlib import Path
    
    llm_cfg = config.get("llm") if isinstance(config.get("llm"), dict) else {}
    provider = (llm_cfg.get("provider") or "anthropic").lower()
    
    if provider == "dgx":
        return get_dgx_provider(
            fast_port=llm_cfg.get("fast_port", 30001),
            reasoning_port=llm_cfg.get("reasoning_port", 30002),
            host=llm_cfg.get("host", "localhost"),
        )
    
    # Fall back to original provider logic
    from meridian.llm.providers import get_provider as original_get_provider
    return original_get_provider(config, project_path)


if __name__ == "__main__":
    # Quick test
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    
    provider = get_dgx_provider()
    
    print("Model Status:")
    for tier, info in provider.get_model_status().items():
        print(f"  {tier}: {info}")
    
    if provider.test_connection():
        print("\n✓ All models online")
        
        # Test a simple completion
        provider.set_mode("0")
        response = provider.complete("Say 'hello' and nothing else.")
        print(f"\nTest response: {response}")
    else:
        print("\n✗ Some models offline")
        sys.exit(1)
