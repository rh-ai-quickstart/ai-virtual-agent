"""
Unit tests for the runner abstraction layer (CrewAI focus).

Tests the ChatService dispatcher, BaseRunner interface, runner_type on
models/schemas, and the CrewAIRunner instantiation. Mirrors the structure
and patterns of test_runner_abstraction.py (LlamaStack).
"""

from __future__ import annotations

import json
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
from backend.app.services.runners.crewai_runner import CrewAIRunner, _StreamDeduplicator
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
    agent.name = "test-crewai-agent"
    agent.runner_type = "crewai"
    agent.model_name = "test-crewai-model"
    agent.prompt = "You are a helpful crewai assistant."
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
    """Test runner resolution in ChatService (same pattern as test_runner_abstraction)."""

    def test_get_runner_llamastack(self, chat_service):
        """runner_type 'llamastack' returns LlamaStackRunner."""
        runner = chat_service._get_runner("llamastack")
        assert isinstance(runner, LlamaStackRunner)

    def test_get_runner_crewai(self, chat_service):
        """runner_type 'crewai' returns CrewAIRunner."""
        runner = chat_service._get_runner("crewai")
        assert isinstance(runner, CrewAIRunner)

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
        runner = chat_service._get_runner("crewai")
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
        mock_agent.runner_type = "crewai"

        with patch.object(
            chat_service, "_get_runner", wraps=chat_service._get_runner
        ) as spy:
            try:
                async for _ in chat_service.stream(mock_agent, "s1", "hi"):
                    break
            except Exception:
                pass  # Runner may not be fully available in unit tests

            spy.assert_called_once_with("crewai")

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

    def test_crewai_runner_is_base_runner(self, mock_request, mock_db_session, user_id):
        """CrewAIRunner is a subclass of BaseRunner."""
        runner = CrewAIRunner(mock_request, mock_db_session, user_id)
        assert isinstance(runner, BaseRunner)


class TestCrewAIRunnerStream:
    """Test CrewAIRunner.stream() behavior (runner-specific, like LlamaStack runner tests)."""

    @pytest.mark.asyncio
    async def test_stream_yields_error_and_done_when_crewai_not_available(
        self, mock_request, mock_db_session, user_id, mock_agent
    ):
        """When CrewAI is not installed, stream yields an error event then [DONE]."""
        import backend.app.services.runners.crewai_runner as crewai_runner_module

        with patch.object(crewai_runner_module, "CREWAI_AVAILABLE", False):
            runner = CrewAIRunner(mock_request, mock_db_session, user_id)
            events = []
            async for event in runner.stream(mock_agent, "sess-1", "hello"):
                events.append(event)

        assert len(events) == 2
        assert events[-1] == "data: [DONE]\n\n"
        data = events[0]
        assert data.startswith("data: ")
        payload = json.loads(data[5:].strip())
        assert payload.get("type") == "error"
        assert "CrewAI" in payload.get("message", "")
        assert payload.get("session_id") == "sess-1"

    @pytest.mark.asyncio
    async def test_stream_yields_error_and_done_for_empty_prompt(
        self, mock_request, mock_db_session, user_id, mock_agent
    ):
        """When prompt is empty, stream yields error then [DONE]."""
        import backend.app.services.runners.crewai_runner as crewai_runner_module

        with patch.object(crewai_runner_module, "CREWAI_AVAILABLE", True):
            runner = CrewAIRunner(mock_request, mock_db_session, user_id)
            events = []
            async for event in runner.stream(mock_agent, "sess-2", ""):
                events.append(event)

        assert len(events) == 2
        assert events[-1] == "data: [DONE]\n\n"
        payload = json.loads(events[0][5:].strip())
        assert payload.get("type") == "error"
        assert "No user message" in payload.get("message", "")
        assert payload.get("session_id") == "sess-2"


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


# ---------------------------------------------------------------------------
# _StreamDeduplicator thought extraction and noise filtering tests
# ---------------------------------------------------------------------------


