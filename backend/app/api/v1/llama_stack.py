"""
LlamaStack Integration API endpoints for direct LlamaStack operations.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from ...api.llamastack import get_client_from_request
from ...config import ENV_DEFAULT_MODEL_SENTINEL, settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_model_metadata(model) -> Dict[str, Any]:
    """Extract metadata fields from a Model object returned by models.list().

    Supports both old and new llama-stack client API structures:
    - In llama-stack-client 0.5.x: model_type and provider_resource_id live inside custom_metadata
    - In newer versions: model uses api_model_type and provider_resource_id properties directly
    """
    # Try new API structure first
    if hasattr(model, 'api_model_type') and hasattr(model, 'provider_resource_id'):
        return {
            "model_type": model.api_model_type,
            "provider_resource_id": model.provider_resource_id,
        }

    # Fall back to old API structure
    meta = model.custom_metadata or {}
    return {
        "model_type": meta.get("model_type"),
        "provider_resource_id": meta.get("provider_resource_id"),
    }


def _build_env_default_entry() -> Dict[str, Any] | None:
    """Return an env-default model entry when any runner default is configured."""
    configured = []
    if settings.LANGGRAPH_DEFAULT_MODEL:
        configured.append(f"LangGraph: {settings.LANGGRAPH_DEFAULT_MODEL}")
    if settings.CREWAI_DEFAULT_MODEL:
        configured.append(f"CrewAI: {settings.CREWAI_DEFAULT_MODEL}")
    if not configured:
        return None
    return {
        "model_name": ENV_DEFAULT_MODEL_SENTINEL,
        "provider_resource_id": "environment",
        "model_type": "llm",
        "display_name": f"Default Model (Environment Configured — {', '.join(configured)})",
    }


@router.get("/llms", response_model=List[Dict[str, Any]])
async def get_llms(request: Request):
    """
    Retrieve all available Large Language Models from LlamaStack.
    Excludes models that are used as shields.

    When ``LANGGRAPH_DEFAULT_MODEL`` or ``CREWAI_DEFAULT_MODEL`` env vars are
    set, an additional *"Default Model (Environment Configured)"* entry is
    prepended so users can select the env-configured model from the dropdown.
    """
    env_entry = _build_env_default_entry()

    client = get_client_from_request(request)
    try:
        logger.info(f"Attempting to fetch models from LlamaStack at {client.base_url}")
        try:
            models = await client.models.list()
            logger.info(f"Received response from LlamaStack: {models}")
        except Exception as client_error:
            logger.error(f"Error calling LlamaStack API: {str(client_error)}")
            if env_entry:
                logger.info(
                    "LlamaStack unavailable but env-default model configured; "
                    "returning env-default entry only"
                )
                return [env_entry]
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to LlamaStack API: {str(client_error)}",
            )

        if not models:
            logger.warning("No models returned from LlamaStack")
            return [env_entry] if env_entry else []

        # Fetch shields to filter them out from LLM list
        shield_resource_ids = set()
        try:
            shields = await client.shields.list()
            shield_resource_ids = {
                str(shield.provider_resource_id) for shield in shields
            }
        except Exception as shield_error:
            logger.warning(f"Could not fetch shields: {str(shield_error)}")

        llms: List[Dict[str, Any]] = []
        if env_entry:
            llms.append(env_entry)

        for model in models:
            try:
                meta = _get_model_metadata(model)
                if meta["model_type"] == "llm":
                    # Skip models that are used as shields
                    provider_resource_id = str(meta["provider_resource_id"] or "")

                    # Support both old and new API for model identifier
                    model_id = str(getattr(model, 'identifier', None) or getattr(model, 'id', ''))

                    if (
                        provider_resource_id in shield_resource_ids
                        or model_id in shield_resource_ids
                    ):
                        continue

                    llm_config = {
                        "model_name": model_id,
                        "provider_resource_id": meta["provider_resource_id"],
                        "model_type": meta["model_type"],
                    }
                    llms.append(llm_config)
            except (AttributeError, KeyError, TypeError) as ae:
                logger.error(
                    f"Error processing model data: {str(ae)}. Model data: {model}"
                )
                continue

        logger.info(f"Successfully processed {len(llms)} LLM models")
        return llms

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_llms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/tools", response_model=List[Dict[str, Any]])
async def get_tools(request: Request):
    """
    Retrieve all available MCP (Model Context Protocol) servers from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        servers = await client.toolgroups.list()
        return [
            {
                "id": str(server.identifier),
                "name": server.provider_resource_id,
                "title": server.provider_id,
                "toolgroup_id": str(server.identifier),
            }
            for server in servers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safety_models", response_model=List[Dict[str, Any]])
async def get_safety_models(request: Request):
    """
    Retrieve all available safety models from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        models = await client.models.list()
        safety_models = []
        for model in models:
            meta = _get_model_metadata(model)
            if meta["model_type"] == "safety":
                safety_model = {
                    "id": str(model.id),
                    "name": meta["provider_resource_id"],
                    "model_type": meta["model_type"],
                }
                safety_models.append(safety_model)
        return safety_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embedding_models", response_model=List[Dict[str, Any]])
async def get_embedding_models(request: Request):
    """
    Retrieve all available embedding models from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        models = await client.models.list()
        embedding_models = []
        for model in models:
            meta = _get_model_metadata(model)
            if meta["model_type"] == "embedding":
                embedding_model = {
                    "name": str(model.id),
                    "provider_resource_id": meta["provider_resource_id"],
                    "model_type": meta["model_type"],
                }
                embedding_models.append(embedding_model)
        return embedding_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shields", response_model=List[Dict[str, Any]])
async def get_shields(request: Request):
    """
    Retrieve all available safety shields from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        shields = await client.shields.list()
        shields_list = []
        for shield in shields:
            # Use provider_resource_id as the identifier since that's the full model path
            # that needs to be sent to the Responses API (e.g., "llama-guard-3-1b/meta-llama/Llama-Guard-3-1B")
            shield_data = {
                "identifier": str(shield.provider_resource_id),
                "provider_id": str(shield.provider_id),
                "name": shield.provider_resource_id,
                "type": shield.type,
            }
            shields_list.append(shield_data)
        return shields_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=List[Dict[str, Any]])
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
