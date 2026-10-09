"""Helpers shared by live browser integration tests."""

import json
import re
import time
from typing import Any, Callable

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page


def _cleanup_request(request: Callable[[], Any], description: str) -> Any | None:
    """Retry transient transport failures without letting cleanup mask test results."""
    attempts = 6
    for attempt in range(attempts):
        try:
            return request()
        except PlaywrightError as error:
            message = str(error)
            transient = any(
                marker in message.casefold()
                for marker in (
                    "socket hang up",
                    "econnreset",
                    "connection reset",
                    "econnrefused",
                    "connection refused",
                )
            )
            if transient and attempt + 1 < attempts:
                time.sleep(min(2**attempt, 5))
                continue
            print(f"Could not {description}: {message}")
            return None


def require_admin(page: Page, frontend_url: str) -> dict[str, Any]:
    """Return the real current user or skip when live admin access is unavailable."""
    response = page.request.get(f"{frontend_url}/api/v1/users/profile")
    if not response.ok:
        pytest.skip(
            "Live admin browser coverage needs an authenticated user; "
            f"profile returned HTTP {response.status}"
        )
    profile = response.json()
    if profile.get("role") != "admin":
        pytest.skip("This live browser test requires an admin user")
    return profile


def live_model(page: Page, frontend_url: str) -> str:
    """Return the first model currently served by LlamaStack."""
    response = page.request.get(f"{frontend_url}/api/v1/llama_stack/llms")
    assert response.ok, (
        "Could not list live inference models: "
        f"HTTP {response.status} {response.text()}"
    )
    models = response.json()
    if not models:
        pytest.skip("No live inference model is available")
    return str(models[0]["model_name"])


def parse_sse_events(body: str) -> list[dict[str, Any]]:
    """Decode the JSON data blocks from an SSE response body."""
    events: list[dict[str, Any]] = []
    for block in re.split(r"\r?\n\r?\n", body):
        data_lines = [
            line[6:] for line in block.splitlines() if line.startswith("data: ")
        ]
        if not data_lines:
            continue
        data = "\n".join(data_lines)
        if data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def cleanup_agent_sessions(page: Page, frontend_url: str, agent_id: str) -> None:
    """Delete all sessions for a unique temporary test agent."""
    response = _cleanup_request(
        lambda: page.request.get(
            f"{frontend_url}/api/v1/chat_sessions/",
            params={"agent_id": agent_id, "limit": 100},
        ),
        f"list sessions for temporary agent {agent_id}",
    )
    if response is None:
        return
    if not response.ok:
        print(
            f"Could not list sessions for temporary agent {agent_id}: "
            f"HTTP {response.status} {response.text()}"
        )
        return

    for session in response.json():
        session_id = session.get("id")
        if not session_id:
            continue
        delete_response = _cleanup_request(
            lambda: page.request.delete(
                f"{frontend_url}/api/v1/chat_sessions/{session_id}",
                params={"agent_id": agent_id},
            ),
            f"clean up session {session_id}",
        )
        if delete_response is not None and not delete_response.ok:
            print(
                f"Could not clean up session {session_id}: "
                f"HTTP {delete_response.status} {delete_response.text()}"
            )


def remove_agent_assignment(
    page: Page, frontend_url: str, user_id: str, agent_id: str
) -> None:
    response = _cleanup_request(
        lambda: page.request.delete(
            f"{frontend_url}/api/v1/users/{user_id}/agents",
            data={"agent_ids": [agent_id]},
        ),
        f"remove temporary agent assignment {agent_id}",
    )
    if response is not None and not response.ok:
        print(
            f"Could not remove temporary agent assignment {agent_id}: "
            f"HTTP {response.status} {response.text()}"
        )


def delete_agent(page: Page, frontend_url: str, agent_id: str) -> None:
    response = _cleanup_request(
        lambda: page.request.delete(f"{frontend_url}/api/v1/virtual_agents/{agent_id}"),
        f"delete temporary agent {agent_id}",
    )
    if response is not None and not response.ok:
        print(
            f"Could not delete temporary agent {agent_id}: "
            f"HTTP {response.status} {response.text()}"
        )


def assign_agent(page: Page, frontend_url: str, user_id: str, agent_id: str) -> None:
    response = page.request.post(
        f"{frontend_url}/api/v1/users/{user_id}/agents",
        data={"agent_ids": [agent_id]},
    )
    assert response.ok, (
        f"Could not assign temporary agent {agent_id}: "
        f"HTTP {response.status} {response.text()}"
    )
