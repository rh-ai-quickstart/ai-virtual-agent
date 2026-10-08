"""Template browser and deployment-dialog workflows with a fake initializer."""

import json
from urllib.parse import urlsplit

from playwright.sync_api import Page, Route, expect
from ui_mocks import MODEL, mock_current_user


def _install_template_api(
    page: Page, *, model_catalog: list[dict] | None = None
) -> dict:
    state = {"initialize": [], "agents": []}
    mock_current_user(page)
    page.route(
        "**/api/v1/virtual_agents/**", lambda route: route.fulfill(json=state["agents"])
    )
    page.route(
        "**/api/v1/users/ui-admin/agents",
        lambda route: route.fulfill(json=[agent["id"] for agent in state["agents"]]),
    )
    page.route(
        "**/api/v1/llama_stack/llms",
        lambda route: route.fulfill(
            json=[MODEL] if model_catalog is None else model_catalog
        ),
    )
    page.route("**/api/v1/llama_stack/tools", lambda route: route.fulfill(json=[]))
    page.route("**/api/v1/knowledge_bases/**", lambda route: route.fulfill(json=[]))

    def templates(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path
        if request.method == "POST" and path.endswith("/initialize"):
            payload = request.post_data_json or {}
            state["initialize"].append(payload)
            template_id = payload["template_name"]
            if template_id == "template-failure":
                route.fulfill(
                    json={
                        "status": "failed",
                        "agent_name": "Failing Agent",
                        "message": "mock deployment error",
                    }
                )
            else:
                row = {
                    "id": f"agent-{template_id}",
                    "name": "Support Agent",
                    "template_id": template_id,
                    "model_name": payload.get("model_name", "test-model"),
                    "prompt": "Support persona",
                    "tools": [],
                    "knowledge_base_ids": [],
                    "input_shields": [],
                    "output_shields": [],
                }
                state["agents"].append(row)
                route.fulfill(
                    json={
                        "status": "success",
                        "agent_name": "Support Agent",
                        "agent": row,
                    }
                )
        elif path.endswith("/suites/categories"):
            route.fulfill(json={"customer_support": ["support_suite"]})
        elif path.endswith("/categories/info"):
            route.fulfill(
                json={
                    "customer_support": {
                        "name": "Customer Support",
                        "description": "Support tools",
                        "icon": "support",
                        "suite_count": 1,
                    }
                }
            )
        elif path.endswith("/suites/support_suite/details"):
            route.fulfill(
                json={
                    "id": "support_suite",
                    "name": "Support Suite",
                    "description": "Support agents",
                    "category": "customer_support",
                    "agent_count": 2,
                    "agent_names": ["Support Agent", "Failing Agent"],
                    "template_ids": ["template-support", "template-failure"],
                }
            )
        elif path.endswith("/template-support") or path.endswith("/template-failure"):
            template_id = path.rsplit("/", 1)[-1]
            route.fulfill(
                json={
                    "template_name": template_id,
                    "model_name": "test-model",
                    "runner_type": "llamastack",
                    "tools": [],
                    "knowledge_base_ids": [],
                    "demo_questions": ["Ask about the demo topic?"],
                }
            )
        else:
            route.fulfill(
                status=404, json={"detail": f"Unmocked template endpoint {path}"}
            )

    page.route("**/api/v1/agent_templates/**", templates)
    return state


def _open_templates(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("tab", name="Agent Templates").click()
    expect(page.get_by_role("heading", name="AI Agent Templates")).to_be_visible(
        timeout=20_000
    )
    expect(page.get_by_role("heading", name="Support Suite")).to_be_visible(
        timeout=20_000
    )


def test_template_suite_selection_cancel_and_deploy_overrides(
    page: Page, frontend_url: str
) -> None:
    state = _install_template_api(page)
    _open_templates(page, frontend_url)
    page.get_by_role("button", name="Deploy Suite").click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_role("heading", name="Deploy Support Suite")).to_be_visible()
    expect(dialog.get_by_role("button", name="Deploy Selected (2)")).to_be_disabled()
    dialog.locator("#template-template-failure").uncheck()
    page.locator("#runner-type-template-support-select").select_option("langgraph")
    expect(dialog.get_by_role("button", name="Deploy Selected (1)")).to_be_enabled(
        timeout=15_000
    )

    dialog.get_by_role("button", name="Cancel").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert state["initialize"] == []

    page.get_by_role("button", name="Deploy Suite").click()
    dialog = page.get_by_role("dialog")
    dialog.locator("#template-template-failure").uncheck()
    page.locator("#model-template-support").select_option("test-model")
    page.locator("#runner-type-template-support-select").select_option("langgraph")
    dialog.get_by_role("button", name="Deploy Selected (1)").click()

    progress = page.get_by_text("Deployed Support Agent")
    expect(progress).to_be_visible(timeout=15_000)
    assert state["initialize"] == [
        {
            "template_name": "template-support",
            "include_knowledge_base": True,
            "runner_type": "langgraph",
        }
    ]


def test_template_deployment_reports_success_and_failure(
    page: Page, frontend_url: str
) -> None:
    state = _install_template_api(page)
    _open_templates(page, frontend_url)
    page.get_by_role("button", name="Deploy Suite").click()
    dialog = page.get_by_role("dialog")
    page.locator("#model-template-support").select_option("test-model")
    page.locator("#model-template-failure").select_option("test-model")
    expect(dialog.get_by_role("button", name="Deploy Selected (2)")).to_be_enabled(
        timeout=15_000
    )
    dialog.get_by_role("button", name="Deploy Selected (2)").click()
    expect(page.get_by_text("Deployed Support Agent")).to_be_visible(timeout=15_000)
    expect(
        page.get_by_text("Failed to deploy Failing Agent: mock deployment error")
    ).to_be_visible(timeout=15_000)
    assert {row["template_name"] for row in state["initialize"]} == {
        "template-support",
        "template-failure",
    }


def test_template_deploy_requires_available_model_and_selection(
    page: Page, frontend_url: str
) -> None:
    state = _install_template_api(page, model_catalog=[])
    _open_templates(page, frontend_url)
    page.get_by_role("button", name="Deploy Suite").click()
    dialog = page.get_by_role("dialog")
    deploy = dialog.get_by_role("button", name="Deploy Selected (2)")
    expect(deploy).to_be_disabled(timeout=15_000)
    dialog.locator("#select-all-templates").uncheck()
    expect(dialog.get_by_role("button", name="Deploy Selected (0)")).to_be_disabled()
    expect(dialog.get_by_role("button", name="Deploy All")).to_be_disabled()
    dialog.get_by_role("button", name="Cancel").click()
    assert state["initialize"] == []


def test_mocked_deployed_template_agent_can_chat(page: Page, frontend_url: str) -> None:
    state = _install_template_api(page)
    state["chat_requests"] = []
    state["chat_sessions"] = []

    def chat_sessions(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path.rstrip("/")
        if request.method == "GET" and path.endswith("/chat_sessions"):
            route.fulfill(json=state["chat_sessions"])
        elif request.method == "POST" and path.endswith("/chat_sessions"):
            payload = request.post_data_json or {}
            agent = next(
                item for item in state["agents"] if item["id"] == payload["agent_id"]
            )
            session = {
                "id": "session-deployed-template",
                "title": payload.get("session_name", "New chat"),
                "agent_name": agent["name"],
                "agent_id": agent["id"],
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
            }
            state["chat_sessions"].append(session)
            route.fulfill(status=201, json={**session, "messages": []})
        elif request.method == "GET" and path.endswith("/messages"):
            route.fulfill(json={"messages": []})
        elif request.method == "GET":
            session = next(
                (
                    item
                    for item in state["chat_sessions"]
                    if item["id"] == path.rsplit("/", 1)[-1]
                ),
                None,
            )
            route.fulfill(status=200 if session else 404, json=session or {})
        else:
            route.fulfill(
                status=404, json={"detail": "Unexpected chat session request"}
            )

    def chat(route: Route) -> None:
        payload = route.request.post_data_json or {}
        state["chat_requests"].append(payload)
        event = {
            "type": "response",
            "session_id": payload.get("sessionId"),
            "delta": "The deployed support template replied.",
            "status": "completed",
            "id": "deployed-template-reply",
        }
        route.fulfill(
            status=200,
            content_type="text/event-stream",
            body=f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n",
        )

    page.route("**/api/v1/chat_sessions**", chat_sessions)
    page.route("**/api/v1/chat", chat)

    _open_templates(page, frontend_url)
    page.get_by_role("button", name="Deploy Suite").click()
    dialog = page.get_by_role("dialog")
    dialog.locator("#template-template-failure").uncheck()
    page.locator("#model-template-support").select_option("test-model")
    dialog.get_by_role("button", name="Deploy Selected (1)").click()
    expect(page.get_by_text("Deployed Support Agent")).to_be_visible(timeout=15_000)
    assert state["initialize"][0]["template_name"] == "template-support"

    page.get_by_role("button", name="Close").click()
    page.get_by_role("link", name="Chat").click()
    agent_selector = page.get_by_role("button", name="Select model")
    expect(agent_selector).to_contain_text("Support Agent", timeout=15_000)

    suggested = page.get_by_role(
        "button", name="Suggested question: Ask about the demo topic?"
    )
    expect(suggested).to_be_visible(timeout=15_000)
    suggested.click()
    expect(page.get_by_text("The deployed support template replied.")).to_be_visible(
        timeout=15_000
    )

    assert state["chat_requests"][0]["virtualAgentId"] == "agent-template-support"
    assert (
        state["chat_requests"][0]["message"]["content"][0]["text"]
        == "Ask about the demo topic?"
    )
