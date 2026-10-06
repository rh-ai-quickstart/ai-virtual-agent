"""Live browser and API authorization coverage for non-admin users."""

import uuid

import pytest
from live_test_utils import require_admin
from playwright.sync_api import Page, expect


def test_live_non_admin_cannot_open_or_mutate_user_administration(
    page: Page, frontend_url: str
) -> None:
    """Create a real user, authenticate as that user, and verify admin denial."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    require_admin(page, frontend_url)

    unique = uuid.uuid4().hex[:10]
    username = f"ui-live-user-{unique}"
    email = f"ui-live-user-{unique}@example.test"
    user_id: str | None = None
    non_admin_page: Page | None = None

    try:
        create_response = page.request.post(
            f"{frontend_url}/api/v1/users/",
            data={
                "username": username,
                "email": email,
                "role": "user",
                "agent_ids": [],
            },
        )
        assert create_response.status == 201, (
            "Could not create live non-admin test identity: "
            f"HTTP {create_response.status} {create_response.text()}"
        )
        user_id = str(create_response.json()["id"])

        non_admin_page = page.context.new_page()
        non_admin_page.set_extra_http_headers(
            {"X-Forwarded-User": username, "X-Forwarded-Email": email}
        )
        non_admin_page.goto(
            f"{frontend_url}/config/users", wait_until="domcontentloaded"
        )
        expect(
            non_admin_page.get_by_role("heading", name="Access Denied")
        ).to_be_visible(timeout=30_000)
        expect(non_admin_page.get_by_text("Your current role: user")).to_be_visible()

        current_profile = _read_profile_from_page(non_admin_page)
        assert current_profile == {"username": username, "role": "user"}

        users_status = non_admin_page.evaluate(
            """async () => (await fetch('/api/v1/users/')).status"""
        )
        assert (
            users_status == 403
        ), f"Expected the live users API to deny a non-admin, got HTTP {users_status}"

        create_status = non_admin_page.evaluate(
            """async (payload) => (await fetch('/api/v1/users/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })).status""",
            {
                "username": f"denied-create-{unique}",
                "email": f"denied-create-{unique}@example.test",
                "role": "user",
                "agent_ids": [],
            },
        )
        assert create_status == 403, (
            "Expected the live users API to deny user creation by a non-admin, "
            f"got HTTP {create_status}"
        )
    finally:
        if non_admin_page:
            non_admin_page.close()
        if user_id:
            delete_response = page.request.delete(
                f"{frontend_url}/api/v1/users/{user_id}"
            )
            if not delete_response.ok:
                print(
                    f"Could not clean up non-admin user {user_id}: "
                    f"HTTP {delete_response.status} {delete_response.text()}"
                )


def _read_profile_from_page(page: Page) -> dict[str, str]:
    """Read profile through the page so its forwarded identity headers apply."""
    profile = page.evaluate("""async () => {
            const response = await fetch('/api/v1/users/profile');
            if (!response.ok) return { status: response.status };
            const value = await response.json();
            return { username: value.username, role: value.role };
        }""")
    if profile.get("status"):
        pytest.fail(f"Non-admin profile request returned HTTP {profile['status']}")
    return profile
