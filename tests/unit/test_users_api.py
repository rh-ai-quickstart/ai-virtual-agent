"""
Unit tests for the Users API endpoints.

Tests role-based access control, user management operations,
and proper error handling for the protected users API.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.models import RoleEnum, User


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
    from backend.database import get_db
    from backend.routes.users import get_current_user

    def _setup(user=None, db_session=None):
        if user:
            app.dependency_overrides[get_current_user] = override_get_current_user(user)
        if db_session:
            app.dependency_overrides[get_db] = override_get_db(db_session)

    yield _setup

    # Cleanup after each test
    app.dependency_overrides.clear()


class TestUserAuthentication:
    """Test user authentication and authorization."""

    def test_admin_can_list_users(
        self, test_client, admin_user, mock_db_session, setup_dependencies
    ):
        """Test that admin can list all users."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        # Mock the database query result
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [admin_user]
        mock_result = AsyncMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        response = test_client.get("/api/users/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == admin_user.username


class TestCreateUser:
    """Test user creation endpoint."""

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_create_user_as_admin_success(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        mock_db_session,
    ):
        """Test successful user creation by admin."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock database query to return no existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        new_user_data = {
            "username": "new_user",
            "email": "new@example.com",
            "role": "user",
        }

        response = test_client.post("/api/users/", json=new_user_data)
        assert response.status_code == status.HTTP_201_CREATED

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_create_user_as_regular_user_forbidden(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test that regular users cannot create new users."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        new_user_data = {
            "username": "new_user",
            "email": "new@example.com",
            "role": "user",
        }

        response = test_client.post("/api/users/", json=new_user_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_create_user_duplicate_conflict(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        mock_db_session,
    ):
        """Test creating user with existing username/email returns conflict."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock existing user found
        existing_user = User(
            username="existing", email="existing@example.com", role=RoleEnum.user
        )
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db_session.execute.return_value = mock_result

        new_user_data = {
            "username": "existing",
            "email": "new@example.com",
            "role": "user",
        }

        response = test_client.post("/api/users/", json=new_user_data)
        assert response.status_code == status.HTTP_409_CONFLICT


class TestReadUsers:
    """Test user listing endpoint."""

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_list_users_as_admin_success(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        mock_db_session,
    ):
        """Test admin can list all users."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock users list
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db_session.execute.return_value = mock_result

        response = test_client.get("/api/users/")
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_list_users_as_regular_user_forbidden(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test regular user cannot list all users."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        response = test_client.get("/api/users/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestReadSingleUser:
    """Test single user retrieval endpoint."""

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_admin_can_read_any_user(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
    ):
        """Test admin can read any user's profile."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock user found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.get(f"/api/users/{regular_user.id}")
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_user_can_read_own_profile(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test user can read their own profile."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        # Mock user found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.get(f"/api/users/{regular_user.id}")
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_user_cannot_read_other_user_profile(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        admin_user,
        mock_db_session,
    ):
        """Test user cannot read another user's profile."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        response = test_client.get(f"/api/users/{admin_user.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_read_nonexistent_user_returns_404(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        mock_db_session,
    ):
        """Test reading non-existent user returns 404."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock user not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        fake_uuid = uuid.uuid4()
        response = test_client.get(f"/api/users/{fake_uuid}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateUser:
    """Test user update endpoint."""

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_admin_can_update_user(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
    ):
        """Test admin can update any user."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock user found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_db_session.execute.return_value = mock_result

        update_data = {"username": "updated_user"}
        response = test_client.put(f"/api/users/{regular_user.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_regular_user_cannot_update_user(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test regular user cannot update users."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        update_data = {"username": "updated_user"}
        response = test_client.put(f"/api/users/{regular_user.id}", json=update_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteUser:
    """Test user deletion endpoint."""

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_admin_can_delete_other_user(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
    ):
        """Test admin can delete other users."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock user found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.delete(f"/api/users/{regular_user.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_admin_cannot_delete_own_account(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        mock_db_session,
    ):
        """Test admin cannot delete their own account."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock user found (admin themselves)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = admin_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.delete(f"/api/users/{admin_user.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_regular_user_cannot_delete_user(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test regular user cannot delete users."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        response = test_client.delete(f"/api/users/{regular_user.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserAgents:
    """Test user agents management endpoints."""

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_user_can_view_own_agents(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test user can view their own assigned agents."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        # Mock user found with agents
        regular_user.agent_ids = ["agent1", "agent2"]
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.get(f"/api/users/{regular_user.id}/agents")
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_user_cannot_view_other_user_agents(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        admin_user,
        mock_db_session,
    ):
        """Test user cannot view another user's agents."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        response = test_client.get(f"/api/users/{admin_user.id}/agents")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_admin_can_assign_agents(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
    ):
        """Test admin can assign agents to users."""
        mock_get_current_user.return_value = admin_user
        mock_get_db.return_value = mock_db_session

        # Mock user found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_db_session.execute.return_value = mock_result

        agent_data = {"agent_ids": ["agent1", "agent2"]}
        response = test_client.post(
            f"/api/users/{regular_user.id}/agents", json=agent_data
        )
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.routes.users.get_db")
    @patch("backend.routes.users.get_current_user")
    def test_regular_user_cannot_assign_agents(
        self,
        mock_get_current_user,
        mock_get_db,
        test_client,
        regular_user,
        mock_db_session,
    ):
        """Test regular user cannot assign agents."""
        mock_get_current_user.return_value = regular_user
        mock_get_db.return_value = mock_db_session

        agent_data = {"agent_ids": ["agent1", "agent2"]}
        response = test_client.post(
            f"/api/users/{regular_user.id}/agents", json=agent_data
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
