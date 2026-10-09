"""Mocked user administration, profile permissions, and auth redirect flows."""

import re
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, Route, expect
from ui_mocks import ADMIN, AGENTS, mock_current_user


def _click_new_user(page: Page) -> None:
    card = page.locator(".pf-v6-c-card").filter(
        has=page.get_by_role("heading", name="New User")
    )
    card.locator("button.pf-v6-c-card__clickable-action").click()


def _install_user_api(page: Page, *, current_user: dict | None = None) -> dict:
    state = {
        "users": [
            {
                "id": "user-target",
                "username": "target_user",
                "email": "target@example.test",
                "role": "user",
                "agent_ids": ["agent-alpha"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ],
        "created": [],
        "updated": [],
        "assignments": [],
        "removed": [],
        "deleted": [],
    }
    identity = current_user or ADMIN
    mock_current_user(page, identity)
    page.route("**/api/v1/virtual_agents/**", lambda route: route.fulfill(json=AGENTS))
    page.route(
        "**/api/v1/users/ui-admin/agents",
        lambda route: route.fulfill(json=identity.get("agent_ids", [])),
    )

    def users(route: Route) -> None:
        request = route.request
        path = urlsplit(request.url).path.rstrip("/")
        parts = path.split("/")
        if request.method == "GET" and path.endswith("/users/profile"):
            route.fulfill(json=identity)
        elif request.method == "GET" and path.endswith("/users"):
            route.fulfill(json=state["users"])
        elif request.method == "POST" and path.endswith("/users"):
            payload = request.post_data_json or {}
            state["created"].append(payload)
            row = {
                **payload,
                "id": "user-created",
                "agent_ids": payload.get("agent_ids", []),
                "created_at": "2026-10-05T12:00:00Z",
                "updated_at": "2026-10-05T12:00:00Z",
            }
            state["users"].append(row)
            route.fulfill(status=201, json=row)
        elif len(parts) >= 6 and parts[-1] == "agents" and request.method == "GET":
            user_id = parts[-2]
            row = next(
                (item for item in state["users"] if item["id"] == user_id),
                identity if identity["id"] == user_id else None,
            )
            route.fulfill(json=(row or {}).get("agent_ids", []))
        elif (
            len(parts) >= 6
            and parts[-1] == "agents"
            and request.method in {"POST", "DELETE"}
        ):
            user_id = parts[-2]
            row = next(item for item in state["users"] if item["id"] == user_id)
            payload = request.post_data_json or {}
            if request.method == "POST":
                state["assignments"].append(payload)
                row["agent_ids"] = list(
                    dict.fromkeys(
                        [*row.get("agent_ids", []), *payload.get("agent_ids", [])]
                    )
                )
            else:
                state["removed"].append(payload)
                row["agent_ids"] = [
                    agent_id
                    for agent_id in row.get("agent_ids", [])
                    if agent_id not in payload.get("agent_ids", [])
                ]
            route.fulfill(json=row)
        elif request.method == "GET" and len(parts) == 5:
            user_id = parts[-1]
            row = next(
                (item for item in state["users"] if item["id"] == user_id),
                identity if identity["id"] == user_id else None,
            )
            route.fulfill(
                status=200 if row else 404, json=row or {"detail": "User not found"}
            )
        elif request.method == "PUT":
            user_id = parts[-1]
            payload = request.post_data_json or {}
            state["updated"].append(payload)
            row = next(item for item in state["users"] if item["id"] == user_id)
            row.update(payload)
            route.fulfill(json=row)
        elif request.method == "DELETE":
            user_id = parts[-1]
            state["deleted"].append(user_id)
            state["users"] = [item for item in state["users"] if item["id"] != user_id]
            route.fulfill(status=204)
        else:
            route.fulfill(
                status=404,
                json={"detail": f"Unhandled user API {request.method} {path}"},
            )

    page.route("**/api/v1/users/**", users)
    return state


def _open_users(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("link", name="Users").click()
    expect(page.get_by_role("heading", name="Users")).to_be_visible(timeout=20_000)


def test_admin_creates_user_with_validation_role_and_agent_assignment(
    page: Page, frontend_url: str
) -> None:
    state = _install_user_api(page)
    _open_users(page, frontend_url)
    _click_new_user(page)
    create = page.get_by_role("button", name="Create User")
    expect(create).to_be_disabled()
    page.locator("#user-form-username").fill("bad name")
    expect(
        page.get_by_text(
            "Username can only contain letters, numbers, hyphens, and underscores"
        )
    ).to_be_visible()
    page.locator("#user-form-email").fill("not-an-email")
    expect(page.get_by_text("Please enter a valid email address")).to_be_visible()
    page.locator("#user-form-username").fill("new_operator")
    page.locator("#user-form-email").fill("operator@example.test")
    page.locator("#user-form-role").select_option("devops")
    page.get_by_role("button", name="Add Agent").click()
    page.get_by_role("menuitem", name="Beta Assistant").click()
    create.click()

    expect(page.get_by_text("@new_operator")).to_be_visible(timeout=10_000)
    assert state["created"] == [
        {
            "username": "new_operator",
            "email": "operator@example.test",
            "role": "devops",
            "agent_ids": ["agent-beta"],
        }
    ]


def test_admin_edits_profile_assignments_and_confirms_delete(
    page: Page, frontend_url: str
) -> None:
    state = _install_user_api(page)
    _open_users(page, frontend_url)
    page.get_by_role("button", name="View Profile").first.click()
    expect(page.get_by_role("heading", name="User Profile")).to_be_visible(
        timeout=15_000
    )
    page.get_by_role("button", name="Edit Profile").click()
    page.locator("#user-form-email").fill("updated@example.test")
    page.get_by_role("button", name="Save Changes").first.click()
    expect(page.get_by_text("updated@example.test")).to_be_visible(timeout=10_000)
    assert state["updated"][0]["email"] == "updated@example.test"

    page.get_by_role("button", name="Add Agent").click()
    page.get_by_role("menuitem", name="Beta Assistant").click()
    expect(
        page.get_by_role("list", name="Label group category").get_by_text(
            "Beta Assistant", exact=True
        )
    ).to_be_visible()
    expect(page.get_by_role("button", name="Remove Beta Assistant")).to_be_visible()
    assert state["assignments"][-1] == {"agent_ids": ["agent-alpha", "agent-beta"]}
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Remove Alpha Assistant").click()
    expect(page.get_by_role("button", name="Remove Alpha Assistant")).to_have_count(0)
    assert state["removed"][-1] == {"agent_ids": ["agent-alpha"]}

    page.get_by_role("button", name="Delete Profile").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("target_user")
    dialog.get_by_role("button", name="Cancel").click()
    expect(page.get_by_role("heading", name="User Profile")).to_be_visible()
    page.get_by_role("button", name="Delete Profile").click()
    page.get_by_role("dialog").get_by_role("button", name="Delete Profile").click()
    expect(page.get_by_role("heading", name="Users", exact=True)).to_be_visible(
        timeout=10_000
    )
    assert state["deleted"] == ["user-target"]


def test_non_admin_profile_permissions_admin_denial_and_auth_redirect(
    page: Page, frontend_url: str
) -> None:
    non_admin = {
        "id": "self-user",
        "username": "self",
        "email": "self@example.test",
        "role": "user",
        "agent_ids": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    _install_user_api(page, current_user=non_admin)
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    expect(page.get_by_role("heading", name="User Profile")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_role("button", name="Add Agent")).to_be_visible()
    expect(page.get_by_role("button", name="Edit Profile")).to_have_count(0)
    expect(page.get_by_role("button", name="Delete Profile")).to_have_count(0)

    page.goto(f"{frontend_url}/config/agents", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Access Denied")).to_be_visible(
        timeout=15_000
    )

    page.unroute("**/api/v1/users/profile")
    page.route(
        "**/api/v1/users/profile",
        lambda route: route.fulfill(status=401, json={"detail": "Not authenticated"}),
    )
    page.goto(f"{frontend_url}/config/agents", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/oauth/sign_in\?redirect="), timeout=15_000)
    assert "/config/agents" in unquote(urlsplit(page.url).query)


def test_users_page_reports_api_error(page: Page, frontend_url: str) -> None:
    mock_current_user(page)

    def user_error(route: Route) -> None:
        if urlsplit(route.request.url).path.endswith("/users/profile"):
            route.fulfill(json=ADMIN)
        else:
            route.fulfill(status=503, json={"detail": "User directory unavailable"})

    page.route("**/api/v1/users/**", user_error)
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("link", name="Users").click()
    expect(page.get_by_role("heading", name="Error loading users")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_text("User directory unavailable")).to_be_visible()
