"""Browser coverage for knowledge-base navigation, source forms, and CRUD."""

import re
import uuid
from typing import Any

from playwright.sync_api import Page, expect


def open_knowledge_bases(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("link", name="Knowledge Bases").click()
    expect(page.get_by_role("heading", name="Knowledge Bases")).to_be_visible()


def click_new_knowledge_base_card(page: Page) -> None:
    card = page.locator(".pf-v6-c-card").filter(
        has=page.get_by_role("heading", name="New Knowledge Base")
    )
    card.locator("button.pf-v6-c-card__clickable-action").click()


def open_new_knowledge_base_form(page: Page, frontend_url: str) -> None:
    open_knowledge_bases(page, frontend_url)
    click_new_knowledge_base_card(page)
    expect(page.locator("#kb-form-name")).to_be_visible()


def test_knowledge_base_page_and_create_form_load(
    page: Page, frontend_url: str, knowledge_base_api: dict[str, Any]
) -> None:
    open_knowledge_bases(page, frontend_url)
    expect(page.get_by_text("No knowledge bases configured yet.")).to_be_visible()

    click_new_knowledge_base_card(page)
    expect(page.locator("#kb-form-name")).to_be_visible()

    expect(page.locator("#kb-form-version")).to_be_visible()
    expect(page.get_by_label("Select Embedding Model")).to_be_visible()
    expect(page.get_by_label("Select Provider")).to_be_visible()
    expect(page.get_by_label("Select Source")).to_be_visible()
    submit = page.get_by_role("button", name="Submit")
    expect(submit).to_be_visible()
    expect(submit).to_be_disabled()
    assert knowledge_base_api["items"] == []


def test_s3_source_shows_credentials_and_requires_https(
    page: Page, frontend_url: str, knowledge_base_api: dict[str, Any]
) -> None:
    open_new_knowledge_base_form(page, frontend_url)
    page.locator("#kb-form-source").select_option("S3")

    for field_id in (
        "#kb-form-s3-access-key",
        "#kb-form-s3-secret-key",
        "#kb-form-s3-endpoint",
        "#kb-form-s3-bucket",
        "#kb-form-s3-region",
    ):
        expect(page.locator(field_id)).to_be_visible()

    endpoint = page.locator("#kb-form-s3-endpoint")
    endpoint.fill("http://s3.example.test")
    expect(page.get_by_text("Endpoint URL should use HTTPS")).to_be_visible()

    endpoint.fill("https://s3.example.test")
    expect(page.get_by_text("Endpoint URL should use HTTPS")).to_have_count(0)

    region = page.locator("#kb-form-s3-region")
    region.fill("US_EAST_1")
    expect(
        page.get_by_text(
            "Region should contain only lowercase letters, numbers, and hyphens"
        )
    ).to_be_visible()
    region.fill("us-east-1")
    expect(
        page.get_by_text(
            "Region should contain only lowercase letters, numbers, and hyphens"
        )
    ).to_have_count(0)
    assert knowledge_base_api["created"] == []


def test_github_source_validates_repository_and_relative_path(
    page: Page, frontend_url: str, knowledge_base_api: dict[str, Any]
) -> None:
    open_new_knowledge_base_form(page, frontend_url)
    page.locator("#kb-form-source").select_option("GITHUB")

    repository_url = page.locator("#kb-form-github-url")
    repository_url.fill("https://example.test/owner/repo")
    expect(page.get_by_text("Must be a GitHub repository URL")).to_be_visible()

    repository_url.fill("https://github.com/owner/repo")
    expect(page.get_by_text("Must be a GitHub repository URL")).to_have_count(0)

    repository_path = page.locator("#kb-form-github-path")
    repository_path.fill("../private")
    expect(
        page.get_by_text('Path should be relative and not contain ".."')
    ).to_be_visible()

    repository_path.fill("docs/guides")
    expect(
        page.get_by_text('Path should be relative and not contain ".."')
    ).to_have_count(0)
    assert knowledge_base_api["created"] == []


def test_url_source_supports_multiple_validated_urls(
    page: Page, frontend_url: str, knowledge_base_api: dict[str, Any]
) -> None:
    open_new_knowledge_base_form(page, frontend_url)
    page.locator("#kb-form-source").select_option("URL")

    first_url = page.get_by_placeholder("URL 1")
    first_url.fill("ftp://docs.example.test")
    expect(page.get_by_text("URL must start with http:// or https://")).to_be_visible()

    first_url.fill("https://docs.example.test/guide")
    expect(page.get_by_text("URL must start with http:// or https://")).to_have_count(0)

    page.get_by_role("button", name="+ Add URL").click()
    second_url = page.get_by_placeholder("URL 2")
    expect(second_url).to_be_visible()
    second_url.fill("https://docs.example.test/reference")
    expect(page.get_by_placeholder(re.compile(r"^URL "))).to_have_count(2)

    page.get_by_role("button", name="Remove").nth(1).click()
    expect(page.get_by_placeholder(re.compile(r"^URL "))).to_have_count(1)
    assert knowledge_base_api["created"] == []


def test_knowledge_base_can_be_created_expanded_and_deleted_in_ui(
    page: Page, frontend_url: str, knowledge_base_api: dict[str, Any]
) -> None:
    open_new_knowledge_base_form(page, frontend_url)

    vector_store_name = f"playwright-kb-{uuid.uuid4().hex[:8]}"
    page.locator("#kb-form-name").fill("Browser Test Knowledge Base")
    page.locator("#kb-form-version").fill("v1")
    page.get_by_label("Select Embedding Model").select_option("test-embedding-model")
    page.get_by_label("Select Provider").select_option("test-vector-provider")
    page.locator("#kb-form-vector-store-name").fill(vector_store_name)
    page.locator("#kb-form-source").select_option("URL")
    page.get_by_placeholder("URL 1").fill("https://docs.example.test/guide")

    submit = page.get_by_role("button", name="Submit")
    expect(submit).to_be_enabled()
    submit.click()

    knowledge_base_card = page.locator(f"#expandable-kb-card-{vector_store_name}")
    expect(knowledge_base_card).to_contain_text("Browser Test Knowledge Base")
    expect(knowledge_base_card).to_contain_text("test-embedding-model")
    assert knowledge_base_api["created"][0]["source_configuration"] == [
        "https://docs.example.test/guide"
    ]

    knowledge_base_card.get_by_role("button", name=re.compile(r"Details")).click()
    expect(knowledge_base_card).to_contain_text("Version: v1")
    expect(knowledge_base_card).to_contain_text(f"Vector Store: {vector_store_name}")
    expect(knowledge_base_card).to_contain_text("Source: URL")

    knowledge_base_card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Delete").click()
    delete_dialog = page.get_by_role("dialog")
    expect(delete_dialog).to_contain_text(
        "Are you sure you want to delete this knowledge base?"
    )
    delete_dialog.get_by_role("button", name="Cancel").click()
    expect(knowledge_base_card).to_be_visible()

    knowledge_base_card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Delete").click()
    page.get_by_role("dialog").get_by_role("button", name="Delete").click()

    expect(page.locator(f"#expandable-kb-card-{vector_store_name}")).to_have_count(0)
    assert knowledge_base_api["deleted"] == [vector_store_name]
