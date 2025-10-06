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

from ...api.llamastack import sync_client
from ...schemas.mcp_servers import MCPServerCreate, MCPServerRead
from ...services.toolhive_client import ToolHiveMCPServer, get_toolhive_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp_servers", tags=["mcp_servers"])


def convert_toolhive_mcp_to_llamastack(
    toolhive_mcp: ToolHiveMCPServer,
) -> MCPServerCreate:
    """
    Convert ToolHive MCP server format to LlamaStack MCPServerCreate format.

    Args:
        toolhive_mcp: ToolHive MCP server data

    Returns:
        MCPServerCreate: LlamaStack-compatible MCP server data
    """
    return MCPServerCreate(
        toolgroup_id=f"toolhive-{toolhive_mcp.id}",
        name=toolhive_mcp.name,
        description=toolhive_mcp.description,
        endpoint_url=toolhive_mcp.endpoint_url,
        configuration={
            "toolhive_source": True,
            "toolhive_id": toolhive_mcp.id,
            "toolhive_status": toolhive_mcp.status,
            **toolhive_mcp.metadata,
        },
    )


async def register_mcp_servers_from_toolhive():
    """
    Auto-discovery and registration of MCP servers from ToolHive.
    Following Yuval Turgeman's pattern for MCP server discovery.
    """
    try:
        logger.info("Starting auto-discovery of MCP servers from ToolHive")

        toolhive_client = get_toolhive_client()
        toolhive_mcp_servers = await toolhive_client.list_registered_mcp_servers()

        registered_count = 0
        for toolhive_mcp in toolhive_mcp_servers:
            try:
                llama_stack_mcp = convert_toolhive_mcp_to_llamastack(toolhive_mcp)

                # Register the toolgroup directly with LlamaStack
                await sync_client.toolgroups.register(
                    toolgroup_id=llama_stack_mcp.toolgroup_id,
                    provider_id="model-context-protocol",
                    args={
                        "name": llama_stack_mcp.name,
                        "description": llama_stack_mcp.description,
                        **llama_stack_mcp.configuration,
                    },
                    mcp_endpoint={"uri": llama_stack_mcp.endpoint_url},
                )

                registered_count += 1
                logger.debug(
                    f"Auto-registered MCP server from ToolHive: " f"{toolhive_mcp.name}"
                )

            except Exception as e:
                # Don't fail the entire process if one server fails
                logger.warning(
                    f"Failed to register ToolHive MCP server "
                    f"{toolhive_mcp.name}: {e}"
                )
                continue

        logger.info(
            f"Auto-discovery completed: registered {registered_count} "
            f"MCP servers from ToolHive"
        )

    except Exception as e:
        # Don't break the main API if ToolHive auto-discovery fails
        logger.warning(f"ToolHive auto-discovery failed: {e}")
        pass


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
    Includes auto-discovery from ToolHive for deployed MCP servers.

    Returns:
        List[MCPServerRead]: List of all MCP servers
    """
    try:
        logger.info("Fetching MCP servers from LlamaStack with ToolHive auto-discovery")

        # Auto-discover and register MCP servers from ToolHive
        await register_mcp_servers_from_toolhive()

        # Get all toolgroups from LlamaStack
        toolgroups = await sync_client.toolgroups.list()

        # For local development: also include discovered ToolHive servers
        # even if registration failed
        discovered_toolhive_servers = []
        try:
            toolhive_client = get_toolhive_client()
            toolhive_mcp_servers = await toolhive_client.list_registered_mcp_servers()

            for toolhive_mcp in toolhive_mcp_servers:
                # Check if this server is already registered successfully
                # in LlamaStack
                toolgroup_id = f"toolhive-{toolhive_mcp.id}"
                already_registered = any(
                    str(tg.identifier) == toolgroup_id
                    for tg in toolgroups
                    if hasattr(tg, "provider_id")
                    and tg.provider_id == "model-context-protocol"
                )

                # If not registered, include it as a "discovered" server
                # for UI testing
                if not already_registered:
                    discovered_toolhive_servers.append(
                        MCPServerRead(
                            toolgroup_id=toolgroup_id,
                            name=toolhive_mcp.name,
                            description=(
                                f"{toolhive_mcp.description} "
                                f"(ToolHive Discovery - Local Dev)"
                            ),
                            endpoint_url=toolhive_mcp.endpoint_url,
                            configuration={
                                **toolhive_mcp.metadata,
                                "toolhive_source": True,
                                "toolhive_id": toolhive_mcp.id,
                                "toolhive_status": toolhive_mcp.status,
                                "local_dev_discovery": True,
                                "registration_status": "pending_mcp_provider",
                            },
                            provider_id="toolhive-discovery",
                        )
                    )
        except Exception as e:
            logger.debug(f"Could not fetch ToolHive servers for local dev display: {e}")
            pass

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

        # Add discovered ToolHive servers to the response for local development
        mcp_servers.extend(discovered_toolhive_servers)

        logger.info(
            f"Retrieved {len(mcp_servers)} MCP servers from LlamaStack "
            f"({len(discovered_toolhive_servers)} discovered from "
            f"ToolHive for local dev)"
        )
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


@router.get("/toolhive/test", response_model=dict)
async def test_toolhive_discovery():
    """
    Test endpoint for ToolHive auto-discovery without LlamaStack
    registration.

    Returns debug information about discovered MCP servers and conversion
    process.
    Useful for testing and validation without requiring LlamaStack MCP
    provider.

    Returns:
        dict: Discovery results with debug information
    """
    try:
        logger.info("Testing ToolHive auto-discovery")

        # Get ToolHive client and discover servers
        toolhive_client = get_toolhive_client()

        # Test ToolHive connection first
        health_check = await toolhive_client.health_check()

        # Discover MCP servers
        toolhive_mcp_servers = await toolhive_client.list_registered_mcp_servers()

        # Convert to LlamaStack format
        converted_servers = []
        conversion_errors = []

        for toolhive_mcp in toolhive_mcp_servers:
            try:
                llama_stack_mcp = convert_toolhive_mcp_to_llamastack(toolhive_mcp)
                converted_servers.append(
                    {
                        "original": {
                            "id": toolhive_mcp.id,
                            "name": toolhive_mcp.name,
                            "description": toolhive_mcp.description,
                            "endpoint_url": toolhive_mcp.endpoint_url,
                            "status": toolhive_mcp.status,
                            "metadata": toolhive_mcp.metadata,
                        },
                        "converted": {
                            "toolgroup_id": llama_stack_mcp.toolgroup_id,
                            "name": llama_stack_mcp.name,
                            "description": llama_stack_mcp.description,
                            "endpoint_url": llama_stack_mcp.endpoint_url,
                            "configuration": llama_stack_mcp.configuration,
                        },
                    }
                )
            except Exception as e:
                conversion_errors.append(
                    {"server_name": toolhive_mcp.name, "error": str(e)}
                )

        result = {
            "toolhive_health": health_check,
            "toolhive_base_url": toolhive_client.base_url,
            "discovered_count": len(toolhive_mcp_servers),
            "converted_count": len(converted_servers),
            "conversion_errors_count": len(conversion_errors),
            "servers": converted_servers,
            "conversion_errors": conversion_errors,
            "test_timestamp": "2025-10-06T18:12:00Z",
        }

        logger.info(
            f"ToolHive test completed: discovered {len(toolhive_mcp_servers)} "
            f"servers, converted {len(converted_servers)}"
        )
        return result

    except Exception as e:
        logger.error(f"ToolHive test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ToolHive test failed: {str(e)}",
        )
