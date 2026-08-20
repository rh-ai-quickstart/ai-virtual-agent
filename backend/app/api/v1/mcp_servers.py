"""
Model Context Protocol (MCP) Server management API endpoints.

This module provides CRUD operations for MCP servers through direct integration
with LlamaStack's toolgroups API. MCP servers are managed entirely within
LlamaStack without local database storage.

Key Features:
- Direct LlamaStack toolgroups API integration
- Create, read, update, and delete MCP server configurations
- No local database storage - all data managed by LlamaStack
- Integration with virtual agents for enhanced capabilities
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.llamastack import sync_client
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas.mcp_servers import MCPServerCreate, MCPServerRead
from ...services.k8s_mcp_discovery import get_k8s_discovery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp_servers", tags=["mcp_servers"])


@router.post(
    "/",
    response_model=MCPServerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_mcp_server(server: MCPServerCreate):
    """
    Create a new MCP server by registering it directly with LlamaStack.

    Args:
        server: MCP server creation data including name, endpoint, and
                configuration

    Returns:
        MCPServerRead: The created MCP server configuration

    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    # Check if toolgroup_id already exists
    toolgroups = await sync_client().toolgroups.list()
    for tg in toolgroups:
        if str(tg.identifier) == server.toolgroup_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"MCP server with toolgroup_id '{server.toolgroup_id}' already exists",
            )

    try:
        logger.info(f"Creating MCP server in LlamaStack: {server.name}")

        # Register the toolgroup directly with LlamaStack
        # Spread configuration first, then override with name/description to ensure they're preserved
        await sync_client().toolgroups.register(
            toolgroup_id=server.toolgroup_id,
            provider_id="model-context-protocol",
            args={
                **server.configuration,
                "name": server.name,
                "description": server.description,
            },
            mcp_endpoint={"uri": server.endpoint_url},
        )

        logger.info(f"Successfully created MCP server: {server.toolgroup_id}")

        return MCPServerRead(
            toolgroup_id=server.toolgroup_id,
            name=server.name,
            description=server.description,
            endpoint_url=server.endpoint_url,
            configuration=server.configuration,
            provider_id="model-context-protocol",
        )

    except Exception as e:
        logger.error(f"Failed to create MCP server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MCP server: {str(e)}",
        )


@router.get("/", response_model=List[MCPServerRead])
async def read_mcp_servers():
    """
    Retrieve all MCP servers directly from LlamaStack.

    Returns:
        List[MCPServerRead]: List of all MCP servers
    """
    try:
        logger.info("Fetching MCP servers from LlamaStack")

        # Get all toolgroups from LlamaStack
        toolgroups = await sync_client().toolgroups.list()

        # Filter for MCP toolgroups
        mcp_servers = []
        for toolgroup in toolgroups:
            if (
                hasattr(toolgroup, "provider_id")
                and toolgroup.provider_id == "model-context-protocol"
            ):
                raw_args = getattr(toolgroup, "args", {}) or {}
                if isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = (
                        raw_args.model_dump()
                        if hasattr(raw_args, "model_dump")
                        else vars(raw_args)
                    )

                # Debug: Log what we're getting from LlamaStack
                logger.debug(
                    f"Toolgroup {toolgroup.identifier}: args={args}, "
                    f"has description: {'description' in args}"
                )

                endpoint_obj = getattr(toolgroup, "mcp_endpoint", None)
                endpoint_uri = (
                    getattr(endpoint_obj, "uri", None)
                    if endpoint_obj is not None
                    else None
                )

                # Filter out name and description from configuration since they're separate fields
                config = {
                    k: v for k, v in args.items() if k not in ("name", "description")
                }

                mcp_server = MCPServerRead(
                    toolgroup_id=str(toolgroup.identifier),
                    name=args.get("name")
                    or getattr(
                        toolgroup,
                        "provider_resource_id",
                        str(toolgroup.identifier),
                    ),
                    description=args.get("description", ""),
                    endpoint_url=endpoint_uri or "",
                    configuration=config,
                    provider_id=toolgroup.provider_id,
                )
                mcp_servers.append(mcp_server)

        logger.info(f"Retrieved {len(mcp_servers)} MCP servers from LlamaStack")
        return mcp_servers

    except Exception as e:
        logger.error(f"Failed to fetch MCP servers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MCP servers: {str(e)}",
        )


@router.get("/discover", response_model=List[Dict[str, Any]])
async def discover_mcp_servers():
    """
    Discover MCP servers from Kubernetes resources.

    Searches for:
    - MCPServer custom resources (toolhive.stacklok.dev)
    - Service resources with label app.kubernetes.io/component=mcp-server

    Returns:
        List[Dict]: List of discovered MCP servers with metadata including:
            - source: "mcpserver" or "service"
            - name: Resource name
            - description: Server description
            - endpoint_url: Constructed endpoint URL
    """
    try:
        logger.info("Discovering MCP servers from Kubernetes")
        discovery = get_k8s_discovery()
        servers = discovery.discover_mcp_servers()
        logger.info(f"Discovered {len(servers)} MCP servers from Kubernetes")
        return servers
    except Exception as e:
        logger.error(f"Failed to discover MCP servers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover MCP servers: {str(e)}",
        )


