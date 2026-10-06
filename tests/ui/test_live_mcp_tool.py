"""Live MCP registration and tool invocation through chat."""

import re
import time
import uuid

import pytest
from live_test_utils import (
    assign_agent,
    cleanup_agent_sessions,
    delete_agent,
    parse_sse_events,
    remove_agent_assignment,
    require_admin,
)
from playwright.sync_api import Page, expect


@pytest.mark.e2e_only
def test_live_mcp_tool_can_be_registered_and_called_from_chat(
    page: Page, frontend_url: str
) -> None:
    """Register the discovered travel MCP server, call its tool, and clean up."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile = require_admin(page, frontend_url)
    discovered_response = page.request.get(
        f"{frontend_url}/api/v1/mcp_servers/discover", timeout=30_000
    )
    assert discovered_response.ok, (
        "Could not discover the deployment's MCP services: "
        f"HTTP {discovered_response.status} {discovered_response.text()}"
    )
    discovered_servers = discovered_response.json()
    travel_server = next(
        (
            server
            for server in discovered_servers
            if server.get("name") == "mcp-travel-research"
        ),
        None,
    )
    assert travel_server, (
        "The live MCP test requires the mcp-travel-research service, which is "
        "enabled in the E2E deployment"
    )

    models_response = page.request.get(f"{frontend_url}/api/v1/llama_stack/llms")
    assert models_response.ok, (
        "Could not list live inference models: "
        f"HTTP {models_response.status} {models_response.text()}"
    )
    models = models_response.json()
    assert models, "Live MCP inference requires at least one configured model"
    model_name = str(models[0]["model_name"])

    unique = uuid.uuid4().hex[:10]
    server_name = f"live-travel-{unique}"
    toolgroup_id = f"mcp::{server_name}"
    tool_name = "tavily_travel_search"
    agent_name = f"UI Live MCP Agent {unique}"
    agent_id: str | None = None
    server_created = False
    assignment_created = False

    try:
        page.get_by_role("link", name="Config").click()
        page.get_by_role("link", name="MCP Servers").click()
        new_server_card = page.locator(".pf-v6-c-card").filter(
            has=page.get_by_role("heading", name="New MCP Server")
        )
        new_server_card.locator("button.pf-v6-c-card__clickable-action").click()
        page.locator("#discovered-server-select").select_option(
            str(travel_server["name"])
        )
        name_input = page.locator("#mcp-form-name")
        expect(name_input).to_have_value("mcp-travel-research")
        name_input.fill(server_name)
        page.locator("#mcp-form-description").fill(
            "Temporary live travel MCP fixture for integration coverage"
        )
        expect(page.locator("#mcp-form-endpoint")).to_have_value(
            str(travel_server["endpoint_url"])
        )
        expect(page.locator("#mcp-form-toolgroup-id")).to_have_value(toolgroup_id)

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/mcp_servers/"),
            timeout=120_000,
        ) as create_server_response_info:
            page.get_by_role("button", name="Create").click()

        create_server_response = create_server_response_info.value
        assert create_server_response.status == 201, (
            "Live MCP registration failed: "
            f"HTTP {create_server_response.status} {create_server_response.text()}"
        )
        server_created = True
        registered_server = create_server_response.json()
        assert registered_server["toolgroup_id"] == toolgroup_id
        expect(page.get_by_text(server_name, exact=False)).to_be_visible(timeout=30_000)

        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            tools_response = page.request.get(
                f"{frontend_url}/api/v1/llama_stack/tools", timeout=15_000
            )
            assert tools_response.ok, (
                "Could not verify LlamaStack MCP registration: "
                f"HTTP {tools_response.status} {tools_response.text()}"
            )
            tools = tools_response.json()
            if any(tool.get("toolgroup_id") == toolgroup_id for tool in tools):
                break
            page.wait_for_timeout(5_000)
        else:
            pytest.fail(f"MCP toolgroup {toolgroup_id} did not appear in LlamaStack")

        agent_response = page.request.post(
            f"{frontend_url}/api/v1/virtual_agents/",
            data={
                "name": agent_name,
                "model_name": model_name,
                "prompt": (
                    f"When asked, call {tool_name} exactly once. Use the user's "
                    "requested travel destination as the query and set max_results "
                    "to 1. Return the tool result without adding outside information."
                ),
                "runner_type": "llamastack",
                "tools": [{"toolgroup_id": toolgroup_id}],
                "knowledge_base_ids": [],
                "input_shields": [],
                "output_shields": [],
                "temperature": 0.0,
                "top_p": 1.0,
                "max_tokens": 256,
                # Allow one tool call and its final answer without permitting
                # repeated tool rounds to exceed LlamaStack's conversation limit.
                "max_infer_iters": 2,
            },
        )
        assert agent_response.status == 201, (
            "Could not create the live MCP agent: "
            f"HTTP {agent_response.status} {agent_response.text()}"
        )
        agent_id = str(agent_response.json()["id"])
        assign_agent(page, frontend_url, str(profile["id"]), agent_id)
        assignment_created = True

        page.goto(f"{frontend_url}/?agentId={agent_id}", wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="Select model")).to_contain_text(
            agent_name, timeout=60_000
        )
        message_box = page.get_by_role("textbox").last
        expect(message_box).to_be_visible(timeout=30_000)
        message_box.fill("Search for Banff travel basics.")
        send_button = page.get_by_role(
            "button", name=re.compile("send", re.IGNORECASE)
        ).last
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/chat"),
            timeout=240_000,
        ) as chat_response_info:
            send_button.click()

        chat_response = chat_response_info.value
        assert chat_response.status == 200, (
            f"Live MCP chat failed: HTTP {chat_response.status} "
            f"{chat_response.text()}"
        )
        events = parse_sse_events(chat_response.text())
        errors = [event for event in events if event.get("type") == "error"]
        tool_events = [
            event
            for event in events
            if event.get("type") == "tool_call"
            and (
                event.get("name") == tool_name
                or str(event.get("name", "")).endswith(f"::{tool_name}")
            )
            and event.get("status") == "completed"
        ]
        assert (
            tool_events
        ), f"The model did not complete an MCP call to {tool_name}: {events}"
        assert any(
            str(event.get("output", "")).strip() for event in tool_events
        ), f"The live MCP tool returned no output: {tool_events}"
        text_only_error = (
            "The assistant couldn't generate a text response. Please try again or "
            "rephrase your request."
        )
        unexpected_errors = [
            event for event in errors if event.get("message") != text_only_error
        ]
        assert (
            not unexpected_errors
        ), f"Live MCP inference returned unexpected errors: {unexpected_errors}"
    finally:
        if agent_id:
            cleanup_agent_sessions(page, frontend_url, agent_id)
            if assignment_created:
                remove_agent_assignment(
                    page, frontend_url, str(profile["id"]), agent_id
                )
            delete_agent(page, frontend_url, agent_id)
        if server_created:
            delete_server_response = page.request.delete(
                f"{frontend_url}/api/v1/mcp_servers/{toolgroup_id}",
                timeout=120_000,
            )
            if not delete_server_response.ok:
                print(
                    f"Could not clean up MCP toolgroup {toolgroup_id}: "
                    f"HTTP {delete_server_response.status} "
                    f"{delete_server_response.text()}"
                )
