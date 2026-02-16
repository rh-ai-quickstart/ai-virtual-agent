"""
LlamaStack Integration API endpoints for direct LlamaStack operations.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from ...api.llamastack import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/llms", response_model=List[Dict[str, Any]])
async def get_llms(request: Request):
    """
    Retrieve all available Large Language Models from LlamaStack.
    Excludes models that are used as shields.
    """
    client = get_client_from_request(request)
    try:
        logger.info(f"Attempting to fetch models from LlamaStack at {client.base_url}")
        try:
            models = await client.models.list()
            logger.info(f"Received response from LlamaStack: {models}")
        except Exception as client_error:
            logger.error(f"Error calling LlamaStack API: {str(client_error)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to LlamaStack API: {str(client_error)}",
            )

        if not models:
            logger.warning("No models returned from LlamaStack")
            return []

        # Fetch shields to filter them out from LLM list
        shield_resource_ids = set()
        try:
            shields = await client.shields.list()
            shield_resource_ids = {
                str(shield.provider_resource_id) for shield in shields
            }
        except Exception as shield_error:
            logger.warning(f"Could not fetch shields: {str(shield_error)}")
            # Continue without shield filtering

        llms = []
        for model in models:
            try:
                metadata = model.custom_metadata or {}
                model_type = metadata.get("model_type")
                if model_type == "llm":
                    # Skip models that are used as shields
                    provider_resource_id = str(metadata.get("provider_resource_id", ""))
                    model_id = str(model.id)

                    if (
                        provider_resource_id in shield_resource_ids
                        or model_id in shield_resource_ids
                    ):
                        continue

                    llm_config = {
                        "model_name": model_id,
                        "provider_resource_id": provider_resource_id,
                        "model_type": model_type,
                    }
                    llms.append(llm_config)
            except (AttributeError, KeyError) as ae:
                logger.error(
                    f"Error processing model data: {str(ae)}. Model data: {model}"
                )
                continue

        logger.info(f"Successfully processed {len(llms)} LLM models")
        return llms

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
                "name": server.provider_resource_id or str(server.identifier),
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
            metadata = model.custom_metadata or {}
            if metadata.get("model_type") == "safety":
                safety_model = {
                    "id": str(model.id),
                    "name": metadata.get("provider_resource_id", ""),
                    "model_type": "safety",
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
            metadata = model.custom_metadata or {}
            if metadata.get("model_type") == "embedding":
                embedding_model = {
                    "name": str(model.id),
                    "provider_resource_id": metadata.get("provider_resource_id", ""),
                    "model_type": "embedding",
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
