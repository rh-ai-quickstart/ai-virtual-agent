"""
Virtual Assistants API endpoints for managing AI agents through LlamaStack.

This module provides CRUD operations for virtual assistants (AI agents) that are
managed through the LlamaStack platform. Virtual assistants can be configured with
different models, tools, knowledge bases, and safety shields.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Request, status
from llama_stack_client.lib.agents.agent import AgentUtils

from .. import schemas
from ..api.llamastack import get_client_from_request
from ..utils.logging_config import get_logger
from ..virtual_agents.agent_model import VirtualAgent

logger = get_logger(__name__)

router = APIRouter(prefix="/virtual_assistants", tags=["virtual_assistants"])


def get_strategy(temperature, top_p):
    """
    Determines the sampling strategy for the LLM based on temperature.

    Args:
        temperature: Temperature parameter for sampling (0 = greedy)
        top_p: Top-p parameter for nucleus sampling

    Returns:
        Dict containing the sampling strategy configuration
    """
    return (
        {"type": "greedy"}
        if temperature == 0
        else {"type": "top_p", "temperature": temperature, "top_p": top_p}
    )


@router.post(
    "/",
    response_model=schemas.VirtualAssistantRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_virtual_assistant(
    va: schemas.VirtualAssistantCreate, request: Request
):
    """
    Create a new virtual assistant agent in LlamaStack.

    Args:
        va: Virtual assistant configuration including model, tools, and settings

    Returns:
        The created virtual assistant with generated ID

    Raises:
        HTTPException: If creation fails
    """
    client = get_client_from_request(request)
    try:
        sampling_params = {
            "strategy": get_strategy(va.temperature, va.top_p),
            "max_tokens": va.max_tokens,
            "repetition_penalty": va.repetition_penalty,
        }

        tools = []
        for i, tool_info in enumerate(va.tools):
            if tool_info.toolgroup_id == "builtin::rag":
                if len(va.knowledge_base_ids) > 0:
                    tool_dict = dict(
                        name="builtin::rag",
                        args={
                            "vector_db_ids": list(va.knowledge_base_ids),
                        },
                    )
                    tools.append(tool_dict)
            else:
                tools.append(tool_info.toolgroup_id)

        agent_config = AgentUtils.get_agent_config(
            model=va.model_name,
            instructions=va.prompt,
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

        return schemas.VirtualAssistantRead(
            id=agentic_system_create_response.agent_id,
            name=va.name,
            input_shields=va.input_shields,
            output_shields=va.output_shields,
            prompt=va.prompt,
            model_name=va.model_name,
            knowledge_base_ids=va.knowledge_base_ids,
            tools=va.tools,
        )

    except Exception as e:
        logger.error(f"ERROR: create_virtual_assistant: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


def to_va_response(agent: VirtualAgent):
    """
    Convert a LlamaStack VirtualAgent to API response format.

    Args:
        agent: VirtualAgent object from LlamaStack

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

    return schemas.VirtualAssistantRead(
        id=id,
        name=name,
        input_shields=input_shields,
        output_shields=output_shields,
        prompt=prompt,
        model_name=model_name,
        knowledge_base_ids=kb_ids,
        tools=tools,  # Use the 'tools' field with the correct structure
    )


@router.get("/", response_model=List[schemas.VirtualAssistantRead])
async def get_virtual_assistants(request: Request):
    """
    Retrieve all virtual assistants from LlamaStack.

    Returns:
        List of all virtual assistants configured in the system
    """
    # get all virtual assitants or agents from llama stack
    client = get_client_from_request(request)
    agents = await client.agents.list()
    response_list = []
    for agent in agents:
        response_list.append(to_va_response(agent))
    return response_list


@router.get("/{va_id}", response_model=schemas.VirtualAssistantRead)
async def read_virtual_assistant(va_id: str, request: Request):
    """
    Retrieve a specific virtual assistant by ID.

    Args:
        va_id: The unique identifier of the virtual assistant

    Returns:
        The virtual assistant configuration and metadata

    Raises:
        HTTPException: If virtual assistant not found
    """
    client = get_client_from_request(request)
    agent = await client.agents.retrieve(agent_id=va_id)
    return to_va_response(agent)


# @router.put("/{va_id}", response_model=schemas.VirtualAssistantRead)
# async def update_virtual_assistant(va_id: str):
#     pass


@router.delete("/{va_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_assistant(va_id: str, request: Request):
    """
    Delete a virtual assistant from LlamaStack.

    Args:
        va_id: The unique identifier of the virtual assistant to delete

    Returns:
        None (204 No Content status)
    """
    client = get_client_from_request(request)
    await client.agents.delete(agent_id=va_id)
    return None
