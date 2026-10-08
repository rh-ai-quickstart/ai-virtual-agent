"""Deterministic UI checks for chat, session history, tools, and attachments."""

import json
import re
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, Route, expect
from ui_mocks import AGENTS, mock_current_user


def install_chat_api(page: Page, *, template_agent: bool = False) -> dict:
    state = {
        "sessions": {
            "agent-alpha": [
                {
                    "id": "session-alpha-1",
                    "title": "Alpha history",
                    "agent_name": "Alpha Assistant",
                    "agent_id": "agent-alpha",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                },
                {
                    "id": "session-alpha-2",
                    "title": "Alpha second",
                    "agent_name": "Alpha Assistant",
                    "agent_id": "agent-alpha",
                    "created_at": "2026-01-02T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                },
            ],
            "agent-beta": [
                {
                    "id": "session-beta-1",
                    "title": "Beta history",
                    "agent_name": "Beta Assistant",
                    "agent_id": "agent-beta",
                    "created_at": "2026-01-03T00:00:00Z",
                    "updated_at": "2026-01-03T00:00:00Z",
                },
            ],
        },
        "messages": {
            "session-alpha-1": [
                {
                    "id": "old-alpha",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Saved alpha answer"}],
                    "timestamp": "2026-01-01T00:00:00Z",
                }
            ],
            "session-alpha-2": [
                {
                    "id": "old-alpha-2",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Second saved answer"}],
                    "timestamp": "2026-01-02T00:00:00Z",
                }
            ],
            "session-beta-1": [
                {
                    "id": "old-beta",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Saved beta answer"}],
                    "timestamp": "2026-01-03T00:00:00Z",
                }
            ],
        },
        "deleted": [],
        "chat_requests": [],
        "uploads": [],
    }
    agents = []
    for agent in AGENTS:
        row = dict(agent)
        if template_agent and row["id"] == "agent-alpha":
            row["template_id"] = "sample-template"
        agents.append(row)
    if template_agent:
        state["messages"]["session-alpha-1"] = []
    mock_current_user(page)
    page.route(
        "**/api/v1/users/ui-admin/agents",
        lambda route: route.fulfill(json=[a["id"] for a in agents]),
    )
    page.route("**/api/v1/virtual_agents/**", lambda route: route.fulfill(json=agents))
    page.route(
        "**/api/v1/agent_templates/sample-template",
        lambda route: route.fulfill(
            json={"demo_questions": ["Ask about the demo topic?"]}
        ),
    )

    def sessions(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path
        parts = path.rstrip("/").split("/")
        if request.method == "GET" and path.rstrip("/").endswith("chat_sessions"):
            agent_id = parse_qs(urlsplit(request.url).query).get(
                "agent_id", ["agent-alpha"]
            )[0]
            route.fulfill(json=state["sessions"].get(agent_id, []))
        elif request.method == "POST" and path.rstrip("/").endswith("chat_sessions"):
            payload = request.post_data_json or {}
            agent_id = payload.get("agent_id", "agent-alpha")
            session_id = f"created-{len(state['sessions'].get(agent_id, [])) + 1}"
            row = {
                "id": session_id,
                "title": payload.get("session_name") or "New chat",
                "agent_name": next(
                    (a["name"] for a in agents if a["id"] == agent_id), "Agent"
                ),
                "agent_id": agent_id,
                "created_at": "2026-10-05T00:00:00Z",
                "updated_at": "2026-10-05T00:00:00Z",
            }
            state["sessions"].setdefault(agent_id, []).insert(0, row)
            state["messages"][session_id] = []
            route.fulfill(status=201, json={**row, "messages": []})
        elif len(parts) >= 5 and parts[-1] == "messages" and request.method == "GET":
            route.fulfill(json={"messages": state["messages"].get(parts[-2], [])})
        elif len(parts) >= 4 and request.method == "GET":
            session_id = parts[-1]
            row = next(
                (
                    s
                    for values in state["sessions"].values()
                    for s in values
                    if s["id"] == session_id
                ),
                None,
            )
            route.fulfill(
                status=200 if row else 404, json=row or {"detail": "missing session"}
            )
        elif len(parts) >= 4 and request.method == "DELETE":
            session_id = parts[-1]
            agent_id = parse_qs(urlsplit(request.url).query).get(
                "agent_id", ["agent-alpha"]
            )[0]
            state["deleted"].append(session_id)
            state["sessions"][agent_id] = [
                s for s in state["sessions"].get(agent_id, []) if s["id"] != session_id
            ]
            route.fulfill(status=204)
        else:
            route.fulfill(
                status=404,
                json={
                    "detail": f"Unhandled chat session request {request.method} {path}"
                },
            )

    page.route("**/api/v1/chat_sessions**", sessions)

    def chat(route: Route) -> None:
        payload = route.request.post_data_json or {}
        state["chat_requests"].append(payload)
        session_id = payload.get("sessionId") or "session-alpha-1"
        body = (
            "".join(
                f"data: {json.dumps(event)}\n\n"
                for event in [
                    {
                        "type": "response",
                        "session_id": session_id,
                        "delta": "A streamed ",
                        "status": "in_progress",
                        "id": "assistant-message",
                    },
                    {
                        "type": "response",
                        "session_id": session_id,
                        "delta": "reply.",
                        "status": "in_progress",
                        "id": "assistant-message",
                    },
                    {
                        "type": "response",
                        "session_id": session_id,
                        "delta": "",
                        "status": "completed",
                        "id": "assistant-message",
                    },
                    {
                        "type": "token_usage",
                        "session_id": session_id,
                        "input_tokens": 5,
                        "output_tokens": 3,
                    },
                ]
            )
            + "data: [DONE]\n\n"
        )
        route.fulfill(status=200, content_type="text/event-stream", body=body)

    page.route("**/api/v1/chat", chat)

    def upload(route: Route) -> None:
        state["uploads"].append(route.request.post_data or "")
        route.fulfill(status=201, json={"filename": "notes.txt"})

    page.route("**/api/v1/attachments/**", upload)
    return state


def open_history(page: Page) -> None:
    page.get_by_role("button", name="Toggle menu").click()


def test_chat_sends_message_and_renders_streamed_reply(
    page: Page, frontend_url: str
) -> None:
    state = install_chat_api(page)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    expect(page.get_by_text("Saved alpha answer")).to_be_visible(timeout=30_000)
    composer = page.get_by_role("textbox").last
    composer.fill("Say hello")
    page.get_by_role("button", name=re.compile("send", re.I)).last.click()

    expect(page.get_by_text("Say hello")).to_be_visible()
    expect(page.get_by_text("A streamed reply.")).to_be_visible(timeout=15_000)
    expect(page.get_by_text("Tokens:")).to_be_visible()
    expect(page.get_by_role("textbox", name="Send a message...")).to_be_enabled()
    assert state["chat_requests"][0]["virtualAgentId"] == "agent-alpha"
    assert state["chat_requests"][0]["sessionId"] == "session-alpha-1"


def test_chat_history_creates_and_switches_sessions(
    page: Page, frontend_url: str
) -> None:
    state = install_chat_api(page)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    expect(page.get_by_text("Saved alpha answer")).to_be_visible(timeout=30_000)
    open_history(page)
    expect(page.get_by_text("Alpha second")).to_be_visible(timeout=10_000)
    page.get_by_text("Alpha second", exact=True).click()
    expect(page.get_by_text("Second saved answer")).to_be_visible(timeout=10_000)

    open_history(page)
    page.get_by_role(
        "button", name=re.compile("new chat|new conversation", re.I)
    ).click()
    expect(page.get_by_text("Second saved answer")).not_to_be_visible(timeout=10_000)
    assert any(
        row["id"].startswith("created-") for row in state["sessions"]["agent-alpha"]
    )


def test_chat_session_delete_cancel_and_confirm(page: Page, frontend_url: str) -> None:
    state = install_chat_api(page)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    expect(page.get_by_text("Saved alpha answer")).to_be_visible(timeout=30_000)
    open_history(page)
    session = page.get_by_text("Alpha history", exact=True)
    expect(session).to_be_visible()
    session.hover()
    page.locator('button[aria-label="Conversation options"]').first.click()
    page.get_by_role("menuitem", name="Delete").click()
    expect(page.get_by_role("heading", name="Delete Session")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    expect(page.get_by_text("Alpha history", exact=True)).to_be_visible()

    session.hover()
    page.locator('button[aria-label="Conversation options"]').first.click()
    page.get_by_role("menuitem", name="Delete").click()
    page.get_by_role("dialog").get_by_role("button", name="Delete").click()
    expect(page.get_by_text("Alpha history", exact=True)).not_to_be_visible(
        timeout=10_000
    )
    assert state["deleted"] == ["session-alpha-1"]


def test_switching_agents_loads_their_own_sessions(
    page: Page, frontend_url: str
) -> None:
    state = install_chat_api(page)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    expect(page.get_by_text("Saved alpha answer")).to_be_visible(timeout=30_000)
    page.get_by_role("button", name="Select model").click()
    page.get_by_role("menuitem", name="Beta Assistant").click()
    expect(page.get_by_text("Saved beta answer")).to_be_visible(timeout=15_000)
    open_history(page)
    expect(page.get_by_text("Beta history", exact=True)).to_be_visible()
    expect(page.get_by_text("Alpha history", exact=True)).not_to_be_visible()
    assert state["sessions"]["agent-beta"][0]["agent_id"] == "agent-beta"


def test_chat_tool_trace_expands_and_stream_error_recovers(
    page: Page, frontend_url: str
) -> None:
    state = install_chat_api(page)

    def tool_then_error(route: Route) -> None:
        payload = route.request.post_data_json or {}
        state["chat_requests"].append(payload)
        sid = payload.get("sessionId", "session-alpha-1")
        if len(state["chat_requests"]) == 1:
            events = [
                {
                    "type": "tool_call",
                    "session_id": sid,
                    "name": "knowledge_search",
                    "server_label": "llamastack",
                    "status": "completed",
                    "arguments": '{"query":"sample"}',
                    "output": "Search result text",
                    "id": "tool-1",
                },
                {
                    "type": "tool_call",
                    "session_id": sid,
                    "name": "failed_search",
                    "server_label": "llamastack",
                    "status": "failed",
                    "arguments": "{}",
                    "error": "Tool backend failed",
                    "id": "tool-2",
                },
                {
                    "type": "response",
                    "session_id": sid,
                    "delta": "Recovered answer",
                    "status": "completed",
                    "id": "assistant-message",
                },
            ]
        else:
            events = [
                {"type": "error", "session_id": sid, "message": "Temporary model error"}
            ]
        route.fulfill(
            status=200,
            content_type="text/event-stream",
            body="".join(f"data: {json.dumps(e)}\n\n" for e in events)
            + "data: [DONE]\n\n",
        )

    page.unroute("**/api/v1/chat")
    page.route("**/api/v1/chat", tool_then_error)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    expect(page.get_by_text("Saved alpha answer")).to_be_visible(timeout=30_000)
    box = page.get_by_role("textbox").last
    box.fill("Search this")
    page.get_by_role("button", name=re.compile("send", re.I)).last.click()
    trace = page.get_by_text(re.compile("Tool Call: llamastack::knowledge_search"))
    expect(trace).to_be_visible(timeout=10_000)
    trace.click()
    expect(page.get_by_text("Arguments:").first).to_be_visible()
    expect(page.get_by_text('"query": "sample"', exact=False).first).to_be_visible()
    expect(page.get_by_text("Search result text").first).to_be_visible()
    expect(page.get_by_text("Recovered answer")).to_be_visible()
    failed_trace = page.get_by_role(
        "button", name=re.compile("Tool Call: llamastack::failed_search")
    )
    failed_trace.click()
    expect(page.get_by_text("Tool backend failed")).to_be_visible()
    box = page.get_by_role("textbox").last
    box.fill("Try again")
    page.get_by_role("button", name=re.compile("send", re.I)).last.click()
    expect(page.get_by_text("Temporary model error")).to_be_visible(timeout=10_000)
    expect(page.get_by_role("textbox", name="Send a message...")).to_be_enabled()
    assert len(state["chat_requests"]) == 2


def test_template_suggested_question_sends_and_disappears(
    page: Page, frontend_url: str
) -> None:
    state = install_chat_api(page, template_agent=True)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    suggested = page.get_by_role(
        "button", name="Suggested question: Ask about the demo topic?"
    )
    expect(suggested).to_be_visible(timeout=30_000)
    suggested.click()
    expect(page.get_by_text("Ask about the demo topic?")).to_be_visible()
    expect(suggested).not_to_be_visible()
    expect(page.get_by_text("A streamed reply.")).to_be_visible(timeout=15_000)
    assert (
        state["chat_requests"][0]["message"]["content"][0]["text"]
        == "Ask about the demo topic?"
    )


def test_chat_attachment_can_be_removed_and_uploaded_for_active_session(
    page: Page, frontend_url: str
) -> None:
    state = install_chat_api(page)
    page.goto(f"{frontend_url}/?agentId=agent-alpha", wait_until="domcontentloaded")
    expect(page.get_by_text("Saved alpha answer")).to_be_visible(timeout=30_000)

    file_input = page.locator('input[type="file"]')
    file_input.set_input_files(
        {"name": "discard.txt", "mimeType": "text/plain", "buffer": b"discard me"}
    )
    close_button = page.get_by_role("button", name="Close discard.txt")
    expect(close_button).to_be_visible()
    close_button.click()
    expect(page.get_by_role("button", name="Close discard.txt")).to_have_count(0)

    file_input.set_input_files(
        {
            "name": "meeting-notes.txt",
            "mimeType": "text/plain",
            "buffer": b"Project meeting notes",
        }
    )
    expect(page.get_by_role("button", name="Close meeting-notes.txt")).to_be_visible()
    page.get_by_role("textbox").last.fill("Summarize this file")
    page.get_by_role("button", name=re.compile("send", re.I)).last.click()

    expect(page.get_by_text("A streamed reply.")).to_be_visible(timeout=15_000)
    expect(page.get_by_role("button", name="Close meeting-notes.txt")).to_have_count(0)
    assert "meeting-notes.txt" in state["uploads"][0]
    request = state["chat_requests"][0]
    assert request["sessionId"] == "session-alpha-1"
    assert any(item["type"] == "input_image" for item in request["message"]["content"])
