"""
Unit tests for the declarative graph engine.

Tests cover:
- Environment variable expansion
- Template rendering with _DotDict
- Path resolution (_get_path)
- List coercion (_coerce_list)
- Argument normalisation and sanitisation
- SSE event formatting
- LLM node execution
- MCP tool node execution (mocked)
- MCP tool map node execution (mocked)
- GraphEngine graph building and streaming
- Runner dispatch (graph_config vs ReAct)
"""

from __future__ import annotations

import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.runners.graph_engine import (
    _coerce_list,
    _DotDict,
    _expand_env,
    _get_path,
    _normalize_arg,
    _render_template,
    _sanitize_args,
    _sse,
    _summarize_output,
)

# ---------------------------------------------------------------------------
# Environment variable expansion
# ---------------------------------------------------------------------------


class TestExpandEnv:
    """Test ${VAR:default} expansion."""

    def test_simple_default(self):
        result = _expand_env("${MISSING_VAR:http://localhost:8000}")
        assert result == "http://localhost:8000"

    def test_env_var_present(self):
        with patch.dict(os.environ, {"TEST_URL": "http://custom:9000"}):
            result = _expand_env("${TEST_URL:http://default}")
            assert result == "http://custom:9000"

    def test_nested_dict(self):
        data = {"url": "${MISSING:http://fallback}", "port": 8080}
        result = _expand_env(data)
        assert result["url"] == "http://fallback"
        assert result["port"] == 8080

    def test_nested_list(self):
        data = ["${MISSING:val1}", "literal"]
        result = _expand_env(data)
        assert result == ["val1", "literal"]

    def test_no_pattern(self):
        assert _expand_env("no pattern here") == "no pattern here"
        assert _expand_env(42) == 42


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    """Test {inputs.x} / {outputs.y} rendering."""

    def test_basic_render(self):
        ctx = {"inputs": _DotDict({"city": "Tokyo"})}
        assert _render_template("{inputs.city}", ctx) == "Tokyo"

    def test_missing_key_returns_empty(self):
        ctx = {"inputs": _DotDict({})}
        result = _render_template("{inputs.missing}", ctx)
        assert result == ""

    def test_dict_render(self):
        ctx = {"inputs": _DotDict({"dest": "Paris"})}
        result = _render_template({"destination": "{inputs.dest}", "count": 5}, ctx)
        assert result["destination"] == "Paris"
        assert result["count"] == 5

    def test_list_render(self):
        ctx = {"inputs": _DotDict({"a": "X"})}
        result = _render_template(["{inputs.a}", "literal"], ctx)
        assert result == ["X", "literal"]

    def test_keyerror_returns_original(self):
        result = _render_template("{undefined_key}", {})
        assert result == "{undefined_key}"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


class TestGetPath:
    """Test dot-path resolution."""

    def test_simple_path(self):
        data = {"outputs": {"task1": "result"}}
        assert _get_path(data, "outputs.task1") == "result"

    def test_nested_path(self):
        data = {"a": {"b": {"c": "deep"}}}
        assert _get_path(data, "a.b.c") == "deep"

    def test_missing_path(self):
        assert _get_path({"a": 1}, "b.c") == ""

    def test_empty_path(self):
        assert _get_path({"a": 1}, "") == ""


# ---------------------------------------------------------------------------
# List coercion
# ---------------------------------------------------------------------------


class TestCoerceList:
    """Test _coerce_list for various input formats."""

    def test_list_passthrough(self):
        assert _coerce_list(["a", "b"]) == ["a", "b"]

    def test_json_string(self):
        assert _coerce_list('["Tokyo", "Kyoto"]') == ["Tokyo", "Kyoto"]

    def test_csv_string(self):
        assert _coerce_list("a, b, c") == ["a", "b", "c"]

    def test_newline_string(self):
        assert _coerce_list("- item1\n- item2") == ["item1", "item2"]

    def test_none(self):
        assert _coerce_list(None) == []

    def test_empty_string(self):
        assert _coerce_list("") == []

    def test_scalar(self):
        assert _coerce_list(42) == ["42"]


# ---------------------------------------------------------------------------
# Argument normalisation
# ---------------------------------------------------------------------------


