"""MCP server management tests with discovery and service endpoints mocked."""

from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, Route, expect
from ui_mocks import mock_current_user


def _click_card(page: Page, title: str) -> None:
    card = page.locator(".pf-v6-c-card").filter(
        has=page.get_by_role("heading", name=title)
    )
    card.locator("button.pf-v6-c-card__clickable-action").click()


def _open_mcp(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("link", name="MCP Servers").click()
    expect(page.get_by_role("heading", name="MCP Servers")).to_be_visible(
        timeout=20_000
    )


def test_mcp_server_discovery_create_edit_and_delete(
    page: Page, frontend_url: str
) -> None:
    state = {"servers": [], "created": [], "updated": [], "deleted": []}
    mock_current_user(page)

    def api(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path
        if path.endswith("/discover"):
            route.fulfill(
                json=[
                    {
                        "name": "sample_tools",
                        "description": "Sample tools endpoint",
                        "endpoint_url": "https://mcp.example.test/api",
                        "source": "test catalog",
                    }
                ]
            )
        elif request.method == "GET":
            route.fulfill(json=state["servers"])
        elif request.method == "POST":
            payload = request.post_data_json or {}
            state["created"].append(payload)
            row = {
                **payload,
                "provider_id": "model-context-protocol",
                "created_at": "2026-10-05T12:00:00Z",
            }
            state["servers"].append(row)
            route.fulfill(status=201, json=row)
        elif request.method == "PUT":
            payload = request.post_data_json or {}
            server_id = unquote(path.rstrip("/").rsplit("/", 1)[-1])
            state["updated"].append({"id": server_id, **payload})
            row = {
                **payload,
                "provider_id": "model-context-protocol",
                "created_at": "2026-10-05T12:00:00Z",
            }
            state["servers"] = [
                row if s["toolgroup_id"] == server_id else s for s in state["servers"]
            ]
            route.fulfill(json=row)
        elif request.method == "DELETE":
            server_id = unquote(path.rstrip("/").rsplit("/", 1)[-1])
            state["deleted"].append(server_id)
            state["servers"] = [
                s for s in state["servers"] if s["toolgroup_id"] != server_id
            ]
            route.fulfill(status=204)
        else:
            route.fulfill(status=404, json={"detail": "Not found"})

    page.route("**/api/v1/mcp_servers/**", api)
    _open_mcp(page, frontend_url)
    expect(page.get_by_text("No MCP servers configured yet.")).to_be_visible()
    _click_card(page, "New MCP Server")
    expect(page.locator("#discovered-server-select")).to_be_visible()
    page.locator("#discovered-server-select").select_option("sample_tools")
    expect(page.locator("#mcp-form-name")).to_have_value("sample_tools")
    expect(page.locator("#mcp-form-toolgroup-id")).to_have_value("mcp::sample_tools")
    expect(page.locator("#mcp-form-endpoint")).to_have_value(
        "https://mcp.example.test/api"
    )
    page.locator("#mcp-form-name").fill("")
    expect(page.get_by_text("Name is required")).to_be_visible()
    expect(page.get_by_role("button", name="Create")).to_be_disabled()
    page.locator("#mcp-form-name").fill("sample_tools")
    page.locator("#mcp-form-description").fill("")
    page.locator("#mcp-form-endpoint").fill("not-a-url")
    page.locator("#mcp-form-config").fill("{invalid json")
    expect(page.get_by_text("Description is required")).to_be_visible()
    expect(page.get_by_text("Please enter a valid URL")).to_be_visible()
    expect(page.get_by_text("Invalid JSON format")).to_be_visible()
    expect(page.get_by_role("button", name="Create")).to_be_disabled()
    page.locator("#mcp-form-description").fill("Sample tools endpoint")
    page.locator("#mcp-form-endpoint").fill("https://mcp.example.test/api")
    page.locator("#mcp-form-config").fill('{"api_key":"mock-secret"}')
    page.get_by_role("button", name="Create").click()

    card = page.locator('[id="expandable-mcp-card-mcp::sample_tools"]')
    expect(card).to_contain_text("sample_tools", timeout=10_000)
    assert state["created"][0]["toolgroup_id"] == "mcp::sample_tools"
    assert state["created"][0]["configuration"] == {"api_key": "mock-secret"}

    card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Edit").click()
    expect(page.locator("#mcp-form-description")).to_have_value("Sample tools endpoint")
    page.locator("#mcp-form-description").fill("Edited description")
    page.get_by_role("button", name="Update").click()
    expect(
        page.locator('[id="expandable-mcp-card-mcp::sample_tools"]')
    ).to_contain_text("Edited description", timeout=10_000)
    assert state["updated"][0]["description"] == "Edited description"

    card = page.locator('[id="expandable-mcp-card-mcp::sample_tools"]')
    card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Delete").click()
    page.get_by_role("dialog").get_by_role("button", name="Cancel").click()
    expect(card).to_be_visible()
    card.get_by_role("button", name="kebab dropdown toggle").click()
    page.get_by_role("menuitem", name="Delete").click()
    page.get_by_role("dialog").get_by_role("button", name="Delete").click()
    expect(card).not_to_be_visible(timeout=10_000)
    assert state["deleted"] == ["mcp::sample_tools"]


def test_mcp_discovery_validation_and_api_error_refresh(
    page: Page, frontend_url: str
) -> None:
    mock_current_user(page)
    calls = {"list": 0, "discover": 0}

    def api(route: Route) -> None:
        path = urlsplit(route.request.url).path
        if path.endswith("/discover"):
            calls["discover"] += 1
            route.fulfill(status=503, json={"detail": "Discovery unavailable"})
        else:
            calls["list"] += 1
            route.fulfill(status=503, json={"detail": "MCP service unavailable"})

    page.route("**/api/v1/mcp_servers/**", api)
    _open_mcp(page, frontend_url)
    expect(page.get_by_role("heading", name="Error loading MCP servers")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_text("MCP service unavailable")).to_be_visible()
    with page.expect_response(
        lambda response: response.request.method == "GET"
        and response.url.endswith("/api/v1/mcp_servers/")
    ):
        page.get_by_role("button", name="Refresh MCP servers").click()
    with page.expect_response(
        lambda response: response.url.endswith("/api/v1/mcp_servers/discover")
    ):
        _click_card(page, "New MCP Server")
    expect(
        page.get_by_role("heading", name="Could not discover MCP servers")
    ).to_be_visible(timeout=15_000)
    assert calls["list"] >= 2
    # The query client retries failed requests, so discovery may be requested
    # more than once even though the user opened the form once.
    assert calls["discover"] >= 1
    expect(page.get_by_role("button", name="Create")).to_be_disabled()
