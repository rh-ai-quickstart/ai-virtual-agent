"""
Unit tests for MCP Server management API endpoints.

Tests CRUD operations for MCP servers through LlamaStack integration,
including server discovery from Kubernetes resources.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import VirtualAgent


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_llamastack_toolgroups():
    """Mock LlamaStack toolgroups API."""
    with patch("backend.app.api.v1.mcp_servers.sync_client") as mock_client:
        mock_client.toolgroups.list = AsyncMock()
        mock_client.toolgroups.register = AsyncMock()
        mock_client.toolgroups.unregister = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_k8s_discovery_service():
    """Mock K8s MCP discovery service."""
    with patch("backend.app.api.v1.mcp_servers.get_k8s_discovery") as mock_discovery:
        yield mock_discovery


@pytest.fixture
def mock_virtual_agents_crud():
    """Mock virtual agents CRUD operations."""
    with patch("backend.app.api.v1.mcp_servers.virtual_agents") as mock_crud:
        mock_crud.get_all_with_templates = AsyncMock()
        yield mock_crud


@pytest.fixture
def sample_toolgroup():
    """Create a sample LlamaStack toolgroup."""
    toolgroup = MagicMock()
    toolgroup.identifier = "test-mcp-server"
    toolgroup.provider_id = "model-context-protocol"
    toolgroup.args = {
        "name": "Test MCP Server",
        "description": "Test Description",
        "extra_config": "value",
    }
    mcp_endpoint = MagicMock()
    mcp_endpoint.uri = "http://test-server:8080/mcp"
    toolgroup.mcp_endpoint = mcp_endpoint
    return toolgroup


class TestCreateMCPServer:
    """Test MCP server creation endpoint."""

    def test_create_mcp_server_success(self, test_client, mock_llamastack_toolgroups):
        """Test successful MCP server creation."""
        # Mock list to return no existing servers
        mock_llamastack_toolgroups.toolgroups.list.return_value = []

        server_data = {
            "toolgroup_id": "new-mcp-server",
            "name": "New MCP Server",
            "description": "New Server Description",
            "endpoint_url": "http://new-server:8080/mcp",
            "configuration": {"setting1": "value1"},
        }

        response = test_client.post("/api/v1/mcp_servers/", json=server_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["toolgroup_id"] == "new-mcp-server"
        assert data["name"] == "New MCP Server"
        assert data["provider_id"] == "model-context-protocol"

        # Verify registration was called with correct args
        mock_llamastack_toolgroups.toolgroups.register.assert_called_once()
        call_args = mock_llamastack_toolgroups.toolgroups.register.call_args
        assert call_args.kwargs["toolgroup_id"] == "new-mcp-server"
        assert call_args.kwargs["args"]["name"] == "New MCP Server"
        assert call_args.kwargs["args"]["description"] == "New Server Description"

    def test_create_mcp_server_duplicate_conflict(
        self, test_client, mock_llamastack_toolgroups, sample_toolgroup
    ):
        """Test creating MCP server with existing toolgroup_id returns conflict."""
        # Mock list to return existing server
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        server_data = {
            "toolgroup_id": "test-mcp-server",
            "name": "Duplicate Server",
            "description": "Duplicate",
            "endpoint_url": "http://duplicate:8080/mcp",
            "configuration": {},
        }

        response = test_client.post("/api/v1/mcp_servers/", json=server_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_mcp_server_llamastack_error(
        self, test_client, mock_llamastack_toolgroups
    ):
        """Test MCP server creation handles LlamaStack errors."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = []
        mock_llamastack_toolgroups.toolgroups.register.side_effect = Exception(
            "LlamaStack error"
        )

        server_data = {
            "toolgroup_id": "error-server",
            "name": "Error Server",
            "description": "Error",
            "endpoint_url": "http://error:8080/mcp",
            "configuration": {},
        }

        response = test_client.post("/api/v1/mcp_servers/", json=server_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create MCP server" in response.json()["detail"]


class TestListMCPServers:
    """Test MCP server listing endpoint."""

    def test_list_mcp_servers_success(
        self, test_client, mock_llamastack_toolgroups, sample_toolgroup
    ):
        """Test listing all MCP servers."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        response = test_client.get("/api/v1/mcp_servers/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["toolgroup_id"] == "test-mcp-server"
        assert data[0]["name"] == "Test MCP Server"
        assert data[0]["description"] == "Test Description"

    def test_list_mcp_servers_empty(self, test_client, mock_llamastack_toolgroups):
        """Test listing MCP servers when none exist."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = []

        response = test_client.get("/api/v1/mcp_servers/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_mcp_servers_filters_non_mcp_toolgroups(
        self, test_client, mock_llamastack_toolgroups, sample_toolgroup
    ):
        """Test listing only returns MCP toolgroups."""
        non_mcp_toolgroup = MagicMock()
        non_mcp_toolgroup.identifier = "other-toolgroup"
        non_mcp_toolgroup.provider_id = "other-provider"

        mock_llamastack_toolgroups.toolgroups.list.return_value = [
            sample_toolgroup,
            non_mcp_toolgroup,
        ]

        response = test_client.get("/api/v1/mcp_servers/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["toolgroup_id"] == "test-mcp-server"

    def test_list_mcp_servers_handles_different_args_formats(
        self, test_client, mock_llamastack_toolgroups
    ):
        """Test listing handles different args formats from LlamaStack."""
        # Test with object args that has model_dump
        toolgroup_with_obj = MagicMock()
        toolgroup_with_obj.identifier = "obj-server"
        toolgroup_with_obj.provider_id = "model-context-protocol"
        args_obj = MagicMock()
        args_obj.model_dump.return_value = {"name": "Object Server", "description": ""}
        toolgroup_with_obj.args = args_obj
        toolgroup_with_obj.mcp_endpoint = None

        mock_llamastack_toolgroups.toolgroups.list.return_value = [toolgroup_with_obj]

        response = test_client.get("/api/v1/mcp_servers/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_list_mcp_servers_llamastack_error(
        self, test_client, mock_llamastack_toolgroups
    ):
        """Test listing MCP servers handles LlamaStack errors."""
        mock_llamastack_toolgroups.toolgroups.list.side_effect = Exception(
            "LlamaStack error"
        )

        response = test_client.get("/api/v1/mcp_servers/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestDiscoverMCPServers:
    """Test MCP server discovery from Kubernetes."""

    def test_discover_mcp_servers_success(
        self, test_client, mock_k8s_discovery_service
    ):
        """Test successful discovery of MCP servers from K8s."""
        mock_discovery = MagicMock()
        mock_discovery.discover_mcp_servers.return_value = [
            {
                "source": "mcpserver",
                "name": "discovered-server",
                "description": "Discovered from K8s",
                "endpoint_url": "http://discovered:8080/mcp",
            }
        ]
        mock_k8s_discovery_service.return_value = mock_discovery

        response = test_client.get("/api/v1/mcp_servers/discover")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "discovered-server"
        assert data[0]["source"] == "mcpserver"

    def test_discover_mcp_servers_empty(self, test_client, mock_k8s_discovery_service):
        """Test discovery returns empty list when no servers found."""
        mock_discovery = MagicMock()
        mock_discovery.discover_mcp_servers.return_value = []
        mock_k8s_discovery_service.return_value = mock_discovery

        response = test_client.get("/api/v1/mcp_servers/discover")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_discover_mcp_servers_error(
        self, test_client, mock_k8s_discovery_service
    ):
        """Test discovery handles K8s errors gracefully."""
        mock_k8s_discovery_service.side_effect = Exception("K8s error")

        response = test_client.get("/api/v1/mcp_servers/discover")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetMCPServer:
    """Test single MCP server retrieval endpoint."""

    def test_get_mcp_server_success(
        self, test_client, mock_llamastack_toolgroups, sample_toolgroup
    ):
        """Test retrieving a single MCP server."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        response = test_client.get("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["toolgroup_id"] == "test-mcp-server"
        assert data["name"] == "Test MCP Server"

    def test_get_mcp_server_not_found(self, test_client, mock_llamastack_toolgroups):
        """Test retrieving non-existent MCP server returns 404."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = []

        response = test_client.get("/api/v1/mcp_servers/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_mcp_server_llamastack_error(
        self, test_client, mock_llamastack_toolgroups
    ):
        """Test get MCP server handles LlamaStack errors."""
        mock_llamastack_toolgroups.toolgroups.list.side_effect = Exception(
            "LlamaStack error"
        )

        response = test_client.get("/api/v1/mcp_servers/test-server")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestUpdateMCPServer:
    """Test MCP server update endpoint."""

    def test_update_mcp_server_success(
        self, test_client, mock_llamastack_toolgroups, sample_toolgroup
    ):
        """Test successful MCP server update."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        update_data = {
            "toolgroup_id": "test-mcp-server",
            "name": "Updated Name",
            "description": "Updated Description",
            "endpoint_url": "http://updated:8080/mcp",
            "configuration": {"new_setting": "new_value"},
        }

        response = test_client.put(
            "/api/v1/mcp_servers/test-mcp-server", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Description"

        # Verify unregister and register were called
        mock_llamastack_toolgroups.toolgroups.unregister.assert_called_once_with(
            toolgroup_id="test-mcp-server"
        )
        mock_llamastack_toolgroups.toolgroups.register.assert_called_once()

    def test_update_mcp_server_not_found(
        self, test_client, mock_llamastack_toolgroups
    ):
        """Test updating non-existent MCP server returns 404."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = []

        update_data = {
            "toolgroup_id": "nonexistent",
            "name": "Updated",
            "description": "Updated",
            "endpoint_url": "http://updated:8080/mcp",
            "configuration": {},
        }

        response = test_client.put("/api/v1/mcp_servers/nonexistent", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_mcp_server_llamastack_error(
        self, test_client, mock_llamastack_toolgroups, sample_toolgroup
    ):
        """Test update handles LlamaStack errors."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]
        mock_llamastack_toolgroups.toolgroups.unregister.side_effect = Exception(
            "LlamaStack error"
        )

        update_data = {
            "toolgroup_id": "test-mcp-server",
            "name": "Updated",
            "description": "Updated",
            "endpoint_url": "http://updated:8080/mcp",
            "configuration": {},
        }

        response = test_client.put(
            "/api/v1/mcp_servers/test-mcp-server", json=update_data
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestDeleteMCPServer:
    """Test MCP server deletion endpoint."""

    def test_delete_mcp_server_success(
        self,
        test_client,
        mock_llamastack_toolgroups,
        mock_virtual_agents_crud,
        sample_toolgroup,
    ):
        """Test successful MCP server deletion."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]
        mock_virtual_agents_crud.get_all_with_templates.return_value = []

        response = test_client.delete("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_llamastack_toolgroups.toolgroups.unregister.assert_called_once_with(
            toolgroup_id="test-mcp-server"
        )

    def test_delete_mcp_server_not_found(
        self, test_client, mock_llamastack_toolgroups, mock_virtual_agents_crud
    ):
        """Test deleting non-existent MCP server returns 404."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = []

        response = test_client.delete("/api/v1/mcp_servers/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_mcp_server_in_use_conflict(
        self,
        test_client,
        mock_llamastack_toolgroups,
        mock_virtual_agents_crud,
        sample_toolgroup,
    ):
        """Test deleting MCP server in use by agents returns conflict."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        # Mock agent using this MCP server
        agent = MagicMock(spec=VirtualAgent)
        agent.name = "Test Agent"
        agent.tools = [{"toolgroup_id": "test-mcp-server"}]
        mock_virtual_agents_crud.get_all_with_templates.return_value = [agent]

        response = test_client.delete("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Cannot delete MCP server" in response.json()["detail"]
        assert "Test Agent" in response.json()["detail"]

    def test_delete_mcp_server_checks_dict_tools(
        self,
        test_client,
        mock_llamastack_toolgroups,
        mock_virtual_agents_crud,
        sample_toolgroup,
    ):
        """Test deletion checks for MCP server in dict-format tools."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        agent = MagicMock(spec=VirtualAgent)
        agent.name = "Agent with Dict Tool"
        agent.tools = [{"toolgroup_id": "test-mcp-server"}]
        mock_virtual_agents_crud.get_all_with_templates.return_value = [agent]

        response = test_client.delete("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_delete_mcp_server_checks_object_tools(
        self,
        test_client,
        mock_llamastack_toolgroups,
        mock_virtual_agents_crud,
        sample_toolgroup,
    ):
        """Test deletion checks for MCP server in object-format tools."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        tool_obj = MagicMock()
        tool_obj.toolgroup_id = "test-mcp-server"
        agent = MagicMock(spec=VirtualAgent)
        agent.name = "Agent with Object Tool"
        agent.tools = [tool_obj]
        mock_virtual_agents_crud.get_all_with_templates.return_value = [agent]

        response = test_client.delete("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_delete_mcp_server_checks_string_tools(
        self,
        test_client,
        mock_llamastack_toolgroups,
        mock_virtual_agents_crud,
        sample_toolgroup,
    ):
        """Test deletion checks for MCP server in string-format tools."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]

        agent = MagicMock(spec=VirtualAgent)
        agent.name = "Agent with String Tool"
        agent.tools = ["test-mcp-server"]
        mock_virtual_agents_crud.get_all_with_templates.return_value = [agent]

        response = test_client.delete("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_delete_mcp_server_llamastack_error(
        self,
        test_client,
        mock_llamastack_toolgroups,
        mock_virtual_agents_crud,
        sample_toolgroup,
    ):
        """Test delete handles LlamaStack errors."""
        mock_llamastack_toolgroups.toolgroups.list.return_value = [sample_toolgroup]
        mock_virtual_agents_crud.get_all_with_templates.return_value = []
        mock_llamastack_toolgroups.toolgroups.unregister.side_effect = Exception(
            "LlamaStack error"
        )

        response = test_client.delete("/api/v1/mcp_servers/test-mcp-server")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
