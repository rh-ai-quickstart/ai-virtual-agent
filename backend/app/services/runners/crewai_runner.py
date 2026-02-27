"""
CrewAI runner implementation.

Streams responses from CrewAI using the Python SDK with stream=True and
akickoff(), mapping CrewAI chunks to the same SSE event types as LlamaStack.
"""

import os

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List

from sqlalchemy import select
from .base import BaseRunner
from ...models.agent import VirtualAgent
from ...models import ChatSession

try:
    from crewai import Agent, Crew, Task, LLM
    from crewai.types.streaming import StreamChunkType  # type: ignore[attr-defined]

    CREWAI_AVAILABLE = True
    CREWAI_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - environment dependent
    # Keep the module importable in unit-test/dev environments where CrewAI is missing
    # or partially installed. stream() returns a clear error event in that case.
    Agent = Crew = Task = LLM = Any  # type: ignore[assignment]
    StreamChunkType = Any  # type: ignore[assignment]
    CREWAI_AVAILABLE = False
    CREWAI_IMPORT_ERROR = exc


logger = logging.getLogger(__name__)


class CrewAIRunner(BaseRunner):
    """
    Runner for CrewAI agents using the CrewAI Python SDK.

    Builds a single-agent Crew from the VirtualAgent config (prompt as
    backstory), runs with stream=True and a async kickoff(), and maps stream chunks
    to the same SSE event types as LlamaStack (reasoning, response, tool_call,
    error) so the frontend works unchanged.
    """

    def __init__(self, request: Any, db: Any, user_id: Any):
        super().__init__(request, db, user_id)

    @staticmethod
    def _sse(event_type: str, data: dict, session_id: str) -> str:
        """Create an SSE-formatted event string (matches graph engine format)."""
        payload = {"type": event_type, "session_id": str(session_id), **data}
        return f"data: {json.dumps(payload)}\n\n"

    _SMALL_MODEL_PATTERNS = re.compile(
        r"(?:^|/)(?:.*\b(?:1b|2b|3b)\b)", re.IGNORECASE,
    )

    @classmethod
    def _is_small_model(cls, model_name: str) -> bool:
        """Return True for models too small to reliably execute ReAct tool loops."""
        return bool(cls._SMALL_MODEL_PATTERNS.search(model_name))

    _REACT_NOISE_RE = re.compile(
        r"^(#{0,3}\s*)?(Thought|Action|Action Input|Input|Observation)\s*:",
        re.IGNORECASE,
    )
    _FINAL_ANSWER_PREFIX_RE = re.compile(
        r"^\s*(?:final answer|answer)\s*:\s*",
        re.IGNORECASE,
    )
    _PLACEHOLDER_OUTPUT_RE = re.compile(
        r"^\s*this is the expected criteria for my final answer\s*:",
        re.IGNORECASE,
    )
    _GENERIC_BOILERPLATE_RE = re.compile(
        r"^\s*i now can give (?:a )?great answer\.?\s*$",
        re.IGNORECASE,
    )

    @classmethod
    def _clean_react_output(cls, raw: str) -> str:
        """Strip ReAct formatting artifacts from a CrewAI final output.

        When the model fails to properly execute the ReAct loop, the raw
        output contains ``Thought: / Action: / Input:`` lines that are noise
        to the end-user.  This strips them and returns only meaningful text.
        """
        lines = raw.strip().splitlines()
        kept: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if cls._REACT_NOISE_RE.match(stripped):
                continue
            if cls._PLACEHOLDER_OUTPUT_RE.match(stripped):
                continue
            if cls._GENERIC_BOILERPLATE_RE.match(stripped):
                continue
            stripped = cls._FINAL_ANSWER_PREFIX_RE.sub("", stripped).strip()
            if stripped and not stripped.startswith("{") and not stripped.startswith("'"):
                kept.append(stripped)
        return "\n".join(kept) if kept else raw.strip()

    @classmethod
    def _is_placeholder_output(cls, text: str) -> bool:
        """Return True when CrewAI returns rubric metadata instead of an answer."""
        return bool(cls._PLACEHOLDER_OUTPUT_RE.match(text.strip()))

    @classmethod
    def _extract_final_output_text(cls, result: Any) -> str:
        """Best-effort extraction of meaningful final response text from CrewAI output."""

        def _get_values(obj: Any) -> List[str]:
            values: List[str] = []
            if obj is None:
                return values

            if isinstance(obj, str):
                return [obj]

            if isinstance(obj, dict):
                for key in ("raw", "output", "result", "final_output", "summary", "text"):
                    value = obj.get(key)
                    if isinstance(value, str) and value.strip():
                        values.append(value)
                return values

            for key in ("raw", "output", "result", "final_output", "summary", "text"):
                value = getattr(obj, key, None)
                if isinstance(value, str) and value.strip():
                    values.append(value)
            return values

        candidates: List[str] = []
        candidates.extend(_get_values(result))

        tasks_output = getattr(result, "tasks_output", None)
        if isinstance(tasks_output, list):
            for task_output in tasks_output:
                candidates.extend(_get_values(task_output))

        for candidate in candidates:
            cleaned = cls._clean_react_output(candidate)
            if not cleaned:
                continue
            if cls._is_placeholder_output(cleaned):
                continue
            return cleaned

        return ""

    @staticmethod
    def _extract_prompt_text(prompt: Any) -> str:
        """
        Extract plain text from prompt (str or list of content items).
        Matches the shape used by the chat API (e.g. InterleavedContent items
        with .text or .type / .content).
        """
        if isinstance(prompt, str):
            return prompt.strip() or ""
        if isinstance(prompt, list):
            parts: List[str] = []
            for item in prompt:
                if hasattr(item, "text") and item.text:
                    parts.append(str(item.text))
                elif isinstance(item, dict):
                    if item.get("type") == "input_text" and item.get("text"):
                        parts.append(str(item["text"]))
                    elif item.get("content") and isinstance(item["content"], str):
                        parts.append(item["content"])
            return " ".join(parts).strip() or ""
        return str(prompt).strip() or ""

    def __get_llm(self, agent: VirtualAgent) -> LLM:
        """Get the LLM configured for LiteLLM (used by CrewAI internally).

        LiteLLM requires the provider prefix in the model string itself,
        e.g. "ollama/model-name" or "openai/model-name".

        For the ollama/ provider, LiteLLM reads OLLAMA_API_BASE from the
        environment automatically and constructs the correct API paths.
        Passing base_url explicitly causes double-path bugs
        (e.g. /api/generate/api/show).
        """
        openai_url = os.getenv("OPENAI_API_URL")

        extra_kwargs: Dict[str, Any] = {}
        if agent.temperature is not None:
            extra_kwargs["temperature"] = float(agent.temperature)
        if agent.max_tokens is not None:
            extra_kwargs["max_tokens"] = int(agent.max_tokens)
        if agent.top_p is not None:
            extra_kwargs["top_p"] = float(agent.top_p)

        if agent.model_name == "gpt-4o":
            return LLM(
                model="openai/gpt-4o",
                base_url=openai_url,
                api_key=os.getenv("OPENAI_API_KEY"),
                **extra_kwargs,
            )
        elif agent.model_name == "meta-llama/Llama-3.1-8B-Instruct":
            return LLM(
                model="ollama/llama3.2:1b-instruct-fp16",
                **extra_kwargs,
            )
        else:
            return LLM(
                model="openai/gpt-4o",
                base_url=openai_url,
                api_key=os.getenv("OPENAI_API_KEY"),
                **extra_kwargs,
            )

    def _build_tools(self, agent: Any) -> List[Any]:
        """Build a list of tools from the virtual agent config."""
        requested_tools = agent.tools

        if not requested_tools:
            return []

        tools = []
        tavily_tool_cls = None
        try:
            from ...lib.agent_tools.travel_tools import TavilySearchTool

            tavily_tool_cls = TavilySearchTool
        except Exception as exc:  # pragma: no cover - optional dependency path
            logger.warning("TavilySearchTool unavailable: %s", exc)

        for tool in requested_tools:
            if (
                tool["toolgroup_id"] == "builtin::websearch"
                and os.getenv("TAVILY_API_KEY")
                and tavily_tool_cls
            ):
                tools.append(tavily_tool_cls())

        return tools

    async def _build_crew(self, agent: VirtualAgent) -> Crew:
        """Build a CrewAI Agent, Task, and Crew from the virtual agent config."""
        role = getattr(agent, "persona", None) or getattr(agent, "name", None) or "CrewAI Agent"
        backstory = getattr(agent, "prompt", None) or "You are a helpful assistant."
        goal = getattr(agent, "goal", None) or "Answer the user's message. User message: {user_input}"

        logger.debug("Building crew for agent id=%s name=%s model=%s",
                      agent.id, agent.name, agent.model_name)
        logger.debug(f"Role: {role}, Backstory: {backstory}, Goal: {goal}")

        llm = self.__get_llm(agent)

        new_agent: VirtualAgent = agent
        logger.debug(f"New agent role: {role}")
        logger.debug(f"New agent backstory: {backstory}")
        logger.debug(f"New agent goal: {goal}")

        logger.debug(f"New agent model: {llm.model}")
        logger.debug(f"New agent tools: {agent.tools}")

        tools = self._build_tools(agent)
        model_str = getattr(llm, "model", "")
        if tools and self._is_small_model(model_str):
            logger.warning(
                "Model %s is too small for reliable ReAct tool use; "
                "dropping tools so the model responds directly.", model_str,
            )
            tools = []

        crew_agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory or f"You are {role}.",
            tools=tools,
            verbose=True,
            llm=llm,
            allow_delegation=False,
            max_iter=5,
        )

        task = Task(
            description="Answer the user's message. User message: {user_input}",
            expected_output="A clear, helpful response to the user.",
            agent=crew_agent,
        )

        crew = Crew(
            agents=[crew_agent],
            tasks=[task],
            verbose=True,
            stream=True,
        )

        return crew

    async def _update_session_title(self, session_id: str, user_input: Any) -> None:
        """Update chat session title from the first user message."""
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
                    title = (txt[:50] + "...") if len(txt) > 50 else txt[:50]
                    break
        elif hasattr(user_input, "text"):
            txt = user_input.text
            title = (txt[:50] + "...") if len(txt) > 50 else txt[:50]
        elif isinstance(user_input, str) and user_input:
            title = (user_input[:50] + "...") if len(user_input) > 50 else user_input[:50]

        session.title = title
        try:
            await self.db.commit()
        except Exception as e:
            logger.error("Error updating session title: %s", e)
            await self.db.rollback()

    @staticmethod
    def _done_event() -> str:
        """Return the SSE terminator used by the frontend stream handler."""
        return "data: [DONE]\n\n"

    def _crewai_unavailable_message(self) -> str | None:
        """Return an import error message when CrewAI is unavailable."""
        if CREWAI_AVAILABLE:
            return None
        logger.warning("CrewAI unavailable: %s", CREWAI_IMPORT_ERROR)
        return (
            "CrewAI is not available in this environment. "
            f"Import error: {CREWAI_IMPORT_ERROR}"
        )

    def _validate_prompt_text(self, prompt: Any, sid: str, agent: Any) -> str | None:
        """Extract and validate prompt text, returning None when empty."""
        text = self._extract_prompt_text(prompt)
        if text:
            return text

        logger.warning(
            "Empty prompt for session %s, agent=%s",
            sid,
            getattr(agent, "id", None),
        )
        return None

    @classmethod
    def _should_emit_text_chunk(cls, content: str) -> bool:
        """Filter out non-user-facing CrewAI ReAct artifacts in stream chunks."""
        stripped = content.strip()
        if not stripped:
            return False
        if cls._is_placeholder_output(content):
            return False
        if cls._GENERIC_BOILERPLATE_RE.match(stripped):
            return False
        if cls._REACT_NOISE_RE.match(stripped):
            return False
        return True

    def _build_response_event(
        self,
        sid: str,
        final_response_id: str,
        *,
        delta: str,
        status: str = "in_progress",
    ) -> str:
        """Build a response SSE event for streaming and completion updates."""
        return self._sse(
            "response",
            {"delta": delta, "status": status, "id": final_response_id},
            sid,
        )

    def _build_tool_call_event(self, chunk: Any, sid: str, task_node_id: str) -> str | None:
        """Map a CrewAI tool call chunk into the shared SSE schema."""
        tool_call = getattr(chunk, "tool_call", None)
        if not tool_call:
            return None

        name = getattr(tool_call, "tool_name", None) or getattr(tool_call, "name", "tool")
        args = getattr(tool_call, "arguments", None) or {}
        return self._sse(
            "tool_call",
            {
                "id": f"tool-{task_node_id}",
                "name": name,
                "server_label": "crewai",
                "arguments": json.dumps(args) if isinstance(args, dict) else str(args),
                "output": None,
                "error": None,
                "status": "in_progress",
            },
            sid,
        )

    async def _stream_result_chunks(
        self,
        result: Any,
        sid: str,
        task_node_id: str,
        final_response_id: str,
    ) -> AsyncIterator[tuple[str, bool]]:
        """Yield (event, has_text_delta) tuples generated from CrewAI chunks."""
        has_output = False
        if not hasattr(result, "__aiter__"):
            return

        async for chunk in result:
            chunk_type = getattr(chunk, "chunk_type", None)
            content = getattr(chunk, "content", "") or ""
            logger.debug(
                "CrewAI chunk type=%s content_len=%d",
                chunk_type,
                len(content),
            )

            if chunk_type == StreamChunkType.TEXT and content:
                # Preserve raw spacing in streamed chunks. Cleaning each chunk
                # introduces whitespace regressions at chunk boundaries.
                if not self._should_emit_text_chunk(content):
                    continue
                has_output = True
                yield (
                    self._build_response_event(
                        sid,
                        final_response_id,
                        delta=content,
                    ),
                    True,
                )
            elif chunk_type == StreamChunkType.TOOL_CALL:
                tool_event = self._build_tool_call_event(chunk, sid, task_node_id)
                if tool_event:
                    yield (tool_event, False)

        if has_output:
            yield (
                self._build_response_event(
                    sid,
                    final_response_id,
                    delta="",
                    status="completed",
                ),
                False,
            )

    async def _emit_fallback_result(
        self,
        result: Any,
        sid: str,
        final_response_id: str,
    ) -> AsyncIterator[str]:
        """Emit a final response extracted from CrewOutput when no text chunks exist."""
        cleaned = self._extract_final_output_text(result)
        if cleaned:
            logger.info(
                "Using CrewOutput fallback text (%d chars) for session %s",
                len(cleaned),
                sid,
            )
            yield self._build_response_event(
                sid,
                final_response_id,
                delta=cleaned,
            )
            yield self._build_response_event(
                sid,
                final_response_id,
                delta="",
                status="completed",
            )
            return

        yield self._sse(
            "error",
            {
                "message": (
                    "The assistant couldn't generate a final text response. "
                    "Please try again."
                )
            },
            sid,
        )

    async def stream(
        self,
        agent: Any,
        session_id: str,
        prompt: Any,
    ) -> AsyncIterator[str]:
        """Stream a response using CrewAI with stream=True and akickoff().

        Emits node_started / node_completed lifecycle events around the task
        so the frontend renders output in expandable GraphNodeOutputSection
        components (same as the LangGraph vacation planner).
        """
        sid = str(session_id)
        unavailable_msg = self._crewai_unavailable_message()
        if unavailable_msg:
            yield self._sse("error", {"message": unavailable_msg}, sid)
            yield self._done_event()
            return

        try:
            text = self._validate_prompt_text(prompt, sid, agent)
            if text is None:
                yield self._sse("error", {"message": "No user message provided."}, sid)
                yield self._done_event()
                return

            logger.info("Building CrewAI crew for session %s", sid)
            crew = await self._build_crew(agent)

            task_node_id = "crewai_task"
            final_response_id = "crewai_final_response"

            yield self._sse("node_started", {"node": task_node_id}, sid)

            logger.info("Starting CrewAI kickoff for session %s", sid)
            result = await crew.kickoff_async(inputs={"user_input": text})

            logger.info("CrewAI kickoff returned type=%s for session %s",
                        type(result).__name__, sid)

            has_streamed_output = False
            # Prefer chunk-level streaming for responsiveness; fallback only when
            # CrewAI returns a non-streaming output object.
            async for event, has_text_delta in self._stream_result_chunks(
                result,
                sid,
                task_node_id,
                final_response_id,
            ):
                if has_text_delta:
                    has_streamed_output = True
                yield event

            yield self._sse("node_completed", {"node": task_node_id}, sid)

            if not has_streamed_output:
                async for event in self._emit_fallback_result(result, sid, final_response_id):
                    yield event

            yield self._done_event()

            await self._update_session_title(session_id, prompt)

        except Exception as e:
            logger.exception("Error in CrewAI stream for session %s: %s", sid, e)
            yield self._sse("error", {"message": f"Error: {str(e)}"}, sid)
            yield self._done_event()

