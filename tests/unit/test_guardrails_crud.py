"""
Unit tests for Guardrails CRUD operations.

Tests database operations for guardrail management.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crud.guardrails import guardrail
from backend.app.models import Guardrail
from backend.app.schemas import GuardrailCreate


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def sample_guardrail():
    """Create a sample guardrail."""
    return Guardrail(
        id=uuid.uuid4(),
        name="Test Guardrail",
        rules={"threshold": 0.5},
    )


class TestGetGuardrail:
    """Test get single guardrail."""

    async def test_get_guardrail_success(self, mock_db_session, sample_guardrail):
        """Test retrieving a single guardrail."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guardrail
        mock_db_session.execute.return_value = mock_result

        result = await guardrail.get(mock_db_session, id=sample_guardrail.id)

        assert result == sample_guardrail

    async def test_get_guardrail_not_found(self, mock_db_session):
        """Test retrieving non-existent guardrail returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await guardrail.get(mock_db_session, id=uuid.uuid4())

        assert result is None


class TestCreateGuardrail:
    """Test guardrail creation."""

    async def test_create_guardrail_success(self, mock_db_session):
        """Test creating a new guardrail."""
        guardrail_data = GuardrailCreate(name="New Guardrail", rules={"threshold": 0.7})

        result = await guardrail.create(mock_db_session, obj_in=guardrail_data)

        assert result.name == "New Guardrail"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    async def test_create_guardrail_rollback_on_error(self, mock_db_session):
        """Test rollback on creation error."""
        mock_db_session.commit.side_effect = Exception("DB error")

        guardrail_data = GuardrailCreate(name="Error Guardrail", rules={})

        with pytest.raises(Exception):
            await guardrail.create(mock_db_session, obj_in=guardrail_data)

        mock_db_session.rollback.assert_called_once()


class TestUpdateGuardrail:
    """Test guardrail update."""

    async def test_update_guardrail_success(self, mock_db_session, sample_guardrail):
        """Test updating a guardrail."""
        update_data = GuardrailCreate(name="Updated Name", rules={"threshold": 0.9})

        result = await guardrail.update(
            mock_db_session, db_obj=sample_guardrail, obj_in=update_data
        )

        assert result.name == "Updated Name"
        mock_db_session.commit.assert_called_once()


class TestDeleteGuardrail:
    """Test guardrail deletion."""

    async def test_delete_guardrail_success(self, mock_db_session, sample_guardrail):
        """Test deleting a guardrail."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_guardrail
        mock_db_session.execute.return_value = mock_result

        result = await guardrail.remove(mock_db_session, id=sample_guardrail.id)

        assert result == sample_guardrail
        mock_db_session.delete.assert_called_once_with(sample_guardrail)
        mock_db_session.commit.assert_called_once()
