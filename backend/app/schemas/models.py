"""Schemas for models API."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ProviderConfig(BaseModel):
    """Schema for provider configuration."""

    provider_id: str
    provider_type: str
    config: Dict[str, Any]


class ModelProviderConfig(BaseModel):
    """Schema for registering a provider and model."""

    provider: ProviderConfig
    model_id: str
    metadata: Optional[Dict[str, Any]] = None
