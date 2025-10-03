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

    # Attachments
    ATTACHMENTS_INTERNAL_API_ENDPOINT: str = os.getenv(
        "ATTACHMENTS_INTERNAL_API_ENDPOINT", "http://ai-virtual-agent:8000"
    )

    # Kubernetes Configuration for MCP Auto-Discovery
    KUBERNETES_NAMESPACE: str = os.getenv("KUBERNETES_NAMESPACE", "default")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
