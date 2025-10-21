"""Providers API endpoints for LlamaStack."""

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from .client import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
async def get_providers(request: Request):
    """
    Retrieve all available providers from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        providers = await client.providers.list()
        return [
            {
                "provider_id": str(provider.provider_id),
                "provider_type": provider.provider_type,
                "config": (provider.config if hasattr(provider, "config") else {}),
                "api": provider.api,
            }
            for provider in providers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=List[str])
async def get_provider_models(provider_url: str):
    """
    Fetch available models from a provider URL.
    """
    try:
        # Ensure URL ends with /models
        if not provider_url.endswith("/models"):
            if provider_url.endswith("/"):
                provider_url = f"{provider_url}models"
            else:
                provider_url = f"{provider_url}/models"

        async with httpx.AsyncClient() as client:
            response = await client.get(provider_url, timeout=10.0)
            response.raise_for_status()

            data = response.json()
            # Parse OpenAI-compatible format: {"object":"list","data":[{"id":"model-name",...}]}
            if isinstance(data, dict) and "data" in data:
                model_ids = [model["id"] for model in data["data"] if "id" in model]
                return model_ids
            else:
                logger.warning(
                    f"Unexpected response format from {provider_url}: {data}"
                )
                return []

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch models from {provider_url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch models from provider: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching provider models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
