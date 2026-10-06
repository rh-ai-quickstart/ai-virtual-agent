"""Provider registration and provider detail views using only mocked APIs."""

from urllib.parse import urlsplit

from playwright.sync_api import Page, Route, expect
from ui_mocks import mock_current_user

EXISTING_PROVIDER = {
    "provider_id": "remote-vllm",
    "provider_type": "remote::vllm",
    "api": "inference",
    "config": {"url": "https://inference.example.test/v1", "max_tokens": 4096},
}
EXISTING_MODEL = {
    "model_id": "remote-vllm/test-model",
    "provider_id": "remote-vllm",
    "provider_model_id": "test-model",
    "model_type": "llm",
    "metadata": {},
    "created_at": "2026-01-01T00:00:00Z",
}


def _open_providers(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("link", name="Model Providers").click()
    expect(page.get_by_role("heading", name="Model Providers")).to_be_visible(
        timeout=20_000
    )


def _click_register_card(page: Page) -> None:
    card = page.locator(".pf-v6-c-card").filter(
        has=page.get_by_role("heading", name="Register New Provider")
    )
    card.locator("button.pf-v6-c-card__clickable-action").click()


def test_provider_type_config_confirmation_and_success(
    page: Page, frontend_url: str
) -> None:
    state = {"providers": [], "requests": []}
    mock_current_user(page)

    def api(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path
        if path.endswith("/models/providers/") and request.method == "GET":
            route.fulfill(json=state["providers"])
        elif path.endswith("/models/") and request.method == "GET":
            route.fulfill(json=[])
        elif path.endswith("/models/providers/") and request.method == "POST":
            payload = request.post_data_json or {}
            state["requests"].append(payload)
            row = {**payload, "api": "inference"}
            state["providers"].append(row)
            route.fulfill(status=201, json=row)
        else:
            route.fulfill(status=404, json={"detail": "Not found"})

    page.route("**/api/v1/models/**", api)
    _open_providers(page, frontend_url)
    _click_register_card(page)
    expect(page.locator("#provider-form-token")).to_be_visible()
    expect(page.locator("#provider-form-max-tokens")).to_be_visible()
    page.locator("#provider-form-type").select_option("remote::ollama")
    expect(page.locator("#provider-form-token")).to_have_count(0)
    expect(page.locator("#provider-form-max-tokens")).to_have_count(0)
    page.locator("#provider-form-id").fill("ollama-test")
    page.locator("#provider-form-url").fill("http://ollama.example.test:11434")
    page.get_by_role("button", name="Register Provider").click()

    dialog = page.get_by_role("dialog")
    expect(
        dialog.get_by_role("heading", name="Confirm Provider Registration")
    ).to_be_visible()
    dialog.get_by_role("button", name="Cancel").click()
    assert state["requests"] == []
    page.get_by_role("button", name="Register Provider").click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Yes, Register Provider"
    ).click()

    expect(
        page.get_by_role("heading", name="Provider Registered Successfully")
    ).to_be_visible(timeout=15_000)
    expect(
        page.get_by_text('Provider "ollama-test" has been registered')
    ).to_be_visible()
    assert state["requests"] == [
        {
            "provider_id": "ollama-test",
            "provider_type": "remote::ollama",
            "config": {"url": "http://ollama.example.test:11434"},
        }
    ]
    page.get_by_role("dialog").get_by_role("button", name="OK").click()
    expect(page.get_by_role("heading", name="ollama-test")).to_be_visible(
        timeout=10_000
    )


def test_provider_vllm_error_and_provider_model_details(
    page: Page, frontend_url: str
) -> None:
    state = {"providers": [dict(EXISTING_PROVIDER)], "post_requests": []}
    mock_current_user(page)

    def api(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path
        if path.endswith("/models/providers/") and request.method == "GET":
            route.fulfill(json=state["providers"])
        elif path.endswith("/models/") and request.method == "GET":
            route.fulfill(json=[EXISTING_MODEL])
        elif path.endswith("/models/providers/") and request.method == "POST":
            state["post_requests"].append(request.post_data_json or {})
            route.fulfill(status=500, json={"detail": "Provider registration rejected"})
        else:
            route.fulfill(status=404, json={"detail": "Not found"})

    page.route("**/api/v1/models/**", api)
    _open_providers(page, frontend_url)
    provider_card = page.locator("#expandable-provider-card-remote-vllm")
    expect(provider_card).to_contain_text("1 model", timeout=15_000)
    page.locator("#toggle-provider-button-remote-vllm").click()
    expect(provider_card).to_contain_text("remote-vllm/test-model")
    expect(provider_card).to_contain_text("https://inference.example.test/v1")

    _click_register_card(page)
    page.locator("#provider-form-id").fill("vllm-failure")
    page.locator("#provider-form-url").fill("https://vllm.example.test/v1")
    page.locator("#provider-form-token").fill("test-token")
    page.locator("#provider-form-max-tokens").fill("2048")
    page.get_by_role("button", name="Register Provider").click()
    page.get_by_role("dialog").get_by_role(
        "button", name="Yes, Register Provider"
    ).click()

    expect(page.get_by_text("Provider registration rejected")).to_be_visible(
        timeout=15_000
    )
    expected_request = {
        "provider_id": "vllm-failure",
        "provider_type": "remote::vllm",
        "config": {
            "url": "https://vllm.example.test/v1",
            "api_token": "test-token",
            "max_tokens": 2048,
            "tls_verify": False,
        },
    }
    assert state["post_requests"]
    assert all(request == expected_request for request in state["post_requests"])


def test_provider_pages_show_empty_and_error_states(
    page: Page, frontend_url: str
) -> None:
    mock_current_user(page)
    state = {"fail": False}

    def api(route: Route) -> None:
        path = urlsplit(route.request.url).path
        if state["fail"]:
            route.fulfill(status=503, json={"detail": "Provider catalog unavailable"})
        elif path.endswith("/models/providers/"):
            route.fulfill(json=[])
        elif path.endswith("/models/"):
            route.fulfill(json=[])
        else:
            route.fulfill(status=404, json={"detail": "Not found"})

    page.route("**/api/v1/models/**", api)
    _open_providers(page, frontend_url)
    expect(page.get_by_text("No providers configured yet.")).to_be_visible(
        timeout=15_000
    )
    state["fail"] = True
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and response.url.endswith("/models/providers/")
    ):
        page.get_by_role("button", name="Refresh providers and models").click()
    expect(page.get_by_role("heading", name="Error loading providers")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_text("Provider catalog unavailable")).to_be_visible()
