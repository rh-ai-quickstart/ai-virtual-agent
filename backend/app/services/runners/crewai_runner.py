"""
CrewAI runner implementation.

Streams responses from CrewAI using the Python SDK with stream=True and
akickoff(), mapping CrewAI chunks to the same SSE event types as LlamaStack.
"""

import json
import logging
import os
import re
from collections import deque
from typing import Any, AsyncIterator, Dict, List, Tuple

from sqlalchemy import select

from ...config import ENV_DEFAULT_MODEL_SENTINEL, settings
from ...lib.agent_tools import GoogleFlightsTool, GoogleHotelsTool, TavilySearchTool
from ...models import ChatSession
from ...models.agent import VirtualAgent
from .base import BaseRunner

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

try:
    from crewai import LLM, Agent, Crew, Task
    from crewai.types.streaming import StreamChunkType  # type: ignore[attr-defined]

    CREWAI_AVAILABLE = True
    CREWAI_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - environment dependent
    Agent = Crew = Task = LLM = Any  # type: ignore[assignment]
    StreamChunkType = Any  # type: ignore[assignment]
    CREWAI_AVAILABLE = False
    CREWAI_IMPORT_ERROR = exc

try:
    import litellm as _litellm

    _LITELLM_AVAILABLE = True
except ImportError:
    _litellm = None  # type: ignore[assignment]
    _LITELLM_AVAILABLE = False


logger = logging.getLogger(__name__)


