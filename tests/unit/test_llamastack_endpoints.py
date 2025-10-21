from __future__ import annotations

from typing import List

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.app.main import app

# ---------------------------------------------------------------------------
# Helper mocks – minimal shapes that mimic objects returned by LlamaStack
# ---------------------------------------------------------------------------


class _MockModel(BaseModel):
    """Minimal shape of a LlamaStack *model* object for multiple endpoints."""

    identifier: str
    provider_resource_id: str
    api_model_type: str  # used by /llms
    model_type: str  # used to *filter* safety/embedding endpoints
    type: str  # echoed back in the response (same as model_type)


class _MockVectorStore(BaseModel):
    """Minimal representation of a LlamaStack *vector DB* (knowledge base)."""

    identifier: str
    provider_resource_id: str | None = None
    provider_id: str | None = None
    type: str = "vector_store"
    embedding_model: str | None = None


class _MockToolGroup(BaseModel):
    """Minimal representation of a LlamaStack *tool-group* (MCP server)."""

    identifier: str
    provider_resource_id: str | None = None
    provider_id: str | None = None


# ---------------------------------------------------------------------------
# Mock LlamaStack client stub exposing the subset of endpoints used by backend
# ---------------------------------------------------------------------------


class _MockProvider(BaseModel):
    """Minimal representation of a LlamaStack provider."""

    provider_id: str
    provider_type: str


class _MockLlamaClient:
    """Very small stub that emulates the list-endpoints the backend uses."""

    def __init__(
        self,
        models: List[_MockModel],
        vector_stores: List[_MockVectorStore],
        toolgroups: List[_MockToolGroup],
        providers: List[_MockProvider] | None = None,
    ):
        self._models = models
        self._vector_stores = vector_stores
        self._toolgroups = toolgroups
        self._providers = providers or []

    # Internal proxy object so that `.models.list()` *awaits* to the actual
    # list
    class _Proxy(list):
        async def list(self):  # noqa: D401 – simple coroutine
            return self  # type: ignore[return-value]

    # Expose the collections used by the backend
    @property
    def models(self):  # noqa: D401 – simple property
        return _MockLlamaClient._Proxy(self._models)

    @property
    def vector_stores(self):  # noqa: D401 – simple property
        return _MockLlamaClient._Proxy(self._vector_stores)

    @property
    def toolgroups(self):  # noqa: D401 – simple property
        return _MockLlamaClient._Proxy(self._toolgroups)

    @property
    def providers(self):  # noqa: D401 – simple property
        return _MockLlamaClient._Proxy(self._providers)

    # FastAPI dependency sometimes expects `.base_url` for logging
    base_url: str = "http://mock-llamastack.local"


# ---------------------------------------------------------------------------
# Shared fixture building the TestClient with LlamaStack client patched
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch):
    """Return a FastAPI TestClient with mocked LlamaStack data."""

    # Sample dataset – mixture of model types, two knowledge bases, one MCP
    # server
    models = [
        _MockModel(
            identifier="gpt-4",
            provider_resource_id="openai.gpt-4",
            api_model_type="llm",
            model_type="llm",
            type="llm",
        ),
        _MockModel(
            identifier="toxicity-checker",
            provider_resource_id="llama.guard",
            api_model_type="safety",
            model_type="safety",
            type="safety",
        ),
        _MockModel(
            identifier="text-embedding-ada",
            provider_resource_id="openai.ada",
            api_model_type="embedding",
            model_type="embedding",
            type="embedding",
        ),
    ]

    providers = [
        _MockProvider(provider_id="openai", provider_type="remote"),
        _MockProvider(provider_id="meta-llama", provider_type="local"),
    ]

    vector_stores = [
        _MockVectorStore(
            identifier="kb_stackoverflow",
            provider_resource_id="db.so",
            provider_id="builtin",
            embedding_model="text-embedding-ada",
        ),
        _MockVectorStore(
            identifier="kb_internal_wiki",
            provider_resource_id="db.wiki",
            provider_id="builtin",
            embedding_model="text-embedding-ada",
        ),
    ]

    toolgroups = [
        _MockToolGroup(
            identifier="mcp-server-alpha",
            provider_resource_id="alpha.mcp",
            provider_id="model-context-protocol",
        )
    ]

    # Patch the dependency factory used inside the endpoints
    monkeypatch.setattr(
        "backend.app.api.v1.llama_stack.models.get_client_from_request",
        lambda _request: _MockLlamaClient(models, vector_stores, toolgroups, providers),
    )
    monkeypatch.setattr(
        "backend.app.api.v1.llama_stack.tools.get_client_from_request",
        lambda _request: _MockLlamaClient(models, vector_stores, toolgroups, providers),
    )

    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# Tests – verify filtering / mapping logic of llama_stack endpoints
# ---------------------------------------------------------------------------


def test_get_llms_filters_only_llm_models(client):
    """Endpoint must return only models with `api_model_type == 'llm'`."""

    response = client.get("/api/v1/llama_stack/models/llms")

    assert response.status_code == 200, response.text

    data = response.json()

    # Should include exactly one model (the LLM)
    assert len(data) == 1

    llm = data[0]
    assert llm["model_id"] == "gpt-4"
    assert llm["model_type"] == "llm"


def test_get_tools_returns_mcp_servers(client):
    """Endpoint must map tool-groups to the expected MCP server schema."""

    response = client.get("/api/v1/llama_stack/tools/")

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 1

    server = data[0]
    assert server["id"] == "mcp-server-alpha"
    assert server["title"] == "model-context-protocol"
    assert server["toolgroup_id"] == "mcp-server-alpha"


def test_get_safety_models_filters_correctly(client):
    """/safety_models should return only models where model_type ==
    'safety'."""

    response = client.get("/api/v1/llama_stack/models/safety")

    assert response.status_code == 200, response.text

    data = response.json()

    # Expect exactly one safety model
    assert data == [
        {
            "id": "toxicity-checker",
            "name": "llama.guard",
            "model_type": "safety",
        }
    ]


def test_get_embedding_models_filters_correctly(client):
    """/embedding_models should return only models where model_type ==
    'embedding'."""

    response = client.get("/api/v1/llama_stack/models/embedding")

    assert response.status_code == 200, response.text

    data = response.json()

    # Expect exactly one embedding model dict with required keys
    assert len(data) == 1

    emb = data[0]
    assert emb["model_id"] == "text-embedding-ada"
    assert emb["model_type"] == "embedding"