class TestArgNormalisation:
    """Test _normalize_arg and _sanitize_args."""

    def test_bool_string(self):
        assert _normalize_arg("true") is True
        assert _normalize_arg("false") is False

    def test_int_string(self):
        assert _normalize_arg("42") == 42

    def test_float_string(self):
        assert _normalize_arg("3.14") == 3.14

    def test_regular_string(self):
        assert _normalize_arg("hello") == "hello"

    def test_sanitize_drops_empty(self):
        result = _sanitize_args({"a": "val", "b": "", "c": None})
        assert result == {"a": "val"}


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


class TestSSEHelpers:
    """Test SSE formatting and summarisation."""

    def test_sse_format(self):
        event = _sse("node_started", {"node": "task1"}, "sess-1")
        assert event.startswith("data: ")
        assert event.endswith("\n\n")
        parsed = json.loads(event[len("data: ") : -2])
        assert parsed["type"] == "node_started"
        assert parsed["session_id"] == "sess-1"
        assert parsed["node"] == "task1"

    def test_summarize_output(self):
        assert _summarize_output("First line\nSecond") == "First line"
        assert _summarize_output("") == "No output"
        assert _summarize_output("\n") == "Output generated"


# ---------------------------------------------------------------------------
# LLM node execution
# ---------------------------------------------------------------------------


class TestLLMNode:
    """Test _run_llm_node with mocked LLM."""

    @pytest.mark.asyncio
    async def test_llm_node_success(self):
        from backend.app.services.runners.graph_engine import _run_llm_node

        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Five places in Tokyo"
        mock_llm.ainvoke.return_value = mock_response

        step = {"id": "test", "type": "llm", "prompt": "List places in {inputs.city}"}
        result = await _run_llm_node(mock_llm, step, {"city": "Tokyo"}, {})
        assert result == "Five places in Tokyo"
        mock_llm.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_node_error(self):
        from backend.app.services.runners.graph_engine import _run_llm_node

        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM timeout")

        step = {"id": "test", "type": "llm", "prompt": "Hello"}
        result = await _run_llm_node(mock_llm, step, {}, {})
        assert "LLM error" in result


# ---------------------------------------------------------------------------
# MCP tool node execution (mocked HTTP)
# ---------------------------------------------------------------------------


class TestMCPToolNode:
    """Test _run_mcp_tool_node with mocked httpx."""

    @pytest.mark.asyncio
    async def test_mcp_tool_missing_tool_name(self):
        from backend.app.services.runners.graph_engine import _run_mcp_tool_node

        step = {
            "id": "test",
            "type": "mcp_tool",
            "server": "my_server",
            "tool": "",
        }
        servers = {"my_server": {"url": "http://localhost:7001/mcp"}}
        result = await _run_mcp_tool_node(step, {}, {}, servers, "streamable-http")
        assert "Missing tool name" in result

    @pytest.mark.asyncio
    async def test_mcp_tool_unsupported_transport(self):
        from backend.app.services.runners.graph_engine import _run_mcp_tool_node

        step = {
            "id": "test",
            "type": "mcp_tool",
            "server": "s",
            "tool": "my_tool",
        }
        servers = {"s": {"url": "http://x", "transport": "stdio"}}
        result = await _run_mcp_tool_node(step, {}, {}, servers, "stdio")
        assert "Unsupported" in result


# ---------------------------------------------------------------------------
# GraphEngine build and stream
# ---------------------------------------------------------------------------


