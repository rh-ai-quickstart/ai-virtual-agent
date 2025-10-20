"""
Virtual Agents API endpoints for managing AI agents through LlamaStack.

This module provides CRUD operations for virtual agents (AI agents) that are
managed through the LlamaStack platform. Virtual agents can be configured with
different models, tools, knowledge bases, and safety shields.
"""

import json
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.llamastack import get_client_from_request
from ...crud.virtual_agents import DuplicateVirtualAgentNameError, virtual_agents
from ...database import get_db
from ...schemas import VirtualAgentCreate, VirtualAgentResponse
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

# Feature flag for auto-assignment of agents to users
AUTO_ASSIGN_AGENTS_TO_USERS = (
    os.getenv("AUTO_ASSIGN_AGENTS_TO_USERS", "true").lower() == "true"
)

router = APIRouter(prefix="/virtual_agents", tags=["virtual_agents"])


async def resolve_mcp_tools_from_toolgroups(client, toolgroups: List[str]) -> List[str]:
    """
    Resolve actual tools from MCP toolgroups.

    Args:
        client: LlamaStack client
        toolgroups: List of toolgroup IDs

    Returns:
        List of resolved tool names
    """
    logger.info(
        f"🔍 MCP TOOL RESOLUTION: Starting resolution for {len(toolgroups)} toolgroups"
    )
    logger.info(f"🔍 MCP TOOL RESOLUTION: Input toolgroups: {toolgroups}")

    resolved_tools = []

    for i, toolgroup_id in enumerate(toolgroups):
        logger.info(
            f"🔍 MCP TOOL RESOLUTION: Processing toolgroup {i+1}/{len(toolgroups)}: {toolgroup_id}"
        )

        if toolgroup_id.startswith("mcp:"):
            logger.info(
                f"🔍 MCP TOOL RESOLUTION: Identified MCP toolgroup: {toolgroup_id}"
            )

            # For MCP toolgroups, we'll use the toolgroup as-is
            # LlamaStack should handle the tool resolution internally
            logger.info(
                f"🔍 MCP TOOL RESOLUTION: Using MCP toolgroup as-is: {toolgroup_id}"
            )
            resolved_tools.append(toolgroup_id)
            logger.info(
                f"✅ MCP TOOL RESOLUTION: Added MCP toolgroup: '{toolgroup_id}'"
            )
        else:
            logger.info(
                f"🔍 MCP TOOL RESOLUTION: Skipping non-MCP toolgroup: {toolgroup_id}"
            )

    logger.info(
        f"🔍 MCP TOOL RESOLUTION: Resolution complete. Resolved {len(resolved_tools)} tools: {resolved_tools}"
    )
    return resolved_tools


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


