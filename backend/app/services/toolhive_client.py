"""
ToolHive Client for MCP Server Discovery.

This module provides integration with ToolHive API to discover MCP servers
deployed in the OpenShift/Kubernetes cluster.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ToolHiveMCPServer:
    """Represents an MCP server as discovered from ToolHive API."""

    id: str
    name: str
    description: str
    endpoint_url: str
    status: str
    metadata: Dict[str, Any]

    @classmethod
    def from_workload(cls, workload_data: Dict[str, Any]) -> "ToolHiveMCPServer":
        """Create ToolHiveMCPServer from ToolHive workloads API response."""

        # Extract basic info
        name = workload_data.get("name", "")
        status = workload_data.get("status", "unknown")
        transport_type = workload_data.get("transport_type", "stdio")
        tool_type = workload_data.get("tool_type", "mcp")

        # Handle endpoint URL - the API returns localhost URLs which won't work
        # We need to map to the actual service URLs based on cluster configuration
        api_url = workload_data.get("url", "")
        namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        cluster_domain = os.getenv("CLUSTER_DOMAIN", "svc.cluster.local")

        if name == "oracle-sqlcl":
            endpoint_url = f"http://mcp-oracle-sqlcl-proxy.{namespace}.{cluster_domain}:8080"
        elif name == "weather":
            endpoint_url = f"http://mcp-weather-proxy.{namespace}.{cluster_domain}:8000"
        else:
            # Fallback - try to construct from service naming pattern
            endpoint_url = f"http://mcp-{name}-proxy.{namespace}.{cluster_domain}:{workload_data.get('port', 8080)}"

        return cls(
            id=name,
            name=name,
            description=f"ToolHive MCP Server: {name} ({tool_type}, {transport_type})",
            endpoint_url=endpoint_url,
            status=status,
            metadata={
                "package": workload_data.get("package", ""),
                "transport_type": transport_type,
                "tool_type": tool_type,
                "port": workload_data.get("port", 8080),
                "proxy_mode": workload_data.get("proxy_mode", ""),
                "created_at": workload_data.get("created_at", ""),
                "labels": workload_data.get("labels", {}),
                "original_url": api_url
            }
        )


class ToolHiveClient:
    """Client for discovering MCP servers via ToolHive API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize ToolHive client.

        Args:
            base_url: ToolHive API base URL
            api_key: API key for authentication (if needed)
            headers: Additional headers for requests
        """
        # Default to in-cluster service URL or environment override
        # Use environment-configured namespace for default URL
        default_namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        default_cluster_domain = os.getenv("CLUSTER_DOMAIN", "svc.cluster.local")
        default_url = f"http://toolhive-api.{default_namespace}.{default_cluster_domain}:8080"

        self.base_url = base_url or os.getenv("TOOLHIVE_API_URL", default_url)
        self.api_key = api_key or os.getenv("TOOLHIVE_API_KEY")
        self.headers = headers or {}

        # Set up default headers
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

        self.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    async def list_registered_mcp_servers(self) -> List[ToolHiveMCPServer]:
        """
        Retrieve list of deployed MCP servers from ToolHive API.

        Returns:
            List[ToolHiveMCPServer]: List of discovered MCP servers
        """
        try:
            logger.info(f"Fetching MCP servers from ToolHive API: {self.base_url}")

            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                url = f"{self.base_url}/api/v1beta/workloads"

                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    servers = []

                    # Parse workloads response
                    workloads = data.get("workloads", [])
                    logger.debug(f"Found {len(workloads)} workloads from ToolHive API")

                    for workload in workloads:
                        try:
                            # Only process MCP servers that are running
                            if (workload.get("tool_type") == "mcp" and
                                workload.get("status", "").lower() == "running"):

                                server = ToolHiveMCPServer.from_workload(workload)
                                servers.append(server)
                                logger.debug(f"Found running MCP server: {server.name} at {server.endpoint_url}")
                            else:
                                logger.debug(f"Skipping workload {workload.get('name')}: tool_type={workload.get('tool_type')}, status={workload.get('status')}")

                        except Exception as e:
                            logger.warning(f"Failed to parse workload data: {e}")
                            logger.debug(f"Problematic workload data: {workload}")
                            continue

                    logger.info(f"Retrieved {len(servers)} running MCP servers from ToolHive API")
                    return servers

                elif response.status_code == 404:
                    logger.info("ToolHive workloads endpoint not found - no servers registered")
                    return []

                else:
                    error_text = response.text
                    logger.error(f"ToolHive API error: {response.status_code} - {error_text}")
                    # Don't raise - return empty list to avoid breaking main functionality
                    return []

        except httpx.ConnectError as e:
            logger.warning(f"Cannot connect to ToolHive API at {self.base_url}: {e}")
            return []  # Return empty list if ToolHive is not available
        except httpx.TimeoutException:
            logger.warning(f"Timeout connecting to ToolHive API at {self.base_url}")
            return []
        except Exception as e:
            logger.error(f"Error fetching MCP servers from ToolHive API: {e}")
            return []  # Return empty list on error to not break the main functionality

    async def get_mcp_server(self, server_id: str) -> Optional[ToolHiveMCPServer]:
        """
        Get a specific MCP server by ID from ToolHive API.

        Args:
            server_id: The name of the MCP server

        Returns:
            Optional[ToolHiveMCPServer]: The MCP server if found, None otherwise
        """
        try:
            # Get all servers and find the matching one
            servers = await self.list_registered_mcp_servers()
            for server in servers:
                if server.id == server_id or server.name == server_id:
                    return server

            logger.debug(f"MCP server {server_id} not found in ToolHive API")
            return None

        except Exception as e:
            logger.error(f"Error fetching MCP server {server_id} from ToolHive API: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if ToolHive API is available and responding.

        Returns:
            bool: True if ToolHive API is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=5.0) as client:
                url = f"{self.base_url}/api/v1beta/version"

                response = await client.get(url)
                if response.status_code == 200:
                    version_info = response.json()
                    logger.debug(f"ToolHive API health check successful: {version_info}")
                    return True
                else:
                    logger.debug(f"ToolHive API health check failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.debug(f"ToolHive API health check failed: {e}")
            return False


# Global client instance
_toolhive_client: Optional[ToolHiveClient] = None


def get_toolhive_client(base_url: Optional[str] = None) -> ToolHiveClient:
    """Get or create a ToolHive client instance."""
    global _toolhive_client
    if _toolhive_client is None:
        _toolhive_client = ToolHiveClient(base_url=base_url)
    return _toolhive_client