class TestGraphEngine:
    """Test GraphEngine building and streaming."""

    @pytest.mark.asyncio
    async def test_llm_only_graph(self):
        """A graph with a single LLM node builds and streams correctly."""
        from backend.app.services.runners.graph_engine import GraphEngine

        config = {
            "nodes": [
                {
                    "id": "greet",
                    "type": "llm",
                    "prompt": "Say hello to {inputs.name}",
                }
            ]
        }

        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Hello, Alice!"
        mock_llm.ainvoke.return_value = mock_response

        engine = GraphEngine(config=config, llm=mock_llm)
        events = []
        async for event in engine.run_streaming({"name": "Alice"}, "session-1"):
            events.append(event)

        parsed = [
            json.loads(e[len("data: ") : -2]) for e in events if e.startswith("data: ")
        ]

        node_started = [p for p in parsed if p["type"] == "node_started"]
        assert len(node_started) == 1
        assert node_started[0]["node"] == "greet"

        node_completed = [p for p in parsed if p["type"] == "node_completed"]
        assert len(node_completed) == 1

        responses = [p for p in parsed if p["type"] == "response"]
        assert any("Hello, Alice!" in r.get("delta", "") for r in responses)

    @pytest.mark.asyncio
    async def test_multi_node_graph(self):
        """A graph with two LLM nodes runs sequentially."""
        from backend.app.services.runners.graph_engine import GraphEngine

        config = {
            "nodes": [
                {"id": "step1", "type": "llm", "prompt": "Step 1"},
                {"id": "step2", "type": "llm", "prompt": "Step 2"},
            ]
        }

        mock_llm = AsyncMock()
        call_count = 0

        async def mock_ainvoke(messages):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.content = f"Result {call_count}"
            return resp

        mock_llm.ainvoke = mock_ainvoke

        engine = GraphEngine(config=config, llm=mock_llm)
        events = []
        async for event in engine.run_streaming({}, "sess"):
            events.append(event)

        parsed = [
            json.loads(e[len("data: ") : -2]) for e in events if e.startswith("data: ")
        ]

        nodes_started = [p["node"] for p in parsed if p["type"] == "node_started"]
        assert nodes_started == ["step1", "step2"]

    def test_empty_nodes_raises(self):
        """GraphEngine raises on empty node list."""
        from backend.app.services.runners.graph_engine import GraphEngine

        with pytest.raises(ValueError, match="non-empty"):
            GraphEngine(config={"nodes": []}, llm=MagicMock())


# ---------------------------------------------------------------------------
# Runner dispatch (graph_config vs ReAct)
# ---------------------------------------------------------------------------


class TestRunnerDispatch:
    """Test that LangGraphRunner dispatches correctly based on graph_config."""

    @pytest.fixture
    def runner(self):
        from backend.app.services.runners.langgraph_runner import (
            LangGraphRunner,
        )

        return LangGraphRunner(
            MagicMock(spec=Request),
            AsyncMock(spec=AsyncSession),
            uuid.uuid4(),
        )

    @pytest.mark.asyncio
    async def test_dispatches_to_graph_engine_when_config_present(self, runner):
        """Agent with graph_config runs declarative graph, not ReAct."""
        agent = MagicMock()
        agent.id = uuid.uuid4()
        agent.graph_config = {
            "nodes": [
                {"id": "greet", "type": "llm", "prompt": "Hello {inputs.message}"}
            ]
        }
        agent.model_name = "test-model"
        agent.temperature = None
        agent.tools = []

        mock_llm = MagicMock()

        with patch(
            "backend.app.services.runners.langgraph_runner._check_langgraph",
            return_value=True,
        ), patch.object(runner, "_create_llm", return_value=mock_llm), patch(
            "backend.app.services.runners.graph_engine.GraphEngine"
        ) as MockEngine, patch.object(
            runner, "_update_session_title", new_callable=AsyncMock
        ):
            mock_engine_instance = MagicMock()

            async def mock_stream(inputs, session_id):
                yield 'data: {"type": "response", "session_id": "s1", "delta": "Hi"}\n\n'

            mock_engine_instance.run_streaming = mock_stream
            MockEngine.return_value = mock_engine_instance

            events = []
            async for event in runner.stream(agent, "s1", "Hello"):
                events.append(event)

            MockEngine.assert_called_once()
            assert any("response" in e for e in events)
            assert events[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_dispatches_to_react_when_no_config(self, runner):
        """Agent without graph_config uses ReAct (create_react_agent)."""
        agent = MagicMock()
        agent.id = uuid.uuid4()
        agent.graph_config = None
        agent.model_name = "test-model"
        agent.prompt = "Be helpful."
        agent.temperature = None
        agent.tools = []
        agent.max_infer_iters = 5

        ai_chunk = MagicMock()
        ai_chunk.content = "Hi!"
        ai_chunk.__class__.__name__ = "AIMessageChunk"

        ai_msg = MagicMock()
        ai_msg.model_dump.return_value = {"type": "ai", "content": "Hi!"}

        async def mock_astream(input_dict, config, stream_mode):
            yield ("messages", (ai_chunk, {"langgraph_node": "agent"}))
            yield ("updates", {"agent": {"messages": [ai_msg]}})
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
            runner, "_update_session_title", new_callable=AsyncMock
        ):
            events = []
            async for event in runner.stream(agent, "s1", "Hello"):
                events.append(event)

            response_events = [e for e in events if '"type": "response"' in e]
            assert len(response_events) >= 1
            assert events[-1] == "data: [DONE]\n\n"