class _StreamDeduplicator:
    """Buffers streamed chunks into complete lines, classifies them as
    response content or agent thinking, and suppresses ReAct noise.

    CrewAI streams tokens that can split a single logical line across
    multiple chunks.  This class reassembles complete lines, extracts
    "Thought:" reasoning for live display, and suppresses other ReAct
    noise (Action/Input/JSON/code fences).
    """

    # --- Thought extraction (shown to user as live "thinking") ---

    _THOUGHT_LINE_RE = re.compile(
        r"^\s*(?:#{0,3}\s*)?Thought\s*:\s*(.*)",
        re.IGNORECASE,
    )

    _MID_LINE_THOUGHT_RE = re.compile(
        r"[}\]`\"]\s*Thought\s*:\s*(.*)",
        re.IGNORECASE,
    )

    # --- Noise suppression (Action, Input, Observation, boilerplate) ---

    _NOISE_LINE_RE = re.compile(
        r"^\s*("
        r"(?:#{0,3}\s*)?(?:Action|Action Input|Input|Observation)\s*:.*"
        r"|i now can give (?:a )?great answer\.?"
        r"|(?:final answer\s*:\s*)?your final answer must be.*"
        r"|this is the expected criteria for my final answer\s*:.*"
        r"|begin!.*use the tools available.*"
        r"|final answer\s*:?"
        r")\s*$",
        re.IGNORECASE,
    )

    _MID_LINE_REACT_RE = re.compile(
        r"[}\]`\"]\s*(?:Action|Action Input|Observation)\s*:",
        re.IGNORECASE,
    )

    _TRUNCATED_MARKER_RE = re.compile(
        r"^\s*(?:tion|put|ervation)\s*:\s*\S",
        re.IGNORECASE,
    )

    _CODE_FENCE_RE = re.compile(r"^\s*```\w*\s*$")

    _JSON_STRUCTURAL_RE = re.compile(r"^\s*[{}\[\]]+\s*$")

    _JSON_CONTENT_RE = re.compile(r'^\s*\{?\s*"[a-z_]+"\s*:', re.IGNORECASE)

    def __init__(self) -> None:
        self._line_buffer: str = ""
        self._suppressing: bool = False

    def reset_for_new_task(self) -> None:
        self._line_buffer = ""
        self._suppressing = False

    def _extract_thought(self, line: str) -> str:
        """Extract reasoning text from a Thought: line, or return empty."""
        m = self._THOUGHT_LINE_RE.match(line)
        if m:
            text = m.group(1).strip()
            if text:
                self._suppressing = True
                return text
        m = self._MID_LINE_THOUGHT_RE.search(line)
        if m:
            text = m.group(1).strip()
            if text:
                self._suppressing = True
                return text
        return ""

    def _is_noise(self, line: str) -> bool:
        if self._NOISE_LINE_RE.match(line):
            self._suppressing = True
            return True
        if self._MID_LINE_REACT_RE.search(line):
            self._suppressing = True
            return True
        if self._TRUNCATED_MARKER_RE.match(line):
            self._suppressing = True
            return True
        if self._CODE_FENCE_RE.match(line):
            return True
        if self._JSON_STRUCTURAL_RE.match(line):
            return True
        if self._suppressing and self._JSON_CONTENT_RE.match(line):
            return True
        if self._suppressing and not line.strip():
            return True
        if line.strip():
            self._suppressing = False
        return False

    def filter_chunk(self, content: str) -> tuple[str, str]:
        """Classify buffered content into response text and thinking text.

        Returns ``(response_text, thinking_text)`` where *thinking_text*
        contains extracted "Thought:" reasoning (for live display) and
        *response_text* contains clean content for the final answer.
        """
        self._line_buffer += content
        if "\n" not in self._line_buffer:
            return ("", "")

        *complete_lines, remainder = self._line_buffer.split("\n")
        self._line_buffer = remainder

        kept: list[str] = []
        thoughts: list[str] = []

        for line in complete_lines:
            thought = self._extract_thought(line)
            if thought:
                thoughts.append(thought)
                continue
            if self._is_noise(line):
                continue
            kept.append(line)

        response_text = "\n".join(kept) + "\n" if kept else ""
        thinking_text = " ".join(thoughts) if thoughts else ""
        return (response_text, thinking_text)

    def flush(self) -> tuple[str, str]:
        """Flush remaining buffer content as (response_text, thinking_text)."""
        remaining = self._line_buffer
        self._line_buffer = ""
        if not remaining.strip():
            return ("", "")
        thought = self._extract_thought(remaining)
        if thought:
            return ("", thought)
        if self._is_noise(remaining):
            return ("", "")
        return (remaining, "")


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
        r"(?:^|/)(?:.*\b(?:1b|2b|3b)\b)",
        re.IGNORECASE,
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
    _FINAL_ANSWER_BOILERPLATE_RE = re.compile(
        r"^\s*(?:final answer\s*:\s*)?your final answer must be.*$",
        re.IGNORECASE,
    )
    _TOOL_CLASS_BY_NAME = {
        "tavily_travel_search": TavilySearchTool,
        "google_hotels_search": GoogleHotelsTool,
        "google_flights_search": GoogleFlightsTool,
    }
    _SERVER_TOOL_NAME_HINTS = (
        ("research", "tavily_travel_search"),
        ("tavily", "tavily_travel_search"),
        ("hotel", "google_hotels_search"),
        ("flight", "google_flights_search"),
    )
    _LITELLM_PROVIDER_PREFIXES = (
        "openai/",
        "azure/",
        "anthropic/",
        "ollama/",
        "huggingface/",
        "bedrock/",
        "vertex_ai/",
        "gemini/",
        "groq/",
        "mistral/",
        "cohere/",
        "together_ai/",
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
        suppressing = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if cls._REACT_NOISE_RE.match(stripped):
                suppressing = True
                continue
            if cls._PLACEHOLDER_OUTPUT_RE.match(stripped):
                continue
            if cls._GENERIC_BOILERPLATE_RE.match(stripped):
                continue
            if _StreamDeduplicator._MID_LINE_REACT_RE.search(stripped):
                suppressing = True
                continue
            if _StreamDeduplicator._MID_LINE_THOUGHT_RE.search(stripped):
                suppressing = True
                continue
            if _StreamDeduplicator._TRUNCATED_MARKER_RE.match(stripped):
                suppressing = True
                continue
            if _StreamDeduplicator._CODE_FENCE_RE.match(stripped):
                continue
            if _StreamDeduplicator._JSON_STRUCTURAL_RE.match(stripped):
                continue
            if suppressing and _StreamDeduplicator._JSON_CONTENT_RE.match(stripped):
                continue
            suppressing = False
            stripped = cls._FINAL_ANSWER_PREFIX_RE.sub("", stripped).strip()
            if (
                stripped
                and not stripped.startswith("{")
                and not stripped.startswith("'")
            ):
                kept.append(stripped)
        return "\n".join(kept) if kept else ""

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
                for key in (
                    "raw",
                    "output",
                    "result",
                    "final_output",
                    "summary",
                    "text",
                ):
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

    @classmethod
    def _extract_task_output_text(cls, task_output: Any) -> str:
        """Extract clean text from a single CrewAI TaskOutput."""
        for attr in ("raw", "output", "result", "summary", "text"):
            value = getattr(task_output, attr, None)
            if isinstance(value, str) and value.strip():
                cleaned = cls._clean_react_output(value)
                if cleaned and not cls._is_placeholder_output(cleaned):
                    return cleaned
        return ""

    @staticmethod
    def _extract_prompt_text(prompt: Any) -> str:
        """Extract plain text from a prompt (content items list, string, or object)."""
        if isinstance(prompt, str):
            return prompt.strip()

        if isinstance(prompt, list):
            parts: list[str] = []
            for item in prompt:
                text = getattr(item, "text", None)
                if text:
                    parts.append(text)
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(item["text"])
            if parts:
                return "\n".join(parts).strip()

        if hasattr(prompt, "text") and prompt.text:
            return str(prompt.text).strip()

        return str(prompt).strip() or ""

    @classmethod
    def _to_litellm_model(cls, model_name: str) -> str:
        """Ensure model is provider-qualified for LiteLLM routing."""
        normalized = (model_name or "").strip()
        if not normalized:
            return "openai/meta/llama-3.1-70b-instruct"
        if normalized.startswith(cls._LITELLM_PROVIDER_PREFIXES):
            return normalized
        return f"openai/{normalized}"

    _DESTINATION_RE = re.compile(
        r"(?:to|in|visit(?:ing)?|explore|trip\s+to)\s+"
        r"([A-Z][A-Za-z\s]{1,30}?)(?:\s+(?:for|with|from|next|this|in|during|$))",
        re.IGNORECASE,
    )
    _NUM_DAYS_RE = re.compile(
        r"(\d{1,2})[\s-]*(?:day|night)",
        re.IGNORECASE,
    )
    _ORIGIN_RE = re.compile(
        r"(?:from|departing|leaving)\s+"
        r"([A-Z][A-Za-z\s]{1,30}?)(?:\s+(?:to|for|on|next|this|$))",
        re.IGNORECASE,
    )

    @classmethod
    def _regex_extract_input_fields(
        cls,
        user_text: str,
        defaults: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Best-effort regex extraction for common travel fields.

        Used as a fallback when LLM extraction fails or misses fields.
        """
        extracted: Dict[str, Any] = {}
        if "destination" in defaults:
            m = cls._DESTINATION_RE.search(user_text)
            if m:
                extracted["destination"] = m.group(1).strip()
        if "num_days" in defaults:
            m = cls._NUM_DAYS_RE.search(user_text)
            if m:
                extracted["num_days"] = m.group(1)
        if "origin" in defaults:
            m = cls._ORIGIN_RE.search(user_text)
            if m:
                extracted["origin"] = m.group(1).strip()
        return extracted

    @classmethod
    async def _extract_input_fields(
        cls,
        user_text: str,
        defaults: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use an LLM to pull structured fields out of a natural-language message.

        Mirrors the LangGraph runner's extraction step so that a user message
        like "Plan a 3-day trip to Paris" overrides ``destination: Tokyo`` and
        ``num_days: 7`` from the template defaults.

        Falls back to regex extraction when the LLM call fails or returns
        incomplete results.

        Resolution order (mirrors ``__get_llm``):
        - Model:    ``CREWAI_DEFAULT_MODEL``  > ``gpt-4o-mini``
        - Base URL: ``CREWAI_LLM_API_BASE``
        - API key:  ``CREWAI_LLM_API_KEY``
        """
        regex_fields = cls._regex_extract_input_fields(user_text, defaults)
        if regex_fields:
            logger.info("Regex-extracted input fields: %s", regex_fields)

        if not _LITELLM_AVAILABLE:
            logger.info("litellm unavailable; using regex extraction only")
            return regex_fields

        field_descriptions = json.dumps(
            {k: f"default: {v}" for k, v in defaults.items()}, indent=2
        )
        extraction_prompt = (
            "Extract values for the following fields from the user message.\n"
            "Return ONLY a valid JSON object with the fields you can "
            "confidently extract. Do NOT wrap in markdown code fences.\n"
            "Omit any field that the user did not mention or imply.\n\n"
            f"Fields (with their defaults):\n{field_descriptions}\n\n"
            f"User message: {user_text}\n\n"
            "JSON:"
        )

        api_base = settings.CREWAI_LLM_API_BASE
        api_key = settings.CREWAI_LLM_API_KEY or "no-key"
        raw_model = settings.CREWAI_DEFAULT_MODEL or "gpt-4o-mini"

        if not raw_model.startswith("openai/"):
            extraction_model = f"openai/{raw_model}"
        else:
            extraction_model = raw_model

        try:
            response = await _litellm.acompletion(
                model=extraction_model,
                messages=[{"role": "user", "content": extraction_prompt}],
                api_base=api_base,
                api_key=api_key,
                timeout=30,
            )
            raw = response.choices[0].message.content.strip()
            logger.debug("LLM extraction raw response: %s", raw[:500])

            if raw.startswith("```"):
                lines = raw.splitlines()
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                raw = "\n".join(lines).strip()

            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                llm_fields = {
                    k: str(v) for k, v in parsed.items() if k in defaults and v
                }
                logger.info("LLM-extracted input fields: %s", llm_fields)
                merged = dict(regex_fields)
                merged.update(llm_fields)
                return merged
        except Exception as e:
            logger.warning(
                "LLM input field extraction failed (falling back to regex): %s", e
            )

        return regex_fields

    def __get_llm(self, agent: VirtualAgent) -> LLM:
        """Get the LLM configured for LiteLLM (used by CrewAI internally).

        Resolution order:
        - Model:    ``CREWAI_DEFAULT_MODEL`` > agent.model_name
        - Base URL: ``CREWAI_LLM_API_BASE``
        - API key:  ``CREWAI_LLM_API_KEY``
        """
        api_base = settings.CREWAI_LLM_API_BASE
        api_key = settings.CREWAI_LLM_API_KEY

        extra_kwargs: Dict[str, Any] = {}
        if agent.temperature is not None:
            extra_kwargs["temperature"] = float(agent.temperature)
        if agent.max_tokens is not None:
            extra_kwargs["max_tokens"] = int(agent.max_tokens)
        if agent.top_p is not None:
            extra_kwargs["top_p"] = float(agent.top_p)

        agent_model = (
            agent.model_name.strip()
            if isinstance(agent.model_name, str) and agent.model_name.strip()
            else None
        )
        if agent_model == ENV_DEFAULT_MODEL_SENTINEL:
            agent_model = None

        requested_model = (
            settings.CREWAI_DEFAULT_MODEL
            or agent_model
            or "meta/llama-3.1-70b-instruct"
        )
        litellm_model = self._to_litellm_model(requested_model)

        llm_kwargs: Dict[str, Any] = {"model": litellm_model, **extra_kwargs}
        if api_base:
            llm_kwargs["base_url"] = api_base
        if api_key:
            llm_kwargs["api_key"] = api_key

        return LLM(**llm_kwargs)

    @classmethod
    def _infer_tool_name_for_server(cls, server_name: str) -> str | None:
        """Best-effort tool-name inference from an MCP server label."""
        normalized = (server_name or "").lower()
        for hint, tool_name in cls._SERVER_TOOL_NAME_HINTS:
            if hint in normalized:
                return tool_name
        return None

    @classmethod
    def _build_tools_from_servers(cls, graph_config: Any) -> List[Any]:
        """Resolve CrewAI tools from graph_config.mcp.servers entries."""
        if not isinstance(graph_config, dict):
            return []

        mcp_cfg = graph_config.get("mcp")
        if not isinstance(mcp_cfg, dict):
            return []

        servers = mcp_cfg.get("servers")
        if not isinstance(servers, dict) or not servers:
            return []

        server_tool_names: Dict[str, str] = {}
        nodes = graph_config.get("nodes")
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                server_name = node.get("server")
                tool_name = node.get("tool")
                if (
                    isinstance(server_name, str)
                    and isinstance(tool_name, str)
                    and server_name in servers
                ):
                    server_tool_names[server_name] = tool_name

        resolved: List[Any] = []
        seen_tool_names: set[str] = set()
        for server_name in servers.keys():
            tool_name = server_tool_names.get(
                server_name
            ) or cls._infer_tool_name_for_server(server_name)
            if not tool_name or tool_name in seen_tool_names:
                continue

            tool_cls = cls._TOOL_CLASS_BY_NAME.get(tool_name)
            if not tool_cls:
                logger.info(
                    "No local CrewAI tool mapped for server '%s' tool '%s'",
                    server_name,
                    tool_name,
                )
                continue

            resolved.append(tool_cls())
            seen_tool_names.add(tool_name)

        return resolved

    @classmethod
    def _resolve_tools_for_server_names(
        cls, server_names: List[str], graph_config: Dict
    ) -> List[Any]:
        """Resolve CrewAI tool instances for a list of MCP server names."""
        tools: List[Any] = []
        seen: set[str] = set()
        for server_name in server_names:
            tool_name = cls._infer_tool_name_for_server(server_name)
            if not tool_name or tool_name in seen:
                continue
            tool_cls = cls._TOOL_CLASS_BY_NAME.get(tool_name)
            if tool_cls:
                tools.append(tool_cls())
                seen.add(tool_name)
            else:
                logger.info(
                    "No local CrewAI tool for server '%s' (inferred '%s')",
                    server_name,
                    tool_name,
                )
        return tools

    def _build_tools(self, agent: Any) -> List[Any]:
        """Build CrewAI tools from servers config and legacy tool associations."""
        tools: List[Any] = []
        seen_names: set[str] = set()

        for tool in self._build_tools_from_servers(
            getattr(agent, "graph_config", None)
        ):
            name = getattr(tool, "name", tool.__class__.__name__)
            if name not in seen_names:
                tools.append(tool)
                seen_names.add(name)

        requested_tools = getattr(agent, "tools", None) or []
        for tool in requested_tools:
            if not isinstance(tool, dict):
                continue
            if tool.get("toolgroup_id") != "builtin::websearch":
                continue
            tool_cls = self._TOOL_CLASS_BY_NAME.get("tavily_travel_search")
            if not tool_cls:
                continue
            instance = tool_cls()
            name = getattr(instance, "name", instance.__class__.__name__)
            if name not in seen_names:
                tools.append(instance)
                seen_names.add(name)

        return tools

    def _build_multi_agent_crew(
        self,
        agent: VirtualAgent,
        graph_config: Dict,
        task_callback: Any = None,
    ) -> Tuple[Crew, List[str]]:
        """Build a multi-agent CrewAI Crew from graph_config agents/tasks.

        Returns ``(crew, task_ids)`` where *task_ids* is the ordered list of
        template task IDs for emitting per-task node lifecycle events.
        """
        llm = self.__get_llm(agent)
        model_str = getattr(llm, "model", "")
        small_model = self._is_small_model(model_str)

        agents_cfg = graph_config.get("agents", {})
        tasks_cfg = graph_config.get("tasks", [])
        process_type = graph_config.get("process", "sequential")

        crew_agents: Dict[str, Agent] = {}
        for agent_id, acfg in agents_cfg.items():
            server_names = acfg.get("tools", [])
            tools = self._resolve_tools_for_server_names(server_names, graph_config)
            if tools and small_model:
                logger.warning(
                    "Model %s too small for tools; dropping for agent '%s'",
                    model_str,
                    agent_id,
                )
                tools = []

            crew_agents[agent_id] = Agent(
                role=acfg.get("role", agent_id).strip(),
                goal=acfg.get("goal", "Help the user.").strip(),
                backstory=acfg.get("backstory", "You are a helpful assistant.").strip(),
                tools=tools,
                verbose=True,
                llm=llm,
                allow_delegation=False,
                max_iter=15,
                max_retry_limit=3,
            )

        crew_tasks: Dict[str, Task] = {}
        ordered_tasks: List[Task] = []
        task_ids: List[str] = []
        for tcfg in tasks_cfg:
            task_id = tcfg.get("id", "task")
            assigned_agent = crew_agents.get(tcfg.get("agent", ""))

            task_kwargs: Dict[str, Any] = dict(
                name=task_id,
                description=tcfg.get("description", "").strip(),
                expected_output=tcfg.get(
                    "expected_output", "A clear response."
                ).strip(),
                agent=assigned_agent,
            )
            if "context" in tcfg:
                context_tasks = [
                    crew_tasks[cid]
                    for cid in (tcfg.get("context") or [])
                    if cid in crew_tasks
                ]
                task_kwargs["context"] = context_tasks
            if tcfg.get("async_execution"):
                task_kwargs["async_execution"] = True

            task = Task(**task_kwargs)
            crew_tasks[task_id] = task
            ordered_tasks.append(task)
            if not tcfg.get("internal"):
                task_ids.append(task_id)

        logger.info(
            "Built multi-agent crew: %d agents, %d tasks, process=%s",
            len(crew_agents),
            len(ordered_tasks),
            process_type,
        )

        crew_kwargs: Dict[str, Any] = dict(
            agents=list(crew_agents.values()),
            tasks=ordered_tasks,
            verbose=True,
            stream=True,
            tracing=True,
            process=process_type,
        )
        if task_callback is not None:
            crew_kwargs["task_callback"] = task_callback

        return Crew(**crew_kwargs), task_ids

    async def _build_crew(
        self,
        agent: VirtualAgent,
        task_callback: Any = None,
    ) -> Tuple[Crew, List[str]]:
        """Build a CrewAI Crew from the virtual agent config.

        Returns ``(crew, task_ids)``.  For multi-agent crews ``task_ids``
        contains the ordered template task IDs; for single-agent crews it
        contains a single synthetic ``"crewai_task"`` entry.
        """
        graph_config = getattr(agent, "graph_config", None) or {}
        if isinstance(graph_config, dict) and graph_config.get("agents"):
            return self._build_multi_agent_crew(
                agent, graph_config, task_callback=task_callback
            )

        role = (
            getattr(agent, "persona", None)
            or getattr(agent, "name", None)
            or "CrewAI Agent"
        )
        backstory = (
            getattr(agent, "description", None) or "You are a helpful assistant."
        )
        goal = (
            getattr(agent, "goal", None)
            or "Answer the user's message. User message: {user_input}"
        )

        logger.debug(
            "Building crew for agent id=%s name=%s model=%s",
            agent.id,
            agent.name,
            agent.model_name,
        )
        logger.debug(f"Role: {role}, Backstory: {backstory}, Goal: {goal}")

        llm = self.__get_llm(agent)

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
                "dropping tools so the model responds directly.",
                model_str,
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
            max_iter=15,
            max_retry_limit=3,
        )

        task = Task(
            description=getattr(agent, "prompt", None)
            or "Answer the user's message. User message: {user_input}",
            expected_output="A clear, helpful response to the user.",
            agent=crew_agent,
        )

        crew_kwargs: Dict[str, Any] = dict(
            agents=[crew_agent],
            tasks=[task],
            verbose=True,
            stream=True,
            tracing=True,
        )
        if task_callback is not None:
            crew_kwargs["task_callback"] = task_callback

        return Crew(**crew_kwargs), ["crewai_task"]

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
            title = (
                (user_input[:50] + "...") if len(user_input) > 50 else user_input[:50]
            )

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
        """Quick pre-filter for obviously empty or placeholder chunks.

        The heavy lifting (line-level ReAct noise, boilerplate, and dedup)
        is handled by ``_StreamDeduplicator`` which operates on complete lines.
        """
        if not content.strip():
            return False
        if cls._is_placeholder_output(content):
            return False
        return True

    def _build_reasoning_event(
        self,
        sid: str,
        response_id: str,
        *,
        text: str,
    ) -> str:
        """Build a reasoning SSE event for live thinking display."""
        return self._sse(
            "reasoning",
            {
                "text": text,
                "status": "in_progress",
                "id": f"thinking-{response_id}",
            },
            sid,
        )

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

    def _build_tool_call_event(
        self, chunk: Any, sid: str, task_node_id: str
    ) -> str | None:
        """Map a CrewAI tool call chunk into the shared SSE schema."""
        tool_call = getattr(chunk, "tool_call", None)
        if not tool_call:
            return None

        name = getattr(tool_call, "tool_name", None) or getattr(
            tool_call, "name", "tool"
        )
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
        task_ids: List[str],
        started_nodes: set,
        completed_nodes: set,
        dedup: _StreamDeduplicator | None = None,
        streamed_tasks: set | None = None,
    ) -> AsyncIterator[tuple[str, bool]]:
        """Yield (event, has_text_delta) tuples generated from CrewAI chunks.

        The response ``id`` is set to the most recently started (but not yet
        completed) task ID, so the frontend groups output text under the
        correct node heading.
        """
        has_output = False
        if not hasattr(result, "__aiter__"):
            return

        def _current_response_id() -> str:
            for tid in reversed(task_ids):
                if tid in started_nodes and tid not in completed_nodes:
                    return tid
            return task_ids[-1] if task_ids else "crewai_task"

        async for chunk in result:
            chunk_type = getattr(chunk, "chunk_type", None)
            content = getattr(chunk, "content", "") or ""
            logger.debug(
                "CrewAI chunk type=%s content_len=%d",
                chunk_type,
                len(content),
            )

            if chunk_type == StreamChunkType.TEXT and content:
                if not self._should_emit_text_chunk(content):
                    continue
                if dedup:
                    response_text, thinking_text = dedup.filter_chunk(content)
                    if thinking_text:
                        yield (
                            self._build_reasoning_event(
                                sid,
                                _current_response_id(),
                                text=thinking_text,
                            ),
                            False,
                        )
                    if not response_text:
                        continue
                    content = response_text
                has_output = True
                if streamed_tasks is not None:
                    streamed_tasks.add(_current_response_id())
                yield (
                    self._build_response_event(
                        sid,
                        _current_response_id(),
                        delta=content,
                    ),
                    True,
                )
            elif chunk_type == StreamChunkType.TOOL_CALL:
                tool_event = self._build_tool_call_event(
                    chunk, sid, _current_response_id()
                )
                if tool_event:
                    yield (tool_event, False)

        if dedup:
            response_text, thinking_text = dedup.flush()
            if thinking_text:
                yield (
                    self._build_reasoning_event(
                        sid,
                        _current_response_id(),
                        text=thinking_text,
                    ),
                    False,
                )
            if response_text:
                has_output = True
                yield (
                    self._build_response_event(
                        sid,
                        _current_response_id(),
                        delta=response_text,
                    ),
                    True,
                )

        if has_output:
            yield (
                self._build_response_event(
                    sid,
                    _current_response_id(),
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

    def _drain_task_events(
        self,
        event_queue: deque,
        task_ids: List[str],
        started_nodes: set,
        completed_nodes: set,
        sid: str,
        dedup: _StreamDeduplicator | None = None,
        streamed_tasks: set | None = None,
    ) -> Tuple[List[str], bool]:
        """Drain task-completion events from the queue and return SSE strings.

        Uses the ``name`` attribute on ``TaskOutput`` to identify which task
        completed, supporting both sequential and parallel (async_execution)
        task ordering.

        Returns ``(events, has_task_content)`` where *has_task_content* is
        True when at least one task emitted meaningful response text.
        """
        events: List[str] = []
        has_task_content = False
        while event_queue:
            output = event_queue.popleft()
            task_name = getattr(output, "name", None) or ""

            if task_name and task_name not in completed_nodes:
                completed_nodes.add(task_name)

                if task_name not in task_ids:
                    continue

                if task_name not in started_nodes:
                    events.append(self._sse("node_started", {"node": task_name}, sid))
                    started_nodes.add(task_name)

                task_text = self._extract_task_output_text(output)
                already_streamed = bool(streamed_tasks and task_name in streamed_tasks)

                if not already_streamed:
                    if task_text:
                        has_task_content = True
                        events.append(
                            self._build_response_event(
                                sid,
                                task_name,
                                delta=task_text,
                            )
                        )
                    else:
                        logger.warning(
                            "Task '%s' completed with no usable output "
                            "(raw output was ReAct noise or empty)",
                            task_name,
                        )
                        fallback_msg = (
                            "*This step did not produce results.* "
                            "The agent may not have executed its tool "
                            "correctly. You can try rephrasing your request."
                        )
                        events.append(
                            self._build_response_event(
                                sid,
                                task_name,
                                delta=fallback_msg,
                            )
                        )

                events.append(
                    self._build_response_event(
                        sid,
                        task_name,
                        delta="",
                        status="completed",
                    )
                )

                events.append(self._sse("node_completed", {"node": task_name}, sid))
                if dedup:
                    dedup.reset_for_new_task()

                for tid in task_ids:
                    if tid not in started_nodes and tid not in completed_nodes:
                        events.append(self._sse("node_started", {"node": tid}, sid))
                        started_nodes.add(tid)
                        break
        return events, has_task_content

    async def _build_kickoff_inputs(self, agent: Any, user_text: str) -> Dict[str, Any]:
        """Build kickoff inputs, using LLM extraction when input_fields exist."""
        kickoff_inputs: Dict[str, Any] = {"user_input": user_text}
        graph_config = getattr(agent, "graph_config", None) or {}
        if not isinstance(graph_config, dict):
            return kickoff_inputs

        input_fields = graph_config.get("input_fields")
        if not isinstance(input_fields, dict) or not input_fields:
            return kickoff_inputs

        merged = dict(input_fields)
        merged["user_input"] = user_text

        extracted = await self._extract_input_fields(user_text, input_fields)
        if extracted:
            merged.update(extracted)
            logger.info("Extracted input fields from user message: %s", extracted)

        return merged

    async def stream(
        self,
        agent: Any,
        session_id: str,
        prompt: Any,
    ) -> AsyncIterator[str]:
        """Stream a response using CrewAI with stream=True and akickoff().

        Emits per-task ``node_started`` / ``node_completed`` lifecycle events
        so the frontend renders output in expandable sections (same pattern as
        the LangGraph vacation planner).  For multi-agent crews, the task
        callback tracks transitions; for single-agent crews a single synthetic
        ``crewai_task`` node is used.
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

            # -- Per-task event tracking via task_callback --------------------
            task_event_queue: deque = deque()

            def _on_task_done(output: Any) -> None:
                task_event_queue.append(output)

            logger.info("Building CrewAI crew for session %s", sid)
            crew, task_ids = await self._build_crew(agent, task_callback=_on_task_done)

            # -- Build kickoff inputs with LLM extraction ---------------------
            kickoff_inputs = await self._build_kickoff_inputs(agent, text)

            # Node lifecycle tracking (supports parallel async tasks)
            started_nodes: set = set()
            completed_nodes: set = set()
            if task_ids:
                yield self._sse("node_started", {"node": task_ids[0]}, sid)
                started_nodes.add(task_ids[0])

            logger.info("Starting CrewAI kickoff for session %s", sid)
            result = await crew.kickoff_async(inputs=kickoff_inputs)

            logger.info(
                "CrewAI kickoff returned type=%s for session %s",
                type(result).__name__,
                sid,
            )

            has_streamed_output = False
            dedup = _StreamDeduplicator()
            tasks_with_stream_content: set = set()

            async for event, has_text_delta in self._stream_result_chunks(
                result,
                sid,
                task_ids,
                started_nodes,
                completed_nodes,
                dedup=dedup,
                streamed_tasks=tasks_with_stream_content,
            ):
                drain_events, had_task_content = self._drain_task_events(
                    task_event_queue,
                    task_ids,
                    started_nodes,
                    completed_nodes,
                    sid,
                    dedup=dedup,
                    streamed_tasks=tasks_with_stream_content,
                )
                for node_event in drain_events:
                    yield node_event
                if had_task_content:
                    has_streamed_output = True

                if has_text_delta:
                    has_streamed_output = True
                yield event

            # Drain any remaining task events after the stream ends
            drain_events, had_task_content = self._drain_task_events(
                task_event_queue,
                task_ids,
                started_nodes,
                completed_nodes,
                sid,
                dedup=dedup,
                streamed_tasks=tasks_with_stream_content,
            )
            for node_event in drain_events:
                yield node_event
            if had_task_content:
                has_streamed_output = True

            # Close any nodes that started but never got a completion callback
            for tid in task_ids:
                if tid in started_nodes and tid not in completed_nodes:
                    yield self._sse("node_completed", {"node": tid}, sid)

            if not has_streamed_output:
                fallback_id = task_ids[-1] if task_ids else "crewai_task"
                async for event in self._emit_fallback_result(result, sid, fallback_id):
                    yield event

            yield self._done_event()

            await self._update_session_title(session_id, prompt)

        except Exception as e:
            logger.exception("Error in CrewAI stream for session %s: %s", sid, e)
            yield self._sse("error", {"message": f"Error: {str(e)}"}, sid)
            yield self._done_event()
