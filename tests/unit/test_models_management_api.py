"""
Unit tests for Models Management API endpoints.

Tests model registration and management with LlamaStack.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
        "backend.app.api.v1.models_management.get_client_from_request"
    ) as mock:
        client = AsyncMock()
        client.models.register = AsyncMock()
        client.models.list = AsyncMock()
        client.models.get = AsyncMock()
        client.models.unregister = AsyncMock()
        client.shields.list = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_model():
    """Create sample model."""
    model = MagicMock()
    model.identifier = "test-model"
    model.provider_id = "test-provider"
    model.provider_resource_id = "test-resource"
    model.model_type = "llm"
    model.metadata = {"key": "value"}
    return model


class TestRegisterModel:
    """Test model registration endpoint."""

    def test_register_model_success(self, test_client, mock_llama_client, sample_model):
        """Test successful model registration."""
        mock_llama_client.models.register.return_value = sample_model

        model_data = {
            "model_id": "new-model",
            "provider_model_id": "provider-model",
            "provider_id": "test-provider",
            "model_type": "llm",
            "metadata": {},
        }

        response = test_client.post("/api/v1/models/", json=model_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["model_id"] == "test-model"

    def test_register_model_error(self, test_client, mock_llama_client):
        """Test model registration handles errors."""
        mock_llama_client.models.register.side_effect = Exception("Registration error")

        model_data = {
            "model_id": "error-model",
            "provider_model_id": "provider-model",
            "provider_id": "test-provider",
            "model_type": "llm",
            "metadata": {},
        }

        response = test_client.post("/api/v1/models/", json=model_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestListModels:
    """Test model listing endpoint."""

    def test_list_models_success(self, test_client, mock_llama_client, sample_model):
        """Test listing all models."""
        mock_llama_client.models.list.return_value = [sample_model]
        mock_llama_client.shields.list.return_value = []

        response = test_client.get("/api/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_id"] == "test-model"

    def test_list_models_with_shields(
        self, test_client, mock_llama_client, sample_model
    ):
        """Test listing models identifies shield models."""
        mock_llama_client.models.list.return_value = [sample_model]

        shield = MagicMock()
        shield.provider_resource_id = "test-resource"
        mock_llama_client.shields.list.return_value = [shield]

        response = test_client.get("/api/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data[0]["is_shield"] is True

    def test_list_models_shield_error(
        self, test_client, mock_llama_client, sample_model
    ):
        """Test listing models handles shield fetch errors gracefully."""
        mock_llama_client.models.list.return_value = [sample_model]
        mock_llama_client.shields.list.side_effect = Exception("Shield error")

        response = test_client.get("/api/v1/models/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1

    def test_list_models_error(self, test_client, mock_llama_client):
        """Test listing models handles errors."""
        mock_llama_client.models.list.side_effect = Exception("List error")

        response = test_client.get("/api/v1/models/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetModel:
    """Test single model retrieval endpoint."""

    def test_get_model_success(self, test_client, mock_llama_client, sample_model):
        """Test retrieving a single model."""
        mock_llama_client.models.retrieve.return_value = sample_model

        response = test_client.get("/api/v1/models/test-model")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["model_id"] == "test-model"

    def test_get_model_not_found(self, test_client, mock_llama_client):
        """Test retrieving non-existent model returns 404."""
        mock_llama_client.models.retrieve.side_effect = Exception("Not found")

        response = test_client.get("/api/v1/models/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteModel:
    """Test model deletion endpoint."""

    @patch("backend.app.api.v1.models_management.virtual_agents")
    def test_delete_model_success(
        self, mock_agents, test_client, mock_llama_client, sample_model
    ):
        """Test successful model deletion."""
        from backend.app.api.v1.models_management import get_db

        mock_db = AsyncMock()
        mock_llama_client.models.list.return_value = [sample_model]
        mock_agents.get_all_with_templates = AsyncMock(return_value=[])

        app.dependency_overrides[get_db] = lambda: mock_db
        response = test_client.delete("/api/v1/models/test-model")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("backend.app.api.v1.models_management.virtual_agents")
    def test_delete_model_not_found(self, mock_agents, test_client, mock_llama_client):
        """Test deleting non-existent model returns 404."""
        from backend.app.api.v1.models_management import get_db

        mock_db = AsyncMock()
        mock_agents.get_all_with_templates = AsyncMock(return_value=[])
        mock_llama_client.models.unregister = AsyncMock(side_effect=Exception("Not found"))

        app.dependency_overrides[get_db] = lambda: mock_db
        response = test_client.delete("/api/v1/models/nonexistent")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("backend.app.api.v1.models_management.virtual_agents")
    def test_delete_model_in_use(
        self, mock_agents, test_client, mock_llama_client, sample_model
    ):
        """Test deleting model in use returns conflict."""
        from backend.app.api.v1.models_management import get_db

        mock_db = AsyncMock()
        mock_llama_client.models.list.return_value = [sample_model]

        agent = MagicMock()
        agent.name = "Test Agent"
        agent.model_name = "test-model"
        mock_agents.get_all_with_templates = AsyncMock(return_value=[agent])

        app.dependency_overrides[get_db] = lambda: mock_db
        response = test_client.delete("/api/v1/models/test-model")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_409_CONFLICT
