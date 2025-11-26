"""
Unit tests for Guardrails API endpoints.

Tests guardrail CRUD operations via FastAPI endpoints.
"""

from __future__ import annotations

import uuid
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
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


@pytest.fixture
def sample_guardrail():
    """Create sample guardrail."""
    from datetime import datetime, timezone

    guardrail = MagicMock()
    guardrail.id = uuid.uuid4()
    guardrail.name = "Test Guardrail"
    guardrail.rules = {"threshold": 0.5}
    guardrail.created_by = uuid.uuid4()
    guardrail.created_at = datetime.now(timezone.utc)
    guardrail.updated_at = datetime.now(timezone.utc)
    return guardrail


class TestListGuardrails:
    """Test listing guardrails."""

    @patch("backend.app.api.v1.guardrails.guardrail")
    def test_list_guardrails_success(
        self, mock_crud, test_client, mock_db_session, sample_guardrail
    ):
        """Test listing all guardrails."""
        from backend.app.api.v1.guardrails import get_db

        mock_crud.get_multi = AsyncMock(return_value=[sample_guardrail])

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get("/api/v1/guardrails/")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestGetGuardrail:
    """Test retrieving single guardrail."""

    @patch("backend.app.api.v1.guardrails.guardrail")
    def test_get_guardrail_success(
        self, mock_crud, test_client, mock_db_session, sample_guardrail
    ):
        """Test getting guardrail by ID."""
        from backend.app.api.v1.guardrails import get_db

        mock_crud.get = AsyncMock(return_value=sample_guardrail)

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get(f"/api/v1/guardrails/{sample_guardrail.id}")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK

    @patch("backend.app.api.v1.guardrails.guardrail")
    def test_get_guardrail_not_found(self, mock_crud, test_client, mock_db_session):
        """Test getting non-existent guardrail."""
        from backend.app.api.v1.guardrails import get_db

        mock_crud.get = AsyncMock(return_value=None)

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get(f"/api/v1/guardrails/{uuid.uuid4()}")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateGuardrail:
    """Test creating guardrails."""

    @patch("backend.app.api.v1.guardrails.guardrail")
    def test_create_guardrail_success(
        self, mock_crud, test_client, mock_db_session, sample_guardrail
    ):
        """Test successful guardrail creation."""
        from backend.app.api.v1.guardrails import get_db

        mock_crud.create = AsyncMock(return_value=sample_guardrail)

        guardrail_data = {
            "name": "New Guardrail",
            "rules": {"threshold": 0.7},
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/guardrails/", json=guardrail_data)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_201_CREATED


class TestUpdateGuardrail:
    """Test updating guardrails."""

    @patch("backend.app.api.v1.guardrails.guardrail")
    def test_update_guardrail_success(
        self, mock_crud, test_client, mock_db_session, sample_guardrail
    ):
        """Test successful guardrail update."""
        from backend.app.api.v1.guardrails import get_db

        mock_crud.get = AsyncMock(return_value=sample_guardrail)
        mock_crud.update = AsyncMock(return_value=sample_guardrail)

        update_data = {"name": "Updated Guardrail", "rules": {"threshold": 0.8}}

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.put(
            f"/api/v1/guardrails/{sample_guardrail.id}", json=update_data
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK


class TestDeleteGuardrail:
    """Test deleting guardrails."""

    @patch("backend.app.api.v1.guardrails.guardrail")
    def test_delete_guardrail_success(
        self, mock_crud, test_client, mock_db_session, sample_guardrail
    ):
        """Test successful guardrail deletion."""
        from backend.app.api.v1.guardrails import get_db

        mock_crud.get = AsyncMock(return_value=sample_guardrail)
        mock_crud.remove = AsyncMock()

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.delete(f"/api/v1/guardrails/{sample_guardrail.id}")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_204_NO_CONTENT
