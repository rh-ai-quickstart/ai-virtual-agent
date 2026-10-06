"""Live template deployment and inference test against configured services."""

import json
import os
import uuid

import requests


def test_deployed_template_uses_live_inference_and_persists_chat() -> None:
    """Deploy a real template, chat through its real model, and clean up records."""
    base_url = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000").rstrip("/")
    client = requests.Session()
    agent_id: str | None = None
    session_id: str | None = None

    try:
        templates_response = client.get(
            f"{base_url}/api/v1/agent_templates/", timeout=30
        )
        templates_response.raise_for_status()
        templates = templates_response.json()
        assert templates, "No agent templates are available in the live backend"
        template_name = None
        for candidate in templates:
            detail_response = client.get(
                f"{base_url}/api/v1/agent_templates/{candidate}", timeout=30
            )
            detail_response.raise_for_status()
            details = detail_response.json()
            if not details.get("graph_config") and not details.get(
                "knowledge_base_config"
            ):
                template_name = candidate
                break
        assert template_name, (
            "No non-graph template without a configured knowledge base is "
            "available for live LlamaStack inference"
        )

        models_response = client.get(f"{base_url}/api/v1/llama_stack/llms", timeout=60)
        models_response.raise_for_status()
        models = models_response.json()
        assert models, "No inference model is available in LlamaStack"
        model_name = models[0]["model_name"]

        unique = uuid.uuid4().hex[:12]
        agent_name = f"Live Template Chat {unique}"
        prompt = (
            "For every user message, reply with exactly LIVE_TEMPLATE_CHAT_OK and "
            "no other words or punctuation."
        )
        deploy_response = client.post(
            f"{base_url}/api/v1/agent_templates/initialize",
            json={
                "template_name": template_name,
                "custom_name": agent_name,
                "custom_prompt": prompt,
                "include_knowledge_base": False,
                "model_name": model_name,
                "tools": [],
                "knowledge_base_ids": [],
                "runner_type": "llamastack",
            },
            timeout=120,
        )
        deploy_response.raise_for_status()
        deployment = deploy_response.json()
        assert (
            deployment["status"] == "success"
        ), f"Expected a fresh template deployment, got: {deployment}"
        agent_id = deployment["agent_id"]

        agent_response = client.get(
            f"{base_url}/api/v1/virtual_agents/{agent_id}", timeout=30
        )
        agent_response.raise_for_status()
        deployed_agent = agent_response.json()
        assert deployed_agent["name"] == agent_name
        assert deployed_agent[
            "template_id"
        ], "The created agent is missing template metadata"
        assert deployed_agent["model_name"] == model_name

        session_response = client.post(
            f"{base_url}/api/v1/chat_sessions/",
            json={"agent_id": agent_id, "session_name": f"Live Template {unique}"},
            timeout=30,
        )
        session_response.raise_for_status()
        session_id = session_response.json()["id"]

        chat_response = client.post(
            f"{base_url}/api/v1/chat",
            json={
                "virtualAgentId": agent_id,
                "sessionId": session_id,
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Follow your instruction."}
                    ],
                },
            },
            headers={"Accept": "text/event-stream"},
            timeout=180,
        )
        chat_response.raise_for_status()
        events = []
        for line in chat_response.text.splitlines():
            if line.startswith("data: ") and line[6:] != "[DONE]":
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    continue

        errors = [
            event.get("message", "unknown error")
            for event in events
            if event.get("type") == "error"
        ]
        assert not errors, f"Live template chat returned errors: {errors}"
        answer = "".join(
            event.get("delta", "")
            for event in events
            if event.get("type") == "response"
        )
        assert "LIVE_TEMPLATE_CHAT_OK" in answer, (
            "The deployed template did not produce the expected live inference "
            f"response: {answer!r}"
        )
        assert any(
            event.get("type") == "response" and event.get("status") == "completed"
            for event in events
        ), "Live template chat ended without a completed assistant response"

        messages_response = client.get(
            f"{base_url}/api/v1/chat_sessions/{session_id}/messages", timeout=30
        )
        messages_response.raise_for_status()
        messages = messages_response.json()["messages"]
        assert any(
            item.get("role") == "user"
            and any(
                content.get("text") == "Follow your instruction."
                for content in item.get("content", [])
            )
            for item in messages
        ), "The live chat user message was not persisted in the session"
    finally:
        if session_id:
            try:
                client.delete(
                    f"{base_url}/api/v1/chat_sessions/{session_id}",
                    params={"agent_id": agent_id},
                    timeout=30,
                )
            except requests.RequestException as error:
                print(
                    f"Could not clean up live template chat session {session_id}: "
                    f"{error}"
                )
        if agent_id:
            try:
                client.delete(
                    f"{base_url}/api/v1/virtual_agents/{agent_id}", timeout=30
                )
            except requests.RequestException as error:
                print(f"Could not clean up live template agent {agent_id}: {error}")
        client.close()
