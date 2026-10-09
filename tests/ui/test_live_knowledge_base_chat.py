"""Live browser coverage for grounding chat answers in an existing knowledge base."""

import ast
import json
import os
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


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _contains_word_sequence(text: str, phrase: str) -> bool:
    text_words = _words(text)
    phrase_words = _words(phrase)
    width = len(phrase_words)
    return bool(width) and any(
        text_words[index : index + width] == phrase_words
        for index in range(len(text_words) - width + 1)
    )


def _search_result_text(output: str) -> str:
    """Extract passage text from LlamaStack's serialized file-search result list."""
    try:
        result: object = json.loads(output)
    except json.JSONDecodeError:
        try:
            result = ast.literal_eval(output)
        except (SyntaxError, ValueError):
            return output

    passages: list[str] = []

    def collect_text(value: object) -> None:
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                passages.append(text)
            else:
                for nested_value in value.values():
                    collect_text(nested_value)
        elif isinstance(value, (list, tuple)):
            for nested_value in value:
                collect_text(nested_value)

    collect_text(result)
    return "\n".join(passages) if passages else output


def _select_first_available_option(page: Page, selector: str, description: str) -> str:
    select = page.locator(selector)
    expect(select).to_be_visible(timeout=60_000)
    page.wait_for_function(
        """selector => {
          const element = document.querySelector(selector);
          return element && [...element.options].some(option => option.value && !option.disabled);
        }""",
        arg=selector,
        timeout=60_000,
    )
    options = select.locator("option").evaluate_all(
        "options => options"
        ".filter(option => option.value && !option.disabled)"
        ".map(option => option.value)"
    )
    assert options, f"The UI did not provide an available {description} option"
    select.select_option(options[0])
    return str(options[0])


