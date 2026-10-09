"""Live browser coverage for template deployment and model inference."""

import json
import re
import uuid

import pytest
from live_test_utils import (
    assign_agent,
    cleanup_agent_sessions,
    delete_agent,
    live_model,
    remove_agent_assignment,
    require_admin,
)
from playwright.sync_api import Page, expect


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in re.split(r"\r?\n\r?\n", body):
        data_lines = [
            line[6:] for line in block.splitlines() if line.startswith("data: ")
        ]
        if not data_lines:
            continue
        data = "\n".join(data_lines)
        if data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _report_cleanup_failure(label: str, response) -> None:
    if not response.ok:
        print(f"Could not clean up {label}: HTTP {response.status} {response.text()}")


def test_live_template_agent_can_chat_in_browser(page: Page, frontend_url: str) -> None:
    """Deploy a unique template agent, use real inference in the UI, and clean up."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile_response = page.request.get(f"{frontend_url}/api/v1/users/profile")
    if not profile_response.ok:
        pytest.skip(
            "Live template browser coverage needs an authenticated admin user; "
            f"profile returned HTTP {profile_response.status}"
        )
    profile = profile_response.json()
    if profile.get("role") != "admin":
        pytest.skip("Live template browser coverage requires an admin user")

    templates_response = page.request.get(f"{frontend_url}/api/v1/agent_templates/")
    assert templates_response.ok, (
        "Could not list live templates: "
        f"HTTP {templates_response.status} {templates_response.text()}"
    )
    template_ids = templates_response.json()

    selected_template = None
    for template_id in template_ids:
        detail_response = page.request.get(
            f"{frontend_url}/api/v1/agent_templates/{template_id}"
        )
        assert detail_response.ok, (
            f"Could not load live template {template_id}: "
            f"HTTP {detail_response.status} {detail_response.text()}"
        )
        details = detail_response.json()
        if not details.get("graph_config"):
            selected_template = template_id
            break
    if selected_template is None:
        pytest.skip("No non-graph template is available for live inference coverage")

    models_response = page.request.get(f"{frontend_url}/api/v1/llama_stack/llms")
    assert models_response.ok, (
        "Could not list live inference models: "
        f"HTTP {models_response.status} {models_response.text()}"
    )
    models = models_response.json()
    if not models:
        pytest.skip("No live inference model is available")
    model_name = models[0]["model_name"]

    unique = uuid.uuid4().hex[:10]
    agent_name = f"UI Live Template {unique}"
    marker = f"LIVE_TEMPLATE_{unique.upper()}"
    deployment_response = page.request.post(
        f"{frontend_url}/api/v1/agent_templates/initialize",
        data={
            "template_name": selected_template,
            "custom_name": agent_name,
            "custom_prompt": (
                "For every user message, reply with exactly "
                f"{marker} and no other words or punctuation."
            ),
            "include_knowledge_base": False,
            "model_name": model_name,
            "tools": [],
            "knowledge_base_ids": [],
            "runner_type": "llamastack",
        },
        timeout=120_000,
    )
    assert deployment_response.ok, (
        "Could not deploy the live template: "
        f"HTTP {deployment_response.status} {deployment_response.text()}"
    )
    deployment = deployment_response.json()
    agent_id = str(deployment["agent_id"])
    agent_created = False
    assignment_created = False

    try:
        assert (
            deployment["status"] == "success"
        ), f"Expected a fresh template deployment, received: {deployment}"
        agent_created = True
        assignment_response = page.request.post(
            f"{frontend_url}/api/v1/users/{profile['id']}/agents",
            data={"agent_ids": [agent_id]},
        )
        assert assignment_response.ok, (
            "Could not assign the temporary template agent to the live user: "
            f"HTTP {assignment_response.status} {assignment_response.text()}"
        )
        assignment_created = True

        page.goto(f"{frontend_url}/?agentId={agent_id}", wait_until="domcontentloaded")
        agent_selector = page.get_by_role("button", name="Select model")
        expect(agent_selector).to_contain_text(agent_name, timeout=60_000)
        message_box = page.get_by_role("textbox").last
        expect(message_box).to_be_visible(timeout=30_000)
        message_box.fill("Follow your instruction.")
        send_button = page.get_by_role(
            "button", name=re.compile("send", re.IGNORECASE)
        ).last
        expect(send_button).to_be_enabled(timeout=60_000)

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/chat"),
            timeout=180_000,
        ) as chat_response_info:
            send_button.click()

        chat_response = chat_response_info.value
        assert chat_response.status == 200, (
            f"Live chat request failed: HTTP {chat_response.status} "
            f"{chat_response.text()}"
        )
        events = _parse_sse_events(chat_response.text())
        errors = [
            str(event.get("message", "unknown chat error"))
            for event in events
            if event.get("type") == "error"
        ]
        assert not errors, f"Live template chat returned errors: {errors}"
        answer = "".join(
            str(event.get("delta", ""))
            for event in events
            if event.get("type") == "response"
        )
        assert (
            marker in answer
        ), f"Live template inference did not return its expected marker: {answer!r}"
        assert any(
            event.get("type") == "response" and event.get("status") == "completed"
            for event in events
        ), "Live template chat ended without a completed assistant response"
        expect(page.get_by_text(marker, exact=False).last).to_be_visible(timeout=30_000)
    finally:
        if agent_created:
            sessions_response = page.request.get(
                f"{frontend_url}/api/v1/chat_sessions/",
                params={"agent_id": agent_id, "limit": 100},
            )
            if sessions_response.ok:
                for session in sessions_response.json():
                    session_id = session.get("id")
                    if session_id:
                        cleanup_response = page.request.delete(
                            f"{frontend_url}/api/v1/chat_sessions/{session_id}",
                            params={"agent_id": agent_id},
                        )
                        _report_cleanup_failure(
                            f"template chat session {session_id}", cleanup_response
                        )
            else:
                print(
                    "Could not list live template chat sessions for cleanup: "
                    f"HTTP {sessions_response.status} {sessions_response.text()}"
                )

            if assignment_created:
                cleanup_response = page.request.delete(
                    f"{frontend_url}/api/v1/users/{profile['id']}/agents",
                    data={"agent_ids": [agent_id]},
                )
                _report_cleanup_failure(
                    "temporary user agent assignment", cleanup_response
                )

            cleanup_response = page.request.delete(
                f"{frontend_url}/api/v1/virtual_agents/{agent_id}"
            )
            _report_cleanup_failure(f"template agent {agent_id}", cleanup_response)


def test_live_template_deploy_dialog_creates_chat_agent(
    page: Page, frontend_url: str
) -> None:
    """Deploy an unused no-KB template through the real UI and chat with it."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile = require_admin(page, frontend_url)

    suites_response = page.request.get(
        f"{frontend_url}/api/v1/agent_templates/suites/categories"
    )
    assert suites_response.ok, (
        "Could not list live template suites: "
        f"HTTP {suites_response.status} {suites_response.text()}"
    )
    suites_by_category = suites_response.json()
    existing_agents_response = page.request.get(
        f"{frontend_url}/api/v1/virtual_agents/"
    )
    assert existing_agents_response.ok, (
        "Could not list live agents before template deployment: "
        f"HTTP {existing_agents_response.status} {existing_agents_response.text()}"
    )
    existing_agents = existing_agents_response.json()
    existing_agent_keys = {
        (item.get("template_name"), item.get("name")) for item in existing_agents
    }
    user_agents_response = page.request.get(
        f"{frontend_url}/api/v1/users/{profile['id']}/agents"
    )
    assert user_agents_response.ok, (
        "Could not read current user agent assignments: "
        f"HTTP {user_agents_response.status} {user_agents_response.text()}"
    )
    initial_agent_ids = set(user_agents_response.json())

    candidate: dict[str, str] | None = None
    candidate_suite_template_ids: list[str] = []
    for suite_ids in suites_by_category.values():
        for suite_id in suite_ids:
            suite_response = page.request.get(
                f"{frontend_url}/api/v1/agent_templates/suites/{suite_id}/details"
            )
            assert suite_response.ok, (
                f"Could not read suite {suite_id}: HTTP {suite_response.status} "
                f"{suite_response.text()}"
            )
            suite = suite_response.json()
            for template_id in suite.get("template_ids", []):
                detail_response = page.request.get(
                    f"{frontend_url}/api/v1/agent_templates/{template_id}"
                )
                assert detail_response.ok, (
                    f"Could not read template {template_id}: "
                    f"HTTP {detail_response.status} {detail_response.text()}"
                )
                details = detail_response.json()
                template_name = str(details["name"])
                if (
                    not details.get("graph_config")
                    and not details.get("knowledge_base_config")
                    and (template_name, template_name) not in existing_agent_keys
                ):
                    candidate = {
                        "suite_id": str(suite_id),
                        "suite_name": str(suite["name"]),
                        "template_id": str(template_id),
                        "template_name": template_name,
                    }
                    candidate_suite_template_ids = [
                        str(item) for item in suite.get("template_ids", [])
                    ]
                    break
            if candidate:
                break
        if candidate:
            break

    if candidate is None:
        pytest.skip("No undeployed no-KB, non-graph template is available")

    model_name = live_model(page, frontend_url)
    agent_id: str | None = None
    agent_created = False
    assignment_created = False
    try:
        page.get_by_role("link", name="Config").click()
        page.get_by_role("tab", name="Agent Templates").click()
        suite_card = page.locator(".pf-v6-c-card").filter(
            has=page.get_by_role("heading", name=candidate["suite_name"])
        )
        suite_card.get_by_role("button", name="Deploy Suite").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=30_000)

        for template_id in candidate_suite_template_ids:
            if template_id != candidate["template_id"]:
                checkbox = dialog.locator(f'[id="template-{template_id}"]')
                if checkbox.is_checked():
                    checkbox.uncheck()
        model_selector = f'[id="model-{candidate["template_id"]}"]'
        model_select = dialog.locator(model_selector)
        page.wait_for_function(
            """([selector, modelName]) => Array.from(
                document.querySelectorAll(`${selector} option`)
            ).some((option) => option.value === modelName && !option.disabled)""",
            arg=[model_selector, model_name],
            timeout=120_000,
        )
        model_select.select_option(model_name)
        deploy_button = dialog.get_by_role("button", name="Deploy Selected (1)")
        expect(deploy_button).to_be_enabled(timeout=120_000)

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/agent_templates/initialize"),
            timeout=180_000,
        ) as deployment_response_info:
            deploy_button.click()

        deployment_response = deployment_response_info.value
        assert deployment_response.ok, (
            "Live template deployment failed: "
            f"HTTP {deployment_response.status} {deployment_response.text()}"
        )
        deployment = deployment_response.json()
        if deployment["status"] != "success":
            pytest.skip(
                "Template deployment did not create a new agent: "
                f"{deployment.get('status')} {deployment.get('message', '')}"
            )
        agent_created = True
        agent_id = str(deployment["agent_id"])
        assert deployment["agent_name"] == candidate["template_name"]
        expect(
            page.get_by_text(f"Deployed {candidate['template_name']}", exact=False)
        ).to_be_visible(timeout=30_000)

        if agent_id not in initial_agent_ids:
            assign_agent(page, frontend_url, str(profile["id"]), agent_id)
            assignment_created = True

        page.get_by_role("button", name="Close").click()
        page.goto(f"{frontend_url}/?agentId={agent_id}", wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="Select model")).to_contain_text(
            candidate["template_name"], timeout=60_000
        )
        message_box = page.get_by_role("textbox").last
        expect(message_box).to_be_visible(timeout=30_000)
        message_box.fill("Briefly tell me what you can help with.")
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/chat"),
            timeout=240_000,
        ) as chat_response_info:
            page.get_by_role(
                "button", name=re.compile("send", re.IGNORECASE)
            ).last.click()

        chat_response = chat_response_info.value
        assert chat_response.status == 200, (
            f"Live template chat failed: HTTP {chat_response.status} "
            f"{chat_response.text()}"
        )
        events = _parse_sse_events(chat_response.text())
        errors = [event for event in events if event.get("type") == "error"]
        assert not errors, f"Live template chat returned errors: {errors}"
        assert any(
            event.get("type") == "response" and event.get("status") == "completed"
            for event in events
        ), "Live template chat ended without a completed assistant response"
        answer = "".join(
            str(event.get("delta", ""))
            for event in events
            if event.get("type") == "response"
        )
        assert answer.strip(), "Live template chat returned an empty answer"
    finally:
        if agent_id and agent_created:
            cleanup_agent_sessions(page, frontend_url, agent_id)
            if assignment_created:
                remove_agent_assignment(
                    page, frontend_url, str(profile["id"]), agent_id
                )
            delete_agent(page, frontend_url, agent_id)
