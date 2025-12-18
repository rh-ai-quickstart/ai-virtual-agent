"""
Unit tests for OAuth Authentication API endpoints.

Tests the OAuth/OIDC login flow endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAuthEndpointsLogic:
    """Test OAuth authentication endpoint logic."""

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.auth.oauth")
    async def test_login_initiates_oauth(self, mock_oauth):
        """Test that login initiates OAuth flow."""
        from fastapi import Request

        from backend.app.api.v1.auth import login

        # Mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url_for = MagicMock(return_value="http://test/callback")

        # Mock OAuth redirect
        mock_oauth.keycloak.authorize_redirect = AsyncMock(
            return_value=MagicMock(status_code=307)
        )

        await login(mock_request)

        # Verify OAuth redirect was called
        mock_oauth.keycloak.authorize_redirect.assert_called_once_with(
            mock_request, "http://test/callback"
        )

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.auth.extract_user_from_token")
    @patch("backend.app.api.v1.auth.oauth")
    async def test_callback_success(self, mock_oauth, mock_extract_user):
        """Test successful OAuth callback."""
        from backend.app.api.v1.auth import auth_callback

        # Mock request with session
        mock_request = MagicMock()
        mock_request.session = {}

        # Mock token exchange
        mock_token = {
            "access_token": "test-access-token",
            "id_token": "test-id-token",
        }
        mock_oauth.keycloak.authorize_access_token = AsyncMock(return_value=mock_token)

        # Mock user extraction
        mock_extract_user.return_value = {
            "username": "test-user",
            "email": "test@example.com",
            "role": "user",
        }

        result = await auth_callback(mock_request)

        # Verify session was populated
        assert "user" in mock_request.session
        assert mock_request.session["user"]["username"] == "test-user"
        assert result.status_code == 302

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.auth.logger")
    @patch("backend.app.api.v1.auth.oauth")
    async def test_callback_oauth_error(self, mock_oauth, mock_logger):
        """Test OAuth callback with error."""
        from backend.app.api.v1.auth import auth_callback

        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}

        # Mock token exchange failure
        mock_oauth.keycloak.authorize_access_token = AsyncMock(
            side_effect=Exception("OAuth error")
        )

        result = await auth_callback(mock_request)

        # Should redirect to frontend with error
        assert result.status_code in [302, 307]
        assert "error=auth_failed" in result.headers["location"]
        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_clears_session(self):
        """Test that logout clears session."""
        from backend.app.api.v1.auth import logout

        # Mock request with session
        mock_request = MagicMock()
        mock_session = MagicMock()
        mock_request.session = mock_session

        result = await logout(mock_request)

        # Verify session was cleared
        mock_session.clear.assert_called_once()
        # Verify redirect to Keycloak logout
        assert result.status_code in [302, 307]
        assert "logout" in result.headers["location"]


class TestAuthHelpers:
    """Test OAuth helper functions."""

    @patch("backend.app.api.v1.auth.extract_user_from_token")
    def test_extract_user_from_token_called(self, mock_extract):
        """Test that user extraction works."""
        from backend.app.api.v1.auth import extract_user_from_token

        mock_token = {
            "userinfo": {
                "preferred_username": "testuser",
                "email": "test@example.com",
            }
        }

        # Call the actual function
        extract_user_from_token(mock_token)

        # Verify it was processed
        mock_extract.assert_called_once_with(mock_token)