class TestStreamDeduplicatorThoughtExtraction:
    """Test that _extract_thought captures Thought: text for live display."""

    def _make(self) -> _StreamDeduplicator:
        return _StreamDeduplicator()

    def test_extracts_standard_thought(self):
        d = self._make()
        assert d._extract_thought("Thought: I need to search for hotels") == (
            "I need to search for hotels"
        )

    def test_extracts_thought_with_heading(self):
        d = self._make()
        assert d._extract_thought("## Thought: analyzing the data") == (
            "analyzing the data"
        )

    def test_extracts_mid_line_brace_thought(self):
        d = self._make()
        result = d._extract_thought(
            '"beach" }Thought: The search results show options.'
        )
        assert result == "The search results show options."

    def test_extracts_mid_line_backtick_thought(self):
        d = self._make()
        result = d._extract_thought("```Thought: I will start searching for flights")
        assert result == "I will start searching for flights"

    def test_returns_empty_for_non_thought(self):
        d = self._make()
        assert d._extract_thought("Action: google_hotels_search") == ""

    def test_returns_empty_for_regular_text(self):
        d = self._make()
        assert d._extract_thought("Here are the top beach resorts:") == ""

    def test_sets_suppressing_on_extraction(self):
        d = self._make()
        d._extract_thought("Thought: I need to search")
        assert d._suppressing is True


class TestStreamDeduplicatorNoise:
    """Test that _is_noise suppresses non-thought ReAct artifacts."""

    def _make(self) -> _StreamDeduplicator:
        return _StreamDeduplicator()

    # -- Action/Input/Observation noise --

    def test_filters_action_line(self):
        d = self._make()
        assert d._is_noise("Action: google_hotels_search")

    def test_filters_action_input_line(self):
        d = self._make()
        assert d._is_noise('Action Input: {"destination": "Mexico"}')

    def test_filters_observation_line(self):
        d = self._make()
        assert d._is_noise("Observation: Search returned 5 results")

    # -- Mid-line non-thought markers --

    def test_filters_quote_action(self):
        d = self._make()
        assert d._is_noise('"some value"Action: google_flights_search')

    def test_filters_bracket_observation(self):
        d = self._make()
        assert d._is_noise("]Observation: got the results")

    # -- Truncated markers --

    def test_filters_truncated_action(self):
        d = self._make()
        assert d._is_noise("tion: google_hotels_search")

    def test_filters_truncated_input(self):
        d = self._make()
        assert d._is_noise('put: {"destination": "Mexico"}')

    def test_filters_truncated_observation(self):
        d = self._make()
        assert d._is_noise("ervation: Search returned results")

    # -- Code fences --

    def test_filters_code_fence_json(self):
        d = self._make()
        assert d._is_noise("```json")

    def test_filters_code_fence_plain(self):
        d = self._make()
        assert d._is_noise("```")

    # -- JSON structural characters --

    def test_filters_standalone_braces(self):
        d = self._make()
        assert d._is_noise("{")
        assert d._is_noise("}")

    # -- JSON key-value in suppression context --

    def test_filters_json_kv_during_suppression(self):
        d = self._make()
        d._extract_thought("Thought: I need to search")  # enters suppression
        assert d._is_noise('  "destination": "Mexico",')

    def test_filters_json_object_start_during_suppression(self):
        d = self._make()
        d._is_noise("Action: search_tool")  # enters suppression
        assert d._is_noise('{"origin": "JFK",')

    def test_passes_json_kv_outside_suppression(self):
        d = self._make()
        assert not d._is_noise('  "destination": "Mexico",')

    # -- Suppression state transitions --

    def test_suppression_cleared_by_content(self):
        d = self._make()
        d._extract_thought("Thought: I should search")
        assert d._suppressing is True
        d._is_noise("- **Hotel Cancun**, $200/night")
        assert d._suppressing is False

    def test_suppression_not_cleared_by_blank_line(self):
        d = self._make()
        d._extract_thought("Thought: searching")
        assert d._suppressing is True
        d._is_noise("")
        assert d._suppressing is True

    def test_blank_line_is_noise_during_suppression(self):
        d = self._make()
        d._extract_thought("Thought: searching")
        assert d._is_noise("") is True
        assert d._is_noise("   ") is True

    def test_blank_line_passes_outside_suppression(self):
        d = self._make()
        assert d._is_noise("") is False
        assert d._is_noise("   ") is False

    # -- Legitimate content passes through --

    def test_passes_markdown_heading(self):
        d = self._make()
        assert not d._is_noise("### Flight Options from New York to Mexico")

    def test_passes_bullet_point(self):
        d = self._make()
        assert not d._is_noise("- **All Ritmo Cancun Resort**, Cancún, Mexico, $336")

    def test_passes_url(self):
        d = self._make()
        assert not d._is_noise("https://www.beach.com/best-beaches-mexico/")

    def test_passes_regular_text(self):
        d = self._make()
        assert not d._is_noise("April is a great time to visit with warm weather.")

    def test_passes_itinerary(self):
        d = self._make()
        assert not d._is_noise("Day 1 (2026-04-01): Arrival in Cancún")


