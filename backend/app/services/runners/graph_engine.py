"""
Declarative graph engine for LangGraph agents.

Parses a graph config (YAML-style dict) and executes a DAG of typed nodes
using LangGraph's StateGraph. Adapted from the vacation-planner POC with:

  * Async execution throughout (httpx for MCP, ChatOpenAI for LLM)
  * SSE event yielding compatible with the BaseRunner interface
  * Reuse of the existing LLM configuration from LangGraphRunner

Supported node types
--------------------
  llm          - Call the LLM with a rendered prompt template
  mcp_tool     - Call a single MCP tool via JSON-RPC over HTTP
  mcp_tool_map - Fan-out: call an MCP tool once per item from a prior node's output
  router       - Conditional edge based on a prior node's output

State flows between nodes via ``outputs[node_id] = result``.
Templates use ``{inputs.field}`` and ``{outputs.node_id}`` for substitution.
"""

from __future__ import annotations

import json
import logging
import operator
import os
import re
from typing import Annotated, Any, AsyncIterator, Dict, List, Optional, Tuple, TypedDict

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variable expansion  (${VAR:default})
# ---------------------------------------------------------------------------

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::([^}]*))?\}")


def _expand_env(value: Any) -> Any:
    """Recursively expand ``${VAR:default}`` patterns in strings."""
    if isinstance(value, str):

        def _repl(m: re.Match) -> str:
            var = m.group(1)
            default = m.group(2) if m.group(2) is not None else ""
            return os.getenv(var, default)

        return _ENV_PATTERN.sub(_repl, value)
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------------------
# Template rendering helpers
# ---------------------------------------------------------------------------


class _DotDict(dict):
    """Dict subclass allowing attribute access (returns '' for missing keys)."""

    def __getattr__(self, name: str) -> Any:
        return self.get(name, "")

    def __getitem__(self, key: str) -> Any:
        return self.get(key, "")


def _render_template(value: Any, context: Dict[str, Any]) -> Any:
    """Recursively render ``{inputs.x}`` / ``{outputs.y}`` in strings."""
    if isinstance(value, str):
        try:
            return value.format_map(context)
        except (KeyError, IndexError):
            return value
    if isinstance(value, list):
        return [_render_template(v, context) for v in value]
    if isinstance(value, dict):
        return {k: _render_template(v, context) for k, v in value.items()}
    return value


