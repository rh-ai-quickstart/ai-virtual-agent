# LangGraph & CrewAI Agent Runners: Plan and Comparison

## Reference: vacation-planner **langgraph-implementation** branch

**Primary reference:** [vacation-planner](https://github.com/skattoju/vacation-planner) repo, **branch `langgraph-implementation`** (`git@github.com:skattoju/vacation-planner.git`). That branch implements **both** CrewAI and **LangGraph**; we use it as the reference for how LangGraph agents are implemented (declarative graph, MCP integration, job-based async). The same repo’s main branch is CrewAI-only.

---

## 1. Vacation-planner langgraph-implementation branch – LangGraph reference

On the **langgraph-implementation** branch, LangGraph is implemented as follows:

| Aspect | How it works |
|--------|----------------|
| **Entry point** | `backend/agent/langgraph/runner.py` — `LangGraphPlanner` class loads YAML config, builds a `StateGraph(PlannerState)`, compiles and runs it. |
| **Config** | Declarative `backend/agent/langgraph/config/graph.yaml`: `name`, `mcp.servers` (urls, transport), `nodes` (id, type, type-specific fields), optional `edges` and `entry`. |
| **State** | `PlannerState`: `inputs`, `outputs` (per-node results), `tasks_output` (list of `{name, summary, raw}`). |
| **Node types** | `llm` (OpenAI prompt with `{inputs.*}` / `{outputs.*}`), `mcp_tool` (single MCP tool call), `mcp_tool_map` (iterate over list, call MCP tool per item), `router` (conditional edges via `route_on` + `routes`). |
| **MCP** | Streamable-HTTP MCP client in runner: session init, `tools/list` (schema cache), `tools/call`; args filtered to tool schema to avoid strict-server errors. |
| **Invocation** | `planner.run(inputs)` — sync `graph.invoke(state)`; optional `on_node_complete(step_id, result, outputs, tasks_output)` callback for partial results. |
| **API** | `POST /langgraph/plan/start` → returns `job_id`; background thread runs `LangGraphPlanner(config_path, on_node_complete=...)`; `GET /langgraph/plan/status/{job_id}` returns `logs`, `done`, `result`, **`partial_result`** (updated each node), `error`. |
| **Input shape** | Structured (same `PlanRequest` as CrewAI: destination, dates, budget, preferences, etc.). |
| **Streaming** | No token-level streaming; partial progress via `partial_result.tasks_output` on each node completion. |

**Patterns:** `backend/agent/langgraph/PATTERNS.md` documents sequential pipeline, router, fan-out/fan-in, etc., using the same `graph.yaml` format.

**CrewAI on the same branch:** Still present under `agent/crewai/` (crew.py, agents.yaml, tasks.yaml); `/plan` and `/plan/start` use CrewAI; LangGraph is an additional backend via `/langgraph/plan/start` and `/langgraph/plan/status/{job_id}`.

---

## 2. Vacation-planner – CrewAI (same branch or main)

| Aspect | How it works |
|--------|----------------|
| **Framework** | CrewAI (`crewai[tools]==1.4.1`). Single `AgenticAi` crew in `agent/crewai/crew.py`. |
| **Config** | `crew.yaml`, `agents.yaml`, `tasks.yaml`; agents/tasks defined in code + YAML. |
| **Invocation** | `AgenticAi().crew().kickoff(inputs=...)` — synchronous, no streaming. |
| **API** | `POST /plan`, `POST /plan/start`, `GET /plan/status/{job_id}` (thread + in-memory `JOBS`). |
| **Input/Output** | Same structured `PlanRequest`; final result only (no partial_result). |

---

## 3. Our ai-virtual-agent (current) approach – summary

| Aspect | How it works |
|--------|----------------|
| **Framework** | LlamaStack only (Responses API + Conversations). |
| **Agent definition** | DB-backed virtual agents (name, model, prompt, tools, KBs, shields); optional templates. |
| **Invocation** | `client.responses.create(model=..., input=..., conversation=..., stream=True)` per user message. |
| **API** | `POST /chat` with SSE stream; session id and message content; conversation history in LlamaStack. |
| **Session / history** | LlamaStack conversation_id per chat session; history managed by LlamaStack. |
| **Input shape** | Free-form chat (text + optional multimodal); OpenAI-style content items. |
| **Output** | SSE stream: reasoning, output text, tool calls; aggregated and normalized for frontend. |
| **Tools** | From agent config (MCP, RAG, etc.); built per request and passed to LlamaStack. |

---

## 4. Pros and cons

### Vacation-planner LangGraph (langgraph-implementation branch)

**Pros**

- **Declarative graph:** `graph.yaml` defines nodes (llm, mcp_tool, mcp_tool_map, router) and edges; no graph code per use case.
- **MCP-first:** Tools come from MCP servers (streamable-http); session init, schema caching, arg filtering; same MCP servers can be shared with CrewAI.
- **Partial progress:** `on_node_complete` callback updates job `partial_result` so the frontend can show tasks as they complete.
- **Patterns:** Router, map-reduce, sequential pipeline documented in PATTERNS.md using the same YAML.
- **Single runner class:** `LangGraphPlanner(config_path, on_node_complete)` builds and runs the graph; easy to plug into our runner abstraction.

**Cons**

- **No token streaming:** Only node-level progress; no LLM token stream.
- **Job-based async:** Thread + in-memory `LANGGRAPH_JOBS`; not durable or horizontally scalable.
- **Structured input only:** Expects a flat dict (e.g. destination, dates); no free-form chat history in the reference.

### Vacation-planner CrewAI (same branch or main)

**Pros**

- **Simple surface:** One crew, one `kickoff()`; YAML agents/tasks.
- **Structured inputs:** Typed trip params; optional `/parse` for natural language.
- **No LlamaStack:** Runs with CrewAI + LLM + tools only.

**Cons**

- **No streaming:** Full run only; no partial_result in the same way as LangGraph job.
- **No conversation model:** Each request is a new run.
- **Background jobs:** Thread + in-memory `JOBS`; same scalability limits as LangGraph jobs.

### Our (ai-virtual-agent) approach

**Pros**

- **Streaming:** Token-level (and reasoning/tool) streaming; better perceived latency and UX.
- **Conversation:** Session + history; true multi-turn chat.
- **Multi-tenant, multi-agent:** Many virtual agents from DB/templates; different models, prompts, tools per agent.
- **Unified chat API:** Same `/chat` + SSE contract regardless of which virtual agent is used.
- **Pluggable tools/KB:** MCP, RAG, shields; validation and config in one place.

**Cons**

- **Single runner today:** Only LlamaStack; adding CrewAI/LangGraph requires design work.
- **Tight coupling to LlamaStack:** Session (conversation_id), events (StreamAggregator), tools format are LlamaStack-specific.
- **Less “workflow” visibility:** No explicit task graph or steps in the product; it’s one black-box response stream.

---

## 5. What we take from vacation-planner langgraph-implementation branch

- **LangGraph runner pattern:** A single class (`LangGraphPlanner`) that loads a declarative graph config (YAML), builds `StateGraph`, and runs it with `invoke()`; optional `on_node_complete` for partial results. We can implement our LangGraph runner similarly, with graph config from agent/template or a path.
- **Declarative graph.yaml:** Node types (`llm`, `mcp_tool`, `mcp_tool_map`, `router`) and MCP server definitions in YAML; we can support the same schema or a subset so that graphs developed in vacation-planner can be reused or adapted.
- **MCP in LangGraph:** Their runner does MCP session init, `tools/list` (with schema cache), and `tools/call` with arg filtering; we already have MCP via LlamaStack but for LangGraph we may need an in-process MCP client like theirs or reuse existing infra.
- **Runner abstraction:** Treat LangGraph (and CrewAI) as another “runner” behind a common interface; same chat/SSE contract where possible. We keep our streaming and sessions; for long graph runs we can optionally adopt a job + `partial_result` pattern similar to their `/langgraph/plan/status`.
- **Structured inputs where useful:** The reference uses structured inputs only; we can keep free-form chat as primary and allow agent/template config to define an optional input schema or parser for graph/crew inputs.

---

## 6. Replan: LangGraph and CrewAI in ai-virtual-agent

### 6.1 Goals

- Support **LangGraph** and **CrewAI** as additional agent runners alongside LlamaStack.
- Keep a **single chat UX:** same `/chat` + SSE stream where possible; optional “job” pattern for long CrewAI runs if needed later.
- Allow **per-agent runner selection** (e.g. `runner_type`: `llamastack` | `langgraph` | `crewai`).

### 6.2 High-level design

1. **Runner type on agent (or template)**
   Add `runner_type` (or `agent_framework`) to `VirtualAgent` and/or `AgentTemplate` so the backend knows which runner to use.

2. **Runner abstraction**
   Define a small interface, e.g.:
   - `get_or_create_session(session_id, ...) -> runner_session_id`
   - `stream(agent, session_id, prompt, **kwargs) -> AsyncIterator[events]`
   Events are normalized (e.g. `{ "type": "text_delta" | "reasoning" | "tool_call" | "done" | "error", ... }`) so the frontend stays unchanged.

3. **Implementations**
   - **LlamaStack runner:** Current logic in `ChatService` (and helpers like `_get_or_create_conversation`, `build_responses_tools`, `StreamAggregator`) moves behind this interface.
   - **LangGraph runner:** New module that builds a graph (or loads from config), invokes it with the current message (and optional history), and maps LangGraph stream events to our normalized events.
   - **CrewAI runner:** New module that builds a crew (from agent/template config or a predefined crew id), runs it (prefer async/streaming if the framework supports it), and maps output to normalized events; if only sync is available, we can buffer and “stream” the final result or add an optional job endpoint later.

4. **Session and history**
   - LlamaStack: keep `conversation_id` as today.
   - LangGraph: use LangGraph’s thread/checkpointing if available; store `langgraph_thread_id` (or similar) on `ChatSession`.
   - CrewAI: no native conversation; either no history per “session” or we maintain a short history in our DB and inject it as context into the crew input.

5. **Config and dependencies**
   - Add settings for LangGraph (e.g. optional server URL or in-process) and CrewAI (e.g. default LLM, API keys).
   - Add optional deps: `langgraph`, `langgraph-sdk` and/or `crewai` (and `crewai-tools` if needed).

### 6.3 Files to touch (recap from earlier plan)

| Area | Files | Change |
|------|--------|--------|
| **Data model** | `backend/app/models/agent.py`, `backend/app/schemas/agent.py` | Add `runner_type` (and optional runner-specific config). |
| **Chat flow** | `backend/app/services/chat.py`, `backend/app/api/v1/chat.py` | Introduce runner abstraction; branch or delegate by `runner_type`. |
| **LlamaStack** | `backend/app/api/llamastack.py` | Remain as-is or become one implementation of the runner interface. |
| **New runners** | New: e.g. `backend/app/services/runners/langgraph_runner.py`, `crewai_runner.py` | Implement stream (and session) interface; map framework events to normalized SSE. |
| **Sessions** | `backend/app/models/chat.py`, `backend/app/api/v1/chat_sessions.py` | Optional: store runner-specific session id (e.g. `langgraph_thread_id`); list/history may need to branch by runner. |
| **KB/tools** | `backend/app/api/v1/virtual_agents.py`, `backend/app/services/chat.py` | KB validation and tool building: only for LlamaStack today; for CrewAI/LangGraph, add or skip as needed. |
| **Config** | `backend/app/config.py` | Add LangGraph and CrewAI settings. |

### 6.4 LangGraph-specific notes (reference: langgraph-implementation branch)

- **Graph definition:** Follow vacation-planner’s approach: **declarative YAML** (e.g. `graph.yaml`) with `nodes` (id, type: llm | mcp_tool | mcp_tool_map | router), `mcp.servers`, optional `edges` and `entry`. Agent or template can reference a graph config path or embed graph config. Alternatively, one or more predefined graphs in code; start with YAML-driven for parity with the reference.
- **Runner class:** Similar to `LangGraphPlanner`: load config, build `StateGraph(State)`, add nodes from config, compile, run. Support `on_node_complete` (or equivalent) so we can emit partial progress as SSE events (e.g. “task_done” with name/summary) and keep our streaming UX.
- **MCP:** Reference implementation uses streamable-http MCP (session init, tools/list, tools/call, schema filtering). We can reuse that pattern in our LangGraph runner; if we already have MCP elsewhere, we may need a small adapter.
- **Streaming:** Reference has no token-level streaming; we can add LangGraph’s streaming API if available and map to our SSE events; otherwise stream node completions as synthetic events so the frontend sees incremental progress.
- **State/threads:** For multi-turn chat, use LangGraph’s thread/checkpoint store and store `langgraph_thread_id` on `ChatSession`; initial state can include conversation history.

### 6.5 CrewAI-specific notes (aligned with vacation-planner)

- **Crew definition:** Start with one or a few predefined crews (e.g. from YAML/code) selected by agent or template; later consider DB-driven crew config.
- **Inputs:** CrewAI expects structured inputs (like vacation-planner). Options: (a) use a single “user_message” input and let the crew parse it, or (b) add optional structured slot in chat (e.g. parsed entities) and pass both to the crew.
- **Streaming:** If CrewAI exposes streaming, use it and normalize; otherwise stream the final output as one or a few chunks so the frontend still receives SSE.
- **No conversation:** Either treat each message as a new run or maintain a small history in our DB and pass “recent messages” as part of the crew input.

### 6.6 Phasing

1. **Phase 1 – Runner abstraction + LlamaStack behind it**
   Add `runner_type` and an interface; move current LlamaStack logic into `LlamaStackRunner`; chat service calls the runner by type. No new frameworks yet.

2. **Phase 2 – LangGraph runner**
   Implement LangGraph runner (predefined graph, streaming, thread id in session); add config and deps; test with one virtual agent with `runner_type=langgraph`.

3. **Phase 3 – CrewAI runner**
   Implement CrewAI runner (one predefined crew, input mapping, output normalization); add config and deps; test with one virtual agent with `runner_type=crewai`.

4. **Phase 4 (optional)**
   Multiple graphs/crews, DB-driven config, optional job API for long-running CrewAI runs.

---

## 7. Summary

- **Reference:** Vacation-planner **langgraph-implementation** branch (`git@github.com:skattoju/vacation-planner.git`) — LangGraph via `LangGraphPlanner` + declarative `graph.yaml` (nodes: llm, mcp_tool, mcp_tool_map, router), MCP integration, job API with `partial_result`. Same repo also has CrewAI on the same branch.
- **Our approach** keeps streaming, sessions, and many virtual agents; the **reference** gives a clear pattern for declarative LangGraph graphs and MCP in-process.
- **Replan:** Add a **runner abstraction** and `runner_type`; implement a **LangGraph runner** inspired by the reference (YAML graph, `LangGraphPlanner`-style class, optional node-callback for partial SSE); add **CrewAI** as a second additional runner; keep LlamaStack as the default and extend sessions/config per runner.
