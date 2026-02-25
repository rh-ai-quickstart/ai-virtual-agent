"""
Application configuration settings.
"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings and configuration."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Virtual Agent"

    # LlamaStack Configuration
    LLAMA_STACK_URL: Optional[str] = os.getenv("LLAMA_STACK_URL")

    # Default inference model for local dev (e.g. Ollama model name).
    # When set and LOCAL_DEV_ENV_MODE is true, template-initialized agents use
    # this model instead of the template's production model name.
    DEFAULT_INFERENCE_MODEL: Optional[str] = os.getenv("DEFAULT_INFERENCE_MODEL")

    # Attachments
    ATTACHMENTS_INTERNAL_API_ENDPOINT: str = os.getenv(
        "ATTACHMENTS_INTERNAL_API_ENDPOINT", "http://ai-virtual-agent:8000"
    )

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # User/Agent Assignment
    AUTO_ASSIGN_AGENTS_TO_USERS: bool = (
        os.getenv("AUTO_ASSIGN_AGENTS_TO_USERS", "true").lower() == "true"
    )

    # LangGraph Runner Configuration
    # Base URL for the OpenAI-compatible LLM API used by LangGraph agents.
    # Falls back to LLAMA_STACK_URL/v1 if not set.
    LANGGRAPH_LLM_API_BASE: Optional[str] = os.getenv("LANGGRAPH_LLM_API_BASE")
    # API key for the LLM API. Use "no-key" for local servers that don't require auth.
    LANGGRAPH_LLM_API_KEY: str = os.getenv("LANGGRAPH_LLM_API_KEY", "no-key")
    # Override model name for LangGraph agents. If not set, uses the agent's model_name.
    LANGGRAPH_DEFAULT_MODEL: Optional[str] = os.getenv("LANGGRAPH_DEFAULT_MODEL")


settings = Settings()
