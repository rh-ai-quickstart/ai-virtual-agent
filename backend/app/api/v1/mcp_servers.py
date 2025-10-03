"""
Model Context Protocol (MCP) Server management API endpoints.

This module provides CRUD operations for MCP servers through direct integration
with LlamaStack's toolgroups API and auto-discovery of Toolhive-managed MCP servers.

Key Features:
- Direct LlamaStack toolgroups API integration
- Auto-discovery of MCP servers from Toolhive (simplified approach)
- Automatic registration of discovered servers with LlamaStack
- Create, read, update, and delete MCP server configurations
- No local database storage - all data managed by LlamaStack
- Integration with virtual agents for enhanced capabilities
"""

import logging
import os
from typing import List

from fastapi import APIRouter, HTTPException, status

from ...api.llamastack import sync_client
from ...schemas.mcp_servers import MCPServerCreate, MCPServerRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp_servers", tags=["mcp_servers"])


async def _discover_toolhive_mcp_servers() -> List[dict]:
    """
    Discover MCP servers managed by Toolhive using simplified approach.

    This function can be extended to support different discovery methods:
    - Environment variables for local development
    - API calls to Toolhive service
    - Configuration files
    - etc.

    Returns:
        List of MCP server information from Toolhive
    """
    discovered_servers = []

    # Method 1: Environment variable based discovery (for local development)
    # This allows manual configuration of MCP servers via environment variables
    mcp_servers_env = os.getenv("MCP_SERVERS", "")
    if mcp_servers_env:
        try:
            # Expected format: "server1:port1,server2:port2" or JSON format
            if mcp_servers_env.startswith("["):
                # JSON format
                import json

                servers_config = json.loads(mcp_servers_env)
                for server_config in servers_config:
                    server_name = server_config.get("name")
                    port = server_config.get("port", 8080)
                    transport = server_config.get("transport", "sse")

                    if server_name:
                        endpoint_url = f"http://localhost:{port}/sse"
                        discovered_servers.append(
                            {
                                "name": server_name,
                                "endpoint_url": endpoint_url,
                                "transport": transport,
                                "port": port,
                                "toolgroup_id": f"mcp::{server_name}",
                                "description": f"Auto-discovered MCP server from environment: {server_name}",
                                "configuration": {
                                    "transport": transport,
                                    "port": port,
                                    "source": "environment",
                                },
                            }
                        )
                        logger.info(
                            f"Discovered MCP server from environment: {server_name} at {endpoint_url}"
                        )
            else:
                # Simple comma-separated format
                servers = mcp_servers_env.split(",")
                for server in servers:
                    if ":" in server:
                        server_name, port = server.split(":", 1)
                        port = int(port.strip())
                        server_name = server_name.strip()

                        endpoint_url = f"http://localhost:{port}/sse"
                        discovered_servers.append(
                            {
                                "name": server_name,
                                "endpoint_url": endpoint_url,
                                "transport": "sse",
                                "port": port,
                                "toolgroup_id": f"mcp::{server_name}",
                                "description": f"Auto-discovered MCP server from environment: {server_name}",
                                "configuration": {
                                    "transport": "sse",
                                    "port": port,
                                    "source": "environment",
                                },
                            }
                        )
                        logger.info(
                            f"Discovered MCP server from environment: {server_name} at {endpoint_url}"
                        )
        except Exception as e:
            logger.warning(f"Failed to parse MCP_SERVERS environment variable: {e}")

    # Method 2: Toolhive API discovery (if TOOLHIVE_API_URL is configured)
    toolhive_api_url = os.getenv("TOOLHIVE_API_URL")
    if toolhive_api_url:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{toolhive_api_url}/api/v1beta/registry", timeout=5.0
                )
                if response.status_code == 200:
                    registry_data = response.json()
                    servers_data = registry_data.get("servers", {})

                    for server_name, server_data in servers_data.items():
                        status = server_data.get("status", "Active")
                        transport = server_data.get("transport", "sse")
                        description = server_data.get(
                            "description", f"MCP server: {server_name}"
                        )

                        # Only include servers that are Active
                        if status == "Active" and server_name:
                            # Use localhost with port forwarding for local development
                            if server_name == "weather":
                                port = 8001
                            elif server_name == "oracle-sqlcl":
                                port = 8081
                            else:
                                port = 8080  # default port

                            endpoint_url = f"http://localhost:{port}/sse"
                            discovered_servers.append(
                                {
                                    "name": server_name,
                                    "endpoint_url": endpoint_url,
                                    "transport": transport,
                                    "port": port,
                                    "toolgroup_id": f"mcp::{server_name}",
                                    "description": f"Auto-discovered MCP server from Toolhive API: {description}",
                                    "configuration": {
                                        "transport": transport,
                                        "port": port,
                                        "source": "toolhive_api",
                                    },
                                }
                            )
                            logger.info(
                                f"Discovered MCP server from Toolhive API: {server_name} at {endpoint_url}"
                            )
        except Exception as e:
            logger.warning(f"Failed to discover MCP servers from Toolhive API: {e}")

    # Method 3: Default local MCP servers (for development)
    # These are the servers we know are available via port forwarding
    default_servers = [
        {"name": "weather", "port": 8001, "description": "Weather MCP server"},
        {"name": "oracle-sqlcl", "port": 8081, "description": "Oracle SQL MCP server"},
        {"name": "inspector", "port": 6275, "description": "MCP Inspector server"},
    ]

    for server in default_servers:
        server_name = server["name"]
        port = server["port"]
        description = server["description"]

        # Check if this server is already discovered
        if not any(s["name"] == server_name for s in discovered_servers):
            endpoint_url = f"http://localhost:{port}/sse"
            discovered_servers.append(
                {
                    "name": server_name,
                    "endpoint_url": endpoint_url,
                    "transport": "sse",
                    "port": port,
                    "toolgroup_id": f"mcp::{server_name}",
                    "description": f"Auto-discovered MCP server (default): {description}",
                    "configuration": {
                        "transport": "sse",
                        "port": port,
                        "source": "default",
                    },
                }
            )
            logger.info(
                f"Discovered default MCP server: {server_name} at {endpoint_url}"
            )

    logger.info(f"Discovered {len(discovered_servers)} MCP servers total")
    return discovered_servers


