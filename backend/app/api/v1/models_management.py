"""
API endpoints for model registration and management in LlamaStack.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.llamastack import get_client_from_request
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas.models import ModelCreate, ModelRead, ModelUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
async def register_model(model_data: ModelCreate, request: Request):
    """
    Register a new model with LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        logger.info(f"Registering model: {model_data.model_id}")

        # Register the model with LlamaStack
        registered_model = await client.models.register(
            model_id=model_data.model_id,
            provider_model_id=model_data.provider_model_id,
            provider_id=model_data.provider_id,
            metadata=model_data.metadata,
            model_type=model_data.model_type,
        )

        logger.info(f"Successfully registered model: {model_data.model_id}")

        # Convert to response schema
        reg_metadata = registered_model.custom_metadata or {}
        return ModelRead(
            model_id=str(registered_model.id),
            provider_id=reg_metadata.get("provider_id", ""),
            provider_model_id=reg_metadata.get("provider_resource_id", ""),
            model_type=reg_metadata.get("model_type", ""),
            metadata=reg_metadata,
        )

    except Exception as e:
        logger.error(f"Error registering model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register model: {str(e)}",
        )


@router.get("/", response_model=List[ModelRead])
async def list_models(request: Request):
    """
    List all registered models from LlamaStack.
    Cross-references with shields to identify shield models.
    """
    client = get_client_from_request(request)
    try:
        # Fetch models and shields in parallel
        logger.debug("Calling client.models.list()")
        models = await client.models.list()
        logger.debug(f"client.models.list() returned {len(models)} models")
        for model in models:
            metadata = model.custom_metadata or {}
            logger.debug(
                f"  Model: id={model.id}, "
                f"provider_id={metadata.get('provider_id')}, "
                f"provider_resource_id={metadata.get('provider_resource_id')}, "
                f"model_type={metadata.get('model_type')}"
            )

        # Fetch shields and create a set of shield resource IDs for efficient lookup
        shield_resource_ids = set()
        try:
            logger.debug("Calling client.shields.list()")
            shields = await client.shields.list()
            logger.debug(f"client.shields.list() returned {len(shields)} shields")
            shield_resource_ids = {
                str(shield.provider_resource_id) for shield in shields
            }
        except Exception as shield_error:
            logger.warning(f"Could not fetch shields: {str(shield_error)}")
            # Continue without shield information

        models_list = []
        for model in models:
            metadata = model.custom_metadata or {}
            provider_resource_id = str(metadata.get("provider_resource_id", ""))
            model_id = str(model.id)

            # Check if this model is used as a shield
            is_shield = (
                provider_resource_id in shield_resource_ids
                or model_id in shield_resource_ids
            )

            model_data = ModelRead(
                model_id=model_id,
                provider_id=metadata.get("provider_id", ""),
                provider_model_id=provider_resource_id,
                model_type=metadata.get("model_type", ""),
                metadata=metadata,
                is_shield=is_shield,
            )
            models_list.append(model_data)

        logger.info(f"Retrieved {len(models_list)} models")
        return models_list

    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        )


@router.get("/{model_id:path}", response_model=ModelRead)
async def get_model(model_id: str, request: Request):
    """
    Get a specific model by ID.
    """
    client = get_client_from_request(request)
    try:
        model = await client.models.retrieve(model_id=model_id)
        metadata = model.custom_metadata or {}

        return ModelRead(
            model_id=str(model.id),
            provider_id=metadata.get("provider_id", ""),
            provider_model_id=metadata.get("provider_resource_id", ""),
            model_type=metadata.get("model_type", ""),
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Error getting model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {str(e)}",
        )


@router.put("/{model_id:path}", response_model=ModelRead)
async def update_model(model_id: str, model_data: ModelUpdate, request: Request):
    """
    Update a model by unregistering and re-registering it.
    Note: LlamaStack doesn't have a direct update endpoint, so we unregister and re-register.
    """
    client = get_client_from_request(request)
    try:

        # Get the existing model first
        existing_model = await client.models.retrieve(model_id=model_id)
        existing_metadata = existing_model.custom_metadata or {}

        # Unregister the existing model
        await client.models.unregister(model_id=model_id)

        # Re-register with updated data
        updated_model = await client.models.register(
            model_id=model_id,
            provider_model_id=model_data.provider_model_id
            or existing_metadata.get("provider_resource_id", ""),
            provider_id=model_data.provider_id
            or existing_metadata.get("provider_id", ""),
            metadata=(
                model_data.metadata
                if model_data.metadata is not None
                else existing_metadata
            ),
            model_type=existing_metadata.get("model_type", "llm"),
        )

        updated_metadata = updated_model.custom_metadata or {}
        return ModelRead(
            model_id=str(updated_model.id),
            provider_id=updated_metadata.get("provider_id", ""),
            provider_model_id=updated_metadata.get("provider_resource_id", ""),
            model_type=updated_metadata.get("model_type", ""),
            metadata=updated_metadata,
        )

    except Exception as e:
        logger.error(f"Error updating model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model: {str(e)}",
        )


@router.delete("/{model_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_model(
    model_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Unregister a model from LlamaStack.
    Prevents deletion if the model is currently in use by any virtual agent.
    """
    client = get_client_from_request(request)

    # Check if any virtual agents are using this model
    agents = await virtual_agents.get_all_with_templates(db)
    agents_using_model = []

    for agent in agents:
        if agent.model_name == model_id:
            agents_using_model.append(agent.name)

    if agents_using_model:
        agent_list = ", ".join(agents_using_model)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete model '{model_id}'. "
                f"It is used by the following virtual agents: {agent_list}"
            ),
        )

    try:
        logger.info(f"Unregistering model: {model_id}")
        await client.models.unregister(model_id=model_id)
        logger.info(f"Successfully unregistered model: {model_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister model: {str(e)}",
        )
