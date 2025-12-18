"""
Unit tests for Authentication Validation API endpoints.

Tests OAuth session-based authentication validation.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import RoleEnum, User


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
def sample_user():
    """Create sample user."""
    return User(
        id=uuid.uuid4(),
        username="test-user",
        email="test@example.com",
        role=RoleEnum.user,
    )


class TestValidateEndpoint:
    """Test main validate endpoint with OAuth sessions."""

    @patch("backend.app.api.v1.validate.get_or_create_user_from_oauth")
    @patch("backend.app.api.v1.validate.get_session_from_request")
    def test_validate_authenticated_user(
        self, mock_get_session, mock_get_user, test_client, mock_db_session, sample_user
    ):
        """Test validation with authenticated user session."""
        from backend.app.api.v1.validate import get_db

        mock_get_session.return_value = {
            "username": "test-user",
            "email": "test@example.com",
            "roles": ["user"],
        }
        mock_get_user.return_value = sample_user

        auth_request = {
            "api_key": "test-key",
            "request": {
                "path": "/",
                "headers": {},
                "params": {},
            },
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/validate/", json=auth_request)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["principal"] == "test-user"
        assert data["message"] == "Authentication successful"
        assert data["attributes"]["roles"] == ["user"]

    @patch("backend.app.api.v1.validate.get_or_create_user_from_oauth")
    @patch("backend.app.api.v1.validate.get_session_from_request")
    def test_validate_admin_user(
        self, mock_get_session, mock_get_user, test_client, mock_db_session
    ):
        """Test validation with admin user session."""
        from backend.app.api.v1.validate import get_db

        admin_user = User(
            id=uuid.uuid4(),
            username="admin",
            email="admin@example.com",
            role=RoleEnum.admin,
        )
        mock_get_session.return_value = {
            "username": "admin",
            "email": "admin@example.com",
            "roles": ["admin"],
        }
        mock_get_user.return_value = admin_user

        auth_request = {
            "api_key": "test-key",
            "request": {
                "path": "/",
                "headers": {},
                "params": {},
            },
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/validate/", json=auth_request)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["principal"] == "admin"
        assert data["attributes"]["roles"] == ["admin"]

    @patch("backend.app.api.v1.validate.get_session_from_request")
    def test_validate_no_session(self, mock_get_session, test_client, mock_db_session):
        """Test validation when user has no session."""
        from backend.app.api.v1.validate import get_db

        mock_get_session.return_value = None  # No session

        auth_request = {
            "api_key": "test-key",
            "request": {
                "path": "/",
                "headers": {},
                "params": {},
            },
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/validate/", json=auth_request)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("backend.app.api.v1.validate.get_or_create_user_from_oauth")
    @patch("backend.app.api.v1.validate.get_session_from_request")
    def test_validate_without_trailing_slash(
        self, mock_get_session, mock_get_user, test_client, mock_db_session, sample_user
    ):
        """Test validation endpoint without trailing slash."""
        from backend.app.api.v1.validate import get_db

        mock_get_session.return_value = {
            "username": "test-user",
            "email": "test@example.com",
            "roles": ["user"],
        }
        mock_get_user.return_value = sample_user

        auth_request = {
            "api_key": "test-key",
            "request": {
                "path": "/",
                "headers": {},
                "params": {},
            },
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/validate", json=auth_request)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["principal"] == "test-user"


class TestGetUserFromSession:
    """Test get_user_from_session helper function."""

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.validate.get_or_create_user_from_oauth")
    @patch("backend.app.api.v1.validate.get_session_from_request")
    async def test_get_user_from_session_success(
        self, mock_get_session, mock_get_user, mock_db_session, sample_user
    ):
        """Test successful user retrieval from session."""
        from backend.app.api.v1.validate import get_user_from_session

        mock_request = MagicMock()
        mock_get_session.return_value = {
            "username": "test-user",
            "email": "test@example.com",
            "roles": ["user"],
        }
        mock_get_user.return_value = sample_user

        user = await get_user_from_session(mock_request, mock_db_session)

        assert user == sample_user
        mock_get_session.assert_called_once_with(mock_request)
        mock_get_user.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.validate.get_session_from_request")
    async def test_get_user_from_session_no_session(
        self, mock_get_session, mock_db_session
    ):
        """Test error when no session exists."""
        from backend.app.api.v1.validate import get_user_from_session

        mock_request = MagicMock()
        mock_get_session.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_session(mock_request, mock_db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Not authenticated"
