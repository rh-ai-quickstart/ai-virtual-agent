"""Mocked agent list, creation, detail, deletion, and form-control coverage."""

import re
import uuid
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, Route, expect
from ui_mocks import AGENTS, MODEL, mock_current_user


def _click_card(page: Page, title: str) -> None:
    card = page.locator(".pf-v6-c-card").filter(
        has=page.get_by_role("heading", name=title)
    )
    card.locator("button.pf-v6-c-card__clickable-action").click()


def _install_agent_api(page: Page) -> dict:
    state = {"agents": [dict(agent) for agent in AGENTS], "created": [], "deleted": []}
    mock_current_user(page)
    page.route("**/api/v1/llama_stack/llms", lambda route: route.fulfill(json=[MODEL]))
    page.route(
        "**/api/v1/llama_stack/tools",
        lambda route: route.fulfill(
            json=[
                {"toolgroup_id": "builtin::rag", "name": "Knowledge Search"},
                {"toolgroup_id": "builtin::websearch", "name": "Web Search"},
            ]
        ),
    )
    page.route(
        "**/api/v1/knowledge_bases/**",
        lambda route: route.fulfill(
            json=[
                {
                    "name": "Policy Manual",
                    "vector_store_name": "policy-v1",
                    "vector_store_id": "vs-policy",
                    "status": "succeeded",
                }
            ]
        ),
    )
    page.route("**/api/v1/llama_stack/shields", lambda route: route.fulfill(json=[]))
    page.route(
        "**/api/v1/users/ui-admin/agents",
        lambda route: route.fulfill(json=[a["id"] for a in state["agents"]]),
    )

    def agents(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path
        if request.method == "GET":
            route.fulfill(json=state["agents"])
        elif request.method == "POST":
            payload = request.post_data_json or {}
            state["created"].append(payload)
            row = {
                **payload,
                "id": "agent-created",
                "created_at": "2026-10-05T12:00:00Z",
                "tools": payload.get("tools", []),
                "knowledge_base_ids": payload.get("knowledge_base_ids", []),
                "input_shields": payload.get("input_shields", []),
                "output_shields": payload.get("output_shields", []),
            }
            state["agents"].append(row)
            route.fulfill(status=201, json=row)
        elif request.method == "DELETE":
            agent_id = unquote(path.rsplit("/", 1)[-1])
            state["deleted"].append(agent_id)
            state["agents"] = [a for a in state["agents"] if a["id"] != agent_id]
            route.fulfill(status=204)
        else:
            route.fulfill(status=405)

    page.route("**/api/v1/virtual_agents/**", agents)
    return state


def _open_agent_admin(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    expect(page.get_by_role("tablist")).to_be_visible()


def test_agent_create_details_and_delete_confirmation(
    page: Page, frontend_url: str
) -> None:
    state = _install_agent_api(page)
    _open_agent_admin(page, frontend_url)
    expect(page.get_by_role("heading", name="Alpha Assistant")).to_be_visible(
        timeout=20_000
    )

    agent_name = f"UI Agent {uuid.uuid4().hex[:8]}"
    _click_card(page, "New Agent")
    page.locator("#agent-name").fill(agent_name)
    page.locator("#ai-model").select_option("test-model")
    page.locator("#prompt").fill("Answer from the selected policy knowledge base.")
    tool_input = page.locator("#tools-multiselect-component-input")
    tool_input.click()
    page.get_by_role("option", name="Knowledge Search").click()
    kb_input = page.locator("#knowledge-bases-multiselect-component-input")
    kb_input.click()
    page.get_by_role("option", name="Policy Manual (policy-v1)").click()
    page.get_by_role("button", name="Submit").click()

    expect(page.get_by_role("heading", name=agent_name)).to_be_visible(timeout=15_000)
    payload = state["created"][0]
    assert payload["model_name"] == "test-model"
    assert payload["prompt"] == "Answer from the selected policy knowledge base."
    assert payload["tools"] == [{"toolgroup_id": "builtin::rag"}]
    assert payload["knowledge_base_ids"] == ["policy-v1"]

    created_card = page.locator("#expandable-agent-card-agent-created")
    created_card.get_by_role("button", name=re.compile("Details")).click()
    expect(created_card).to_contain_text(
        "Answer from the selected policy knowledge base."
    )
    expect(created_card).to_contain_text("policy-v1")
    expect(created_card).to_contain_text("test-model")
    created_card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Delete").click()
    expect(page.get_by_role("heading", name="Delete Agent")).to_be_visible()
    page.get_by_role("dialog").get_by_role("button", name="Cancel").click()
    expect(page.get_by_role("heading", name=agent_name)).to_be_visible()
    created_card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Delete").click()
    page.get_by_role("dialog").get_by_role("button", name="Delete").click()
    expect(page.get_by_role("heading", name=agent_name)).not_to_be_visible(
        timeout=10_000
    )
    assert state["deleted"] == ["agent-created"]


def test_agent_form_validates_rag_sampling_and_multiselect_keys(
    page: Page, frontend_url: str
) -> None:
    _install_agent_api(page)
    _open_agent_admin(page, frontend_url)
    _click_card(page, "New Agent")
    submit = page.get_by_role("button", name="Submit")
    expect(submit).to_be_enabled()
    page.locator("#agent-name").fill("Form Validation Agent")
    page.locator("#ai-model").select_option("test-model")
    page.locator("#prompt").fill("A valid prompt.")

    tools = page.locator("#tools-multiselect-component-input")
    tools.click()
    tools.press("ArrowDown")
    tools.press("Enter")
    expect(page.locator("#knowledge-bases-multiselect-component-input")).to_be_visible()
    tools.press("Escape")
    tools.press("Backspace")
    expect(page.locator("#knowledge-bases-multiselect-component-input")).to_have_count(
        0
    )

    tools.click()
    tools.press("ArrowDown")
    tools.press("Enter")
    expect(page.locator("#knowledge-bases-multiselect-component-input")).to_be_visible()
    kb = page.locator("#knowledge-bases-multiselect-component-input")
    kb.click()
    page.get_by_role("option", name="Policy Manual (policy-v1)").click()
    expect(
        page.get_by_role("tabpanel", name="My Agents").get_by_text(
            "Policy Manual (policy-v1)", exact=True
        )
    ).to_be_visible()

    page.get_by_role("button", name="Clear selections and input").first.click()
    expect(page.locator("#knowledge-bases-multiselect-component-input")).to_have_count(
        0
    )
    page.get_by_role("button", name="Sampling & Generation Parameters").click()
    expect(page.locator("#sampling-strategy")).to_be_visible()
    page.locator("#sampling-strategy").select_option("top-k")
    expect(page.locator("#sampling-strategy")).to_have_value("top-k")
