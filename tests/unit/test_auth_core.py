"""
Unit tests for core authentication utilities.

Tests local development authentication functions.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import (
    get_mock_dev_headers,
    get_or_create_dev_user,
    is_local_dev_mode,
)
from backend.app.models import RoleEnum, User


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.refresh = AsyncMock()
    return mock_session


class TestIsLocalDevMode:
    """Test local dev mode detection."""

    @patch("backend.app.core.auth.os.getenv")
    def test_is_local_dev_mode_enabled(self, mock_getenv):
        """Test detection when local dev mode is enabled."""
        mock_getenv.return_value = "true"

        result = is_local_dev_mode()

        assert result is True

    @patch("backend.app.core.auth.os.getenv")
    def test_is_local_dev_mode_disabled(self, mock_getenv):
        """Test detection when local dev mode is disabled."""
        mock_getenv.return_value = "false"

        result = is_local_dev_mode()

        assert result is False


class TestGetOrCreateDevUser:
    """Test dev user creation and retrieval."""

    async def test_get_existing_dev_user(self, mock_db_session):
        """Test retrieving existing dev user."""
        existing_user = User(
            id=uuid.uuid4(),
            username="dev-user",
            email="dev@localhost.dev",
            role=RoleEnum.admin,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db_session.execute.return_value = mock_result

        result = await get_or_create_dev_user(mock_db_session)

        assert result == existing_user
        mock_db_session.add.assert_not_called()

    async def test_create_new_dev_user(self, mock_db_session):
        """Test creating new dev user."""
        # Mock no existing user
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # Mock no existing agents
        mock_result2 = MagicMock()
        mock_result2.all.return_value = []

        mock_db_session.execute.side_effect = [mock_result1, mock_result2]

        result = await get_or_create_dev_user(mock_db_session)

        assert result.username == "dev-user"
        assert result.email == "dev@localhost.dev"
        assert result.role == RoleEnum.admin
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()


class TestGetMockDevHeaders:
    """Test mock dev headers generation."""

    def test_get_mock_dev_headers(self):
        """Test mock headers contain correct user info."""
        headers = get_mock_dev_headers()

        assert headers["X-Forwarded-User"] == "dev-user"
        assert headers["X-Forwarded-Email"] == "dev@localhost.dev"