async def create_virtual_agent_internal(
    va: VirtualAgentCreate,
    request: Request,
    db: AsyncSession,
) -> VirtualAgentResponse:
    """
    Internal utility function to create a virtual agent with LlamaStack integration.
    Can be used by API endpoints and other services without dependency injection issues.

    Args:
        va: Virtual agent configuration
        request: HTTP request object for LlamaStack client
        db: Database session
    """
    logger.info("=== RECEIVED AGENT CREATION REQUEST ===")
    logger.info(f"Agent name: {va.name}")
    logger.info(f"Agent tools: {va.tools}")
    logger.info(f"Tools type: {type(va.tools)}")
    if va.tools:
        for i, tool in enumerate(va.tools):
            logger.info(f"Tool {i}: {tool}")
            logger.info(
                f"Tool {i} toolgroup_id: '{tool.toolgroup_id}' (type: {type(tool.toolgroup_id)})"
            )
    logger.info("=== END REQUEST ===")

    client = get_client_from_request(request)

    try:
        sampling_params = {
            "strategy": get_strategy(
                getattr(va, "sampling_strategy", "greedy"),
                getattr(va, "temperature", 0.7),
                getattr(va, "top_p", 0.9),
                getattr(va, "top_k", 40),
            ),
            "max_tokens": getattr(va, "max_tokens", 2048),
            "repeat_penalty": getattr(va, "repetition_penalty", 1.1),
        }

        tools = []
        toolgroups = []

        logger.info(
            f"🔧 TOOL PROCESSING: Starting tool processing for agent '{va.name}'"
        )
        logger.info(f"🔧 TOOL PROCESSING: Processing {len(va.tools or [])} tools")

        for i, tool_info in enumerate(va.tools or []):
            logger.info(
                f"🔧 TOOL PROCESSING: Processing tool {i+1}/{len(va.tools or [])}"
            )
            logger.info(
                f"🔧 TOOL PROCESSING: Tool toolgroup_id: '{tool_info.toolgroup_id}'"
            )
            logger.info(
                f"🔧 TOOL PROCESSING: Tool toolgroup_id type: {type(tool_info.toolgroup_id)}"
            )
            logger.info(f"🔧 TOOL PROCESSING: Tool info type: {type(tool_info)}")
            logger.info(f"🔧 TOOL PROCESSING: Tool info attributes: {dir(tool_info)}")

            if tool_info.toolgroup_id == "builtin::rag":
                logger.info("🔧 TOOL PROCESSING: Identified builtin::rag tool")
                if len(va.knowledge_base_ids or []) > 0:
                    logger.info(
                        f"🔧 TOOL PROCESSING: Found {len(va.knowledge_base_ids)} "
                        f"knowledge base IDs: {va.knowledge_base_ids}"
                    )
                    tool_dict = dict(
                        name="builtin::rag",
                        args={
                            "vector_db_ids": list(va.knowledge_base_ids or []),
                        },
                    )
                    tools.append(tool_dict)
                    logger.info(
                        f"🔧 TOOL PROCESSING: Added builtin::rag tool with args: {tool_dict}"
                    )
                else:
                    logger.info(
                        "🔧 TOOL PROCESSING: No knowledge base IDs found, adding builtin::rag as string"
                    )
                    tools.append("builtin::rag")
                    logger.info("🔧 TOOL PROCESSING: Added builtin::rag as string")
            elif tool_info.toolgroup_id.startswith("mcp:"):
                # For MCP tools, use toolgroups instead of tools
                # Keep the full toolgroup_id including "mcp:" prefix
                toolgroup_id = tool_info.toolgroup_id
                logger.info(
                    f"🔧 TOOL PROCESSING: Identified MCP toolgroup: '{toolgroup_id}'"
                )
                toolgroups.append(toolgroup_id)
                logger.info(
                    f"🔧 TOOL PROCESSING: Added to toolgroups array: '{toolgroup_id}'"
                )
            else:
                # For other tools, send as string in tools array
                logger.info(
                    f"🔧 TOOL PROCESSING: Identified regular tool: '{tool_info.toolgroup_id}'"
                )
                tools.append(tool_info.toolgroup_id)
                logger.info(
                    f"🔧 TOOL PROCESSING: Added to tools array: '{tool_info.toolgroup_id}'"
                )

        logger.info("🔧 TOOL PROCESSING: Tool processing complete!")
        logger.info(
            f"🔧 TOOL PROCESSING: Final tools array ({len(tools)} items): {tools}"
        )
        logger.info(
            f"🔧 TOOL PROCESSING: Final toolgroups array ({len(toolgroups)} items): {toolgroups}"
        )

        # Create standardized instructions based on agent type
        standardized_instructions = get_standardized_instructions(
            va.prompt or "", getattr(va, "agent_type", "ReAct"), va.model_name
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

        # Create agent config manually to ensure tools are properly included
        agent_config = {
            "name": va.name,
            "model": va.model_name,
            "instructions": standardized_instructions,
            "sampling_params": sampling_params,
            "max_infer_iters": getattr(va, "max_infer_iters", 10),
            "input_shields": va.input_shields or [],
            "output_shields": va.output_shields or [],
        }

        # Add tools and toolgroups based on what we have
        # For LlamaStack, we need to ensure proper tool resolution
        if tools:
            agent_config["tools"] = tools
        if toolgroups:
            agent_config["toolgroups"] = toolgroups

        # Add tool_choice to ensure tools are used
        if tools or toolgroups:
            agent_config["tool_choice"] = "auto"

        # For MCP toolgroups, we need to ensure tools are properly resolved
        # LlamaStack requires explicit tool resolution from MCP toolgroups
        if toolgroups:
            logger.info(
                f"🔧 AGENT CREATION: Processing {len(toolgroups)} toolgroups: {toolgroups}"
            )

            # Separate MCP and non-MCP toolgroups
            mcp_toolgroups = []
            regular_toolgroups = []

            logger.info("🔧 AGENT CREATION: Separating MCP and regular toolgroups...")
            for i, toolgroup_id in enumerate(toolgroups):
                logger.info(
                    f"🔧 AGENT CREATION: Processing toolgroup {i+1}/{len(toolgroups)}: {toolgroup_id}"
                )
                if toolgroup_id.startswith("mcp:"):
                    mcp_toolgroups.append(toolgroup_id)
                    logger.info(
                        f"🔧 AGENT CREATION: Added to MCP toolgroups: {toolgroup_id}"
                    )
                else:
                    regular_toolgroups.append(toolgroup_id)
                    logger.info(
                        f"🔧 AGENT CREATION: Added to regular toolgroups: {toolgroup_id}"
                    )

            logger.info(f"🔧 AGENT CREATION: MCP toolgroups: {mcp_toolgroups}")
            logger.info(f"🔧 AGENT CREATION: Regular toolgroups: {regular_toolgroups}")

            # Handle MCP toolgroups specially
            if mcp_toolgroups:
                logger.info(
                    f"🔧 AGENT CREATION: Found {len(mcp_toolgroups)} MCP toolgroups: {mcp_toolgroups}"
                )

                # For MCP toolgroups, just use them as-is
                # LlamaStack should handle the tool resolution internally
                logger.info(
                    "🔧 AGENT CREATION: Using MCP toolgroups as-is (no tool resolution needed)"
                )
                agent_config["toolgroups"] = mcp_toolgroups
                logger.info(
                    f"🔧 AGENT CREATION: Set toolgroups to: {agent_config.get('toolgroups', [])}"
                )

                # Add explicit tool configuration for MCP
                # This ensures LlamaStack knows how to resolve tools from MCP toolgroups
                tool_config = {
                    "tool_choice": "auto",
                    "tool_prompt_format": "function_tag",
                }
                agent_config["tool_config"] = tool_config

                logger.info(f"🔧 AGENT CREATION: Added tool_config: {tool_config}")
                logger.info(
                    f"🔧 AGENT CREATION: Final agent_config toolgroups: {agent_config.get('toolgroups', 'NOT_FOUND')}"
                )
                logger.info(
                    f"🔧 AGENT CREATION: Final agent_config tools: {agent_config.get('tools', 'NOT_FOUND')}"
                )
                logger.info(
                    f"🔧 AGENT CREATION: Final agent_config tool_config: {agent_config.get('tool_config', 'NOT_FOUND')}"
                )

            # Handle regular toolgroups
            if regular_toolgroups:
                logger.info(
                    f"🔧 AGENT CREATION: Found {len(regular_toolgroups)} regular toolgroups: {regular_toolgroups}"
                )
                if "toolgroups" not in agent_config:
                    agent_config["toolgroups"] = []
                    logger.info(
                        "🔧 AGENT CREATION: Created new 'toolgroups' array for regular toolgroups"
                    )

                logger.info(
                    f"🔧 AGENT CREATION: Current toolgroups before adding regular: {agent_config.get('toolgroups', [])}"
                )
                agent_config["toolgroups"].extend(regular_toolgroups)
                logger.info(
                    f"🔧 AGENT CREATION: Toolgroups after adding regular: {agent_config.get('toolgroups', [])}"
                )

        logger.info("🚀 AGENT CREATION: === FINAL AGENT CONFIGURATION ===")
        logger.info(f"🚀 AGENT CREATION: Agent name: {va.name}")
        logger.info(
            f"🚀 AGENT CREATION: Agent config keys: {list(agent_config.keys())}"
        )
        logger.info(f"🚀 AGENT CREATION: Original tools array: {tools}")
        logger.info(f"🚀 AGENT CREATION: Original toolgroups array: {toolgroups}")
        logger.info(
            f"🚀 AGENT CREATION: Final agent_config tools: {agent_config.get('tools', 'NOT_FOUND')}"
        )
        logger.info(
            f"🚀 AGENT CREATION: Final agent_config toolgroups: {agent_config.get('toolgroups', 'NOT_FOUND')}"
        )
        logger.info(
            f"🚀 AGENT CREATION: Final agent_config tool_choice: {agent_config.get('tool_choice', 'NOT_FOUND')}"
        )
        logger.info(
            f"🚀 AGENT CREATION: Final agent_config tool_config: {agent_config.get('tool_config', 'NOT_FOUND')}"
        )
        logger.info(
            f"🚀 AGENT CREATION: Tools type: {type(agent_config.get('tools', []))}"
        )
        logger.info(
            f"🚀 AGENT CREATION: Toolgroups type: {type(agent_config.get('toolgroups', []))}"
        )
        logger.info(f"🚀 AGENT CREATION: Full agent config: {agent_config}")
        logger.info("🚀 AGENT CREATION: === END FINAL AGENT CONFIG ===")

        try:
            logger.info(
                "🚀 AGENT CREATION: Attempting to create agent with LlamaStack..."
            )
            logger.info(
                "🚀 AGENT CREATION: Calling client.agents.create() with agent_config"
            )

            agentic_system_create_response = await client.agents.create(
                agent_config=agent_config,
            )

            logger.info("✅ AGENT CREATION: Agent created successfully!")
            logger.info(
                f"✅ AGENT CREATION: Agent ID: {agentic_system_create_response.agent_id}"
            )
            logger.info(
                f"✅ AGENT CREATION: Response type: {type(agentic_system_create_response)}"
            )
            logger.info(
                f"✅ AGENT CREATION: Response attributes: {dir(agentic_system_create_response)}"
            )

        except Exception as e:
            logger.error("❌ AGENT CREATION: Failed to create agent with LlamaStack!")
            logger.error(f"❌ AGENT CREATION: Exception: {e}")
            logger.error(f"❌ AGENT CREATION: Exception type: {type(e)}")
            logger.error(f"❌ AGENT CREATION: Exception args: {e.args}")
            logger.error(f"❌ AGENT CREATION: Agent config that failed: {agent_config}")
            logger.error(
                f"❌ AGENT CREATION: Full agent config JSON: {json.dumps(agent_config, indent=2, default=str)}"
            )
            raise

        # Store agent type in database
        try:
            from ... import models

            converted_agent_type = models.AgentTypeEnum(
                getattr(va, "agent_type", "ReAct")
            )
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

        # Also store in local database for consistency
        agent_uuid = agentic_system_create_response.agent_id

        # Validate knowledge bases and get vector store IDs if needed
        vector_store_ids = []
        if va.knowledge_base_ids:
            vector_store_ids = await validate_and_get_vector_store_ids(
                va.knowledge_base_ids, request
            )

        # Prepare agent data for local storage
        agent_data = {
            "id": agent_uuid,
            "name": va.name,
            "model_name": va.model_name,
            "template_id": getattr(va, "template_id", None),
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

        # Create the agent in local database
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
            created_agent = await virtual_agents.get_with_template(
                db, id=created_agent.id
            )

        result = config_to_response(created_agent)
        return result

    except Exception as e:
        await db.rollback()
        logger.error(f"ERROR: create_virtual_agent_internal: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


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
async def get_virtual_agents(request: Request, db: AsyncSession = Depends(get_db)):
    """Retrieve all virtual agents from LlamaStack."""
    # get all virtual assistants or agents from llama stack
    client = get_client_from_request(request)
    agents = await client.agents.list()
    response_list = []
    for agent in agents:
        # Get agent type from database
        agent_type = "ReAct"  # Default
        try:
            from sqlalchemy.future import select

            from ... import models

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

        # Convert LlamaStack agent to response format
        tools = []
        kb_ids = []

        for toolgroup in agent.agent_config.get("toolgroups", []):
            if isinstance(toolgroup, dict):
                tool_name = toolgroup.get("name")
                tools.append({"toolgroup_id": tool_name})
                if tool_name == "builtin::rag":
                    kb_ids = toolgroup.get("args", {}).get("vector_db_ids", [])
                    logger.debug("Assigned vector_db_ids:", kb_ids)
            elif isinstance(toolgroup, str):
                tools.append({"toolgroup_id": toolgroup})

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

        try:
            from sqlalchemy.orm import selectinload

            from ... import models

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

        response_list.append(
            VirtualAgentResponse(
                id=id,
                name=name,
                agent_type=agent_type,
                input_shields=input_shields,
                output_shields=output_shields,
                prompt=prompt,
                model_name=model_name,
                knowledge_base_ids=kb_ids,
                tools=tools,
                template_id=template_id,
                template_name=template_name,
                suite_id=suite_id,
                suite_name=suite_name,
                category=category,
            )
        )
    return response_list


@router.get("/{va_id}", response_model=VirtualAgentResponse)
async def read_virtual_agent(
    va_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Retrieve a specific virtual agent by ID."""
    client = get_client_from_request(request)
    agent = await client.agents.retrieve(agent_id=va_id)

    # Get agent type from database
    agent_type = "ReAct"  # Default
    try:
        from sqlalchemy.future import select

        from ... import models

        result = await db.execute(
            select(models.AgentType).where(models.AgentType.agent_id == va_id)
        )
        agent_type_record = result.scalar_one_or_none()
        if agent_type_record:
            agent_type = agent_type_record.agent_type.value
    except Exception:
        pass  # Use default

    # Convert LlamaStack agent to response format
    tools = []
    kb_ids = []

    for toolgroup in agent.agent_config.get("toolgroups", []):
        if isinstance(toolgroup, dict):
            tool_name = toolgroup.get("name")
            tools.append({"toolgroup_id": tool_name})
            if tool_name == "builtin::rag":
                kb_ids = toolgroup.get("args", {}).get("vector_db_ids", [])
                logger.debug("Assigned vector_db_ids:", kb_ids)
        elif isinstance(toolgroup, str):
            tools.append({"toolgroup_id": toolgroup})

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

    try:
        from sqlalchemy.orm import selectinload

        from ... import models

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
            suite_id = metadata.template.suite.id if metadata.template.suite else None
            suite_name = (
                metadata.template.suite.name if metadata.template.suite else None
            )
            category = (
                metadata.template.suite.category if metadata.template.suite else None
            )
    except Exception:
        # Fail open if metadata lookup fails or tables don't exist yet
        pass

    return VirtualAgentResponse(
        id=id,
        name=name,
        agent_type=agent_type,
        input_shields=input_shields,
        output_shields=output_shields,
        prompt=prompt,
        model_name=model_name,
        knowledge_base_ids=kb_ids,
        tools=tools,
        template_id=template_id,
        template_name=template_name,
        suite_id=suite_id,
        suite_name=suite_name,
        category=category,
    )


@router.delete("/{va_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_agent(
    va_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Delete a virtual agent from LlamaStack and clean up database records."""
    client = get_client_from_request(request)

    try:
        # Delete from LlamaStack first
        await client.agents.delete(agent_id=va_id)

        # Clean up database records
        try:
            from sqlalchemy import delete

            from ... import models

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

            # Delete from local database
            deleted = await virtual_agents.delete_with_sessions(db, id=va_id)

            await db.commit()

            # Log cleanup results
            if metadata_result.rowcount > 0:
                logger.info(f"Cleaned up agent metadata for {va_id}")
            if type_result.rowcount > 0:
                logger.info(f"Cleaned up agent type for {va_id}")
            if deleted:
                logger.info(
                    f"Successfully deleted virtual agent {va_id} from local database"
                )

            # Sync all users with remaining agents if enabled
            if AUTO_ASSIGN_AGENTS_TO_USERS:
                try:
                    sync_result = await virtual_agents.sync_all_users_with_all_agents(
                        db
                    )
                    logger.info(
                        f"Agent-user sync completed after deletion: {sync_result}"
                    )
                except Exception as sync_error:
                    logger.error(
                        f"Error syncing users after deletion: {str(sync_error)}"
                    )

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
