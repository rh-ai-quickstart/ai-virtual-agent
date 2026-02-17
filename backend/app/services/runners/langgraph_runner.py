"""
LangGraph runner implementation.

Uses LangGraph's create_react_agent for ReAct-style agent execution
with streaming support, MCP tool integration, and session persistence
via an in-memory checkpointer (thread_id = session_id).

SSE event mapping
-----------------
LangGraph stream modes -> our normalized events:

  "messages" mode  (token-level)
    AIMessageChunk.content          -> response  {delta, status}
  "updates" mode   (node-level)
    agent node with tool_calls      -> tool_call {status: in_progress}
    tools node with ToolMessage     -> tool_call {status: completed}
    any node start                  -> node_started {node}
    any node end                    -> node_completed {node}

The stream ends with ``data: [DONE]\\n\\n``.
"""

import json
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from ...config import settings
from ...models import ChatSession
from .base import BaseRunner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional LangGraph imports (module-level for patchability in tests)
# ---------------------------------------------------------------------------

try:
    from langchain_core.messages import AIMessageChunk
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.prebuilt import create_react_agent

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    AIMessageChunk = None  # type: ignore[assignment,misc]
    ChatOpenAI = None  # type: ignore[assignment,misc]
    InMemorySaver = None  # type: ignore[assignment,misc]
    create_react_agent = None  # type: ignore[assignment]
    _LANGGRAPH_AVAILABLE = False


def _check_langgraph() -> bool:
    """Return True if langgraph and its dependencies are importable."""
    return _LANGGRAPH_AVAILABLE


# ---------------------------------------------------------------------------
# Shared checkpointer (module-level singleton)
# ---------------------------------------------------------------------------
# InMemorySaver is sufficient for single-process development.
# For production / multi-worker deployments swap with PostgresSaver or
# another durable checkpointer backed by the application database.

_checkpointer = None


def _get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = InMemorySaver()
    return _checkpointer


# ---------------------------------------------------------------------------
# LangGraph Runner
# ---------------------------------------------------------------------------


