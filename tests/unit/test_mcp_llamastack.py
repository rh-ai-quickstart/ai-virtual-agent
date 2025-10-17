"""Unit tests for MCP-LlamaStack integration endpoints.

These tests patch the LlamaStack client used inside 'backend.app.api.v1.tools'
and exercise the '/tools' endpoint with a FastAPI TestClient. All
network access is mocked.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.app.main import app


class _MockToolGroup(BaseModel):
    """Minimal shape of a LlamaStack *tool-group* object."""

    identifier: str
    provider_id: str | None = None
    provider_resource_id: str | None = None
    config: Dict[str, Any] = {}


class _MockTool(BaseModel):
    """Minimal shape of a standalone LlamaStack *tool* object."""

    identifier: str
    description: str | None = None
    toolgroup_id: str | None = None
    provider_id: str | None = None
    metadata: Dict[str, Any] | None = None


class _MockLlamaClient:
    """Very small stub that emulates the two endpoints the backend calls."""

    def __init__(self, toolgroups: List[_MockToolGroup], tools: List[_MockTool]):
        self._toolgroups = toolgroups
        self._tools = tools

    # The real client exposes '.toolgroups.list()' and '.tools.list()'
    class _Proxy(list):
        async def list(self):  # noqa: D401 – simple coroutine
            return self  # type: ignore[return-value]

    @property
    def toolgroups(self):  # noqa: D401 – simple property
        return _MockLlamaClient._Proxy(self._toolgroups)

    @property
    def tools(self):  # noqa: D401 – simple property
        return _MockLlamaClient._Proxy(self._tools)


class TestToolsEndpoint:
    """Test '/tools' endpoint - MCP <---> LlamaStack integration layer."""

    @pytest.fixture
    def _mock_data(self):
        """Return sample tool-groups and tools used across test cases."""

        toolgroups = [
            _MockToolGroup(
                identifier="mcp-server-1",
                provider_id="model-context-protocol",
                provider_resource_id="mcp-1-resource",
                config={"endpoint_url": "http://mcp-1.local"},
            ),
            _MockToolGroup(
                identifier="builtin-tg",
                provider_id="builtin",
                provider_resource_id="builtin-resource",
            ),
        ]

        tools = [
            _MockTool(
                identifier="summarize",
                description="Summarize text",
                toolgroup_id="builtin-tg",
                provider_id="builtin",
                metadata={},
            ),
            _MockTool(
                identifier="standalone-tool",
                description="Standalone tool",
                toolgroup_id="standalone-tool",
                provider_id="builtin",
                metadata={},
            ),
        ]

        return toolgroups, tools

    @pytest.fixture
    def client(self, monkeypatch, _mock_data):
        """Return a FastAPI TestClient with LlamaStack client patched."""

        toolgroups, tools = _mock_data

        monkeypatch.setattr(
            "backend.app.api.v1.llama_stack.tools.get_client_from_request",
            lambda _request: _MockLlamaClient(toolgroups, tools),
        )

        with TestClient(app) as tc:
            yield tc

    def test_merges_mcp_and_builtin_groups(self, client, _mock_data):
        """Endpoint returns MCP tool-groups and builtin groups."""

        response = client.get("/api/v1/llama_stack/tools/")

        assert response.status_code == 200, response.text

        data = response.json()

        # Expect: 2 tool-groups
        assert len(data) == 2

        # Validate MCP group
        mcp_entry = next(
            item for item in data if item["toolgroup_id"] == "mcp-server-1"
        )
        assert mcp_entry["name"] == "mcp-1-resource"
        assert mcp_entry["title"] == "model-context-protocol"

        # Validate builtin group preserved as-is
        builtin_tg = next(item for item in data if item["toolgroup_id"] == "builtin-tg")
        assert builtin_tg["title"] == "builtin"
        assert builtin_tg["name"] == "builtin-resource"
