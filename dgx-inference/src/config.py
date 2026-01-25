"""
Configuration for DGX Inference Router

Environment variables:
- ANTHROPIC_API_KEY: API key for Claude
- SGLANG_URL: URL for local SGLang server
- CLAUDE_MODEL: Claude model to use
- LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ==========================================================================
    # API Keys & URLs
    # ==========================================================================
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude access",
    )
    
    sglang_url: str = Field(
        default="http://localhost:8000",
        description="URL for local SGLang server",
    )
    
    # ==========================================================================
    # Model Configuration
    # ==========================================================================
    claude_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model for coding tasks",
    )
    
    deepseek_model: str = Field(
        default="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        description="DeepSeek model name (for logging/display)",
    )
    
    # ==========================================================================
    # Task Classification
    # ==========================================================================
    # Keywords that indicate a CODING task (route to Claude)
    coding_keywords: list[str] = Field(
        default=[
            # Programming languages
            "python", "javascript", "typescript", "java", "rust", "go", "c++",
            "ruby", "php", "swift", "kotlin", "scala", "haskell",
            # Code-related terms
            "code", "coding", "program", "script", "function", "class", "method",
            "implement", "implementation", "refactor", "debug", "fix bug",
            "write a", "create a", "build a", "develop",
            # Specific tasks
            "api", "endpoint", "database", "sql", "query",
            "test", "unit test", "integration test",
            "dockerfile", "docker", "kubernetes", "yaml", "json",
            "git", "commit", "merge", "branch",
            "frontend", "backend", "fullstack",
            "react", "vue", "angular", "nextjs", "fastapi", "django", "flask",
            # File operations
            "file", "read file", "write file", "parse",
            # Syntax
            "syntax", "error", "exception", "traceback",
        ],
        description="Keywords indicating coding tasks (route to Claude)",
    )
    
    # Keywords that indicate a REASONING task (route to DeepSeek)
    reasoning_keywords: list[str] = Field(
        default=[
            # Analytical thinking
            "reason", "reasoning", "think", "analyze", "analysis",
            "explain", "why", "how does", "what if",
            "compare", "contrast", "evaluate", "assess",
            # Problem solving
            "solve", "problem", "puzzle", "riddle",
            "logic", "logical", "deduce", "infer", "conclude",
            # Math and science
            "math", "mathematics", "calculate", "equation", "formula",
            "proof", "prove", "theorem", "hypothesis",
            "physics", "chemistry", "biology", "science",
            # Planning and strategy
            "plan", "strategy", "approach", "method",
            "step by step", "step-by-step", "walkthrough",
            "pros and cons", "tradeoffs", "trade-offs",
            # Complex reasoning
            "chain of thought", "let's think", "reasoning through",
            "consider", "implications", "consequences",
            # Research and understanding
            "research", "study", "understand", "comprehend",
            "summarize", "summary", "overview",
        ],
        description="Keywords indicating reasoning tasks (route to DeepSeek)",
    )
    
    # ==========================================================================
    # Server Configuration
    # ==========================================================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )
    
    request_timeout: float = Field(
        default=120.0,
        description="Request timeout in seconds",
    )
    
    max_tokens_default: int = Field(
        default=4096,
        description="Default max tokens for responses",
    )
    
    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming responses",
    )
    
    fallback_to_claude: bool = Field(
        default=True,
        description="Fallback to Claude if SGLang is unavailable",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Task type enum for explicit routing
class TaskType:
    CODING = "coding"
    REASONING = "reasoning"
    AUTO = "auto"  # Auto-detect from prompt