class LangGraphRunner(BaseRunner):
    """
    Runner for LangGraph agents using the prebuilt ReAct agent pattern.

    Features
    --------
    * **Token-level streaming** via ``astream(stream_mode=["messages","updates"])``
    * **MCP tools** loaded at runtime through ``langchain-mcp-adapters``
    * **Session persistence** via LangGraph's checkpointer (``thread_id = session_id``)
    * **Normalized SSE events** compatible with the frontend (response, tool_call,
      node_started, node_completed, error)
    """

    # ----- LLM setup -------------------------------------------------------

    def _create_llm(self, agent: Any):
        """
        Create a ``ChatOpenAI`` instance for the given agent.

        Resolution order for base_url:
        1. ``LANGGRAPH_LLM_API_BASE`` env / config
        2. ``LLAMA_STACK_URL`` + ``/v1``  (OpenAI compat layer)
        """
        base_url = settings.LANGGRAPH_LLM_API_BASE
        if not base_url and settings.LLAMA_STACK_URL:
            base_url = f"{settings.LLAMA_STACK_URL}/v1"

        model_name = agent.model_name or settings.LANGGRAPH_DEFAULT_MODEL

        return ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key=settings.LANGGRAPH_LLM_API_KEY,
            temperature=agent.temperature or 0,
            streaming=True,
        )

    # ----- MCP tool resolution ----------------------------------------------

    async def _resolve_mcp_servers(
        self,
        tools: Optional[List],
    ) -> Dict[str, dict]:
        """
        Resolve MCP server URLs from the agent's tool config.

        Uses the LlamaStack toolgroups API (same source as LlamaStackRunner)
        and returns a mapping suitable for ``MultiServerMCPClient``::

            {"server_label": {"url": "http://…", "transport": "streamable_http"}}
        """
        if not tools:
            return {}

        mcp_configs: Dict[str, dict] = {}

        for tool_info in tools:
            tool_id = tool_info.get("toolgroup_id", "")
            if not tool_id.startswith("mcp::"):
                continue

            try:
                from ...api.llamastack import get_client_from_request

                client = get_client_from_request(self.request)
                toolgroups = await client.toolgroups.list()

                for toolgroup in toolgroups:
                    if str(toolgroup.identifier) == tool_id:
                        label = toolgroup.args.get("name", str(toolgroup.identifier))
                        url = toolgroup.mcp_endpoint.uri
                        mcp_configs[label] = {
                            "url": url,
                            "transport": "streamable_http",
                        }
                        logger.info(f"Resolved MCP server '{label}' at {url}")
                        break
            except Exception as e:
                logger.warning(f"Failed to resolve MCP server for {tool_id}: {e}")

        return mcp_configs

    # ----- Input conversion -------------------------------------------------

    @staticmethod
    def _build_input_messages(prompt: Any) -> list:
        """Convert the prompt (content items list) to LangGraph input format."""
        text_parts: list[str] = []

        if isinstance(prompt, list):
            for item in prompt:
                if hasattr(item, "text") and item.text:
                    text_parts.append(item.text)
                elif isinstance(item, dict) and item.get("text"):
                    text_parts.append(item["text"])
        elif isinstance(prompt, str):
            text_parts.append(prompt)
        elif hasattr(prompt, "text"):
            text_parts.append(prompt.text)

        user_text = "\n".join(text_parts) if text_parts else str(prompt)
        return [{"role": "user", "content": user_text}]

    # ----- SSE helpers -------------------------------------------------------

    @staticmethod
    def _sse(event_type: str, data: dict, session_id: str) -> str:
        """Create an SSE-formatted event string."""
        payload = {"type": event_type, "session_id": str(session_id), **data}
        return f"data: {json.dumps(payload)}\n\n"

    @staticmethod
    def _message_to_dict(msg: Any) -> dict:
        """Normalise a LangChain message object to a plain dict."""
        if hasattr(msg, "model_dump"):
            return msg.model_dump()
        if hasattr(msg, "dict"):
            return msg.dict()
        result: dict = {
            "type": getattr(msg, "type", "unknown"),
            "content": getattr(msg, "content", ""),
        }
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": (
                        tc.get("id", "")
                        if isinstance(tc, dict)
                        else getattr(tc, "id", "")
                    ),
                    "name": (
                        tc.get("name", "")
                        if isinstance(tc, dict)
                        else getattr(tc, "name", "")
                    ),
                    "args": (
                        tc.get("args", {})
                        if isinstance(tc, dict)
                        else getattr(tc, "args", {})
                    ),
                }
                for tc in msg.tool_calls
            ]
        if hasattr(msg, "tool_call_id"):
            result["tool_call_id"] = msg.tool_call_id
        if hasattr(msg, "name"):
            result["name"] = msg.name
        return result

    # ----- Core graph execution ---------------------------------------------

    async def _run_graph(
        self,
        agent: Any,
        tools: list,
        session_id: str,
        prompt: Any,
    ) -> AsyncIterator[str]:
        """Build a ReAct agent graph, stream it, and yield SSE events."""
        llm = self._create_llm(agent)
        checkpointer = _get_checkpointer()

        graph = create_react_agent(
            model=llm,
            tools=tools,
            prompt=agent.prompt or "You are a helpful assistant.",
            checkpointer=checkpointer,
        )

        input_messages = self._build_input_messages(prompt)

        max_iters = getattr(agent, "max_infer_iters", None) or 100
        config = {
            "configurable": {"thread_id": str(session_id)},
            "recursion_limit": 2 * max_iters + 1,
        }

        # State tracking across the interleaved stream
        response_id = str(uuid.uuid4())[:8]
        has_output_text = False
        pending_tool_calls: Dict[str, dict] = {}

        try:
            async for mode, chunk in graph.astream(
                {"messages": input_messages},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                # -- Token-level streaming (messages mode) -------------------
                if mode == "messages":
                    msg_chunk, metadata = chunk
                    node = metadata.get("langgraph_node", "")

                    if isinstance(msg_chunk, AIMessageChunk) and node == "agent":
                        content = msg_chunk.content
                        if content and isinstance(content, str):
                            has_output_text = True
                            yield self._sse(
                                "response",
                                {
                                    "delta": content,
                                    "status": "in_progress",
                                    "id": response_id,
                                },
                                session_id,
                            )

                # -- Node-level updates (updates mode) -----------------------
                elif mode == "updates":
                    for node_name, node_output in chunk.items():
                        if node_name == "__end__":
                            continue

                        yield self._sse("node_started", {"node": node_name}, session_id)

                        messages = node_output.get("messages", [])
                        for msg in messages:
                            msg_dict = self._message_to_dict(msg)

                            # Agent decided to call tool(s)
                            if node_name == "agent" and msg_dict.get("tool_calls"):
                                for tc in msg_dict["tool_calls"]:
                                    tc_id = tc.get("id", str(uuid.uuid4()))
                                    pending_tool_calls[tc_id] = tc
                                    yield self._sse(
                                        "tool_call",
                                        {
                                            "id": tc_id,
                                            "name": tc.get("name", "unknown"),
                                            "server_label": "langgraph",
                                            "arguments": json.dumps(tc.get("args", {})),
                                            "output": None,
                                            "error": None,
                                            "status": "in_progress",
                                        },
                                        session_id,
                                    )

                            # Tool execution completed
                            if node_name == "tools" and msg_dict.get("type") == "tool":
                                tc_id = msg_dict.get("tool_call_id", "")
                                tool_name = msg_dict.get("name", "unknown")
                                output = msg_dict.get("content", "")
                                error = None

                                if msg_dict.get("status") == "error":
                                    error = output
                                    output = None

                                orig = pending_tool_calls.get(tc_id, {})
                                yield self._sse(
                                    "tool_call",
                                    {
                                        "id": tc_id,
                                        "name": tool_name,
                                        "server_label": "langgraph",
                                        "arguments": (
                                            json.dumps(orig.get("args", {}))
                                            if orig
                                            else None
                                        ),
                                        "output": output,
                                        "error": error,
                                        "status": ("failed" if error else "completed"),
                                    },
                                    session_id,
                                )

                        yield self._sse(
                            "node_completed",
                            {"node": node_name},
                            session_id,
                        )

            # Mark response complete (only if we emitted text)
            if has_output_text:
                yield self._sse(
                    "response",
                    {"delta": "", "status": "completed", "id": response_id},
                    session_id,
                )
            elif not pending_tool_calls:
                yield self._sse(
                    "error",
                    {
                        "message": (
                            "The assistant couldn't generate a text response. "
                            "Please try again or rephrase your request."
                        )
                    },
                    session_id,
                )

        except Exception as e:
            logger.exception(f"Error during LangGraph execution: {e}")
            yield self._sse(
                "error",
                {"message": f"LangGraph execution error: {str(e)}"},
                session_id,
            )

    # ----- Public interface (BaseRunner) ------------------------------------

    async def stream(
        self,
        agent: Any,
        session_id: str,
        prompt: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a response using LangGraph's ReAct agent.

        Yields SSE-formatted strings with normalised event types.
        """
        if not _check_langgraph():
            error_data = {
                "type": "error",
                "message": (
                    "LangGraph is not installed. "
                    "Install langgraph and langchain-openai to use this runner."
                ),
                "session_id": str(session_id),
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"
            return

        try:
            # Resolve MCP tools from agent config
            mcp_configs = await self._resolve_mcp_servers(agent.tools)
            tools: list = []

            if mcp_configs:
                try:
                    from langchain_mcp_adapters.client import (
                        MultiServerMCPClient,
                    )

                    async with MultiServerMCPClient(mcp_configs) as mcp_client:
                        tools = mcp_client.get_tools()
                        logger.info(
                            f"Loaded {len(tools)} MCP tools "
                            f"for LangGraph agent {agent.id}"
                        )
                        async for event in self._run_graph(
                            agent, tools, session_id, prompt
                        ):
                            yield event
                except ImportError:
                    logger.warning(
                        "langchain-mcp-adapters not installed; "
                        "running LangGraph agent without MCP tools"
                    )
                    async for event in self._run_graph(agent, [], session_id, prompt):
                        yield event
                except Exception as mcp_err:
                    logger.warning(
                        f"MCP tool loading failed ({mcp_err}); "
                        f"running agent without tools"
                    )
                    async for event in self._run_graph(agent, [], session_id, prompt):
                        yield event
            else:
                async for event in self._run_graph(agent, [], session_id, prompt):
                    yield event

            yield "data: [DONE]\n\n"

            # Best-effort session title update
            await self._update_session_title(session_id, prompt)

        except Exception as e:
            logger.exception(f"Error in LangGraph stream for agent {agent.id}: {e}")
            error_data = {
                "type": "error",
                "message": f"Error: {str(e)}",
                "session_id": str(session_id),
            }
            yield f"data: {json.dumps(jsonable_encoder(error_data))}\n\n"

    # ----- Session helpers --------------------------------------------------

    async def _update_session_title(self, session_id: str, user_input: Any) -> None:
        """Update session title from the first user message (best-effort)."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == self.user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            return

        if session.title and not session.title.startswith("Chat"):
            return

        title = "New Chat"
        if isinstance(user_input, list) and user_input:
            for item in user_input:
                if hasattr(item, "text") and item.text:
                    txt = item.text
                    title = txt[:50] + ("..." if len(txt) > 50 else "")
                    break
        elif hasattr(user_input, "text"):
            txt = user_input.text
            title = txt[:50] + ("..." if len(txt) > 50 else "")

        session.title = title

        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating session title: {e}")
            await self.db.rollback()