def _get_path(data: Dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path like ``outputs.places_list_task``."""
    if not path:
        return ""
    parts = path.split(".")
    cursor: Any = data
    for part in parts:
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return ""
    return cursor


_MD_FENCE_RE = re.compile(r"```(?:\w*)\s*\n?(.*?)```", re.DOTALL)


def _coerce_list(value: Any) -> List[str]:
    """Coerce a value (JSON array string, CSV, newline-separated) to a list.

    Handles markdown-fenced JSON that LLMs commonly produce, e.g.::

        Here are 5 places...
        ```json
        ["Shibuya", "Asakusa", ...]
        ```
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        # Try parsing the whole string as JSON first
        parsed_list = _try_parse_json_list(raw)
        if parsed_list is not None:
            return parsed_list
        # Strip markdown code fences and try the inner content
        fence_match = _MD_FENCE_RE.search(raw)
        if fence_match:
            inner = fence_match.group(1).strip()
            parsed_list = _try_parse_json_list(inner)
            if parsed_list is not None:
                return parsed_list
        # Fallback: newline-separated items
        if "\n" in raw:
            return [
                line.strip("- ").strip() for line in raw.splitlines() if line.strip()
            ]
        return [item.strip() for item in raw.split(",") if item.strip()]
    if value is None:
        return []
    return [str(value).strip()]


def _try_parse_json_list(text: str) -> Optional[List[str]]:
    """Try to parse text as a JSON array and return a list of strings."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            items = []
            for v in parsed:
                if isinstance(v, dict):
                    items.append(v.get("name", str(v)))
                elif v is not None:
                    s = str(v).strip()
                    if s:
                        items.append(s)
            return items if items else None
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _normalize_arg(value: Any) -> Any:
    """Normalize string values to native Python types where possible."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in ("true", "false"):
            return stripped.lower() == "true"
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
        if re.fullmatch(r"-?\d+\.\d+", stripped):
            return float(stripped)
        return stripped
    if isinstance(value, list):
        return [_normalize_arg(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_arg(v) for k, v in value.items()}
    return value


def _sanitize_args(value: Any) -> Any:
    """Normalize and drop empty/None values from arg dicts."""
    normalized = _normalize_arg(value)
    if isinstance(normalized, dict):
        return {k: v for k, v in normalized.items() if v not in ("", None)}
    return normalized


# ---------------------------------------------------------------------------
# MCP protocol helpers (async, using httpx)
# ---------------------------------------------------------------------------

_MCP_SESSIONS: Dict[str, str] = {}
_TOOL_SCHEMAS: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _parse_mcp_result(payload: Any) -> str:
    """Extract text from an MCP tools/call result payload."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            texts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            joined = "\n".join([t for t in texts if t])
            if joined:
                return joined
        for key in ("output", "result", "raw"):
            if key in payload and isinstance(payload[key], str):
                return payload[key]
        return json.dumps(payload, indent=2)
    return str(payload)


def _parse_sse_json(text: str) -> Dict[str, Any]:
    """Parse the last ``data:`` payload from an SSE text stream."""
    data_payloads = []
    for line in text.splitlines():
        if line.startswith("data:"):
            data = line[len("data:") :].strip()
            if data:
                data_payloads.append(data)
    if not data_payloads:
        raise ValueError("No JSON data found in SSE response")
    return json.loads(data_payloads[-1])


def _parse_mcp_response(response: httpx.Response) -> Dict[str, Any]:
    """Parse an MCP response (JSON or SSE)."""
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        return _parse_sse_json(response.text)
    return response.json()


def _extract_session_id(response: httpx.Response) -> str:
    """Extract MCP session ID from response headers or JSON body."""
    for key, value in response.headers.items():
        if key.lower() == "mcp-session-id":
            return value
    try:
        data = response.json()
    except (ValueError, json.JSONDecodeError):
        return ""
    if isinstance(data, dict):
        result = data.get("result") or {}
        if isinstance(result, dict):
            return str(result.get("sessionId") or "")
    return ""


async def _initialize_mcp_session(client: httpx.AsyncClient, url: str) -> str:
    """Send MCP ``initialize`` JSON-RPC and return the session ID."""
    logger.info("Initializing MCP session: %s", url)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "langgraph-graph-engine", "version": "1.0"},
            "capabilities": {},
        },
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code >= 400:
            logger.warning("MCP initialize failed %s: %s", resp.status_code, resp.text)
            return ""
        return _extract_session_id(resp)
    except Exception as e:
        logger.warning("MCP initialize error for %s: %s", url, e)
        return ""


async def _get_mcp_session(client: httpx.AsyncClient, url: str) -> str:
    """Get or create an MCP session for the given URL."""
    if url in _MCP_SESSIONS:
        return _MCP_SESSIONS[url]
    session_id = await _initialize_mcp_session(client, url)
    if session_id:
        _MCP_SESSIONS[url] = session_id
        logger.info("MCP session established: %s", session_id)
    return session_id


async def _refresh_mcp_session(client: httpx.AsyncClient, url: str) -> str:
    """Clear and re-initialize an MCP session."""
    _MCP_SESSIONS.pop(url, None)
    _TOOL_SCHEMAS.clear()
    return await _get_mcp_session(client, url)


async def _list_mcp_tools(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Discover available tools from an MCP server."""
    session_id = await _get_mcp_session(client, url)
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code >= 400:
            logger.warning("tools/list failed %s: %s", resp.status_code, resp.text)
            return {}
        data = _parse_mcp_response(resp)
        return data.get("result", {}) if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("tools/list error for %s: %s", url, e)
        return {}


async def _get_tool_input_schema(
    client: httpx.AsyncClient, url: str, tool_name: str
) -> Dict[str, Any]:
    """Get the input schema for a specific MCP tool (cached)."""
    key = (url, tool_name)
    if key in _TOOL_SCHEMAS:
        return _TOOL_SCHEMAS[key]
    result = await _list_mcp_tools(client, url)
    tools = result.get("tools", []) if isinstance(result, dict) else []
    for tool in tools:
        if isinstance(tool, dict) and tool.get("name") == tool_name:
            schema = tool.get("inputSchema") or {}
            if isinstance(schema, dict):
                _TOOL_SCHEMAS[key] = schema
                return schema
    _TOOL_SCHEMAS[key] = {}
    return {}


async def _filter_args_to_schema(
    client: httpx.AsyncClient,
    url: str,
    tool_name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """Drop args not in the tool's input schema (prevents -32602 errors)."""
    schema = await _get_tool_input_schema(client, url, tool_name)
    props = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(props, dict) or not props:
        return args
    allowed = set(props.keys())
    filtered = {k: v for k, v in args.items() if k in allowed}
    dropped = sorted([k for k in args if k not in allowed])
    if dropped:
        logger.info("Filtered MCP args for %s (dropped: %s)", tool_name, dropped)
    return filtered


async def _call_mcp_tool(
    client: httpx.AsyncClient,
    url: str,
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """Call an MCP tool via JSON-RPC over HTTP."""
    if not url:
        return "MCP server URL is missing."

    logger.info("MCP tool call: %s -> %s args=%s", url, tool_name, arguments)

    session_id = await _get_mcp_session(client, url)
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=60)

        _resp_lower = resp.text.lower()
        if resp.status_code in (400, 404) and ("session" in _resp_lower):
            logger.warning("MCP session invalid, refreshing: %s", url)
            session_id = await _refresh_mcp_session(client, url)
            if session_id:
                headers["Mcp-Session-Id"] = session_id
            resp = await client.post(url, json=payload, headers=headers, timeout=60)

        if resp.status_code >= 400:
            logger.warning("MCP tool call failed %s: %s", resp.status_code, resp.text)
            return f"MCP error {resp.status_code}: {resp.text}"

        data = _parse_mcp_response(resp)
        if isinstance(data, dict) and "error" in data:
            logger.error("MCP tool error: %s", data["error"])
            return f"MCP tool error: {data['error']}"

        if isinstance(data, dict):
            return _parse_mcp_result(data.get("result", ""))
        return _parse_mcp_result(data)

    except Exception as e:
        logger.exception("MCP tool call exception for %s: %s", tool_name, e)
        return f"MCP call error: {e}"


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


def _merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer: merge two dicts (used for parallel node output merging)."""
    merged = dict(a)
    merged.update(b)
    return merged


class GraphState(TypedDict, total=False):
    """State passed between nodes in the declarative graph."""

    inputs: Dict[str, Any]
    outputs: Annotated[Dict[str, str], _merge_dicts]
    tasks_output: Annotated[List[Dict[str, Any]], operator.add]


# ---------------------------------------------------------------------------
# Graph engine
# ---------------------------------------------------------------------------


_OUTPUT_REF_RE = re.compile(r"outputs\.(\w+)")


def _extract_output_deps(step: dict) -> set:
    """Return the set of node IDs this step depends on via template references.

    Scans ``prompt``, ``query_template``, ``items_path``, and ``args`` values
    for ``{outputs.node_id}`` / ``outputs.node_id`` patterns.  Also honours
    an explicit ``depends_on`` list in the step config.
    """
    refs: set = set()
    for key in ("prompt", "query_template", "items_path"):
        val = step.get(key, "")
        if isinstance(val, str):
            refs.update(m.group(1) for m in _OUTPUT_REF_RE.finditer(val))
    args = step.get("args") or {}
    if isinstance(args, dict):
        for val in args.values():
            if isinstance(val, str):
                refs.update(m.group(1) for m in _OUTPUT_REF_RE.finditer(val))
    depends_on = step.get("depends_on") or []
    if isinstance(depends_on, list):
        refs.update(str(d) for d in depends_on)
    return refs


class GraphEngine:
    """
    Builds and executes a declarative LangGraph agent from a config dict.

    Parameters
    ----------
    config : dict
        The graph configuration (same schema as graph.yaml).
    llm : ChatOpenAI
        Pre-configured LLM instance from LangGraphRunner.
    """

    def __init__(self, config: Dict[str, Any], llm: Any) -> None:
        cfg = _expand_env(config)
        self.mcp_cfg = cfg.get("mcp") or {}
        self.llm = llm
        nodes = cfg.get("nodes") or cfg.get("steps") or []
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("Graph config must define a non-empty 'nodes' list")
        self.nodes = nodes
        self.edges = cfg.get("edges") or []
        self.entry_id: Optional[str] = cfg.get("entry")

    def _build_graph(self):
        """Build a compiled LangGraph StateGraph from the config."""
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(GraphState)
        node_defs: Dict[str, dict] = {}

        for step in self.nodes:
            if not isinstance(step, dict) or "id" not in step:
                raise ValueError("Each node must be a mapping with an 'id'")
            step_id = str(step["id"])
            node_defs[step_id] = step
            graph.add_node(step_id, self._make_step_fn(step))

        if self.edges:
            # --- Explicit edges from config ---
            if not isinstance(self.edges, list):
                raise ValueError("'edges' must be a list")
            has_start = False
            for edge in self.edges:
                if not isinstance(edge, dict):
                    raise ValueError("Each edge must be a mapping")
                src = str(edge.get("from", "")).strip()
                dst = str(edge.get("to", "")).strip()
                if not src or not dst:
                    raise ValueError("Each edge must define 'from' and 'to'")
                src_def = node_defs.get(src, {})
                if str(src_def.get("type", "")).strip().lower() == "router":
                    continue
                graph.add_edge(src, dst)
                if src == "__start__":
                    has_start = True
            if not has_start:
                entry_id = self.entry_id or str(self.nodes[0]["id"])
                graph.add_edge(START, entry_id)

            for step_id, step in node_defs.items():
                if str(step.get("type", "")).strip().lower() != "router":
                    continue
                router = self._build_router(step)
                graph.add_conditional_edges(step_id, router["fn"], router["routes"])
        else:
            # --- Auto-analyse data dependencies for parallel fan-out ---
            node_ids = [str(s["id"]) for s in self.nodes]
            deps: Dict[str, set] = {
                nid: _extract_output_deps(step)
                for nid, step in zip(node_ids, self.nodes)
            }
            # Only keep deps that reference nodes in this graph
            valid_ids = set(node_ids)
            deps = {nid: d & valid_ids for nid, d in deps.items()}

            for nid in node_ids:
                if deps[nid]:
                    for dep in deps[nid]:
                        graph.add_edge(dep, nid)
                else:
                    graph.add_edge(START, nid)

            depended_on: set = set()
            for d in deps.values():
                depended_on.update(d)
            for nid in node_ids:
                if nid not in depended_on:
                    graph.add_edge(nid, END)

            _topo_info = {
                "deps": {k: sorted(v) for k, v in deps.items() if v},
                "entry_nodes": [n for n in node_ids if not deps[n]],
                "terminal_nodes": [n for n in node_ids if n not in depended_on],
            }
            logger.info("Auto-built graph topology: %s", _topo_info)

        return graph.compile()

    @staticmethod
    def _build_router(step: dict) -> Dict[str, Any]:
        """Build a conditional routing function for a router node."""
        route_on = str(step.get("route_on", "")).strip()
        routes = step.get("routes") or {}
        if not route_on or not isinstance(routes, dict):
            raise ValueError("Router node requires 'route_on' and 'routes' mapping")

        def _route(state: GraphState) -> str:
            inputs = state.get("inputs") or {}
            outputs = state.get("outputs") or {}
            value = _get_path({"inputs": inputs, "outputs": outputs}, route_on)
            value_str = str(value)
            if value_str in routes:
                return str(routes[value_str])
            return str(routes.get("default", ""))

        return {"fn": _route, "routes": routes}

    def _make_step_fn(self, step: dict):
        """Create a node function for the given step config.

        Returns a partial state update (not the full state) so that
        LangGraph's reducers can merge outputs from parallel nodes.
        """
        step_id = str(step["id"])
        step_type = str(step.get("type", "")).strip().lower()
        mcp_servers = self.mcp_cfg.get("servers") or {}
        mcp_transport = str(self.mcp_cfg.get("transport") or "streamable-http").lower()
        llm = self.llm

        async def _run(state: GraphState) -> dict:
            inputs = state.get("inputs") or {}
            outputs = state.get("outputs") or {}

            logger.info("Graph node started: %s (%s)", step_id, step_type)

            result = ""

            if step_type in ("llm", "prompt"):
                result = await _run_llm_node(llm, step, inputs, outputs)

            elif step_type in ("mcp_tool", "mcp"):
                result = await _run_mcp_tool_node(
                    step, inputs, outputs, mcp_servers, mcp_transport
                )

            elif step_type in ("mcp_tool_map", "mcp_map"):
                result = await _run_mcp_tool_map_node(
                    step, inputs, outputs, mcp_servers, mcp_transport
                )

            elif step_type == "router":
                result = "Router node evaluated."

            else:
                result = f"Unsupported node type: {step_type}"

            logger.info("Graph node completed: %s", step_id)
            return {
                "outputs": {step_id: result},
                "tasks_output": [
                    {
                        "name": step_id,
                        "summary": _summarize_output(result),
                        "raw": result,
                    }
                ],
            }

        return _run

    async def run_streaming(
        self,
        inputs: Dict[str, Any],
        session_id: str,
    ) -> AsyncIterator[str]:
        """
        Execute the compiled graph via ``astream`` and yield SSE events
        as each node completes.  Parallel nodes execute concurrently;
        their results appear as soon as each finishes.
        """
        graph = self._build_graph()
        state: GraphState = {
            "inputs": inputs,
            "outputs": {},
            "tasks_output": [],
        }

        total_tasks = 0

        async for chunk in graph.astream(state, stream_mode="updates"):
            for node_name, node_state in chunk.items():
                if node_name in ("__start__", "__end__"):
                    continue

                tasks = node_state.get("tasks_output", [])
                for task in tasks:
                    task_name = task.get("name", node_name)
                    yield _sse("node_started", {"node": task_name}, session_id)

                    raw = task.get("raw", "")
                    if raw:
                        yield _sse(
                            "response",
                            {
                                "delta": raw,
                                "status": "in_progress",
                                "id": task_name,
                            },
                            session_id,
                        )

                    yield _sse("node_completed", {"node": task_name}, session_id)
                    total_tasks += 1

        if total_tasks > 0:
            yield _sse(
                "response",
                {"delta": "", "status": "completed", "id": "graph_final"},
                session_id,
            )
        else:
            yield _sse(
                "error",
                {"message": "Graph produced no output."},
                session_id,
            )


# ---------------------------------------------------------------------------
# Node execution functions
# ---------------------------------------------------------------------------


async def _run_llm_node(
    llm: Any,
    step: dict,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
) -> str:
    """Execute an LLM node: render the prompt and call the model."""
    prompt_template = step.get("prompt", "Provide a response.")
    context = {
        "inputs": _DotDict(inputs),
        "outputs": _DotDict(outputs),
    }
    rendered_prompt = _render_template(str(prompt_template), context)

    content = (
        f"{rendered_prompt}\n\n"
        f"Inputs:\n{json.dumps(inputs, indent=2)}\n\n"
        f"Outputs so far:\n{json.dumps(outputs, indent=2)}\n"
    )

    try:
        response = await llm.ainvoke([{"role": "user", "content": content}])
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.exception("LLM node error: %s", e)
        return f"LLM error: {e}"


async def _run_mcp_tool_node(
    step: dict,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    mcp_servers: Dict[str, Any],
    mcp_transport: str,
) -> str:
    """Execute an MCP tool node: call a single tool with rendered args."""
    server_name = step.get("server", "")
    tool_name = step.get("tool", "")
    server_cfg = mcp_servers.get(server_name, {}) if server_name else {}
    url = str(server_cfg.get("url", "")).strip()
    transport = str(server_cfg.get("transport", mcp_transport)).lower()

    if transport not in ("streamable-http", "http", "streamable"):
        return f"Unsupported MCP transport: {transport}"
    if not tool_name:
        return "Missing tool name for MCP node."

    context = {"inputs": _DotDict(inputs), "outputs": _DotDict(outputs)}
    raw_args = step.get("args") or {}
    args = _render_template(raw_args, context)

    if isinstance(args, dict):
        for key, value in list(args.items()):
            if value in ("", None) and key in inputs:
                args[key] = inputs.get(key)

    args = _sanitize_args(args)

    async with httpx.AsyncClient() as client:
        if isinstance(args, dict):
            args = await _filter_args_to_schema(client, url, str(tool_name), args)
        return await _call_mcp_tool(
            client, url, str(tool_name), args if isinstance(args, dict) else {}
        )


async def _run_mcp_tool_map_node(
    step: dict,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    mcp_servers: Dict[str, Any],
    mcp_transport: str,
) -> str:
    """Execute an MCP tool map node: fan-out over a list of items."""
    server_name = step.get("server", "")
    tool_name = step.get("tool", "")
    server_cfg = mcp_servers.get(server_name, {}) if server_name else {}
    url = str(server_cfg.get("url", "")).strip()
    transport = str(server_cfg.get("transport", mcp_transport)).lower()

    if transport not in ("streamable-http", "http", "streamable"):
        return f"Unsupported MCP transport: {transport}"
    if not tool_name:
        return "Missing tool name for MCP map node."

    items_path = str(step.get("items_path", "")).strip()
    items_value = _get_path({"inputs": inputs, "outputs": outputs}, items_path)
    items = _coerce_list(items_value)
    max_items = int(step.get("max_items", 5) or 5)
    items = items[:max_items]

    if not items:
        return "No items to iterate for MCP map node."

    results = []
    async with httpx.AsyncClient() as client:
        for idx, item in enumerate(items, start=1):
            context = {
                "inputs": _DotDict(inputs),
                "outputs": _DotDict(outputs),
                "item": item,
                "item_index": idx,
            }
            query_template = step.get("query_template")
            if query_template:
                raw_args = {
                    "query": query_template,
                    "max_results": step.get("max_results", 5),
                }
            else:
                raw_args = step.get("args") or {}

            args = _render_template(raw_args, context)
            if isinstance(args, dict):
                for key, value in list(args.items()):
                    if value in ("", None) and key in inputs:
                        args[key] = inputs.get(key)
            args = _sanitize_args(args)
            if isinstance(args, dict):
                args = await _filter_args_to_schema(client, url, str(tool_name), args)
            item_result = await _call_mcp_tool(
                client,
                url,
                str(tool_name),
                args if isinstance(args, dict) else {},
            )
            results.append(f"#{idx} {item}\n{item_result}")

    return "\n\n".join(results)


# ---------------------------------------------------------------------------
# SSE / summary helpers
# ---------------------------------------------------------------------------


def _sse(event_type: str, data: dict, session_id: str) -> str:
    """Create an SSE-formatted event string."""
    payload = {"type": event_type, "session_id": str(session_id), **data}
    return f"data: {json.dumps(payload)}\n\n"


def _summarize_output(text: str) -> str:
    """One-line summary of a node's output."""
    if not text:
        return "No output"
    first_line = text.splitlines()[0].strip()
    return first_line if first_line else "Output generated"
