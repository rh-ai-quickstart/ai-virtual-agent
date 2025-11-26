"""
Pytest configuration and fixtures for unit tests.

Provides common fixtures for mocking external dependencies like
Kubernetes, LlamaStack, database sessions, and test users.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.main import app
from backend.app.models import RoleEnum, User


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def admin_user():
    """Create a mock admin user."""
    return User(
        id=uuid.uuid4(),
        username="admin_user",
        email="admin@example.com",
        role=RoleEnum.admin,
        agent_ids=[],
    )


@pytest.fixture
def regular_user():
    """Create a mock regular user."""
    return User(
        id=uuid.uuid4(),
        username="regular_user",
        email="user@example.com",
        role=RoleEnum.user,
        agent_ids=[],
    )


def override_get_current_user(mock_user):
    """Factory to create a dependency override for get_current_user."""

    async def _get_current_user():
        return mock_user

    return _get_current_user


def override_get_db(mock_session):
    """Factory to create a dependency override for get_db."""

    def _get_db():
        return mock_session

    return _get_db


@pytest.fixture
def setup_dependencies():
    """Fixture to easily setup and teardown FastAPI dependency overrides."""
    from backend.app.api.v1.users import get_current_user
    from backend.app.database import get_db

    def _setup(user=None, db_session=None):
        if user:
            app.dependency_overrides[get_current_user] = override_get_current_user(user)
        if db_session:
            app.dependency_overrides[get_db] = override_get_db(db_session)

    yield _setup

    # Cleanup after each test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes CoreV1Api client."""
    with patch("kubernetes.client.CoreV1Api") as mock:
        yield mock


@pytest.fixture
def mock_k8s_custom_api():
    """Mock Kubernetes CustomObjectsApi client."""
    with patch("kubernetes.client.CustomObjectsApi") as mock:
        yield mock


@pytest.fixture
def mock_k8s_config():
    """Mock Kubernetes config loading."""
    with patch("kubernetes.config.load_incluster_config") as mock_incluster, \
         patch("kubernetes.config.load_kube_config") as mock_kubeconfig:
        yield {"incluster": mock_incluster, "kubeconfig": mock_kubeconfig}


@pytest.fixture
def mock_llamastack_client():
    """Mock LlamaStack client."""
    with patch("backend.app.clients.llamastack.get_llamastack_client") as mock:
        yield mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for external API calls."""
    with patch("httpx.AsyncClient") as mock:
        yield mock