async def _register_mcp_server_with_llamastack(server_info: dict) -> bool:
    """
    Register a discovered MCP server with LlamaStack.

    Args:
        server_info: Dictionary containing MCP server information

    Returns:
        True if registration successful, False otherwise
    """
    try:
        await sync_client.toolgroups.register(
            toolgroup_id=server_info["toolgroup_id"],
            provider_id="mcp-server-provider",
            args={
                "name": server_info["name"],
                "description": server_info["description"],
                **server_info["configuration"],
            },
            mcp_endpoint={"uri": server_info["endpoint_url"]},
        )
        logger.info(
            f"Successfully registered MCP server with LlamaStack: {server_info['toolgroup_id']}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Failed to register MCP server {server_info['toolgroup_id']} with LlamaStack: {e}"
        )
        return False


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
            provider_id="mcp-server-provider",
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
            provider_id="mcp-server-provider",
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
    Retrieve all MCP servers with auto-discovery from Toolhive.

    This function:
    1. Scans existing MCP servers in Toolhive
    2. Returns the list of discovered MCP servers directly
    3. Note: LlamaStack registration is temporarily disabled due to provider configuration issues

    Returns:
        List[MCPServerRead]: List of all discovered MCP servers
    """
    try:
        logger.info("Starting MCP server discovery")

        # Step 1: Discover MCP servers from Toolhive
        toolhive_servers = await _discover_toolhive_mcp_servers()

        # Step 2: Convert discovered servers to MCPServerRead format
        mcp_servers = []
        for server_info in toolhive_servers:
            mcp_server = MCPServerRead(
                toolgroup_id=server_info["toolgroup_id"],
                name=server_info["name"],
                description=server_info["description"],
                endpoint_url=server_info["endpoint_url"],
                configuration=server_info["configuration"],
                provider_id="mcp-server-provider",
            )
            mcp_servers.append(mcp_server)

        logger.info(f"Discovered {len(mcp_servers)} MCP servers total")

        return mcp_servers

    except Exception as e:
        logger.error(f"Failed to discover MCP servers: {str(e)}")
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
        logger.info(f"Fetching MCP server: {toolgroup_id}")

        # Get all discovered MCP servers and find the matching one
        toolhive_servers = await _discover_toolhive_mcp_servers()

        for server_info in toolhive_servers:
            if server_info["toolgroup_id"] == toolgroup_id:
                return MCPServerRead(
                    toolgroup_id=server_info["toolgroup_id"],
                    name=server_info["name"],
                    description=server_info["description"],
                    endpoint_url=server_info["endpoint_url"],
                    configuration=server_info["configuration"],
                    provider_id="mcp-server-provider",
                )

        raise HTTPException(status_code=404, detail="Server not found")

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
                and tg.provider_id == "mcp-server-provider"
            ):
                existing_toolgroup = tg
                break

        if not existing_toolgroup:
            raise HTTPException(status_code=404, detail="Server not found")

        # Update by re-registering with new config
        await sync_client.toolgroups.register(
            toolgroup_id=server.toolgroup_id,
            provider_id="mcp-server-provider",
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
            provider_id="mcp-server-provider",
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
                and tg.provider_id == "mcp-server-provider"
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
