"""Pydantic schemas for provider management."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProviderConfigVLLM(BaseModel):
    """Configuration for vLLM provider."""

    base_url: str = Field(
        ...,
        description="vLLM server URL (e.g., http://my-vllm.namespace.svc.cluster.local/v1)",
    )
    api_token: str = Field(default="fake", description="API token for authentication")
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    tls_verify: bool = Field(default=False, description="Enable TLS verification")


class ProviderConfigOllama(BaseModel):
    """Configuration for Ollama provider."""

    base_url: str = Field(
        ..., description="Ollama server URL (e.g., http://ollama:11434)"
    )


class ProviderCreate(BaseModel):
    """Schema for creating a new provider."""

    provider_id: str = Field(..., description="Unique identifier for the provider")
    provider_type: Literal["remote::vllm", "remote::ollama"] = Field(
        ..., description="Type of provider (remote::vllm or remote::ollama)"
    )
    config: dict[str, Any] = Field(..., description="Provider configuration")


class ProviderRead(BaseModel):
    """Schema for reading a provider."""

    provider_id: str
    provider_type: str
    api: str
    config: dict[str, Any]

    class Config:
        from_attributes = True
