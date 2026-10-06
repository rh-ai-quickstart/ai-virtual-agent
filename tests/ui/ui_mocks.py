"""Shared mock records and identity routes for isolated UI workflows."""

from typing import Any

from playwright.sync_api import Page, Route

ADMIN = {
    "id": "ui-admin",
    "username": "ui-admin",
    "email": "ui-admin@example.test",
    "role": "admin",
    "agent_ids": ["agent-alpha", "agent-beta"],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

MODEL = {
    "model_name": "test-model",
    "provider_resource_id": "test-provider",
    "model_type": "llm",
    "display_name": "Test Model",
}

AGENTS = [
    {
        "id": "agent-alpha",
        "name": "Alpha Assistant",
        "model_name": "test-model",
        "prompt": "Help with alpha topics.",
        "tools": [],
        "knowledge_base_ids": [],
        "input_shields": [],
        "output_shields": [],
        "created_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": "agent-beta",
        "name": "Beta Assistant",
        "model_name": "test-model",
        "prompt": "Help with beta topics.",
        "tools": [],
        "knowledge_base_ids": [],
        "input_shields": [],
        "output_shields": [],
        "created_at": "2026-01-02T00:00:00Z",
    },
]


def mock_current_user(
    page: Page, user: dict[str, Any] | None = None, status: int = 200
) -> None:
    """Mock the authenticated-user endpoint; call before navigating."""
    profile = user or ADMIN

    def handler(route: Route) -> None:
        if status == 200:
            route.fulfill(status=status, json=profile)
        else:
            route.fulfill(status=status, json={"detail": "Not authenticated"})

    page.route("**/api/v1/users/profile", handler)


def mock_common_agent_lookups(
    page: Page, agents: list[dict[str, Any]] | None = None
) -> None:
    """Mock model/tool/KB/shield and agent lookups used in administration forms."""
    records = agents if agents is not None else AGENTS
    page.route("**/api/v1/virtual_agents/**", lambda route: route.fulfill(json=records))
    page.route("**/api/v1/llama_stack/llms", lambda route: route.fulfill(json=[MODEL]))
    page.route(
        "**/api/v1/llama_stack/tools",
        lambda route: route.fulfill(
            json=[{"toolgroup_id": "builtin::rag", "name": "rag"}]
        ),
    )
    page.route("**/api/v1/knowledge_bases/**", lambda route: route.fulfill(json=[]))
    page.route("**/api/v1/llama_stack/shields", lambda route: route.fulfill(json=[]))
    page.route(
        "**/api/v1/users/ui-admin/agents",
        lambda route: route.fulfill(json=[a["id"] for a in records]),
    )