class TestStreamDeduplicatorFilterChunk:
    """Test filter_chunk returns (response, thinking) tuples."""

    def test_separates_thought_from_noise_and_response(self):
        """Thought text returned as thinking; Action/JSON suppressed; content passes."""
        d = _StreamDeduplicator()
        chunk = (
            "Thought: I need to search for hotels\n"
            "Action: google_hotels_search\n"
            '{"destination": "Mexico"}\n'
            "Observation: found 5 results\n"
        )
        response, thinking = d.filter_chunk(chunk)
        assert "I need to search for hotels" in thinking
        assert "Action" not in response
        assert "destination" not in response

    def test_response_text_passes_through(self):
        d = _StreamDeduplicator()
        # First a thought block (enters suppression)
        d.filter_chunk("Thought: searching\nAction: search\n")
        # Then real content
        response, thinking = d.filter_chunk("Here are the top beach resorts:\n")
        assert "top beach resorts" in response

    def test_mid_line_thought_extracted(self):
        d = _StreamDeduplicator()
        chunk = (
            '"beach" }Thought: The results look promising.\n' "### Recommended Hotels\n"
        )
        response, thinking = d.filter_chunk(chunk)
        assert "The results look promising" in thinking
        assert "Recommended Hotels" in response

    def test_code_fenced_json_suppressed(self):
        d = _StreamDeduplicator()
        chunk = (
            "Thought: I will search for flights\n"
            "```json\n"
            '{"origin": "JFK",\n'
            '  "destination": "MEX"\n'
            "}\n"
            "```\n"
        )
        response, thinking = d.filter_chunk(chunk)
        assert "I will search for flights" in thinking
        assert "origin" not in response
        assert "JFK" not in response

    def test_flush_returns_tuple(self):
        d = _StreamDeduplicator()
        response, thinking = d.flush()
        assert response == ""
        assert thinking == ""

    def test_reset_clears_suppression(self):
        d = _StreamDeduplicator()
        d._extract_thought("Thought: searching")
        assert d._suppressing is True
        d.reset_for_new_task()
        assert d._suppressing is False

    def test_blank_line_between_thought_and_action_suppressed(self):
        """A blank line between Thought: and Action: should not leak through."""
        d = _StreamDeduplicator()
        chunk = (
            "Thought: I need to search\n"
            "\n"
            "Action:\n"
            "```json\n"
            "{\n"
            '  "query": "top beaches"\n'
            "}\n"
            "```\n"
        )
        response, thinking = d.filter_chunk(chunk)
        assert "I need to search" in thinking
        assert response.strip() == ""


# ---------------------------------------------------------------------------
# _clean_react_output tests
# ---------------------------------------------------------------------------


class TestCleanReactOutput:
    """Test _clean_react_output strips ReAct noise and JSON fragments."""

    def test_returns_empty_for_all_noise(self):
        raw = (
            "Thought: I need to search\n\n"
            "Action:\n"
            "```json\n"
            "{\n"
            '  "query": "top beaches in Mexico",\n'
            '  "max_results": 10\n'
            "}\n"
            "```"
        )
        assert CrewAIRunner._clean_react_output(raw) == ""

    def test_preserves_clean_content(self):
        raw = (
            "### Beach Destinations in Mexico\n"
            "1. Cancún - Beautiful beaches\n"
            "2. Playa del Carmen - Great nightlife\n"
        )
        result = CrewAIRunner._clean_react_output(raw)
        assert "Cancún" in result
        assert "Playa del Carmen" in result

    def test_strips_react_keeps_answer(self):
        raw = (
            "Thought: I have all the info.\n"
            "Final Answer:\n"
            "Here are 3 great options for your trip.\n"
        )
        result = CrewAIRunner._clean_react_output(raw)
        assert "3 great options" in result
        assert "Thought" not in result

    def test_strips_json_after_action(self):
        raw = (
            "Action: tavily_search\n"
            '  "query": "best beaches",\n'
            '  "max_results": 5\n'
        )
        assert CrewAIRunner._clean_react_output(raw) == ""


