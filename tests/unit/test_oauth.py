"""
Unit tests for OAuth and Keycloak integration utilities.

Tests Keycloak API interaction functions with mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.core.oauth import delete_keycloak_user


class TestDeleteKeycloakUser:
    """Test Keycloak user deletion function."""

    @pytest.mark.asyncio
    @patch("backend.app.core.oauth.get_keycloak_admin_token")
    @patch("backend.app.core.oauth.httpx.AsyncClient")
    async def test_delete_user_success(self, mock_client_class, mock_get_token):
        """Test successful user deletion from Keycloak."""
        mock_get_token.return_value = "mock-admin-token"

        # Mock successful deletion response (204 No Content)
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await delete_keycloak_user("test-user-id-123")

        assert result is True
        mock_client.delete.assert_called_once()
        # Verify the URL contains the user ID
        call_args = mock_client.delete.call_args
        assert "test-user-id-123" in call_args[0][0]
        # Verify authorization header
        assert call_args[1]["headers"]["Authorization"] == "Bearer mock-admin-token"

    @pytest.mark.asyncio
    @patch("backend.app.core.oauth.get_keycloak_admin_token")
    @patch("backend.app.core.oauth.httpx.AsyncClient")
    async def test_delete_user_not_found(self, mock_client_class, mock_get_token):
        """Test deletion when user doesn't exist in Keycloak (404)."""
        mock_get_token.return_value = "mock-admin-token"

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await delete_keycloak_user("nonexistent-user-id")

        assert result is False

    @pytest.mark.asyncio
    @patch("backend.app.core.oauth.get_keycloak_admin_token")
    @patch("backend.app.core.oauth.httpx.AsyncClient")
    async def test_delete_user_forbidden(self, mock_client_class, mock_get_token):
        """Test deletion fails when service account lacks permissions (403)."""
        mock_get_token.return_value = "mock-admin-token"

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Forbidden", request=MagicMock(), response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await delete_keycloak_user("some-user-id")

    @pytest.mark.asyncio
    @patch("backend.app.core.oauth.get_keycloak_admin_token")
    @patch("backend.app.core.oauth.httpx.AsyncClient")
    async def test_delete_user_server_error(self, mock_client_class, mock_get_token):
        """Test deletion fails when Keycloak returns server error (500)."""
        mock_get_token.return_value = "mock-admin-token"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await delete_keycloak_user("some-user-id")

    @pytest.mark.asyncio
    @patch("backend.app.core.oauth.get_keycloak_admin_token")
    @patch("backend.app.core.oauth.httpx.AsyncClient")
    async def test_delete_user_network_error(self, mock_client_class, mock_get_token):
        """Test deletion fails on network errors."""
        mock_get_token.return_value = "mock-admin-token"

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.RequestError):
            await delete_keycloak_user("some-user-id")
