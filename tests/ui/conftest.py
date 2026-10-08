"""Shared Playwright fixtures for browser based UI tests."""

import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest
from playwright.sync_api import Browser, Page, Route, sync_playwright

DEFAULT_SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip cluster-dependent UI tests outside the OpenShift E2E deployment."""
    if os.environ.get("TEST_E2E_DEPLOYMENT", "").lower() == "true":
        return

    skip_e2e = pytest.mark.skip(reason="Requires the OpenShift E2E deployment")
    for item in items:
        if item.get_closest_marker("e2e_only"):
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def frontend_url() -> str:
    """Return the UI base URL used by this test run."""
    return os.environ.get("TEST_FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    """Start Chromium and download its browser binary the first time if needed."""
    playwright = sync_playwright().start()
    try:
        chromium_executable = Path(playwright.chromium.executable_path)
        if not chromium_executable.is_file():
            print(
                "Chromium is not installed for this Playwright version; installing it now."
            )
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )

        browser_instance = playwright.chromium.launch(
            headless=os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
        )
        yield browser_instance
        browser_instance.close()
    finally:
        playwright.stop()


@pytest.fixture
def page(browser: Browser, request: pytest.FixtureRequest) -> Page:
    """Give each test a clean page and save a screenshot after it finishes."""
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    test_page = context.new_page()
    test_page.set_default_timeout(10_000)

    try:
        yield test_page
    finally:
        screenshot_dir = Path(
            os.environ.get("UI_SCREENSHOT_DIR", DEFAULT_SCREENSHOT_DIR)
        )
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        safe_test_name = re.sub(r"[^A-Za-z0-9._-]+", "_", request.node.nodeid)
        screenshot_path = screenshot_dir / f"{safe_test_name}.png"
        try:
            test_page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Saved UI screenshot: {screenshot_path}")
        finally:
            context.close()


@pytest.fixture
def knowledge_base_api(page: Page) -> dict[str, Any]:
    """Stub knowledge-base service calls to keep browser CRUD tests isolated."""
    state: dict[str, Any] = {
        "items": [],
        "created": [],
        "deleted": [],
    }

    def mock_embedding_models(route: Route) -> None:
        route.fulfill(
            status=200,
            json=[
                {
                    "name": "test-embedding-model",
                    "provider_resource_id": "test-embedding-provider",
                    "model_type": "embedding",
                }
            ],
        )

    def mock_providers(route: Route) -> None:
        route.fulfill(
            status=200,
            json=[
                {
                    "provider_id": "test-vector-provider",
                    "provider_type": "test-vector-store",
                    "config": {},
                    "api": "vector_io",
                }
            ],
        )

    def mock_knowledge_bases(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path

        if request.method == "GET" and path.endswith("/knowledge_bases/"):
            route.fulfill(status=200, json=state["items"])
            return

        if request.method == "POST" and path.endswith("/knowledge_bases/"):
            payload = request.post_data_json
            state["created"].append(payload)
            record = {
                **payload,
                "vector_store_id": "vs-playwright-test",
                "created_by": None,
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
                "status": "succeeded",
            }
            state["items"].append(record)
            route.fulfill(status=201, json=record)
            return

        if request.method == "DELETE":
            vector_store_name = unquote(path.rsplit("/", maxsplit=1)[-1])
            state["deleted"].append(vector_store_name)
            state["items"] = [
                item
                for item in state["items"]
                if item["vector_store_name"] != vector_store_name
            ]
            route.fulfill(status=204)
            return

        route.continue_()

    page.route("**/api/v1/llama_stack/embedding_models", mock_embedding_models)
    page.route("**/api/v1/llama_stack/providers", mock_providers)
    page.route("**/api/v1/knowledge_bases**", mock_knowledge_bases)
    return state
