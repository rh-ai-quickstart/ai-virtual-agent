"""
Unit tests for the LangGraph runner.

Tests cover:
- ChatService routing to LangGraphRunner
- LangGraphRunner instantiation and BaseRunner compliance
- Input message building from various prompt formats
- SSE event formatting
- Message-to-dict normalisation
- Streaming with mocked LangGraph agent (messages + updates modes)
- MCP tool resolution (success and failure paths)
- Graceful handling when langgraph is not installed
- Session title update
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.agent import VirtualAgent
from backend.app.services.chat import ChatService
from backend.app.services.runners.base import BaseRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_request():
    return MagicMock(spec=Request)


@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def chat_service(mock_request, mock_db_session, user_id):
    return ChatService(mock_request, mock_db_session, user_id)


@pytest.fixture
def mock_agent():
    """Create a mock VirtualAgent configured for LangGraph."""
    agent = MagicMock(spec=VirtualAgent)
    agent.id = uuid.uuid4()
    agent.name = "test-langgraph-agent"
    agent.runner_type = "langgraph"
    agent.model_name = "test-model"
    agent.prompt = "You are a helpful test assistant."
    agent.tools = []
    agent.vector_store_ids = []
    agent.knowledge_base_ids = []
    agent.input_shields = []
    agent.output_shields = []
    agent.temperature = None
    agent.max_infer_iters = 10
    return agent


@pytest.fixture
def langgraph_runner(mock_request, mock_db_session, user_id):
    """Create a LangGraphRunner with mock dependencies."""
    from backend.app.services.runners.langgraph_runner import LangGraphRunner

    return LangGraphRunner(mock_request, mock_db_session, user_id)


# ---------------------------------------------------------------------------
# ChatService routing
# ---------------------------------------------------------------------------


class TestChatServiceLangGraphRouting:
    """Test that ChatService routes to LangGraphRunner."""

    def test_get_runner_langgraph(self, chat_service):
        """runner_type 'langgraph' returns a LangGraphRunner."""
        from backend.app.services.runners.langgraph_runner import (
            LangGraphRunner,
        )

        runner = chat_service._get_runner("langgraph")
        assert isinstance(runner, LangGraphRunner)

    def test_langgraph_runner_is_base_runner(self, chat_service):
        """LangGraphRunner is a BaseRunner subclass."""
        runner = chat_service._get_runner("langgraph")
        assert isinstance(runner, BaseRunner)

    def test_runner_preserves_dependencies(
        self, chat_service, mock_request, mock_db_session, user_id
    ):
        """LangGraphRunner receives the same deps as ChatService."""
        runner = chat_service._get_runner("langgraph")
        assert runner.request is mock_request
        assert runner.db is mock_db_session
        assert runner.user_id == user_id


# ---------------------------------------------------------------------------
# Input message building
# ---------------------------------------------------------------------------


class TestBuildInputMessages:
    """Test _build_input_messages for various prompt types."""

    def test_string_prompt(self, langgraph_runner):
        msgs = langgraph_runner._build_input_messages("Hello world")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello world"

    def test_list_of_content_items(self, langgraph_runner):
        items = [
            SimpleNamespace(text="Hello", type="input_text"),
            SimpleNamespace(text=" world", type="input_text"),
        ]
        msgs = langgraph_runner._build_input_messages(items)
        assert msgs[0]["content"] == "Hello\n world"

    def test_single_content_item(self, langgraph_runner):
        item = SimpleNamespace(text="Hi there")
        msgs = langgraph_runner._build_input_messages(item)
        assert msgs[0]["content"] == "Hi there"

    def test_empty_list(self, langgraph_runner):
        msgs = langgraph_runner._build_input_messages([])
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "[]"

    def test_dict_items(self, langgraph_runner):
        items = [{"text": "Hello from dict", "type": "input_text"}]
        msgs = langgraph_runner._build_input_messages(items)
        assert "Hello from dict" in msgs[0]["content"]


# ---------------------------------------------------------------------------
# SSE event formatting
# ---------------------------------------------------------------------------


class TestSSEFormatting:
    """Test _sse helper produces valid SSE strings."""

    def test_sse_format(self, langgraph_runner):
        event = langgraph_runner._sse("response", {"delta": "hi"}, "sess-1")
        assert event.startswith("data: ")
        assert event.endswith("\n\n")
        parsed = json.loads(event[len("data: ") : -2])
        assert parsed["type"] == "response"
        assert parsed["session_id"] == "sess-1"
        assert parsed["delta"] == "hi"

    def test_sse_error_event(self, langgraph_runner):
        event = langgraph_runner._sse("error", {"message": "boom"}, "sess-2")
        parsed = json.loads(event[len("data: ") : -2])
        assert parsed["type"] == "error"
        assert parsed["message"] == "boom"


# ---------------------------------------------------------------------------
# Message-to-dict normalisation
# ---------------------------------------------------------------------------


class TestMessageToDict:
    """Test _message_to_dict for various LangChain message shapes."""

    def test_with_model_dump(self, langgraph_runner):
        msg = MagicMock()
        msg.model_dump.return_value = {"type": "ai", "content": "hello"}
        result = langgraph_runner._message_to_dict(msg)
        assert result == {"type": "ai", "content": "hello"}

    def test_with_tool_calls(self, langgraph_runner):
        msg = MagicMock(spec=[])
        msg.type = "ai"
        msg.content = ""
        msg.tool_calls = [{"id": "tc1", "name": "get_weather", "args": {"city": "SF"}}]
        del msg.model_dump
        del msg.dict
        result = langgraph_runner._message_to_dict(msg)
        assert result["tool_calls"][0]["name"] == "get_weather"

    def test_tool_message(self, langgraph_runner):
        msg = MagicMock()
        msg.model_dump.return_value = {
            "type": "tool",
            "content": "sunny",
            "tool_call_id": "tc1",
            "name": "get_weather",
        }
        result = langgraph_runner._message_to_dict(msg)
        assert result["type"] == "tool"
        assert result["tool_call_id"] == "tc1"


# ---------------------------------------------------------------------------
# Streaming (mocked LangGraph agent)
# ---------------------------------------------------------------------------


class TestLangGraphStreaming:
    """Test the stream method with a fully mocked LangGraph graph."""

    @pytest.mark.asyncio
    async def test_stream_simple_response(self, langgraph_runner, mock_agent):
        """Agent generates a simple text response (no tools)."""

        # Mock the AIMessageChunk for messages mode
        ai_chunk_1 = MagicMock()
        ai_chunk_1.content = "Hello"
        ai_chunk_1.__class__.__name__ = "AIMessageChunk"

        ai_chunk_2 = MagicMock()
        ai_chunk_2.content = " there!"
        ai_chunk_2.__class__.__name__ = "AIMessageChunk"

        # Mock the complete AIMessage for updates mode
        ai_message = MagicMock()
        ai_message.model_dump.return_value = {
            "type": "ai",
            "content": "Hello there!",
        }

        # Simulate the interleaved stream
        async def mock_astream(input_dict, config, stream_mode):
            # Token 1
            yield ("messages", (ai_chunk_1, {"langgraph_node": "agent"}))
            # Token 2
            yield ("messages", (ai_chunk_2, {"langgraph_node": "agent"}))
            # Node complete
            yield (
                "updates",
                {"agent": {"messages": [ai_message]}},
            )
            # Graph end
            yield ("updates", {"__end__": None})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream

        with patch(
            "backend.app.services.runners.langgraph_runner._check_langgraph",
            return_value=True,
        ), patch(
            "backend.app.services.runners.langgraph_runner.LangGraphRunner._create_llm"
        ), patch(
            "backend.app.services.runners.langgraph_runner._get_checkpointer"
        ), patch(
            "backend.app.services.runners.langgraph_runner.create_react_agent",
            return_value=mock_graph,
        ), patch(
            "backend.app.services.runners.langgraph_runner.AIMessageChunk",
            new=type(ai_chunk_1),
        ), patch.object(
            langgraph_runner,
            "_update_session_title",
            new_callable=AsyncMock,
        ):
            events = []
            async for event in langgraph_runner.stream(mock_agent, "session-1", "Hi"):
                events.append(event)

            # Verify we got response deltas
            response_events = [
                e
                for e in events
                if e.startswith("data: ") and '"type": "response"' in e
            ]
            assert len(response_events) >= 2  # Two text deltas + completed

            # Verify we got node events
            node_events = [
                e for e in events if "node_started" in e or "node_completed" in e
            ]
            assert len(node_events) >= 2  # started + completed for agent

            # Verify stream ends with [DONE]
            assert events[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_stream_with_tool_call(self, langgraph_runner, mock_agent):
        """Agent calls a tool and then responds."""

        # Agent decides to call tool
        ai_tool_msg = MagicMock()
        ai_tool_msg.model_dump.return_value = {
            "type": "ai",
            "content": "",
            "tool_calls": [
                {"id": "tc-1", "name": "get_weather", "args": {"city": "SF"}}
            ],
        }

        # Tool result
        tool_result = MagicMock()
        tool_result.model_dump.return_value = {
            "type": "tool",
            "content": "Sunny, 72F",
            "tool_call_id": "tc-1",
            "name": "get_weather",
        }

        # Final response
        ai_chunk = MagicMock()
        ai_chunk.content = "The weather in SF is sunny!"
        ai_chunk.__class__.__name__ = "AIMessageChunk"

        ai_final = MagicMock()
        ai_final.model_dump.return_value = {
            "type": "ai",
            "content": "The weather in SF is sunny!",
        }

        async def mock_astream(input_dict, config, stream_mode):
            # Agent calls tool
            yield ("updates", {"agent": {"messages": [ai_tool_msg]}})
            # Tool runs
            yield ("updates", {"tools": {"messages": [tool_result]}})
            # Final response (token stream)
            yield ("messages", (ai_chunk, {"langgraph_node": "agent"}))
            # Agent node done
            yield ("updates", {"agent": {"messages": [ai_final]}})
            yield ("updates", {"__end__": None})

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream

        with patch(
            "backend.app.services.runners.langgraph_runner._check_langgraph",
            return_value=True,
        ), patch(
            "backend.app.services.runners.langgraph_runner.LangGraphRunner._create_llm"
        ), patch(
            "backend.app.services.runners.langgraph_runner._get_checkpointer"
        ), patch(
            "backend.app.services.runners.langgraph_runner.create_react_agent",
            return_value=mock_graph,
        ), patch(
            "backend.app.services.runners.langgraph_runner.AIMessageChunk",
            new=type(ai_chunk),
        ), patch.object(
            langgraph_runner,
            "_update_session_title",
            new_callable=AsyncMock,
        ):
            events = []
            async for event in langgraph_runner.stream(
                mock_agent, "session-2", "Weather in SF?"
            ):
                events.append(event)

            # Parse all events
            parsed = []
            for e in events:
                if e.startswith("data: ") and e.strip() != "data: [DONE]":
                    parsed.append(json.loads(e[len("data: ") :].strip()))

            # Find tool_call events
            tool_events = [p for p in parsed if p["type"] == "tool_call"]
            assert len(tool_events) >= 2  # in_progress + completed

            in_progress = [t for t in tool_events if t["status"] == "in_progress"]
            completed = [t for t in tool_events if t["status"] == "completed"]
            assert len(in_progress) >= 1
            assert len(completed) >= 1
            assert completed[0]["output"] == "Sunny, 72F"

            assert events[-1] == "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# LangGraph not installed
# ---------------------------------------------------------------------------


class TestLangGraphNotInstalled:
    """Test graceful handling when langgraph is not installed."""

    @pytest.mark.asyncio
    async def test_stream_without_langgraph(self, langgraph_runner, mock_agent):
        """stream() emits an error and [DONE] if langgraph is missing."""
        with patch(
            "backend.app.services.runners.langgraph_runner._check_langgraph",
            return_value=False,
        ):
            events = []
            async for event in langgraph_runner.stream(mock_agent, "session-x", "Hi"):
                events.append(event)

            assert len(events) == 2
            error_event = json.loads(events[0][len("data: ") :].strip())
            assert error_event["type"] == "error"
            assert "not installed" in error_event["message"]
            assert events[-1] == "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# MCP resolution
# ---------------------------------------------------------------------------


class TestMCPResolution:
    """Test _resolve_mcp_servers for various tool configurations."""

    @pytest.mark.asyncio
    async def test_no_tools(self, langgraph_runner):
        result = await langgraph_runner._resolve_mcp_servers(None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_mcp_tools(self, langgraph_runner):
        result = await langgraph_runner._resolve_mcp_servers(
            [{"toolgroup_id": "builtin::rag"}]
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_mcp_resolution_failure_logged(self, langgraph_runner):
        """MCP resolution failure is handled gracefully."""
        with patch(
            "backend.app.api.llamastack.get_client_from_request",
            side_effect=Exception("No LlamaStack"),
        ):
            result = await langgraph_runner._resolve_mcp_servers(
                [{"toolgroup_id": "mcp::test-server"}]
            )
            assert result == {}


# ---------------------------------------------------------------------------
# LLM creation
# ---------------------------------------------------------------------------


class TestLLMCreation:
    """Test _create_llm with various configurations."""

    def test_create_llm_uses_agent_model(self, langgraph_runner, mock_agent):
        """_create_llm uses the agent's model_name."""
        with patch(
            "backend.app.services.runners.langgraph_runner.settings"
        ) as mock_settings:
            mock_settings.LANGGRAPH_LLM_API_BASE = "http://localhost:8321/v1"
            mock_settings.LANGGRAPH_LLM_API_KEY = "test-key"
            mock_settings.LANGGRAPH_DEFAULT_MODEL = None
            mock_settings.LLAMA_STACK_URL = None

            with patch(
                "backend.app.services.runners.langgraph_runner.ChatOpenAI"
            ) as MockChatOpenAI:
                langgraph_runner._create_llm(mock_agent)
                MockChatOpenAI.assert_called_once_with(
                    model="test-model",
                    base_url="http://localhost:8321/v1",
                    api_key="test-key",
                    temperature=0,
                    streaming=True,
                )

    def test_create_llm_falls_back_to_llama_stack_url(
        self, langgraph_runner, mock_agent
    ):
        """_create_llm builds base_url from LLAMA_STACK_URL when no explicit base set."""
        with patch(
            "backend.app.services.runners.langgraph_runner.settings"
        ) as mock_settings:
            mock_settings.LANGGRAPH_LLM_API_BASE = None
            mock_settings.LANGGRAPH_LLM_API_KEY = "no-key"
            mock_settings.LANGGRAPH_DEFAULT_MODEL = None
            mock_settings.LLAMA_STACK_URL = "http://llamastack:8321"

            with patch(
                "backend.app.services.runners.langgraph_runner.ChatOpenAI"
            ) as MockChatOpenAI:
                langgraph_runner._create_llm(mock_agent)
                MockChatOpenAI.assert_called_once()
                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["base_url"] == "http://llamastack:8321/v1"

    def test_create_llm_uses_override_model(self, langgraph_runner, mock_agent):
        """LANGGRAPH_DEFAULT_MODEL overrides agent.model_name."""
        with patch(
            "backend.app.services.runners.langgraph_runner.settings"
        ) as mock_settings:
            mock_settings.LANGGRAPH_LLM_API_BASE = "http://localhost/v1"
            mock_settings.LANGGRAPH_LLM_API_KEY = "key"
            mock_settings.LANGGRAPH_DEFAULT_MODEL = "override-model"
            mock_settings.LLAMA_STACK_URL = None

            with patch(
                "backend.app.services.runners.langgraph_runner.ChatOpenAI"
            ) as MockChatOpenAI:
                langgraph_runner._create_llm(mock_agent)
                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["model"] == "override-model"


# ---------------------------------------------------------------------------
# Session title update
# ---------------------------------------------------------------------------


class TestSessionTitleUpdate:
    """Test _update_session_title."""

    @pytest.mark.asyncio
    async def test_updates_title_from_text_prompt(
        self, langgraph_runner, mock_db_session
    ):
        """Session title is updated from the first user message."""
        mock_session = MagicMock()
        mock_session.title = "Chat-20250101"
        mock_session.user_id = langgraph_runner.user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db_session.execute.return_value = mock_result

        items = [SimpleNamespace(text="What is the weather in San Francisco?")]
        await langgraph_runner._update_session_title("session-1", items)

        assert mock_session.title == "What is the weather in San Francisco?"
        mock_db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_if_title_already_set(self, langgraph_runner, mock_db_session):
        """Does not overwrite a meaningful (non-'Chat…') title."""
        mock_session = MagicMock()
        mock_session.title = "Important conversation"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db_session.execute.return_value = mock_result

        await langgraph_runner._update_session_title("s1", [SimpleNamespace(text="hi")])

        mock_db_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handles_missing_session(self, langgraph_runner, mock_db_session):
        """Gracefully handles session not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Should not raise
        await langgraph_runner._update_session_title("missing", "hello")
