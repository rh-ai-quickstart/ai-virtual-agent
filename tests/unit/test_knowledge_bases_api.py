"""
Unit tests for Knowledge Bases API endpoints.

Tests CRUD operations for knowledge base management.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def mock_kb_crud():
    """Mock knowledge base CRUD operations."""
    with patch("backend.app.api.v1.knowledge_bases.knowledge_bases") as mock:
        mock.create = AsyncMock()
        mock.get_multi = AsyncMock()
        mock.get_by_vector_store_name = AsyncMock()
        mock.delete = AsyncMock()
        mock.remove = AsyncMock()
        yield mock


@pytest.fixture
def mock_pipeline_functions():
    """Mock pipeline-related functions."""
    with patch(
        "backend.app.api.v1.knowledge_bases.create_ingestion_pipeline"
    ) as mock_create, patch(
        "backend.app.api.v1.knowledge_bases.get_pipeline_status"
    ) as mock_status, patch(
        "backend.app.api.v1.knowledge_bases.update_vector_store_ids"
    ) as mock_update, patch(
        "backend.app.api.v1.knowledge_bases.delete_ingestion_pipeline"
    ) as mock_delete:
        mock_create.return_value = AsyncMock()
        mock_status.return_value = "completed"
        mock_update.return_value = AsyncMock()
        mock_delete.return_value = AsyncMock()
        yield {
            "create": mock_create,
            "status": mock_status,
            "update": mock_update,
            "delete": mock_delete,
        }


@pytest.fixture
def sample_kb():
    """Create sample knowledge base."""
    import uuid

    kb = MagicMock()
    kb.vector_store_name = "test-kb"
    kb.name = "Test KB"
    kb.version = "v1"
    kb.status = "completed"
    kb.embedding_model = "test-model"
    kb.provider_id = "test-provider"
    kb.source = "S3"
    kb.vector_store_id = "test-store-id"
    kb.created_by = uuid.uuid4()
    return kb


class TestCreateKnowledgeBase:
    """Test knowledge base creation endpoint."""

    def test_create_kb_success(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions, sample_kb
    ):
        """Test successful knowledge base creation."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.create.return_value = sample_kb

        kb_data = {
            "vector_store_name": "new-kb",
            "name": "New KB",
            "version": "v1",
            "embedding_model": "test-model",
            "provider_id": "test-provider",
            "source": "S3",
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/knowledge_bases/", json=kb_data)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_kb_duplicate(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions
    ):
        """Test creating duplicate knowledge base returns conflict."""
        from backend.app.api.v1.knowledge_bases import get_db
        from backend.app.crud.knowledge_bases import DuplicateKnowledgeBaseNameError

        mock_kb_crud.create.side_effect = DuplicateKnowledgeBaseNameError(
            "Duplicate KB"
        )

        kb_data = {
            "vector_store_name": "duplicate-kb",
            "name": "Duplicate KB",
            "version": "v1",
            "embedding_model": "test-model",
            "provider_id": "test-provider",
            "source": "S3",
        }

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.post("/api/v1/knowledge_bases/", json=kb_data)
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_409_CONFLICT


class TestListKnowledgeBases:
    """Test knowledge base listing endpoint."""

    def test_list_kbs_success(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions, sample_kb
    ):
        """Test listing all knowledge bases."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.get_multi.return_value = [sample_kb]

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get("/api/v1/knowledge_bases/")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK

    def test_list_kbs_empty(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions
    ):
        """Test listing when no knowledge bases exist."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.get_multi.return_value = []

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get("/api/v1/knowledge_bases/")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestGetKnowledgeBase:
    """Test single knowledge base retrieval."""

    def test_get_kb_success(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions, sample_kb
    ):
        """Test retrieving a single knowledge base."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.get_by_vector_store_name.return_value = sample_kb

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get("/api/v1/knowledge_bases/test-kb")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK

    def test_get_kb_not_found(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions
    ):
        """Test retrieving non-existent knowledge base returns 404."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.get_by_vector_store_name.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.get("/api/v1/knowledge_bases/nonexistent")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteKnowledgeBase:
    """Test knowledge base deletion endpoint."""

    @patch("backend.app.api.v1.knowledge_bases.get_client_from_request")
    @patch("backend.app.api.v1.knowledge_bases.virtual_agents")
    def test_delete_kb_success(
        self,
        mock_agents,
        mock_client,
        test_client,
        mock_db_session,
        mock_kb_crud,
        mock_pipeline_functions,
        sample_kb,
    ):
        """Test successful knowledge base deletion."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.get_by_vector_store_name.return_value = sample_kb
        mock_agents.get_all_with_templates = AsyncMock(return_value=[])

        # Mock LlamaStack client
        mock_llama_client = AsyncMock()
        mock_llama_client.vector_stores.delete = AsyncMock()
        mock_client.return_value = mock_llama_client

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.delete("/api/v1/knowledge_bases/test-kb")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_kb_not_found(
        self, test_client, mock_db_session, mock_kb_crud, mock_pipeline_functions
    ):
        """Test deleting non-existent knowledge base returns 404."""
        from backend.app.api.v1.knowledge_bases import get_db

        mock_kb_crud.get_by_vector_store_name.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db_session
        response = test_client.delete("/api/v1/knowledge_bases/nonexistent")
        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND
