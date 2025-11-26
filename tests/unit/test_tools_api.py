"""
Unit tests for Tools API endpoints.

Tests tool discovery and retrieval from LlamaStack.
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
    with patch("backend.app.api.v1.tools.get_client_from_request") as mock:
        client = AsyncMock()
        client.tool_runtime.list_runtime_tools = AsyncMock()
        mock.return_value = client
        yield client


class TestListTools:
    """Test listing available tools."""

    def test_list_tools_success(self, test_client, mock_llama_client):
        """Test listing all tools."""
        tool1 = MagicMock()
        tool1.identifier = "tool1"
        tool1.description = "Test tool 1"
        tool1.parameters = {}

        mock_llama_client.tool_runtime.list_runtime_tools.return_value = [tool1]

        response = test_client.get("/api/v1/tools/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_tools_empty(self, test_client, mock_llama_client):
        """Test listing when no tools available."""
        mock_llama_client.tool_runtime.list_runtime_tools.return_value = []

        response = test_client.get("/api/v1/tools/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
