"""
Unit tests for template startup and population.

Tests automatic template loading and database population on startup.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.core.template_startup import ensure_templates_populated


class TestEnsureTemplatesPopulated:
    """Test template population on startup."""

    @patch("backend.app.core.template_startup.AsyncSessionLocal")
    @patch("backend.app.core.template_startup.load_all_templates_from_directory")
    async def test_populate_templates_when_empty(
        self, mock_load_templates, mock_session_local
    ):
        """Test templates are populated when database is empty."""
        # Mock empty database
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        # session.add() is synchronous, not async
        mock_session.add = MagicMock()
        mock_session_local.return_value = mock_session

        # Mock template data
        mock_load_templates.return_value = (
            {"suite1": {"name": "Test Suite", "templates": {"t1": {}}}},
            {"t1": {"name": "Test Template"}},
        )

        await ensure_templates_populated()

        # Verify session was used
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    @patch("backend.app.core.template_startup.AsyncSessionLocal")
    async def test_skip_when_templates_exist(self, mock_session_local):
        """Test skipping population when templates exist."""
        # Mock existing templates
        mock_session = AsyncMock()
        mock_result = MagicMock()
        existing_suite = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_suite]
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        # session.add() is synchronous, not async
        mock_session.add = MagicMock()
        mock_session_local.return_value = mock_session

        await ensure_templates_populated()

        # Should not add anything
        mock_session.add.assert_not_called()
