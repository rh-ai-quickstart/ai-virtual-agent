"""Models API endpoints for LlamaStack."""

import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from ....core.config_management import (
    get_configmap,
    get_current_namespace,
    patch_configmap,
    restart_deployment,
    update_yaml_config,
)
from ....schemas.models import ModelProviderConfig
from .client import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/llms", response_model=List[Dict[str, Any]])
async def get_llms(request: Request):
    """
    Retrieve all available Large Language Models from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        logger.info(f"Attempting to fetch models from LlamaStack at {client.base_url}")
        try:
            models = await client.models.list()
            providers = await client.providers.list()
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

        # Create provider lookup map
        provider_map = {str(p.provider_id): p for p in providers}

        llms = []
        for model in models:
            try:
                if model.api_model_type == "llm":
                    llm_config = {
                        "model_id": str(model.identifier),
                        "model_type": model.api_model_type,
                    }

                    # Add provider information if available
                    if (
                        hasattr(model, "provider_id")
                        and str(model.provider_id) in provider_map
                    ):
                        provider = provider_map[str(model.provider_id)]
                        llm_config["provider_id"] = str(provider.provider_id)
                        llm_config["provider_type"] = provider.provider_type
                        if hasattr(provider, "config"):
                            llm_config["provider_config"] = provider.config

                    llms.append(llm_config)
            except AttributeError as ae:
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


@router.get("/embedding", response_model=List[Dict[str, Any]])
async def get_embedding_models(request: Request):
    """
    Retrieve all available embedding models from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        models = await client.models.list()
        providers = await client.providers.list()

        # Create provider lookup map
        provider_map = {str(p.provider_id): p for p in providers}

        embedding_models = []
        for model in models:
            if model.api_model_type == "embedding":
                embedding_model = {
                    "model_id": str(model.identifier),
                    "model_type": model.api_model_type,
                }

                # Add provider information if available
                if (
                    hasattr(model, "provider_id")
                    and str(model.provider_id) in provider_map
                ):
                    provider = provider_map[str(model.provider_id)]
                    embedding_model["provider_id"] = str(provider.provider_id)
                    embedding_model["provider_type"] = provider.provider_type
                    if hasattr(provider, "config"):
                        embedding_model["provider_config"] = provider.config

                embedding_models.append(embedding_model)
        return embedding_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safety", response_model=List[Dict[str, Any]])
async def get_safety_models(request: Request):
    """
    Retrieve all available safety models from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        models = await client.models.list()
        safety_models = []
        for model in models:
            if model.model_type == "safety":
                safety_model = {
                    "id": str(model.identifier),
                    "name": model.provider_resource_id,
                    "model_type": model.type,
                }
                safety_models.append(safety_model)
        return safety_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_model_provider(model_provider: ModelProviderConfig):
    """
    Register a new provider and model in LlamaStack by updating the ConfigMap.
    """
    try:
        logger.info(
            f"Registering provider '{model_provider.provider.provider_id}' and model '{model_provider.model_id}'"
        )

        # Get ConfigMap name from environment variable
        configmap_name = os.getenv("LLAMA_STACK_RUN_YAML_CONFIG_MAP", "run-config")
        namespace = get_current_namespace()

        # Get and parse ConfigMap
        configmap, yaml_content = get_configmap(namespace, configmap_name)

        # Update YAML with new provider and model
        updated_yaml = update_yaml_config(
            yaml_content=yaml_content,
            provider_id=model_provider.provider.provider_id,
            provider_type=model_provider.provider.provider_type,
            provider_config=model_provider.provider.config,
            model_id=model_provider.model_id,
            metadata=model_provider.metadata,
        )

        # Patch ConfigMap
        patch_configmap(namespace, configmap_name, configmap, updated_yaml)

        # Restart llamastack deployment
        restart_deployment(namespace, deployment_name="llamastack")

        logger.info(
            "Successfully registered provider and model, deployment restart triggered"
        )

        return {
            "message": "Provider and model registered successfully",
            "provider_id": model_provider.provider.provider_id,
            "model_id": model_provider.model_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register provider and model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register provider and model: {str(e)}",
        )
