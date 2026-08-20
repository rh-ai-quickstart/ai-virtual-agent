"""
CRUD operations for User model.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..schemas.user import UserUpdate
from .base import CRUDBase

logger = logging.getLogger(__name__)


class CRUDUser(CRUDBase[User, UserUpdate, UserUpdate]):
    """CRUD operations for User."""

    async def get(self, db: AsyncSession, id: UUID) -> Optional[User]:
        """Get user by keycloak_id."""
        result = await db.execute(select(User).where(User.keycloak_id == id))
        return result.scalar_one_or_none()

    async def remove(self, db: AsyncSession, *, id: UUID) -> Optional[User]:
        """Delete user by keycloak_id."""
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def get_users_with_agent(
        self, db: AsyncSession, *, agent_id: UUID
    ) -> List[User]:
        """Get all users that have access to a specific agent."""
        result = await db.execute(select(User).where(User.agent_ids.any(agent_id)))
        return result.scalars().all()

    async def create_user(
        self,
        db: AsyncSession,
        *,
        keycloak_id: UUID,
        agent_ids: List[UUID] = None,
    ) -> User:
        """Create a new user record for a Keycloak user."""
        try:
            db_obj = User(
                keycloak_id=keycloak_id,
                agent_ids=agent_ids or [],
            )
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception:
            await db.rollback()
            raise

    async def update_agent_assignment(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        agent_ids_to_add: List[UUID] = None,
        agent_ids_to_remove: List[UUID] = None,
    ) -> User:
        """Update user's agent assignments."""
        try:
            user_obj = await self.get(db, id=user_id)
            if not user_obj:
                return None

            current_agents = set(user_obj.agent_ids or [])

            if agent_ids_to_add:
                current_agents.update(agent_ids_to_add)
            if agent_ids_to_remove:
                current_agents.difference_update(agent_ids_to_remove)

            user_obj.agent_ids = list(current_agents)
            await db.commit()
            await db.refresh(user_obj)
            return user_obj
        except Exception:
            await db.rollback()
            raise


user = CRUDUser(User)