@pytest.mark.e2e_only
def test_live_knowledge_base_ingestion_and_grounded_chat(
    page: Page, frontend_url: str
) -> None:
    """Create a knowledge base and RAG agent in the UI, then verify grounded chat."""
    source_url = os.getenv(
        "TEST_KB_SOURCE_URL",
        "https://raw.githubusercontent.com/burrsutter/sample-pdfs/main/"
        "FantaCo/HR/FantaCo-Fabulous-HR-Benefits.pdf",
    )
    expected_text = os.getenv("TEST_KB_EXPECTED_TEXT")

    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile = require_admin(page, frontend_url)
    # Select from the UI's rendered options, allowing E2E deployments to override
    # either choice when their model/provider configuration differs.
    embedding_model_override = os.getenv("TEST_KB_EMBEDDING_MODEL")
    provider_override = os.getenv("TEST_KB_VECTOR_PROVIDER")

    unique = uuid.uuid4().hex[:10]
    kb_name = f"UI Live Source {unique}"
    vector_store_name = f"ui-live-source-{unique}"
    agent_name = f"UI Live RAG {unique}"
    agent_id: str | None = None
    assignment_created = False
    knowledge_base_created = False

    try:
        # Create the knowledge base through the browser form so this covers the
        # same embedding-model and source-selection flow users rely on.
        page.get_by_role("link", name="Config").click()
        page.get_by_role("link", name="Knowledge Bases").click()
        new_kb_card = page.locator(".pf-v6-c-card").filter(
            has=page.get_by_role("heading", name="New Knowledge Base")
        )
        new_kb_card.locator("button.pf-v6-c-card__clickable-action").click()
        page.locator("#kb-form-name").fill(kb_name)
        page.locator("#kb-form-version").fill("v1")
        _select_first_available_option(
            page, "#kb-form-embedding-model", "embedding model"
        )
        _select_first_available_option(page, "#kb-form-provider-id", "vector provider")
        # Keep the environment overrides useful for E2E clusters with a
        # deployment-specific embedding configuration, and fail clearly if the
        # requested option is not actually offered by the UI.
        if embedding_model_override:
            page.locator("#kb-form-embedding-model").select_option(
                embedding_model_override
            )
        if provider_override:
            page.locator("#kb-form-provider-id").select_option(provider_override)
        page.locator("#kb-form-vector-store-name").fill(vector_store_name)
        page.locator("#kb-form-source").select_option("URL")
        page.get_by_placeholder("URL 1").fill(source_url)

        # The backend can persist the record before a pipeline submission error,
        # so try cleanup even if the UI's create request fails.
        knowledge_base_created = True
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/knowledge_bases/"),
            timeout=120_000,
        ) as create_kb_response_info:
            page.get_by_role("button", name="Submit").click()
        create_kb_response = create_kb_response_info.value
        assert create_kb_response.status == 201, (
            "Could not create a live knowledge base through the UI: "
            f"HTTP {create_kb_response.status} {create_kb_response.text()}"
        )
        created_kb = create_kb_response.json()
        assert created_kb.get("vector_store_name") == vector_store_name
        knowledge_base_card = page.locator(f"#expandable-kb-card-{vector_store_name}")
        expect(knowledge_base_card).to_be_visible(timeout=60_000)

        # Poll the status badge through the Knowledge Bases page. The final RAG
        # retrieval assertions below also verify that a reported success really
        # produced searchable document text.
        deadline = time.monotonic() + 900
        status = "unknown"
        while time.monotonic() < deadline:
            status = (
                knowledge_base_card.locator(".pf-v6-c-label").inner_text().casefold()
            )
            if status in {"succeeded", "success", "complete", "completed"}:
                break
            assert status not in {
                "failed",
                "error",
            }, f"Knowledge-base ingestion failed with status {status!r}"
            page.get_by_role("button", name="Refresh knowledge bases").click()
            page.wait_for_timeout(5_000)
        assert status in {"succeeded", "success", "complete", "completed"}, (
            "Knowledge-base ingestion did not complete within 15 minutes; "
            f"the UI still reports {status!r}"
        )

        page.get_by_role("link", name="Agents", exact=True).click()
        new_agent_card = page.locator(".pf-v6-c-card").filter(
            has=page.get_by_role("heading", name="New Agent")
        )
        new_agent_card.locator("button.pf-v6-c-card__clickable-action").click()
        page.locator("#agent-name").fill(agent_name)
        _select_first_available_option(page, "#ai-model", "inference model")
        page.locator("#prompt").fill(
            "Use the attached knowledge base to answer. Copy one factual sentence "
            "exactly from a retrieved passage."
        )
        tools_input = page.locator("#tools-multiselect-component-input")
        tools_input.click()
        rag_option = page.locator('[id="tools-option-builtin::rag"]')
        expect(rag_option).to_be_visible(timeout=60_000)
        rag_option.click()

        knowledge_bases_input = page.locator(
            "#knowledge-bases-multiselect-component-input"
        )
        expect(knowledge_bases_input).to_be_enabled(timeout=60_000)
        knowledge_bases_input.click()
        kb_option = page.get_by_role(
            "option", name=f"{kb_name} ({vector_store_name})", exact=True
        )
        expect(kb_option).to_be_visible(timeout=60_000)
        kb_option.click()
        knowledge_bases_input.press("Escape")

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/virtual_agents/"),
            timeout=60_000,
        ) as create_agent_response_info:
            page.get_by_role("button", name="Submit").click()
        create_agent_response = create_agent_response_info.value
        assert create_agent_response.status == 201, (
            "Could not create a live RAG agent: "
            f"HTTP {create_agent_response.status} {create_agent_response.text()}"
        )
        created_agent = create_agent_response.json()
        agent_id = str(created_agent["id"])
        assert vector_store_name in created_agent.get("knowledge_base_ids", [])
        assign_agent(page, frontend_url, str(profile["id"]), agent_id)
        assignment_created = True

        page.goto(f"{frontend_url}/?agentId={agent_id}", wait_until="domcontentloaded")
        question = (
            "Search the attached knowledge base and answer with one factual sentence "
            "copied exactly from a retrieved passage."
            if not expected_text
            else "Search the attached knowledge base and return this phrase verbatim: "
            f"{expected_text}"
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
            f"Live RAG chat failed: HTTP {chat_response.status} "
            f"{chat_response.text()}"
        )
        events = parse_sse_events(chat_response.text())
        assert not [
            event for event in events if event.get("type") == "error"
        ], f"Live RAG inference returned errors: {events}"
        search_outputs = [
            _search_result_text(str(event.get("output", "")))
            for event in events
            if event.get("type") == "tool_call"
            and event.get("name") == "knowledge_search"
            and event.get("status") == "completed"
        ]
        assert any(
            output.strip() for output in search_outputs
        ), "The live retrieval returned no passage text from the ingested source"
        answer = "".join(
            str(event.get("delta", ""))
            for event in events
            if event.get("type") == "response"
        )
        if expected_text:
            assert any(
                _contains_word_sequence(output, expected_text)
                for output in search_outputs
            ), (
                "The live retrieval did not return the configured fixture phrase "
                f"{expected_text!r}: {search_outputs!r}"
            )
            assert _contains_word_sequence(answer, expected_text), (
                "The assistant did not include the configured phrase in its answer: "
                f"{answer!r}"
            )
        else:
            answer_words = _words(answer)
            matching_answer_sequence = any(
                any(
                    _contains_word_sequence(
                        output, " ".join(answer_words[index : index + 5])
                    )
                    for output in search_outputs
                )
                for index in range(len(answer_words) - 4)
            )
            assert matching_answer_sequence, (
                "The assistant did not repeat a factual sentence from the newly "
                "ingested source. "
                f"Answer: {answer!r}; search output: "
                f"{[output[:1500] for output in search_outputs]!r}"
            )
        assert any(
            event.get("type") == "response" and event.get("status") == "completed"
            for event in events
        ), "Live RAG chat ended without a completed assistant response"
    finally:
        if agent_id:
            cleanup_agent_sessions(page, frontend_url, agent_id)
            if assignment_created:
                remove_agent_assignment(
                    page, frontend_url, str(profile["id"]), agent_id
                )
            delete_agent(page, frontend_url, agent_id)
        if knowledge_base_created:
            delete_kb_response = page.request.delete(
                f"{frontend_url}/api/v1/knowledge_bases/{vector_store_name}",
                timeout=120_000,
            )
            if not delete_kb_response.ok:
                print(
                    f"Could not clean up knowledge base {vector_store_name}: "
                    f"HTTP {delete_kb_response.status} {delete_kb_response.text()}"
                )
