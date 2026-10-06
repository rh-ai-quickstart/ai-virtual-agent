"""Live browser coverage for the admin user create, edit, and delete flow."""

import uuid

import pytest
from playwright.sync_api import Page, expect


def _open_users(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()
    page.get_by_role("link", name="Users").click()
    expect(page.get_by_role("heading", name="Users", exact=True)).to_be_visible(
        timeout=30_000
    )


def _report_cleanup_failure(label: str, response) -> None:
    if not response.ok:
        print(f"Could not clean up {label}: HTTP {response.status} {response.text()}")


def test_live_admin_can_create_edit_and_delete_user(
    page: Page, frontend_url: str
) -> None:
    """Use the real admin API through the browser and remove the temporary user."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    profile_response = page.request.get(f"{frontend_url}/api/v1/users/profile")
    if not profile_response.ok:
        pytest.skip(
            "Live user management needs an authenticated admin user; "
            f"profile returned HTTP {profile_response.status}"
        )
    if profile_response.json().get("role") != "admin":
        pytest.skip("Live user management coverage requires an admin user")

    unique = uuid.uuid4().hex[:10]
    username = f"ui-live-{unique}"
    email = f"ui-live-{unique}@example.test"
    updated_email = f"ui-live-updated-{unique}@example.test"
    user_id: str | None = None

    try:
        _open_users(page, frontend_url)
        new_user_card = page.locator(".pf-v6-c-card").filter(
            has=page.get_by_role("heading", name="New User")
        )
        new_user_card.locator("button.pf-v6-c-card__clickable-action").click()
        page.locator("#user-form-username").fill(username)
        page.locator("#user-form-email").fill(email)

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/users/"),
            timeout=60_000,
        ) as create_response_info:
            page.get_by_role("button", name="Create User").click()

        create_response = create_response_info.value
        assert create_response.status == 201, (
            f"Live user creation failed: HTTP {create_response.status} "
            f"{create_response.text()}"
        )
        user = create_response.json()
        user_id = str(user["id"])
        expect(page.get_by_text(f"@{username}", exact=True)).to_be_visible(
            timeout=15_000
        )

        row = page.get_by_role("listitem").filter(has_text=f"@{username}")
        row.get_by_role("button", name="View Profile").click()
        expect(page.get_by_role("heading", name="User Profile")).to_be_visible(
            timeout=15_000
        )
        page.get_by_role("button", name="Edit Profile").click()
        page.locator("#user-form-email").fill(updated_email)

        with page.expect_response(
            lambda response: response.request.method == "PUT"
            and response.url.endswith(f"/api/v1/users/{user_id}"),
            timeout=60_000,
        ) as update_response_info:
            page.get_by_role("button", name="Save Changes").first.click()

        update_response = update_response_info.value
        assert update_response.ok, (
            f"Live user update failed: HTTP {update_response.status} "
            f"{update_response.text()}"
        )
        expect(page.get_by_text(updated_email, exact=True)).to_be_visible(
            timeout=15_000
        )

        page.get_by_role("button", name="Delete Profile").click()
        dialog = page.get_by_role("dialog")
        with page.expect_response(
            lambda response: response.request.method == "DELETE"
            and response.url.endswith(f"/api/v1/users/{user_id}"),
            timeout=60_000,
        ) as delete_response_info:
            dialog.get_by_role("button", name="Delete Profile").click()

        delete_response = delete_response_info.value
        assert delete_response.status == 204, (
            f"Live user deletion failed: HTTP {delete_response.status} "
            f"{delete_response.text()}"
        )
        user_id = None
        expect(page.get_by_role("heading", name="Users", exact=True)).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text(f"@{username}", exact=True)).to_have_count(0)
    finally:
        if user_id:
            cleanup_response = page.request.delete(
                f"{frontend_url}/api/v1/users/{user_id}"
            )
            _report_cleanup_failure(f"temporary user {user_id}", cleanup_response)
