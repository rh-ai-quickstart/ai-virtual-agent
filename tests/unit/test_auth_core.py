"""
Unit tests for OAuth authentication utilities.

Tests OAuth token extraction and session management.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.app.core.oauth import extract_user_from_token, get_session_from_request


class TestExtractUserFromToken:
    """Test user extraction from OAuth tokens."""

    def test_extract_admin_role(self):
        """Test extraction of admin role from token."""
        token_data = {
            "id_token": (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AZXhhbXBsZS5jb20iLC"
                "JyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiYWRtaW4iLCJkZXZvcHMiLCJ1c2VyIl19fQ."
                "dummysignature"
            ),
            "access_token": "dummy_access_token",
        }

        result = extract_user_from_token(token_data)

        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"
        assert result["role"] == "admin"
        assert result["access_token"] == "dummy_access_token"

    def test_extract_devops_role(self):
        """Test extraction of devops role from token."""
        token_data = {
            "id_token": (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiJkZXZvcHMiLCJlbWFpbCI6ImRldm9wc0BleGFtcGxlLmNvbSI"
                "sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZXZvcHMiLCJ1c2VyIl19fQ."
                "dummysignature"
            ),
            "access_token": "dummy_access_token",
        }

        result = extract_user_from_token(token_data)

        assert result["username"] == "devops"
        assert result["role"] == "devops"

    def test_extract_user_role(self):
        """Test extraction of user role from token (default)."""
        token_data = {
            "id_token": (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiJ1c2VyIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwi"
                "cmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInVzZXIiXX19."
                "dummysignature"
            ),
            "access_token": "dummy_access_token",
        }

        result = extract_user_from_token(token_data)

        assert result["username"] == "user"
        assert result["role"] == "user"

    def test_no_id_token(self):
        """Test error when id_token is missing."""
        token_data = {"access_token": "dummy_access_token"}

        with pytest.raises(ValueError, match="No id_token in token response"):
            extract_user_from_token(token_data)


class TestGetSessionFromRequest:
    """Test session extraction from request."""

    def test_get_session_with_user(self):
        """Test extracting session when user data exists."""
        mock_request = MagicMock()
        mock_request.session = {
            "user": {
                "username": "testuser",
                "email": "test@example.com",
                "role": "user",
            }
        }

        result = get_session_from_request(mock_request)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"

    def test_get_session_without_user(self):
        """Test extracting session when no user data exists."""
        mock_request = MagicMock()
        mock_request.session = {}

        result = get_session_from_request(mock_request)

        assert result is None
