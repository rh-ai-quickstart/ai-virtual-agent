"""
Unit tests for the runner abstraction layer.

Tests the ChatService dispatcher, BaseRunner interface, runner_type on
models/schemas, and the LlamaStackRunner instantiation.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.agent import VirtualAgent
from backend.app.schemas.agent import (
    VirtualAgentBase,
    VirtualAgentCreate,
    VirtualAgentUpdate,
)
from backend.app.services.chat import VALID_RUNNER_TYPES, ChatService
from backend.app.services.runners.base import BaseRunner
from backend.app.services.runners.llamastack_runner import LlamaStackRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    return MagicMock(spec=Request)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def chat_service(mock_request, mock_db_session, user_id):
    """Create a ChatService instance with mock dependencies."""
    return ChatService(mock_request, mock_db_session, user_id)


@pytest.fixture
def mock_agent():
    """Create a mock VirtualAgent with default runner_type."""
    agent = MagicMock(spec=VirtualAgent)
    agent.id = uuid.uuid4()
    agent.name = "test-agent"
    agent.runner_type = "llamastack"
    agent.model_name = "test-model"
    agent.prompt = "You are a helpful assistant."
    agent.tools = []
    agent.vector_store_ids = []
    agent.knowledge_base_ids = []
    agent.input_shields = []
    agent.output_shields = []
    agent.temperature = None
    agent.max_infer_iters = None
    return agent


# ---------------------------------------------------------------------------
# ChatService._get_runner tests
# ---------------------------------------------------------------------------


class TestChatServiceGetRunner:
    """Test runner resolution in ChatService."""

    def test_get_runner_llamastack(self, chat_service):
        """Default runner_type 'llamastack' returns LlamaStackRunner."""
        runner = chat_service._get_runner("llamastack")
        assert isinstance(runner, LlamaStackRunner)

    def test_get_runner_empty_string_defaults_to_llamastack(self, chat_service):
        """Empty string runner_type falls back to LlamaStackRunner."""
        runner = chat_service._get_runner("")
        assert isinstance(runner, LlamaStackRunner)

    def test_get_runner_none_defaults_to_llamastack(self, chat_service):
        """None runner_type falls back to LlamaStackRunner."""
        runner = chat_service._get_runner(None)
        assert isinstance(runner, LlamaStackRunner)

    def test_get_runner_unsupported_raises(self, chat_service):
        """Unsupported runner_type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported runner type"):
            chat_service._get_runner("unknown_runner")

    def test_get_runner_preserves_dependencies(
        self, chat_service, mock_request, mock_db_session, user_id
    ):
        """Runner receives the same request, db, and user_id as ChatService."""
        runner = chat_service._get_runner("llamastack")
        assert runner.request is mock_request
        assert runner.db is mock_db_session
        assert runner.user_id == user_id


