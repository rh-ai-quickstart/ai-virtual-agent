"""Live browser coverage for agent configuration and inference."""

import re
import uuid

from live_test_utils import (
    assign_agent,
    cleanup_agent_sessions,
    delete_agent,
    live_model,
    parse_sse_events,
    remove_agent_assignment,
    require_admin,
)
from playwright.sync_api import Page, expect


def test_live_agent_form_saves_sampling_and_completes_inference(
    page: Page, frontend_url: str
) -> None:
    """Create an agent with real config, chat through it, and delete it."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile = require_admin(page, frontend_url)
    model_name = live_model(page, frontend_url)
    unique = uuid.uuid4().hex[:10]
    agent_name = f"UI Live Agent {unique}"
    marker = f"LIVE_AGENT_{unique.upper()}"
    agent_id: str | None = None
    assignment_created = False

    try:
        page.get_by_role("link", name="Config").click()
        card = page.locator(".pf-v6-c-card").filter(
            has=page.get_by_role("heading", name="New Agent")
        )
        card.locator("button.pf-v6-c-card__clickable-action").click()

        page.locator("#agent-name").fill(agent_name)
        model_select = page.locator("#ai-model")
        page.wait_for_function(
            """(modelName) => Array.from(document.querySelectorAll('#ai-model option'))
                .some((option) => option.value === modelName && !option.disabled)""",
            arg=model_name,
            timeout=60_000,
        )
        model_select.select_option(model_name)
        page.locator("#prompt").fill(
            "For every user message, reply with exactly "
            f"{marker} and no other words or punctuation."
        )
        page.get_by_role("button", name="Sampling & Generation Parameters").click()
        page.locator("#sampling-strategy").select_option("top-k")
        temperature_input = (
            page.locator(".wide-input-slider")
            .filter(has_text="Temperature")
            .locator('input[type="number"]')
        )
        top_k_input = (
            page.locator(".wide-input-slider")
            .filter(has_text="Top-K")
            .locator('input[type="number"]')
        )
        expect(temperature_input).to_have_count(1)
        expect(top_k_input).to_have_count(1)
        temperature_input.fill("0.2")
        top_k_input.fill("18")

        with page.expect_request(
            lambda request: request.method == "POST"
            and request.url.endswith("/api/v1/virtual_agents/"),
            timeout=60_000,
        ) as create_request_info, page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/virtual_agents/"),
            timeout=60_000,
        ) as create_response_info:
            page.get_by_role("button", name="Submit").click()

        create_payload = create_request_info.value.post_data_json
        assert create_payload["sampling_strategy"] == "top-k"
        assert create_payload["temperature"] == 0.2
        assert create_payload["top_k"] == 18

        create_response = create_response_info.value
        assert create_response.status == 201, (
            f"Live agent creation failed: HTTP {create_response.status} "
            f"{create_response.text()}"
        )
        created_agent = create_response.json()
        agent_id = str(created_agent["id"])
        assert created_agent["model_name"] == model_name

        assign_agent(page, frontend_url, str(profile["id"]), agent_id)
        assignment_created = True

        page.goto(f"{frontend_url}/?agentId={agent_id}", wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="Select model")).to_contain_text(
            agent_name, timeout=60_000
        )
        message_box = page.get_by_role("textbox").last
        expect(message_box).to_be_visible(timeout=30_000)
        message_box.fill("Follow your instruction.")
        send_button = page.get_by_role(
            "button", name=re.compile("send", re.IGNORECASE)
        ).last
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/chat"),
            timeout=180_000,
        ) as chat_response_info:
            send_button.click()

        chat_response = chat_response_info.value
        assert chat_response.status == 200, (
            f"Live agent chat failed: HTTP {chat_response.status} "
            f"{chat_response.text()}"
        )
        events = parse_sse_events(chat_response.text())
        errors = [
            str(event.get("message", "unknown inference error"))
            for event in events
            if event.get("type") == "error"
        ]
        assert not errors, f"Live agent inference returned errors: {errors}"
        answer = "".join(
            str(event.get("delta", ""))
            for event in events
            if event.get("type") == "response"
        )
        assert marker in answer, f"Live inference returned {answer!r}"
        assert any(
            event.get("type") == "response" and event.get("status") == "completed"
            for event in events
        ), "Live agent chat ended without a completed assistant response"
    finally:
        if agent_id:
            cleanup_agent_sessions(page, frontend_url, agent_id)
            if assignment_created:
                remove_agent_assignment(
                    page, frontend_url, str(profile["id"]), agent_id
                )
            delete_agent(page, frontend_url, agent_id)
