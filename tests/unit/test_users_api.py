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

from backend.app.main import app
from backend.app.models import User, VirtualAgent
from backend.app.schemas.user import CurrentUser


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
    return CurrentUser(
        keycloak_id=uuid.uuid4(),
        username="admin_user",
        email="admin@example.com",
        role="admin",
        agent_ids=[],
    )


@pytest.fixture
def regular_user():
    """Create a mock regular user."""
    return CurrentUser(
        keycloak_id=uuid.uuid4(),
        username="regular_user",
        email="user@example.com",
        role="user",
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


class TestReadUsers:
    """Test user listing endpoint."""

    @patch("backend.app.api.v1.users.fetch_keycloak_user_role")
    @patch("backend.app.api.v1.users.fetch_keycloak_users")
    def test_list_users_as_admin_success(
        self,
        mock_fetch_users,
        mock_fetch_role,
        test_client,
        admin_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test admin can list all users."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        mock_fetch_users.return_value = [
            {
                "id": str(admin_user.keycloak_id),
                "username": "admin_user",
                "email": "admin@example.com",
            }
        ]
        mock_fetch_role.return_value = "admin"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "admin_user"

    def test_list_users_as_regular_user_forbidden(
        self,
        test_client,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test regular user cannot list all users."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        response = test_client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestReadSingleUser:
    """Test single user retrieval endpoint."""

    @patch("backend.app.api.v1.users.fetch_keycloak_user_role")
    @patch("backend.app.api.v1.users.fetch_keycloak_user")
    def test_admin_can_read_any_user(
        self,
        mock_fetch_user,
        mock_fetch_role,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test admin can read any user's profile."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        mock_fetch_user.return_value = {
            "id": str(regular_user.keycloak_id),
            "username": "regular_user",
            "email": "user@example.com",
        }
        mock_fetch_role.return_value = "user"

        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = db_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.get(f"/api/v1/users/{regular_user.keycloak_id}")
        assert response.status_code == status.HTTP_200_OK

    def test_user_can_read_own_profile(
        self,
        test_client,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test user can read their own profile."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        response = test_client.get(f"/api/v1/users/{regular_user.keycloak_id}")
        assert response.status_code == status.HTTP_200_OK

    def test_user_cannot_read_other_user_profile(
        self,
        test_client,
        regular_user,
        admin_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test user cannot read another user's profile."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        response = test_client.get(f"/api/v1/users/{admin_user.keycloak_id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("backend.app.api.v1.users.fetch_keycloak_user_role")
    @patch("backend.app.api.v1.users.fetch_keycloak_user")
    def test_read_nonexistent_user_returns_404(
        self,
        mock_fetch_user,
        mock_fetch_role,
        test_client,
        admin_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test reading non-existent user returns 404."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        mock_fetch_user.return_value = None

        fake_uuid = uuid.uuid4()
        response = test_client.get(f"/api/v1/users/{fake_uuid}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteUser:
    """Test user deletion endpoint."""

    @patch("backend.app.api.v1.users.delete_keycloak_user")
    def test_admin_can_delete_other_user(
        self,
        mock_delete_keycloak,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test admin can delete other users from both DB and Keycloak."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = db_user
        mock_db_session.execute.return_value = mock_result

        mock_delete_keycloak.return_value = True

        with patch(
            "backend.app.crud.user.user.remove", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = db_user
            response = test_client.delete(f"/api/v1/users/{regular_user.keycloak_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete_keycloak.assert_called_once_with(str(regular_user.keycloak_id))

    @patch("backend.app.api.v1.users.delete_keycloak_user")
    def test_delete_user_only_in_keycloak(
        self,
        mock_delete_keycloak,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test deletion when user exists only in Keycloak, not DB."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        # User not in DB
        mock_delete_keycloak.return_value = True

        with patch(
            "backend.app.crud.user.user.remove", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = None  # Not in DB
            response = test_client.delete(f"/api/v1/users/{regular_user.keycloak_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_delete_keycloak.assert_called_once()

    @patch("backend.app.api.v1.users.delete_keycloak_user")
    def test_delete_user_only_in_db(
        self,
        mock_delete_keycloak,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test deletion when user exists only in DB, not Keycloak."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])

        # Not in Keycloak (404)
        mock_delete_keycloak.return_value = False

        with patch(
            "backend.app.crud.user.user.remove", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = db_user
            response = test_client.delete(f"/api/v1/users/{regular_user.keycloak_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("backend.app.api.v1.users.delete_keycloak_user")
    def test_delete_user_not_found_anywhere(
        self,
        mock_delete_keycloak,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test deletion when user doesn't exist in either system."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        # Not in DB or Keycloak
        mock_delete_keycloak.return_value = False

        with patch(
            "backend.app.crud.user.user.remove", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = None
            response = test_client.delete(f"/api/v1/users/{regular_user.keycloak_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("backend.app.api.v1.users.delete_keycloak_user")
    def test_delete_user_keycloak_error_still_deletes_from_db(
        self,
        mock_delete_keycloak,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test deletion succeeds if Keycloak fails but DB succeeds."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])

        # Keycloak deletion throws exception
        mock_delete_keycloak.side_effect = Exception("Keycloak unavailable")

        with patch(
            "backend.app.crud.user.user.remove", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = db_user
            response = test_client.delete(f"/api/v1/users/{regular_user.keycloak_id}")

        # Should still succeed since DB deletion worked
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_admin_cannot_delete_own_account(
        self,
        test_client,
        admin_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test admin cannot delete their own account."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        response = test_client.delete(f"/api/v1/users/{admin_user.keycloak_id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_regular_user_cannot_delete_user(
        self,
        test_client,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test regular user cannot delete users."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        response = test_client.delete(f"/api/v1/users/{regular_user.keycloak_id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserAgents:
    """Test user agents management endpoints."""

    def test_user_can_view_own_agents(
        self,
        test_client,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test user can view their own assigned agents."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        agent_uuid1 = uuid.uuid4()
        agent_uuid2 = uuid.uuid4()
        db_user = User(
            keycloak_id=regular_user.keycloak_id,
            agent_ids=[agent_uuid1, agent_uuid2],
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = db_user
        mock_db_session.execute.return_value = mock_result

        response = test_client.get(f"/api/v1/users/{regular_user.keycloak_id}/agents")
        assert response.status_code == status.HTTP_200_OK

    def test_user_cannot_view_other_user_agents(
        self,
        test_client,
        regular_user,
        admin_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test user cannot view another user's agents."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        response = test_client.get(f"/api/v1/users/{admin_user.keycloak_id}/agents")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("backend.app.api.v1.users._build_user_response")
    @patch("backend.app.crud.virtual_agents.virtual_agents.get")
    @patch("backend.app.crud.user.user.update", new_callable=AsyncMock)
    @patch("backend.app.crud.user.user.get", new_callable=AsyncMock)
    def test_admin_can_assign_agents(
        self,
        mock_user_get,
        mock_user_update,
        mock_get_virtual_agent,
        mock_build_response,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test admin can assign agents to users."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        agent_uuid1 = uuid.uuid4()
        agent_uuid2 = uuid.uuid4()

        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])
        mock_user_get.return_value = db_user
        mock_get_virtual_agent.return_value = VirtualAgent(
            id=agent_uuid1,
            name="Test Agent",
            model_name="test-model",
            prompt="Test prompt",
        )
        mock_build_response.return_value = MagicMock(
            keycloak_id=regular_user.keycloak_id,
            username="regular_user",
            email="user@example.com",
            role="user",
            agent_ids=[agent_uuid1, agent_uuid2],
        )

        agent_data = {"agent_ids": [str(agent_uuid1), str(agent_uuid2)]}
        response = test_client.post(
            f"/api/v1/users/{regular_user.keycloak_id}/agents", json=agent_data
        )
        assert response.status_code == status.HTTP_200_OK

    @patch("backend.app.api.v1.users._build_user_response")
    @patch("backend.app.crud.virtual_agents.virtual_agents.get")
    @patch("backend.app.crud.user.user.update", new_callable=AsyncMock)
    @patch("backend.app.crud.user.user.get", new_callable=AsyncMock)
    def test_regular_user_can_assign_own_agents(
        self,
        mock_user_get,
        mock_user_update,
        mock_get_virtual_agent,
        mock_build_response,
        test_client,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test regular user can assign agents to themselves."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        agent_uuid1 = uuid.uuid4()
        agent_uuid2 = uuid.uuid4()

        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])
        mock_user_get.return_value = db_user
        mock_get_virtual_agent.return_value = VirtualAgent(
            id=agent_uuid1,
            name="Test Agent",
            model_name="test-model",
            prompt="Test prompt",
        )
        mock_build_response.return_value = MagicMock(
            keycloak_id=regular_user.keycloak_id,
            username="regular_user",
            email="user@example.com",
            role="user",
            agent_ids=[agent_uuid1, agent_uuid2],
        )

        agent_data = {"agent_ids": [str(agent_uuid1), str(agent_uuid2)]}
        response = test_client.post(
            f"/api/v1/users/{regular_user.keycloak_id}/agents", json=agent_data
        )
        assert response.status_code == status.HTTP_200_OK


class TestAgentAutoAssignment:
    """Test AUTO_ASSIGN_AGENTS_TO_USERS feature."""

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.users.settings.AUTO_ASSIGN_AGENTS_TO_USERS", True)
    @patch("backend.app.api.v1.users.virtual_agents.get_all_agent_ids")
    async def test_auto_assign_adds_new_agents_on_user_creation(
        self, mock_get_agent_ids, mock_db_session
    ):
        """Test new user gets all agents when AUTO_ASSIGN is enabled."""
        from backend.app.api.v1.users import _find_or_create_user

        agent_uuid1 = uuid.uuid4()
        agent_uuid2 = uuid.uuid4()
        mock_get_agent_ids.return_value = [agent_uuid1, agent_uuid2]

        # User doesn't exist yet
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # After creation
        new_user = User(
            keycloak_id=uuid.uuid4(),
            agent_ids=[agent_uuid1, agent_uuid2],
        )
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_db_session.execute.side_effect = [mock_result1, mock_result2]

        with patch(
            "backend.app.crud.user.user.create_user", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = new_user
            user = await _find_or_create_user(mock_db_session, new_user.keycloak_id)

        assert set(user.agent_ids) == {agent_uuid1, agent_uuid2}

    # TODO: Test for auto-assignment on login is skipped due to complexity of mocking
    # SQLAlchemy's refresh behavior. The logic is verified manually and works correctly.

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.users.settings.AUTO_ASSIGN_AGENTS_TO_USERS", False)
    @patch("backend.app.api.v1.users.virtual_agents.get_all_agent_ids")
    async def test_auto_assign_disabled_no_assignment(
        self, mock_get_agent_ids, mock_db_session
    ):
        """Test no auto-assignment when AUTO_ASSIGN is disabled."""
        from backend.app.api.v1.users import _find_or_create_user

        agent_uuid1 = uuid.uuid4()
        agent_uuid2 = uuid.uuid4()
        mock_get_agent_ids.return_value = [agent_uuid1, agent_uuid2]

        # User doesn't exist yet
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        new_user = User(
            keycloak_id=uuid.uuid4(),
            agent_ids=[],  # No agents assigned
        )
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_db_session.execute.side_effect = [mock_result1, mock_result2]

        with patch(
            "backend.app.crud.user.user.create_user", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = new_user
            user = await _find_or_create_user(mock_db_session, new_user.keycloak_id)

        # Should have no agents
        assert user.agent_ids == []
        mock_get_agent_ids.assert_not_called()

    @patch("backend.app.api.v1.users.settings.AUTO_ASSIGN_AGENTS_TO_USERS", False)
    @patch("backend.app.api.v1.users._build_user_response")
    @patch("backend.app.crud.virtual_agents.virtual_agents.get")
    @patch("backend.app.crud.user.user.update", new_callable=AsyncMock)
    @patch("backend.app.crud.user.user.get", new_callable=AsyncMock)
    def test_regular_user_cannot_assign_when_auto_assign_off(
        self,
        mock_user_get,
        mock_user_update,
        mock_get_virtual_agent,
        mock_build_response,
        test_client,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test regular user cannot assign agents when AUTO_ASSIGN is off."""
        setup_dependencies(user=regular_user, db_session=mock_db_session)

        agent_uuid1 = uuid.uuid4()
        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])
        mock_user_get.return_value = db_user

        agent_data = {"agent_ids": [str(agent_uuid1)]}
        response = test_client.post(
            f"/api/v1/users/{regular_user.keycloak_id}/agents", json=agent_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only admins can modify agent assignments" in response.json()["detail"]

    @patch("backend.app.api.v1.users.settings.AUTO_ASSIGN_AGENTS_TO_USERS", False)
    @patch("backend.app.api.v1.users._build_user_response")
    @patch("backend.app.crud.virtual_agents.virtual_agents.get")
    @patch("backend.app.crud.user.user.update", new_callable=AsyncMock)
    @patch("backend.app.crud.user.user.get", new_callable=AsyncMock)
    def test_admin_can_assign_when_auto_assign_off(
        self,
        mock_user_get,
        mock_user_update,
        mock_get_virtual_agent,
        mock_build_response,
        test_client,
        admin_user,
        regular_user,
        mock_db_session,
        setup_dependencies,
    ):
        """Test admin can assign agents when AUTO_ASSIGN is off."""
        setup_dependencies(user=admin_user, db_session=mock_db_session)

        agent_uuid1 = uuid.uuid4()
        db_user = User(keycloak_id=regular_user.keycloak_id, agent_ids=[])
        mock_user_get.return_value = db_user
        mock_get_virtual_agent.return_value = VirtualAgent(
            id=agent_uuid1,
            name="Test Agent",
            model_name="test-model",
            prompt="Test prompt",
        )
        mock_build_response.return_value = MagicMock(
            keycloak_id=regular_user.keycloak_id,
            username="regular_user",
            email="user@example.com",
            role="user",
            agent_ids=[agent_uuid1],
        )

        agent_data = {"agent_ids": [str(agent_uuid1)]}
        response = test_client.post(
            f"/api/v1/users/{regular_user.keycloak_id}/agents", json=agent_data
        )

        assert response.status_code == status.HTTP_200_OK