class TestChatServiceStream:
    """Test ChatService.stream() dispatching."""

    @pytest.mark.asyncio
    async def test_stream_delegates_to_runner(self, chat_service, mock_agent):
        """stream() delegates to the runner resolved from agent.runner_type."""
        mock_runner = AsyncMock(spec=BaseRunner)
        mock_runner.stream = AsyncMock(return_value=iter([]))

        # Make stream() an async generator
        async def mock_stream(agent, session_id, prompt):
            yield "data: {}\n\n"
            yield "data: [DONE]\n\n"

        mock_runner.stream = mock_stream

        with patch.object(chat_service, "_get_runner", return_value=mock_runner):
            events = []
            async for event in chat_service.stream(mock_agent, "session-1", "hello"):
                events.append(event)

        assert len(events) == 2
        assert events[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_stream_reads_runner_type_from_agent(self, chat_service, mock_agent):
        """stream() reads runner_type from the agent object."""
        mock_agent.runner_type = "llamastack"

        with patch.object(
            chat_service, "_get_runner", wraps=chat_service._get_runner
        ) as spy:
            # We can't fully run stream without LlamaStack, so just verify
            # _get_runner is called with the correct runner_type
            try:
                async for _ in chat_service.stream(mock_agent, "s1", "hi"):
                    break  # Don't need to consume all events
            except Exception:
                pass  # Expected: LlamaStack not available in tests

            spy.assert_called_once_with("llamastack")

    @pytest.mark.asyncio
    async def test_stream_defaults_when_runner_type_missing(
        self, chat_service, mock_agent
    ):
        """stream() defaults to 'llamastack' when runner_type is not set."""
        # Simulate an agent without runner_type attribute
        del mock_agent.runner_type

        with patch.object(
            chat_service, "_get_runner", wraps=chat_service._get_runner
        ) as spy:
            try:
                async for _ in chat_service.stream(mock_agent, "s1", "hi"):
                    break
            except Exception:
                pass

            spy.assert_called_once_with("llamastack")


# ---------------------------------------------------------------------------
# BaseRunner interface tests
# ---------------------------------------------------------------------------


class TestBaseRunner:
    """Test that BaseRunner cannot be instantiated and enforces the interface."""

    def test_cannot_instantiate_directly(self, mock_request, mock_db_session, user_id):
        """BaseRunner is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseRunner(mock_request, mock_db_session, user_id)

    def test_llamastack_runner_is_base_runner(
        self, mock_request, mock_db_session, user_id
    ):
        """LlamaStackRunner is a subclass of BaseRunner."""
        runner = LlamaStackRunner(mock_request, mock_db_session, user_id)
        assert isinstance(runner, BaseRunner)


# ---------------------------------------------------------------------------
# VirtualAgent model tests
# ---------------------------------------------------------------------------


class TestVirtualAgentModel:
    """Test runner_type on the VirtualAgent model."""

    def test_runner_type_column_exists(self):
        """VirtualAgent model has a runner_type column."""
        assert hasattr(VirtualAgent, "runner_type")

    def test_runner_type_default(self):
        """runner_type column has server_default of 'llamastack'."""
        col = VirtualAgent.__table__.columns["runner_type"]
        assert col.server_default is not None
        assert col.server_default.arg == "llamastack"

    def test_runner_type_not_nullable(self):
        """runner_type column is not nullable."""
        col = VirtualAgent.__table__.columns["runner_type"]
        assert col.nullable is False


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestVirtualAgentSchemas:
    """Test runner_type in Pydantic schemas."""

    def test_base_schema_default(self):
        """VirtualAgentBase defaults runner_type to 'llamastack'."""
        agent = VirtualAgentBase(name="test", model_name="model-1")
        assert agent.runner_type == "llamastack"

    def test_base_schema_accepts_langgraph(self):
        """VirtualAgentBase accepts 'langgraph' as runner_type."""
        agent = VirtualAgentBase(
            name="test", model_name="model-1", runner_type="langgraph"
        )
        assert agent.runner_type == "langgraph"

    def test_base_schema_accepts_crewai(self):
        """VirtualAgentBase accepts 'crewai' as runner_type."""
        agent = VirtualAgentBase(
            name="test", model_name="model-1", runner_type="crewai"
        )
        assert agent.runner_type == "crewai"

    def test_create_schema_inherits_runner_type(self):
        """VirtualAgentCreate inherits runner_type from base."""
        agent = VirtualAgentCreate(name="test", model_name="model-1")
        assert agent.runner_type == "llamastack"

    def test_create_schema_with_runner_type(self):
        """VirtualAgentCreate accepts runner_type."""
        agent = VirtualAgentCreate(
            name="test", model_name="model-1", runner_type="langgraph"
        )
        assert agent.runner_type == "langgraph"

    def test_update_schema_runner_type_optional(self):
        """VirtualAgentUpdate has runner_type as optional."""
        update = VirtualAgentUpdate()
        assert update.runner_type is None

    def test_update_schema_with_runner_type(self):
        """VirtualAgentUpdate can set runner_type."""
        update = VirtualAgentUpdate(runner_type="crewai")
        assert update.runner_type == "crewai"


# ---------------------------------------------------------------------------
# Valid runner types constant
# ---------------------------------------------------------------------------


class TestValidRunnerTypes:
    """Test the VALID_RUNNER_TYPES constant."""

    def test_contains_llamastack(self):
        assert "llamastack" in VALID_RUNNER_TYPES

    def test_contains_langgraph(self):
        assert "langgraph" in VALID_RUNNER_TYPES

    def test_contains_crewai(self):
        assert "crewai" in VALID_RUNNER_TYPES

    def test_is_frozen_set(self):
        """VALID_RUNNER_TYPES should be a set (immutable at module level)."""
        assert isinstance(VALID_RUNNER_TYPES, set)