# ---------------------------------------------------------------------------
# _extract_task_output_text tests
# ---------------------------------------------------------------------------


class TestExtractTaskOutputText:
    """Test _extract_task_output_text extracts clean text from TaskOutput."""

    def test_extracts_clean_raw(self):
        output = MagicMock()
        output.raw = "### Hotels in Cancún\n1. Hotel A - $200/night"
        result = CrewAIRunner._extract_task_output_text(output)
        assert "Hotel A" in result

    def test_returns_empty_for_react_noise(self):
        output = MagicMock()
        output.raw = (
            "Thought: I need to search\n" "Action: search\n" '{"query": "hotels"}\n'
        )
        output.output = None
        output.result = None
        output.summary = None
        output.text = None
        result = CrewAIRunner._extract_task_output_text(output)
        assert result == ""

    def test_falls_back_to_output_attr(self):
        output = MagicMock()
        output.raw = ""
        output.output = "Flight options from JFK to CUN"
        result = CrewAIRunner._extract_task_output_text(output)
        assert "Flight options" in result

    def test_returns_empty_for_no_content(self):
        output = MagicMock()
        output.raw = ""
        output.output = ""
        output.result = ""
        output.summary = ""
        output.text = ""
        result = CrewAIRunner._extract_task_output_text(output)
        assert result == ""


# ---------------------------------------------------------------------------
# _drain_task_events tests
# ---------------------------------------------------------------------------


class TestDrainTaskEvents:
    """Test _drain_task_events emits task content and returns has_content flag."""

    def _make_runner(self, mock_request, mock_db_session, user_id):
        return CrewAIRunner(mock_request, mock_db_session, user_id)

    def _make_task_output(self, name, raw_text):
        output = MagicMock()
        output.name = name
        output.raw = raw_text
        return output

    def test_returns_tuple(self, mock_request, mock_db_session, user_id):
        from collections import deque

        runner = self._make_runner(mock_request, mock_db_session, user_id)
        result = runner._drain_task_events(deque(), ["task1"], set(), set(), "sid")
        assert isinstance(result, tuple)
        assert len(result) == 2
        events, has_content = result
        assert events == []
        assert has_content is False

    def test_emits_task_content(self, mock_request, mock_db_session, user_id):
        from collections import deque

        runner = self._make_runner(mock_request, mock_db_session, user_id)
        output = self._make_task_output(
            "research_task", "### Hotels\n1. Hotel A - $200/night"
        )
        queue = deque([output])
        started = set()
        completed = set()
        events, has_content = runner._drain_task_events(
            queue, ["research_task"], started, completed, "sid"
        )
        assert has_content is True
        response_events = [e for e in events if '"type": "response"' in e]
        assert len(response_events) >= 1
        assert "Hotel A" in response_events[0]

    def test_no_content_for_noise_output(self, mock_request, mock_db_session, user_id):
        from collections import deque

        runner = self._make_runner(mock_request, mock_db_session, user_id)
        output = self._make_task_output(
            "task1",
            "Thought: searching\nAction: search\n" '{"query": "hotels"}\n',
        )
        queue = deque([output])
        events, has_content = runner._drain_task_events(
            queue, ["task1"], set(), set(), "sid"
        )
        assert has_content is False

    def test_skips_reemit_for_streamed_tasks(
        self, mock_request, mock_db_session, user_id
    ):
        from collections import deque

        runner = self._make_runner(mock_request, mock_db_session, user_id)
        output = self._make_task_output(
            "research_task", "### Hotels\n1. Hotel A - $200/night"
        )
        queue = deque([output])
        started = {"research_task"}
        completed = set()
        streamed = {"research_task"}
        events, has_content = runner._drain_task_events(
            queue,
            ["research_task"],
            started,
            completed,
            "sid",
            streamed_tasks=streamed,
        )
        assert has_content is False
        response_events = [e for e in events if '"type": "response"' in e]
        assert len(response_events) == 1
        payload = json.loads(response_events[0][5:].strip())
        assert payload["delta"] == ""
        assert payload["status"] == "completed"

    def test_skips_internal_tasks(self, mock_request, mock_db_session, user_id):
        from collections import deque

        runner = self._make_runner(mock_request, mock_db_session, user_id)
        output = self._make_task_output("internal_task", "Some internal output")
        queue = deque([output])
        events, has_content = runner._drain_task_events(
            queue, ["visible_task"], set(), set(), "sid"
        )
        assert has_content is False
