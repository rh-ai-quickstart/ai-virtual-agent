"""
Unit tests for Provider Management API endpoints.

Tests provider registration and management, including Kubernetes ConfigMap updates.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_llama_client():
    """Mock LlamaStack client."""
    with patch(
        "backend.app.api.v1.providers_management.get_client_from_request"
    ) as mock:
        client = AsyncMock()
        client.providers.list = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_k8s_clients():
    """Mock Kubernetes clients."""
    with patch(
        "backend.app.api.v1.providers_management.get_k8s_clients"
    ) as mock_k8s, patch(
        "backend.app.api.v1.providers_management.get_namespace"
    ) as mock_namespace:
        core_v1 = MagicMock()
        apps_v1 = MagicMock()
        mock_k8s.return_value = (core_v1, apps_v1)
        mock_namespace.return_value = "test-namespace"
        yield {"core_v1": core_v1, "apps_v1": apps_v1, "namespace": mock_namespace}


class TestListProviders:
    """Test provider listing endpoint."""

    def test_list_providers_success(self, test_client, mock_llama_client):
        """Test listing all providers."""
        provider1 = MagicMock()
        provider1.provider_id = "vllm1"
        provider1.provider_type = "remote::vllm"
        provider1.api = "inference"
        provider1.config = {"url": "http://vllm:8000"}

        mock_llama_client.providers.list.return_value = [provider1]

        response = test_client.get("/api/v1/models/providers/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider_id"] == "vllm1"

    def test_list_providers_error(self, test_client, mock_llama_client):
        """Test listing providers handles errors."""
        mock_llama_client.providers.list.side_effect = Exception("LlamaStack error")

        response = test_client.get("/api/v1/models/providers/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestRegisterProvider:
    """Test provider registration endpoint."""

    @patch("backend.app.api.v1.providers_management.yaml")
    def test_register_provider_success(
        self, mock_yaml, test_client, mock_llama_client, mock_k8s_clients
    ):
        """Test successful provider registration."""
        # Mock configmap
        configmap = MagicMock()
        configmap.data = {"config.yaml": "providers:\n  inference: []"}
        mock_k8s_clients["core_v1"].read_namespaced_config_map.return_value = configmap

        # Mock YAML parsing
        mock_yaml.safe_load.return_value = {"providers": {"inference": []}}
        mock_yaml.dump.return_value = "updated_config"

        provider_data = {
            "provider_id": "new-vllm",
            "provider_type": "remote::vllm",
            "config": {"url": "http://new-vllm:8000"},
        }

        with patch("backend.app.api.v1.providers_management.wait_for_llamastack") as mock_wait:
            mock_wait.return_value = True
            response = test_client.post("/api/v1/models/providers/", json=provider_data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_register_provider_configmap_not_found(
        self, test_client, mock_llama_client, mock_k8s_clients
    ):
        """Test registration handles missing configmap."""
        from kubernetes.client.rest import ApiException

        mock_k8s_clients["core_v1"].read_namespaced_config_map.side_effect = (
            ApiException(status=404)
        )

        provider_data = {
            "provider_id": "new-vllm",
            "provider_type": "remote::vllm",
            "config": {"url": "http://new-vllm:8000"},
        }

        response = test_client.post("/api/v1/models/providers/", json=provider_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
