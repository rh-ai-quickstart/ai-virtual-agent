"""Live coverage for the chart's seeded default knowledge-base pipeline."""

import ast
import json
import re
import time
import uuid

import pytest
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

DEFAULT_VECTOR_STORE = "zippity-zoo-vector-db"
DEFAULT_DOCUMENT_MARKER = "breatharian"


def _search_passages(output: str) -> str:
    """Extract indexed passage text from LlamaStack's serialized tool output."""
    try:
        result: object = json.loads(output)
    except json.JSONDecodeError:
        try:
            result = ast.literal_eval(output)
        except (SyntaxError, ValueError):
            return output

    passages: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                passages.append(text)
            else:
                for nested in value.values():
                    collect(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                collect(nested)

    collect(result)
    return "\n".join(passages) if passages else output


@pytest.mark.e2e_only
def test_live_default_ingestion_pipeline_indexes_and_serves_seeded_document(
    page: Page, frontend_url: str
) -> None:
    """Verify the installed default pipeline indexed its storage sample for RAG."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile = require_admin(page, frontend_url)
    model_name = live_model(page, frontend_url)
    unique = uuid.uuid4().hex[:10]
    agent_name = f"UI Live Default Pipeline {unique}"
    agent_id: str | None = None
    assignment_created = False

    try:
        # The default pipeline is installed by a Kubernetes Job. Poll through the
        # same vector-store validation used by agent creation until it is indexed.
        deadline = time.monotonic() + 900
        last_detail = "the seeded vector store is not available yet"
        while time.monotonic() < deadline:
            create_response = page.request.post(
                f"{frontend_url}/api/v1/virtual_agents/",
                data={
                    "name": agent_name,
                    "model_name": model_name,
                    "prompt": (
                        "For questions about FantaCo employee benefits, use the "
                        "attached knowledge base and answer from retrieved passages. "
                        "Do not invent search syntax or use outside information."
                    ),
                    "runner_type": "llamastack",
                    "tools": [{"toolgroup_id": "builtin::rag"}],
                    "knowledge_base_ids": [DEFAULT_VECTOR_STORE],
                    "max_infer_iters": 2,
                },
                timeout=60_000,
            )
            if create_response.status == 201:
                created_agent = create_response.json()
                agent_id = str(created_agent["id"])
                assert DEFAULT_VECTOR_STORE in created_agent.get(
                    "knowledge_base_ids", []
                ), "The live agent did not retain the seeded vector store"
                break

            last_detail = create_response.text()
            if create_response.status != 400 or DEFAULT_VECTOR_STORE not in last_detail:
                raise AssertionError(
                    "Could not create a live agent against the chart's default "
                    f"vector store: HTTP {create_response.status} {last_detail}"
                )
            page.wait_for_timeout(5_000)
        assert agent_id, (
            "The chart's default ingestion pipeline did not make its seeded vector "
            f"store available within 15 minutes: {last_detail}"
        )

        assign_agent(page, frontend_url, str(profile["id"]), agent_id)
        assignment_created = True
        page.goto(f"{frontend_url}/?agentId={agent_id}", wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="Select model")).to_contain_text(
            agent_name, timeout=60_000
        )

        question = (
            "According to FantaCo's employee benefits document, what unusual dietary "
            "restrictions can the benefits team accommodate? Give one example."
        )
        message_box = page.get_by_role("textbox").last
        expect(message_box).to_be_visible(timeout=60_000)
        message_box.fill(question)
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
            "Live default-pipeline chat failed: "
            f"HTTP {chat_response.status} {chat_response.text()}"
        )
        events = parse_sse_events(chat_response.text())
        errors = [event for event in events if event.get("type") == "error"]
        assert not errors, f"Live default-pipeline inference returned errors: {errors}"

        search_events = [
            event
            for event in events
            if event.get("type") == "tool_call"
            and event.get("name") == "knowledge_search"
            and event.get("status") == "completed"
        ]
        assert search_events, (
            "The live chat did not complete a knowledge search against the seeded "
            f"default pipeline: {events}"
        )
        passages = "\n".join(
            _search_passages(str(event.get("output", ""))) for event in search_events
        )
        assert (
            passages.strip()
        ), "The default pipeline's vector store returned no indexed passage text"
        passage_words = set(re.findall(r"[a-z0-9]+", passages.casefold()))
        assert DEFAULT_DOCUMENT_MARKER in passage_words, (
            "The default pipeline did not retrieve the expected FantaCo sample "
            f"document text containing {DEFAULT_DOCUMENT_MARKER!r}: "
            f"{passages[:1500]!r}"
        )

        answer = "".join(
            str(event.get("delta", ""))
            for event in events
            if event.get("type") == "response"
        )
        expect(page.get_by_text(question, exact=True)).to_be_visible()
        if answer.strip():
            expect(page.get_by_text(answer, exact=False).last).to_be_visible()
        assert any(
            event.get("type") == "response" and event.get("status") == "completed"
            for event in events
        ), "Live default-pipeline chat ended without a completed assistant response"
    finally:
        if agent_id:
            cleanup_agent_sessions(page, frontend_url, agent_id)
            if assignment_created:
                remove_agent_assignment(
                    page, frontend_url, str(profile["id"]), agent_id
                )
            delete_agent(page, frontend_url, agent_id)
