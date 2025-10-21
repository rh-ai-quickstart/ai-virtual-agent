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
from typing import List

from fastapi import APIRouter, HTTPException, status

from ....schemas.mcp_servers import MCPServerCreate, MCPServerRead
from .client import sync_client

logger = logging.getLogger(__name__)

router = APIRouter()


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
    try:
        logger.info(f"Creating MCP server in LlamaStack: {server.name}")

        # Register the toolgroup directly with LlamaStack
        await sync_client.toolgroups.register(
            toolgroup_id=server.toolgroup_id,
            provider_id="model-context-protocol",
            args={
                "name": server.name,
                "description": server.description,
                **server.configuration,
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
        toolgroups = await sync_client.toolgroups.list()

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

                endpoint_obj = getattr(toolgroup, "mcp_endpoint", None)
                endpoint_uri = (
                    getattr(endpoint_obj, "uri", None)
                    if endpoint_obj is not None
                    else None
                )

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
                    configuration=args,
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
        toolgroups = await sync_client.toolgroups.list()
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

        return MCPServerRead(
            toolgroup_id=str(toolgroup.identifier),
            name=args.get("name")
            or getattr(toolgroup, "provider_resource_id", str(toolgroup.identifier)),
            description=args.get("description", ""),
            endpoint_url=endpoint_uri or "",
            configuration=args,
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
        toolgroups = await sync_client.toolgroups.list()
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

        # Update by re-registering with new config
        await sync_client.toolgroups.register(
            toolgroup_id=server.toolgroup_id,
            provider_id="model-context-protocol",
            args={
                "name": server.name,
                "description": server.description,
                **server.configuration,
            },
            mcp_endpoint={"uri": server.endpoint_url},
        )

        logger.info(f"Successfully updated MCP server: {server.toolgroup_id}")

        return MCPServerRead(
            toolgroup_id=server.toolgroup_id,
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
async def delete_mcp_server(toolgroup_id: str):
    """
    Delete an MCP server configuration.

    Args:
        toolgroup_id: The tool group identifier of the MCP server to delete

    Raises:
        HTTPException: 404 if the MCP server is not found

    Returns:
        None: 204 No Content on successful deletion
    """
    try:
        # First verify the server exists
        toolgroups = await sync_client.toolgroups.list()
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

        # Unregister the toolgroup from LlamaStack
        await sync_client.toolgroups.unregister(toolgroup_id=toolgroup_id)

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
