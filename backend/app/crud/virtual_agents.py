"""
CRUD operations for Virtual Agents.
"""

import logging
import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import AgentTemplate, ChatMessage, ChatSession, User, VirtualAgent
from ..schemas import VirtualAgentCreate
from .base import CRUDBase

logger = logging.getLogger(__name__)


class DuplicateVirtualAgentNameError(Exception):
    """Raised when trying to create a virtual agent with a name that already exists."""

    pass


class CRUDVirtualAgent(CRUDBase[VirtualAgent, VirtualAgentCreate, dict]):
    async def create(self, db: AsyncSession, *, obj_in: dict) -> VirtualAgent:
        """Create virtual agent with transaction management and name uniqueness validation."""
        try:
            db_obj = VirtualAgent(**obj_in)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await db.rollback()
            # Check if this is a unique constraint violation on the name column
            if "uq_virtual_agents_name" in str(
                e.orig
            ) or "UNIQUE constraint failed" in str(e.orig):
                raise DuplicateVirtualAgentNameError(
                    f"Virtual agent with name '{obj_in['name']}' already exists"
                )
            # Re-raise other integrity errors
            raise
        except Exception:
            await db.rollback()
            raise

    async def get_with_template(
        self, db: AsyncSession, *, id: uuid.UUID
    ) -> Optional[VirtualAgent]:
        """Get virtual agent with loaded template and suite relationships."""
        result = await db.execute(
            select(VirtualAgent)
            .options(
                selectinload(VirtualAgent.template).selectinload(AgentTemplate.suite)
            )
            .where(VirtualAgent.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_template_id(
        self, db: AsyncSession, *, template_id: uuid.UUID
    ) -> Optional[VirtualAgent]:
        """Get virtual agent by template_id."""
        result = await db.execute(
            select(VirtualAgent).where(VirtualAgent.template_id == template_id).limit(1)
        )
        return result.scalars().first()

    async def get_all_with_templates(self, db: AsyncSession) -> List[VirtualAgent]:
        """Get all virtual agents with loaded template and suite relationships."""
        result = await db.execute(
            select(VirtualAgent).options(
                selectinload(VirtualAgent.template).selectinload(AgentTemplate.suite)
            )
        )
        return result.scalars().all()

    async def get_all_agent_ids(self, db: AsyncSession) -> List[uuid.UUID]:
        """Get all virtual agent IDs."""
        result = await db.execute(select(VirtualAgent.id))
        return [row[0] for row in result.all()]

    async def delete_with_sessions(self, db: AsyncSession, *, id: str) -> bool:
        """Delete virtual agent and all associated sessions.

        Note: ChatSession has a foreign key to VirtualAgent with CASCADE delete,
        so deleting the agent will automatically delete associated sessions.
        However, we must manually delete chat messages first.
        """
        try:
            # Check if agent exists
            agent = await self.get(db, id=id)
            if not agent:
                return False

            # Delete messages for all sessions associated with this agent
            # (must be done before CASCADE deletes the sessions)
            await db.execute(
                delete(ChatMessage).where(
                    ChatMessage.session_id.in_(
                        select(ChatSession.id).where(ChatSession.agent_id == id)
                    )
                )
            )

            # Delete the agent (CASCADE will delete associated sessions)
            await db.execute(delete(VirtualAgent).where(VirtualAgent.id == id))

            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise

    async def sync_all_users_with_all_agents(self, db: AsyncSession) -> dict:
        """Ensure all users have access to all agents."""
        try:
            # Get all users
            users_result = await db.execute(select(User))
            all_users = users_result.scalars().all()

            # Get all agent IDs
            all_agent_ids = await self.get_all_agent_ids(db)

            # Update each user's agent_ids
            for user in all_users:
                user.agent_ids = all_agent_ids

            await db.commit()
            return {
                "users_processed": len(all_users),
                "total_agents": len(all_agent_ids),
                "success": True,
            }
        except Exception:
            await db.rollback()
            raise


virtual_agents = CRUDVirtualAgent(VirtualAgent)
