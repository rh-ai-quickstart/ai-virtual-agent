"""Smoke tests for the user-facing application shell and primary navigation."""

import re

from playwright.sync_api import Page, expect


def test_chat_page_loads_with_primary_navigation(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")

    expect(page).to_have_title(re.compile("AI Virtual Agent"))
    expect(page.get_by_role("heading", name="AI Virtual Agent")).to_be_visible()
    main_navigation = page.get_by_role("navigation", name="Main Nav")
    expect(main_navigation.get_by_role("link", name="Chat")).to_be_visible()
    expect(main_navigation.get_by_role("link", name="Config")).to_be_visible()


def test_admin_can_open_agent_configuration(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("link", name="Config").click()

    expect(page).to_have_url(re.compile(r"/config/agents/?$"))
    tabs = page.get_by_role("tablist")
    expect(tabs.get_by_role("tab", name="My Agents")).to_be_visible()
    expect(tabs.get_by_role("tab", name="Agent Templates")).to_be_visible()


def test_user_can_toggle_dark_theme(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    dark_theme_toggle = page.get_by_role("button", name="dark theme toggle")

    dark_theme_toggle.click()
    expect(page.locator("html")).to_have_class(re.compile(r"pf-v6-theme-dark"))

    page.get_by_role("button", name="light theme toggle").click()
    expect(page.locator("html")).not_to_have_class(re.compile(r"pf-v6-theme-dark"))


def test_dark_theme_preference_survives_reload(page: Page, frontend_url: str) -> None:
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    page.get_by_role("button", name="dark theme toggle").click()
    expect(page.locator("html")).to_have_class(re.compile(r"pf-v6-theme-dark"))

    page.reload(wait_until="domcontentloaded")
    expect(page.locator("html")).to_have_class(re.compile(r"pf-v6-theme-dark"))
    page.get_by_role("button", name="light theme toggle").click()
    expect(page.locator("html")).not_to_have_class(re.compile(r"pf-v6-theme-dark"))