@router.get("/{toolgroup_id}", response_model=MCPServerRead)
async def read_mcp_server(toolgroup_id: str):
    """
    Retrieve a specific MCP server by its tool group identifier.

    Args:
        toolgroup_id: The unique tool group identifier of the MCP server

    Returns:
        MCPServerRead: The requested MCP server configuration

    Raises:
        HTTPException: 404 if the MCP server is not found
    """
    try:
        logger.info(f"Fetching MCP server from LlamaStack: {toolgroup_id}")

        # Get all toolgroups and find the matching one
        toolgroups = await sync_client().toolgroups.list()
        toolgroup = None
        for tg in toolgroups:
            if (
                str(tg.identifier) == toolgroup_id
                and hasattr(tg, "provider_id")
                and tg.provider_id == "model-context-protocol"
            ):
                toolgroup = tg
                break

        if not toolgroup:
            raise HTTPException(status_code=404, detail="Server not found")

        raw_args = getattr(toolgroup, "args", {}) or {}
        if isinstance(raw_args, dict):
            args = raw_args
        else:
            args = (
                raw_args.model_dump()
                if hasattr(raw_args, "model_dump")
                else vars(raw_args)
            )

        endpoint_obj = getattr(toolgroup, "mcp_endpoint", None)
        endpoint_uri = (
            getattr(endpoint_obj, "uri", None) if endpoint_obj is not None else None
        )

        # Filter out name and description from configuration since they're separate fields
        config = {k: v for k, v in args.items() if k not in ("name", "description")}

        return MCPServerRead(
            toolgroup_id=str(toolgroup.identifier),
            name=args.get("name")
            or getattr(toolgroup, "provider_resource_id", str(toolgroup.identifier)),
            description=args.get("description", ""),
            endpoint_url=endpoint_uri or "",
            configuration=config,
            provider_id=toolgroup.provider_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch MCP server {toolgroup_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MCP server: {str(e)}",
        )


@router.put("/{toolgroup_id}", response_model=MCPServerRead)
async def update_mcp_server(
    toolgroup_id: str,
    server: MCPServerCreate,
):
    """
    Update an existing MCP server configuration.

    Args:
        toolgroup_id: The tool group identifier of the MCP server to update
        server: Updated MCP server data

    Returns:
        MCPServerRead: The updated MCP server configuration

    Raises:
        HTTPException: 404 if the MCP server is not found
    """
    try:
        # First verify the server exists
        toolgroups = await sync_client().toolgroups.list()
        existing_toolgroup = None
        for tg in toolgroups:
            if (
                str(tg.identifier) == toolgroup_id
                and hasattr(tg, "provider_id")
                and tg.provider_id == "model-context-protocol"
            ):
                existing_toolgroup = tg
                break

        if not existing_toolgroup:
            raise HTTPException(status_code=404, detail="Server not found")

        # Unregister the existing toolgroup first
        await sync_client().toolgroups.unregister(toolgroup_id=toolgroup_id)

        # Re-register with new config (use URL toolgroup_id, not request body)
        # Spread configuration first, then override with name/description to ensure they're preserved
        await sync_client().toolgroups.register(
            toolgroup_id=toolgroup_id,
            provider_id="model-context-protocol",
            args={
                **server.configuration,
                "name": server.name,
                "description": server.description,
            },
            mcp_endpoint={"uri": server.endpoint_url},
        )

        logger.info(f"Successfully updated MCP server: {toolgroup_id}")

        return MCPServerRead(
            toolgroup_id=toolgroup_id,
            name=server.name,
            description=server.description,
            endpoint_url=server.endpoint_url,
            configuration=server.configuration,
            provider_id="model-context-protocol",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MCP server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update MCP server: {str(e)}",
        )


@router.delete("/{toolgroup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(toolgroup_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete an MCP server configuration.

    Args:
        toolgroup_id: The tool group identifier of the MCP server to delete
        db: Database session

    Raises:
        HTTPException: 404 if the MCP server is not found
        HTTPException: 409 if any virtual agents are using this MCP server

    Returns:
        None: 204 No Content on successful deletion
    """
    # First verify the server exists
    toolgroups = await sync_client().toolgroups.list()
    existing_toolgroup = None
    for tg in toolgroups:
        if (
            str(tg.identifier) == toolgroup_id
            and hasattr(tg, "provider_id")
            and tg.provider_id == "model-context-protocol"
        ):
            existing_toolgroup = tg
            break

    if not existing_toolgroup:
        raise HTTPException(status_code=404, detail="Server not found")

    # Check if any virtual agents are using this MCP server
    agents = await virtual_agents.get_all_with_templates(db)
    agents_using_mcp = []

    for agent in agents:
        if agent.tools:
            for tool in agent.tools:
                tool_id = None
                if isinstance(tool, dict):
                    tool_id = tool.get("toolgroup_id")
                elif hasattr(tool, "toolgroup_id"):
                    tool_id = tool.toolgroup_id
                else:
                    tool_id = str(tool)

                if tool_id == toolgroup_id:
                    agents_using_mcp.append(agent.name)
                    break

    if agents_using_mcp:
        agent_list = ", ".join(agents_using_mcp)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete MCP server '{toolgroup_id}'. "
                f"It is used by the following virtual agents: {agent_list}"
            ),
        )

    try:
        # Unregister the toolgroup from LlamaStack
        await sync_client().toolgroups.unregister(toolgroup_id=toolgroup_id)

        logger.info(f"Successfully deleted MCP server: {toolgroup_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete MCP server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete MCP server: {str(e)}",
        )
