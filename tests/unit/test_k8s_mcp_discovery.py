"""
Unit tests for Kubernetes MCP Server Discovery Service.

Tests the K8sMCPDiscovery class that discovers MCP servers from
Kubernetes MCPServer custom resources and Service resources.
"""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest
from kubernetes import client

from backend.app.services.k8s_mcp_discovery import K8sMCPDiscovery, get_k8s_discovery


class TestK8sMCPDiscoveryInit:
    """Test K8sMCPDiscovery initialization."""

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="test-namespace")
    def test_init_with_incluster_config(
        self, mock_file, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test initialization with in-cluster config."""
        mock_exists.return_value = True

        discovery = K8sMCPDiscovery()

        assert discovery.enabled is True
        assert discovery.namespace == "test-namespace"
        mock_incluster.assert_called_once()
        mock_core_api.assert_called_once()
        mock_custom_api.assert_called_once()

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.config.load_kube_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_init_with_kubeconfig_fallback(
        self,
        mock_exists,
        mock_core_api,
        mock_custom_api,
        mock_kubeconfig,
        mock_incluster,
    ):
        """Test initialization falls back to kubeconfig."""
        from kubernetes.config import ConfigException

        mock_exists.return_value = False
        mock_incluster.side_effect = ConfigException("Not in cluster")

        discovery = K8sMCPDiscovery()

        assert discovery.enabled is True
        assert discovery.namespace == "default"
        mock_incluster.assert_called_once()
        mock_kubeconfig.assert_called_once()

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.config.load_kube_config")
    def test_init_disabled_when_no_config(self, mock_kubeconfig, mock_incluster):
        """Test initialization disabled when no K8s config available."""
        from kubernetes.config import ConfigException

        mock_incluster.side_effect = ConfigException("Not in cluster")
        mock_kubeconfig.side_effect = ConfigException("No kubeconfig")

        discovery = K8sMCPDiscovery()

        assert discovery.enabled is False

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    @patch("os.getenv")
    def test_init_with_env_namespace(
        self, mock_getenv, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test initialization with namespace from environment variable."""
        mock_exists.return_value = False
        mock_getenv.return_value = "custom-namespace"

        discovery = K8sMCPDiscovery()

        assert discovery.namespace == "custom-namespace"


class TestDiscoverMCPServers:
    """Test main discover_mcp_servers method."""

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_when_disabled(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test discover returns empty list when disabled."""
        from kubernetes.config import ConfigException

        mock_exists.return_value = False
        mock_incluster.side_effect = ConfigException("Not in cluster")

        with patch("backend.app.services.k8s_mcp_discovery.config.load_kube_config") as mock_kube:
            mock_kube.side_effect = ConfigException("No config")
            discovery = K8sMCPDiscovery()

        result = discovery.discover_mcp_servers()

        assert result == []

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_combines_mcpserver_and_service_resources(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test discover combines both MCPServer and Service resources."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        # Mock MCPServer resources
        mock_custom_api_instance = MagicMock()
        discovery.custom_api = mock_custom_api_instance
        mock_custom_api_instance.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "mcp1", "labels": {}},
                    "spec": {"description": "MCP 1"},
                    "status": {"url": "http://mcp1:8080"},
                }
            ]
        }

        # Mock Service resources
        mock_core_api_instance = MagicMock()
        discovery.core_api = mock_core_api_instance
        mock_service = MagicMock()
        mock_service.metadata.name = "svc1"
        mock_service.metadata.annotations = {"description": "Service 1"}
        mock_service.metadata.labels = {}
        mock_port = MagicMock()
        mock_port.port = 8080
        mock_service.spec.ports = [mock_port]
        mock_core_api_instance.list_namespaced_service.return_value.items = [mock_service]

        result = discovery.discover_mcp_servers()

        assert len(result) == 2
        assert result[0]["source"] == "mcpserver"
        assert result[1]["source"] == "service"

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_handles_mcpserver_error_gracefully(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test discover continues on MCPServer discovery error."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        # Mock MCPServer error
        mock_custom_api_instance = MagicMock()
        discovery.custom_api = mock_custom_api_instance
        mock_custom_api_instance.list_namespaced_custom_object.side_effect = Exception("K8s error")

        # Mock Service resources working
        mock_core_api_instance = MagicMock()
        discovery.core_api = mock_core_api_instance
        mock_core_api_instance.list_namespaced_service.return_value.items = []

        result = discovery.discover_mcp_servers()

        # Should still return empty list without crashing
        assert result == []


class TestDiscoverMCPServerResources:
    """Test _discover_mcpserver_resources method."""

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_mcpserver_with_valid_resources(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test discovering valid MCPServer resources."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_custom_api_instance = MagicMock()
        discovery.custom_api = mock_custom_api_instance
        mock_custom_api_instance.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {
                        "name": "test-mcp",
                        "labels": {"mcp.transport": "sse"},
                    },
                    "spec": {"description": "Test MCP Server"},
                    "status": {"url": "http://test-mcp:8080"},
                }
            ]
        }

        result = discovery._discover_mcpserver_resources()

        assert len(result) == 1
        assert result[0]["name"] == "test-mcp"
        assert result[0]["description"] == "Test MCP Server"
        assert result[0]["endpoint_url"] == "http://test-mcp:8080/sse"
        assert result[0]["source"] == "mcpserver"

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_mcpserver_with_missing_url(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test MCPServer without URL is skipped."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_custom_api_instance = MagicMock()
        discovery.custom_api = mock_custom_api_instance
        mock_custom_api_instance.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "test-mcp", "labels": {}},
                    "spec": {"description": "Test MCP"},
                    "status": {},  # No URL
                }
            ]
        }

        result = discovery._discover_mcpserver_resources()

        assert len(result) == 0

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_mcpserver_auto_generates_description(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test auto-generated description when not provided."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_custom_api_instance = MagicMock()
        discovery.custom_api = mock_custom_api_instance
        mock_custom_api_instance.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "test-mcp", "labels": {}},
                    "spec": {},  # No description
                    "status": {"url": "http://test:8080"},
                }
            ]
        }

        result = discovery._discover_mcpserver_resources()

        assert len(result) == 1
        assert "test-mcp" in result[0]["description"]

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_mcpserver_handles_404_crd_not_found(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test handling of 404 when MCPServer CRD not installed."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_custom_api_instance = MagicMock()
        discovery.custom_api = mock_custom_api_instance
        api_exception = client.exceptions.ApiException(status=404)
        mock_custom_api_instance.list_namespaced_custom_object.side_effect = api_exception

        result = discovery._discover_mcpserver_resources()

        assert result == []


class TestGetMCPServerURL:
    """Test _get_mcpserver_url method."""

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_get_url_with_sse_transport(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test URL construction for SSE transport."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        status = {"url": "http://test:8080"}
        transport = "sse"

        url = discovery._get_mcpserver_url(status, transport)

        assert url == "http://test:8080/sse"

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_get_url_with_other_transport(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test URL construction for non-SSE transport."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        status = {"url": "http://test:8080"}
        transport = "streamable-http"

        url = discovery._get_mcpserver_url(status, transport)

        assert url == "http://test:8080/mcp"

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_get_url_with_missing_status_url(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test URL construction returns None when status.url missing."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        status = {}
        transport = "sse"

        url = discovery._get_mcpserver_url(status, transport)

        assert url is None


class TestDiscoverServiceResources:
    """Test _discover_service_resources method."""

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_service_with_valid_resources(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test discovering valid Service resources."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_core_api_instance = MagicMock()
        discovery.core_api = mock_core_api_instance

        mock_service = MagicMock()
        mock_service.metadata.name = "test-service"
        mock_service.metadata.annotations = {"description": "Test Service"}
        mock_service.metadata.labels = {"mcp.transport": "sse"}
        mock_port = MagicMock()
        mock_port.port = 8080
        mock_service.spec.ports = [mock_port]

        mock_core_api_instance.list_namespaced_service.return_value.items = [mock_service]

        result = discovery._discover_service_resources()

        assert len(result) == 1
        assert result[0]["name"] == "test-service"
        assert result[0]["description"] == "Test Service"
        assert result[0]["endpoint_url"] == "http://test-service.test.svc.cluster.local:8080/sse"
        assert result[0]["source"] == "service"

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_service_with_http_transport(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test Service URL with non-SSE transport uses /mcp suffix."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_core_api_instance = MagicMock()
        discovery.core_api = mock_core_api_instance

        mock_service = MagicMock()
        mock_service.metadata.name = "test-service"
        mock_service.metadata.annotations = {}
        mock_service.metadata.labels = {"mcp.transport": "streamable-http"}
        mock_port = MagicMock()
        mock_port.port = 8080
        mock_service.spec.ports = [mock_port]

        mock_core_api_instance.list_namespaced_service.return_value.items = [mock_service]

        result = discovery._discover_service_resources()

        assert result[0]["endpoint_url"] == "http://test-service.test.svc.cluster.local:8080/mcp"

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_service_auto_generates_description(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test auto-generated description for Service without annotation."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_core_api_instance = MagicMock()
        discovery.core_api = mock_core_api_instance

        mock_service = MagicMock()
        mock_service.metadata.name = "test-service"
        mock_service.metadata.annotations = None
        mock_service.metadata.labels = {}
        mock_port = MagicMock()
        mock_port.port = 8080
        mock_service.spec.ports = [mock_port]

        mock_core_api_instance.list_namespaced_service.return_value.items = [mock_service]

        result = discovery._discover_service_resources()

        assert "test-service" in result[0]["description"]

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.client.CustomObjectsApi")
    @patch("backend.app.services.k8s_mcp_discovery.client.CoreV1Api")
    @patch("os.path.exists")
    def test_discover_service_handles_error_gracefully(
        self, mock_exists, mock_core_api, mock_custom_api, mock_incluster
    ):
        """Test Service discovery handles errors gracefully."""
        mock_exists.return_value = False

        discovery = K8sMCPDiscovery()
        discovery.enabled = True
        discovery.namespace = "test"

        mock_core_api_instance = MagicMock()
        discovery.core_api = mock_core_api_instance
        mock_core_api_instance.list_namespaced_service.side_effect = Exception("K8s error")

        result = discovery._discover_service_resources()

        assert result == []


class TestGetK8sDiscoverySingleton:
    """Test get_k8s_discovery singleton function."""

    @patch("backend.app.services.k8s_mcp_discovery.config.load_incluster_config")
    @patch("backend.app.services.k8s_mcp_discovery.config.load_kube_config")
    def test_get_k8s_discovery_returns_singleton(self, mock_kubeconfig, mock_incluster):
        """Test get_k8s_discovery returns the same instance."""
        from kubernetes.config import ConfigException

        mock_incluster.side_effect = ConfigException("Not in cluster")
        mock_kubeconfig.side_effect = ConfigException("No config")

        # Reset the singleton
        import backend.app.services.k8s_mcp_discovery as discovery_module
        discovery_module._discovery_instance = None

        instance1 = get_k8s_discovery()
        instance2 = get_k8s_discovery()

        assert instance1 is instance2
