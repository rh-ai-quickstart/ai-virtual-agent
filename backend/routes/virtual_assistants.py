"""
Virtual Agents API endpoints for managing AI agents through LlamaStack.

This module provides CRUD operations for virtual agents (AI agents) that are
managed through the LlamaStack platform. Virtual agents can be configured with
different models, tools, knowledge bases, and safety shields.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from llama_stack_client.lib.agents.agent import AgentUtils
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..api.llamastack import get_client_from_request
from ..database import get_db
from ..utils.logging_config import get_logger

# from ..utils.template_loader import load_all_templates_from_directory  # Not needed for normalized approach
from ..virtual_agents.agent_model import VirtualAgent

logger = get_logger(__name__)

router = APIRouter(prefix="/virtual_assistants", tags=["virtual_assistants"])


def get_strategy(sampling_strategy, temperature, top_p, top_k):
    """
    Determines the sampling strategy for the LLM based on user selection.
    Args:
        sampling_strategy: 'greedy', 'top-p', or 'top-k'
        temperature: Temperature parameter for sampling
        top_p: Top-p parameter for nucleus sampling
        top_k: Top-k parameter for k sampling
    Returns:
        Dict containing the sampling strategy configuration
    """
    if sampling_strategy == "top-p":
        temp = max(temperature, 0.1)  # Ensure temp doesn't become 0
        return {"type": "top_p", "temperature": temperature, "top_p": top_p}
    elif sampling_strategy == "top-k":
        temp = max(temperature, 0.1)  # Ensure temp doesn't become 0
        return {"type": "top_k", "temperature": temp, "top_k": top_k}
    # Default and 'greedy' case
    return {"type": "greedy"}


def get_standardized_instructions(
    user_prompt: str, agent_type: str, model_name: str = None
) -> str:
    """
    Creates optimized prompts based on model capabilities and agent type.

    This function implements model-aware prompt engineering that:
    - Adapts instructions based on model capabilities
    - Provides fallbacks for unknown models
    - Validates prompt effectiveness
    - Avoids instructions that cause garbled output

    Args:
        user_prompt: The user's custom prompt/instructions
        agent_type: The type of agent ("ReAct" or "Regular")
        model_name: The model being used

    Returns:
        An optimized prompt that works well with the specific model
    """

    # Start with the user's prompt
    base_prompt = user_prompt.strip() if user_prompt else ""

    # Model-specific optimizations
    model_optimizations = {
        "llama2:latest": {
            "react": (
                "Think through questions step by step and provide clear answers."
            ),
            "regular": "Provide clear, helpful responses in a conversational manner.",
        },
        "llama3.3:latest": {
            "react": (
                "Use reasoning to solve problems and provide detailed, "
                "helpful responses."
            ),
            "regular": "Provide comprehensive, well-reasoned responses.",
        },
        "llama3.3:70b-instruct-q2_K": {
            "react": (
                "Use advanced reasoning to solve complex problems and "
                "provide detailed, helpful responses."
            ),
            "regular": (
                "Provide comprehensive, well-reasoned responses with "
                "depth and clarity."
            ),
        },
        "llama3.2:3b-instruct-fp16": {
            "react": "Provide clear, direct answers to questions.",
            "regular": "Respond naturally and conversationally.",
        },
    }

    # Get model-specific instruction or use safe default
    if model_name and model_name in model_optimizations:
        if agent_type == "ReAct":
            instruction = model_optimizations[model_name]["react"]
        else:
            instruction = model_optimizations[model_name]["regular"]
    else:
        # Safe fallback for unknown models
        instruction = "Provide clear, helpful responses."

    # Combine prompts - keep it simple and effective
    if base_prompt:
        # For regular agents, be very conservative - only use the user's prompt
        if agent_type == "Regular":
            final_prompt = base_prompt
        else:
            # For ReAct agents, be more liberal with instructions
            if instruction.lower() not in base_prompt.lower():
                final_prompt = f"{base_prompt}\n\n{instruction}"
            else:
                final_prompt = base_prompt
    else:
        final_prompt = f"You are a helpful assistant. {instruction}"

    return final_prompt


@router.post(
    "/",
    response_model=schemas.VirtualAssistantRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_virtual_assistant(
    va: schemas.VirtualAssistantCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new virtual agent in LlamaStack.

    Args:
        va: Virtual agent configuration including model, tools, and settings

    Returns:
        The created virtual agent with generated ID

    Raises:
        HTTPException: If creation fails
    """
    client = get_client_from_request(request)
    try:
        sampling_params = {
            "strategy": get_strategy(
                va.sampling_strategy,
                va.temperature,
                va.top_p,
                va.top_k,
            ),
            "max_tokens": va.max_tokens,
            "repetition_penalty": va.repetition_penalty,
        }

        tools = []
        for i, tool_info in enumerate(va.tools or []):
            if tool_info.toolgroup_id == "builtin::rag":
                if len(va.knowledge_base_ids or []) > 0:
                    tool_dict = dict(
                        name="builtin::rag",
                        args={
                            "vector_db_ids": list(va.knowledge_base_ids or []),
                        },
                    )
                    tools.append(tool_dict)
            else:
                tools.append(tool_info.toolgroup_id)

        # Create standardized instructions based on agent type
        standardized_instructions = get_standardized_instructions(
            va.prompt or "", va.agent_type or "ReAct", va.model_name
        )

        # Validate model and provide warnings
        model_warnings = {
            "llama3.3:70b-instruct-q2_K": (
                "This model requires significant resources and may be slow. "
                "Consider using llama2:latest for faster responses."
            ),
            "llama3.3:latest": (
                "This model may be slow on some systems. Consider using "
                "llama2:latest for better performance."
            ),
            "llama3.2:3b-instruct-fp16": (
                "This model may produce garbled output with complex prompts. "
                "Consider using llama2:latest for better reliability."
            ),
        }

        if va.model_name in model_warnings:
            logger.warning(
                f"Model warning for {va.model_name}: "
                f"{model_warnings[va.model_name]}"
            )

        agent_config = AgentUtils.get_agent_config(
            model=va.model_name,
            instructions=standardized_instructions,
            tools=tools,
            sampling_params=sampling_params,
            max_infer_iters=va.max_infer_iters,
            input_shields=va.input_shields,
            output_shields=va.output_shields,
        )
        agent_config["name"] = va.name

        agentic_system_create_response = await client.agents.create(
            agent_config=agent_config,
        )

        # Store agent type in database
        try:
            converted_agent_type = models.AgentTypeEnum(va.agent_type or "ReAct")
            db_agent_type = models.AgentType(
                agent_id=agentic_system_create_response.agent_id,
                agent_type=converted_agent_type,
            )
            db.add(db_agent_type)
            await db.commit()
        except Exception as db_error:
            logger.error(f"Error storing agent_type: {str(db_error)}")
            await db.rollback()
            # Continue anyway, don't fail agent creation

        return schemas.VirtualAssistantRead(
            id=agentic_system_create_response.agent_id,
            name=va.name,
            agent_type=va.agent_type,
            input_shields=va.input_shields,
            output_shields=va.output_shields,
            prompt=va.prompt,
            model_name=va.model_name,
            knowledge_base_ids=va.knowledge_base_ids,
            tools=va.tools,
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"ERROR: create_virtual_assistant: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


async def to_va_response(
    agent: VirtualAgent,
    agent_type: str = "ReAct",
    db: Optional[AsyncSession] = None,
):
    """
    Convert a LlamaStack VirtualAgent to API response format.

    Args:
        agent: VirtualAgent object from LlamaStack
        agent_type: Agent type from database lookup

    Returns:
        VirtualAssistantRead schema with formatted data
    """
    tools = []
    kb_ids = []

    for toolgroup in agent.agent_config.get("toolgroups", []):
        if isinstance(toolgroup, dict):
            tool_name = toolgroup.get("name")
            tools.append(schemas.ToolAssociationInfo(toolgroup_id=tool_name))
            if tool_name == "builtin::rag":
                kb_ids = toolgroup.get("args", {}).get("vector_db_ids", [])
                logger.debug("Assigned vector_db_ids:", kb_ids)
        elif isinstance(toolgroup, str):
            tools.append(schemas.ToolAssociationInfo(toolgroup_id=toolgroup))

    id = agent.agent_id
    name = agent.agent_config.get("name", "")
    name = name if name is not None else "Missing Name"
    input_shields = agent.agent_config.get("input_shields", [])
    output_shields = agent.agent_config.get("output_shields", [])
    prompt = agent.agent_config.get("instructions", "")
    model_name = agent.agent_config.get("model", "")
    # Default metadata values
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    suite_id: Optional[str] = None
    suite_name: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[models.AgentMetadata] = None

    if db is not None:
        try:
            from sqlalchemy.orm import selectinload

            # Use joins to get normalized data efficiently
            result = await db.execute(
                select(models.AgentMetadata)
                .options(
                    selectinload(models.AgentMetadata.template).selectinload(
                        models.AgentTemplate.suite
                    )
                )
                .where(models.AgentMetadata.agent_id == id)
            )
            metadata = result.scalar_one_or_none()

            if metadata and metadata.template:
                template_id = metadata.template.id
                template_name = metadata.template.name
                suite_id = (
                    metadata.template.suite.id if metadata.template.suite else None
                )
                suite_name = (
                    metadata.template.suite.name if metadata.template.suite else None
                )
                category = (
                    metadata.template.suite.category
                    if metadata.template.suite
                    else None
                )
        except Exception:
            # Fail open if metadata lookup fails or tables don't exist yet
            pass

    # Fallback: link existing agents to templates by name matching
    if not any([template_id, template_name, suite_id, suite_name, category]):
        # Try to find a matching template by agent name
        if db is not None:
            try:
                from sqlalchemy.orm import selectinload

                # Look for a template with matching name
                result = await db.execute(
                    select(models.AgentTemplate)
                    .options(selectinload(models.AgentTemplate.suite))
                    .where(models.AgentTemplate.name == name)
                )
                matching_template = result.scalar_one_or_none()

                if matching_template:
                    template_id = matching_template.id
                    template_name = matching_template.name
                    suite_id = (
                        matching_template.suite.id if matching_template.suite else None
                    )
                    suite_name = (
                        matching_template.suite.name
                        if matching_template.suite
                        else None
                    )
                    category = (
                        matching_template.suite.category
                        if matching_template.suite
                        else None
                    )

                    # Create metadata record for this agent
                    metadata = models.AgentMetadata(
                        agent_id=id,
                        template_id=template_id,
                    )
                    db.add(metadata)
                    await db.commit()
                    print(f"🔗 Linked agent '{name}' to template '{template_id}'")
            except Exception:
                # Ignore errors, agent will show as uncategorized
                pass

    return schemas.VirtualAssistantRead(
        id=id,
        name=name,
        agent_type=agent_type,
        input_shields=input_shields,
        output_shields=output_shields,
        prompt=prompt,
        model_name=model_name,
        knowledge_base_ids=kb_ids,
        tools=tools,
        # For now, omit metadata to avoid Pydantic conversion issues
        # metadata=metadata,  # TODO: Convert SQLAlchemy model to Pydantic
        # Backward compatibility fields
        template_id=template_id,
        template_name=template_name,
        suite_id=suite_id,
        suite_name=suite_name,
        category=category,
    )


@router.get("/", response_model=List[schemas.VirtualAssistantRead])
async def get_virtual_assistants(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all virtual agents from LlamaStack.

    Returns:
        List of all virtual agents configured in the system
    """
    # get all virtual assitants or agents from llama stack
    client = get_client_from_request(request)
    agents = await client.agents.list()
    response_list = []
    for agent in agents:
        # Get agent type from database
        agent_type = "ReAct"  # Default
        try:
            from sqlalchemy.future import select

            result = await db.execute(
                select(models.AgentType).where(
                    models.AgentType.agent_id == agent.agent_id
                )
            )
            agent_type_record = result.scalar_one_or_none()
            if agent_type_record:
                agent_type = agent_type_record.agent_type.value
        except Exception:
            pass  # Use default
        response_list.append(await to_va_response(agent, agent_type, db))
    return response_list


@router.get("/{va_id}", response_model=schemas.VirtualAssistantRead)
async def read_virtual_assistant(
    va_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a specific virtual agent by ID.

    Args:
        va_id: The unique identifier of the virtual agent

    Returns:
        The virtual agent configuration and metadata

    Raises:
        HTTPException: If virtual agent not found
    """
    client = get_client_from_request(request)
    agent = await client.agents.retrieve(agent_id=va_id)

    # Get agent type from database
    agent_type = "ReAct"  # Default
    try:
        from sqlalchemy.future import select

        result = await db.execute(
            select(models.AgentType).where(models.AgentType.agent_id == va_id)
        )
        agent_type_record = result.scalar_one_or_none()
        if agent_type_record:
            agent_type = agent_type_record.agent_type.value
    except Exception:
        pass  # Use default

    return await to_va_response(agent, agent_type, db)


# @router.put("/{va_id}", response_model=schemas.VirtualAssistantRead)
# async def update_virtual_assistant(va_id: str):
#     pass


@router.delete("/{va_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_assistant(
    va_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Delete a virtual agent from LlamaStack and clean up database records.

    Args:
        va_id: The unique identifier of the virtual agent to delete

    Returns:
        None (204 No Content status)
    """
    client = get_client_from_request(request)

    try:
        # Delete from LlamaStack first
        await client.agents.delete(agent_id=va_id)

        # Clean up database records
        try:
            from sqlalchemy import delete

            # Delete agent metadata
            metadata_result = await db.execute(
                delete(models.AgentMetadata).where(
                    models.AgentMetadata.agent_id == va_id
                )
            )

            # Delete agent type
            type_result = await db.execute(
                delete(models.AgentType).where(models.AgentType.agent_id == va_id)
            )

            await db.commit()

            # Log cleanup results
            if metadata_result.rowcount > 0:
                logger.info(f"Cleaned up agent metadata for {va_id}")
            if type_result.rowcount > 0:
                logger.info(f"Cleaned up agent type for {va_id}")

        except Exception as db_error:
            await db.rollback()
            logger.warning(
                f"Failed to clean up database records for agent {va_id}: {db_error}"
            )
            # Don't fail the deletion if database cleanup fails

    except Exception as e:
        logger.error(f"Failed to delete agent {va_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete virtual assistant: {str(e)}"
        )

    return None
