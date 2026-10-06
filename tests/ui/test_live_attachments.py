"""Live attachment storage and session cleanup coverage."""

import uuid

from live_test_utils import delete_agent, require_admin
from playwright.sync_api import Page


def test_live_attachment_storage_and_session_cleanup_without_inference(
    page: Page, frontend_url: str
) -> None:
    """Upload and retrieve a file, then verify session deletion removes it."""
    page.goto(f"{frontend_url}/", wait_until="domcontentloaded")
    require_admin(page, frontend_url)

    unique = uuid.uuid4().hex[:10]
    agent_id: str | None = None
    session_id: str | None = None
    attachment_name: str | None = None
    attachment_content = f"live attachment fixture {unique}\n".encode()

    try:
        agent_response = page.request.post(
            f"{frontend_url}/api/v1/virtual_agents/",
            data={
                "name": f"UI Attachment Lifecycle {unique}",
                "model_name": "attachment-storage-test-model",
                "prompt": "This agent is used only to own an attachment test session.",
                "runner_type": "llamastack",
                "tools": [],
                "knowledge_base_ids": [],
                "input_shields": [],
                "output_shields": [],
            },
        )
        assert agent_response.status == 201, (
            "Could not create an attachment test agent: "
            f"HTTP {agent_response.status} {agent_response.text()}"
        )
        agent_id = str(agent_response.json()["id"])

        session_response = page.request.post(
            f"{frontend_url}/api/v1/chat_sessions/",
            data={
                "agent_id": agent_id,
                "session_name": f"Live attachment test {unique}",
            },
        )
        assert session_response.status == 200, (
            "Could not create an attachment test session: "
            f"HTTP {session_response.status} {session_response.text()}"
        )
        session_id = str(session_response.json()["id"])

        upload_response = page.request.post(
            f"{frontend_url}/api/v1/attachments/",
            multipart={
                "session_id": session_id,
                "file": {
                    "name": "lifecycle-fixture.txt",
                    "mimeType": "text/plain",
                    "buffer": attachment_content,
                },
            },
        )
        assert upload_response.status == 201, (
            "Live attachment upload failed: "
            f"HTTP {upload_response.status} {upload_response.text()}"
        )
        attachment_name = str(upload_response.json()["filename"])
        assert attachment_name.endswith(".txt")

        attachment_url = (
            f"{frontend_url}/api/v1/attachments/{session_id}/{attachment_name}"
        )
        download_response = page.request.get(attachment_url)
        assert download_response.status == 200, (
            "Could not retrieve the uploaded attachment from object storage: "
            f"HTTP {download_response.status} {download_response.text()}"
        )
        assert (
            download_response.body() == attachment_content
        ), "Downloaded attachment bytes did not match the uploaded fixture"

        delete_session_response = page.request.delete(
            f"{frontend_url}/api/v1/chat_sessions/{session_id}",
            params={"agent_id": agent_id},
        )
        assert delete_session_response.ok, (
            "Could not delete the attachment test session: "
            f"HTTP {delete_session_response.status} "
            f"{delete_session_response.text()}"
        )
        session_id = None

        missing_attachment_response = page.request.get(attachment_url)
        assert missing_attachment_response.status == 404, (
            "Deleting the session did not remove its attachment; "
            f"download returned HTTP {missing_attachment_response.status}"
        )
    finally:
        if session_id and agent_id:
            page.request.delete(
                f"{frontend_url}/api/v1/chat_sessions/{session_id}",
                params={"agent_id": agent_id},
            )
        if agent_id:
            delete_agent(page, frontend_url, agent_id)
