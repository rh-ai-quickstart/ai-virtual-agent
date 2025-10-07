"""
Model Context Protocol (MCP) Server management API endpoints.

This module provides CRUD operations for MCP servers through direct integration
with LlamaStack's toolgroups API and auto-discovery of Toolhive-managed MCP servers.

Key Features:
- Direct LlamaStack toolgroups API integration
- Auto-discovery of MCP servers from Toolhive operator
- Automatic registration of discovered servers with LlamaStack
- Create, read, update, and delete MCP server configurations
- No local database storage - all data managed by LlamaStack
- Integration with virtual agents for enhanced capabilities
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from ...api.llamastack import sync_client
from ...config import settings
from ...schemas.mcp_servers import MCPServerCreate, MCPServerRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp_servers", tags=["mcp_servers"])


def _get_kubernetes_client() -> Optional[client.CustomObjectsApi]:
    """
    Initialize and return a Kubernetes client for accessing custom resources.

    Returns:
        CustomObjectsApi client if successful, None if Kubernetes is not available
    """
    try:
        # Try to load in-cluster config first (when running in Kubernetes)
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        except config.ConfigException:
            # Fall back to local kubeconfig (for development)
            try:
                config.load_kube_config()
                logger.info("Loaded local kubeconfig")
            except config.ConfigException:
                logger.warning(
                    "No Kubernetes configuration found - MCP auto-discovery disabled"
                )
                return None

        return client.CustomObjectsApi()
    except Exception as e:
        logger.warning(f"Failed to initialize Kubernetes client: {e}")
        return None


async def _discover_toolhive_mcp_servers() -> List[dict]:
    """
    Discover MCP servers managed by Toolhive operator.

    Returns:
        List of MCP server information from Toolhive
    """
    k8s_client = _get_kubernetes_client()
    if not k8s_client:
        logger.info("Kubernetes client not available - skipping Toolhive discovery")
        return []

    try:
        # Get current namespace from configuration
        namespace = settings.KUBERNETES_NAMESPACE

        # List MCPServer custom resources
        mcpservers = k8s_client.list_namespaced_custom_object(
            group="toolhive.stacklok.dev",
            version="v1alpha1",
            namespace=namespace,
            plural="mcpservers",
        )

        discovered_servers = []
        for item in mcpservers.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            # Extract server information
            server_name = metadata.get("name")
            transport = spec.get("transport", "stdio")
            port = spec.get("port", 8080)

            # Construct endpoint URL based on Toolhive proxy naming convention
            endpoint_url = f"http://mcp-{server_name}-proxy:{port}/sse"

            # Check if server is ready (Toolhive should set status conditions)
            is_ready = True  # Assume ready if deployed by Toolhive
            conditions = status.get("conditions", [])
            for condition in conditions:
                if (
                    condition.get("type") == "Ready"
                    and condition.get("status") != "True"
                ):
                    is_ready = False
                    break

            if is_ready:
                discovered_servers.append(
                    {
                        "name": server_name,
                        "endpoint_url": endpoint_url,
                        "transport": transport,
                        "port": port,
                        "toolgroup_id": f"mcp::{server_name}",  # Use mcp:: prefix
                        "description": f"Auto-discovered MCP server from Toolhive: {server_name}",
                        "configuration": {
                            "transport": transport,
                            "port": port,
                            "source": "toolhive",
                        },
                    }
                )
                logger.info(
                    f"Discovered Toolhive MCP server: {server_name} at {endpoint_url}"
                )
            else:
                logger.info(f"Skipping MCP server {server_name} - not ready")

        logger.info(
            f"Discovered {len(discovered_servers)} ready MCP servers from Toolhive"
        )
        return discovered_servers

    except ApiException as e:
        if e.status == 404:
            logger.info("MCPServer CRD not found - Toolhive may not be installed")
        else:
            logger.error(f"Kubernetes API error during MCP discovery: {e}")
        return []
    except Exception as e:
        logger.error(f"Error discovering Toolhive MCP servers: {e}")
        return []


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
            provider_id="model-context-protocol",
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
    Retrieve all MCP servers with auto-discovery from Toolhive.

    This function:
    1. Scans existing MCP servers in Toolhive
    2. For each Toolhive MCP server not yet registered with LlamaStack:
       - Validates its status (trusts Toolhive status)
       - Registers it with LlamaStack using mcp:: prefix
    3. Returns the list of registered MCP servers from LlamaStack

    Returns:
        List[MCPServerRead]: List of all MCP servers
    """
    try:
        logger.info("Starting MCP server discovery and synchronization")

        # Step 1: Discover MCP servers from Toolhive
        toolhive_servers = await _discover_toolhive_mcp_servers()

        # Step 2: Get currently registered MCP servers from LlamaStack
        toolgroups = await sync_client.toolgroups.list()
        registered_toolgroup_ids = set()

        # Build list of currently registered MCP servers
        mcp_servers = []
        for toolgroup in toolgroups:
            if (
                hasattr(toolgroup, "provider_id")
                and toolgroup.provider_id == "model-context-protocol"
            ):
                toolgroup_id = str(toolgroup.identifier)
                registered_toolgroup_ids.add(toolgroup_id)

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
                    toolgroup_id=toolgroup_id,
                    name=args.get("name")
                    or getattr(
                        toolgroup,
                        "provider_resource_id",
                        toolgroup_id,
                    ),
                    description=args.get("description", ""),
                    endpoint_url=endpoint_uri or "",
                    configuration=args,
                    provider_id=toolgroup.provider_id,
                )
                mcp_servers.append(mcp_server)

        logger.info(
            f"Found {len(mcp_servers)} already registered MCP servers in LlamaStack"
        )

        # Step 3: Register newly discovered Toolhive servers with LlamaStack
        newly_registered = 0
        for server_info in toolhive_servers:
            toolgroup_id = server_info["toolgroup_id"]

            # Check if this server is already registered
            if toolgroup_id not in registered_toolgroup_ids:
                logger.info(f"Registering new MCP server from Toolhive: {toolgroup_id}")

                # Register with LlamaStack
                if await _register_mcp_server_with_llamastack(server_info):
                    # Add to our list of MCP servers
                    new_server = MCPServerRead(
                        toolgroup_id=toolgroup_id,
                        name=server_info["name"],
                        description=server_info["description"],
                        endpoint_url=server_info["endpoint_url"],
                        configuration=server_info["configuration"],
                        provider_id="model-context-protocol",
                    )
                    mcp_servers.append(new_server)
                    newly_registered += 1
                    logger.info(
                        f"Successfully auto-registered MCP server: {toolgroup_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to auto-register MCP server: {toolgroup_id}"
                    )
            else:
                logger.debug(f"MCP server {toolgroup_id} already registered, skipping")

        logger.info(f"Auto-registered {newly_registered} new MCP servers from Toolhive")
        logger.info(f"Total MCP servers available: {len(mcp_servers)}")

        return mcp_servers

    except Exception as e:
        logger.error(f"Failed to fetch and synchronize MCP servers: {str(e)}")
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
