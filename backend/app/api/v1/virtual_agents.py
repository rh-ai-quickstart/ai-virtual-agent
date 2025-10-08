"""
Virtual Agents API endpoints.
"""

import logging
import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.llamastack import get_client_from_request
from ...crud.virtual_agents import DuplicateVirtualAgentNameError, virtual_agents
from ...database import get_db
from ...schemas import VirtualAgentCreate, VirtualAgentResponse

logger = logging.getLogger(__name__)

# Feature flag for auto-assignment of agents to users
AUTO_ASSIGN_AGENTS_TO_USERS = (
    os.getenv("AUTO_ASSIGN_AGENTS_TO_USERS", "true").lower() == "true"
)

router = APIRouter(prefix="/virtual_agents", tags=["virtual_agents"])


async def create_virtual_agent_internal(
    va: VirtualAgentCreate,
    request: Request,
    db: AsyncSession,
) -> VirtualAgentResponse:
    """
    Internal utility function to create a virtual agent.
    Can be used by API endpoints and other services without dependency injection issues.
    """
    agent_uuid = uuid.uuid4()

    # Validate knowledge bases and get vector store IDs if needed
    vector_store_ids = []
    if va.knowledge_base_ids:
        vector_store_ids = await validate_and_get_vector_store_ids(
            va.knowledge_base_ids, request
        )

    # Prepare agent data
    agent_data = {
        "id": agent_uuid,
        "name": va.name,
        "model_name": va.model_name,
        "template_id": va.template_id,
        "prompt": va.prompt,
        "tools": [
            (
                tool.dict()
                if hasattr(tool, "dict")
                else tool.__dict__ if hasattr(tool, "__dict__") else str(tool)
            )
            for tool in (va.tools or [])
        ],
        "knowledge_base_ids": va.knowledge_base_ids or [],
        "vector_store_ids": vector_store_ids,
        "input_shields": va.input_shields or [],
        "output_shields": va.output_shields or [],
        "sampling_strategy": getattr(va, "sampling_strategy", None),
        "temperature": getattr(va, "temperature", None),
        "top_p": getattr(va, "top_p", None),
        "top_k": getattr(va, "top_k", None),
        "max_tokens": getattr(va, "max_tokens", None),
        "repetition_penalty": getattr(va, "repetition_penalty", None),
        "max_infer_iters": getattr(va, "max_infer_iters", None),
    }

    # Create the agent
    created_agent = await virtual_agents.create(db, obj_in=agent_data)

    logger.info(f"Created virtual agent: {agent_uuid}")

    # Sync all users with all agents if enabled
    if AUTO_ASSIGN_AGENTS_TO_USERS:
        try:
            sync_result = await virtual_agents.sync_all_users_with_all_agents(db)
            logger.info(f"Agent-user sync completed: {sync_result}")
        except Exception as sync_error:
            logger.error(f"Error syncing users with agents: {str(sync_error)}")

    # Use get_with_template to reload agent with proper selectinload relationships
    if created_agent.template_id:
        created_agent = await virtual_agents.get_with_template(db, id=created_agent.id)

    result = config_to_response(created_agent)
    return result


async def validate_and_get_vector_store_ids(
    knowledge_base_ids: List[str], request: Request
) -> List[str]:
    """Validate knowledge bases exist in LlamaStack and return vector store IDs."""
    if not knowledge_base_ids:
        return []

    try:
        client = get_client_from_request(request)
        vector_stores = await client.vector_stores.list()
        vs_name_to_id = {vs.name: vs.id for vs in vector_stores.data}

        vector_store_ids = []
        missing_kbs = []

        for kb_name in knowledge_base_ids:
            if kb_name in vs_name_to_id:
                vector_store_ids.append(vs_name_to_id[kb_name])
            else:
                missing_kbs.append(kb_name)

        if missing_kbs:
            raise HTTPException(
                status_code=400,
                detail=f"Knowledge bases not found in LlamaStack: {missing_kbs}",
            )

        return vector_store_ids

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate knowledge bases in LlamaStack: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to validate knowledge bases with LlamaStack"
        )


def config_to_response(config) -> VirtualAgentResponse:
    """Convert VirtualAgent model to response format."""
    tools = []
    if config.tools:
        for tool in config.tools:
            if isinstance(tool, dict):
                tools.append(tool)
            else:
                tools.append({"toolgroup_id": str(tool)})

    # Extract template and suite information
    template_id = config.template_id
    template_name = None
    suite_id = None
    suite_name = None
    category = None

    if config.template and hasattr(config.template, "suite"):
        template_name = config.template.name
        suite_id = config.template.suite_id
        if config.template.suite:
            suite_name = config.template.suite.name
            category = config.template.suite.category

    return VirtualAgentResponse(
        id=config.id,
        name=config.name,
        input_shields=config.input_shields or [],
        output_shields=config.output_shields or [],
        prompt=config.prompt,
        model_name=config.model_name,
        knowledge_base_ids=config.knowledge_base_ids or [],
        tools=tools,
        template_id=template_id,
        template_name=template_name,
        suite_id=suite_id,
        suite_name=suite_name,
        category=category,
    )


@router.post(
    "/", response_model=VirtualAgentResponse, status_code=status.HTTP_201_CREATED
)
async def create_virtual_agent(
    va: VirtualAgentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new virtual agent configuration."""
    try:
        return await create_virtual_agent_internal(va, request, db)

    except DuplicateVirtualAgentNameError as e:
        logger.warning(f"Duplicate virtual agent name: {str(e)}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating virtual agent: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/", response_model=List[VirtualAgentResponse])
async def get_virtual_agents(db: AsyncSession = Depends(get_db)):
    """Retrieve all virtual agent configurations."""
    try:
        configs = await virtual_agents.get_all_with_templates(db)
        return [config_to_response(config) for config in configs]
    except Exception as e:
        logger.error(f"Error retrieving virtual agents: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{va_id}", response_model=VirtualAgentResponse)
async def read_virtual_agent(va_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific virtual agent configuration by ID."""
    try:
        config = await virtual_agents.get_with_template(db, id=va_id)
        if not config:
            raise HTTPException(
                status_code=404, detail=f"Virtual agent {va_id} not found"
            )
        return config_to_response(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving virtual agent {va_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.delete("/{va_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_agent(va_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a virtual agent configuration."""
    try:
        # Delete agent and associated sessions
        deleted = await virtual_agents.delete_with_sessions(db, id=va_id)
        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Virtual agent {va_id} not found"
            )

        logger.info(f"Successfully deleted virtual agent {va_id}")

        # Sync all users with remaining agents if enabled
        if AUTO_ASSIGN_AGENTS_TO_USERS:
            try:
                sync_result = await virtual_agents.sync_all_users_with_all_agents(db)
                logger.info(f"Agent-user sync completed after deletion: {sync_result}")
            except Exception as sync_error:
                logger.error(f"Error syncing users after deletion: {str(sync_error)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {va_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete virtual agent: {str(e)}"
        )


@router.post("/sync-users-agents")
async def sync_users_with_agents(db: AsyncSession = Depends(get_db)):
    """Sync all existing users with all existing agents."""
    try:
        result = await virtual_agents.sync_all_users_with_all_agents(db)
        return result
    except Exception as e:
        logger.error(f"Error in sync endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to sync users with agents: {str(e)}"
        )
