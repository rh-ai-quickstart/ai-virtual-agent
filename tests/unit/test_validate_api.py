"""
Unit tests for Authentication Validation API endpoints.

Tests SA-token HMAC validation and local dev mode auth paths.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.user import CurrentUser


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


def _auth_request(api_key="test-key"):
    return {
        "api_key": api_key,
        "request": {
            "path": "/",
            "headers": {},
            "params": {},
        },
    }


class TestValidateEndpoint:
    """Test main validate endpoint."""

    @patch("backend.app.api.v1.validate.is_local_dev_mode")
    @patch("backend.app.api.v1.validate.get_or_create_dev_user")
    def test_validate_local_dev_mode(
        self, mock_get_user, mock_is_dev, test_client, mock_db_session
    ):
        """Test validation in local dev mode returns dev user as principal."""
        from backend.app.database import get_db

        mock_is_dev.return_value = True
        mock_get_user.return_value = CurrentUser(
            keycloak_id=uuid.uuid4(),
            username="dev-user",
            email="dev@localhost.dev",
            role="admin",
            agent_ids=[],
        )

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/validate/", json=_auth_request())
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["principal"] == "dev-user"
        assert data["attributes"]["roles"] == ["admin"]
        assert data["message"] == "Authentication successful"

    @patch("backend.app.api.v1.validate.is_local_dev_mode")
    @patch("backend.app.api.v1.validate.get_sa_token")
    def test_validate_sa_token_success(
        self, mock_sa_token, mock_is_dev, test_client, mock_db_session
    ):
        """Test validation succeeds with matching SA token."""
        from backend.app.database import get_db

        mock_is_dev.return_value = False
        mock_sa_token.return_value = "test-sa-token"

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post(
            "/api/v1/validate/", json=_auth_request(api_key="test-sa-token")
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["principal"] == "admin"
        assert data["attributes"]["roles"] == ["admin"]
        assert data["message"] == "Authentication successful"

    @patch("backend.app.api.v1.validate.is_local_dev_mode")
    @patch("backend.app.api.v1.validate.get_sa_token")
    def test_validate_invalid_token(
        self, mock_sa_token, mock_is_dev, test_client, mock_db_session
    ):
        """Test validation fails with non-matching SA token."""
        from backend.app.database import get_db

        mock_is_dev.return_value = False
        mock_sa_token.return_value = "real-token"

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post(
            "/api/v1/validate/", json=_auth_request(api_key="wrong-token")
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("backend.app.api.v1.validate.is_local_dev_mode")
    @patch("backend.app.api.v1.validate.get_sa_token")
    def test_validate_no_sa_token_available(
        self, mock_sa_token, mock_is_dev, test_client, mock_db_session
    ):
        """Test validation fails when no SA token is configured."""
        from backend.app.database import get_db

        mock_is_dev.return_value = False
        mock_sa_token.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post(
            "/api/v1/validate/", json=_auth_request(api_key="any-token")
        )
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
