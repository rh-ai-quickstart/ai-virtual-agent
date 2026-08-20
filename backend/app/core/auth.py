"""
Authentication utilities for local development mode.
"""

import logging
import os
import uuid as uuid_module

from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models import User, VirtualAgent
from ..schemas.user import CurrentUser

load_dotenv()

DEV_USER_USERNAME = "dev-user"
DEV_USER_EMAIL = "dev@localhost.dev"
DEV_USER_KEYCLOAK_ID = uuid_module.UUID("00000000-0000-0000-0000-000000000001")


def is_local_dev_mode() -> bool:
    return os.getenv("LOCAL_DEV_ENV_MODE", "false").lower() == "true"


async def get_or_create_dev_user(db: AsyncSession) -> CurrentUser:
    """Get or create a dev user, returning a CurrentUser composite."""
    result = await db.execute(
        select(User).where(User.keycloak_id == DEV_USER_KEYCLOAK_ID)
    )
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        try:
            existing_user = User(
                keycloak_id=DEV_USER_KEYCLOAK_ID,
                agent_ids=[],
            )
            db.add(existing_user)
            await db.commit()
            await db.refresh(existing_user)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(User).where(User.keycloak_id == DEV_USER_KEYCLOAK_ID)
            )
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                raise

        try:
            agent_result = await db.execute(select(VirtualAgent.id))
            all_agent_ids = [row[0] for row in agent_result.all()]
            if all_agent_ids:
                existing_user.agent_ids = all_agent_ids
                await db.commit()
                logging.info(f"Assigned {len(all_agent_ids)} agents to dev user")
        except Exception as e:
            logging.error(f"Error assigning agents to dev user: {e}")

    return CurrentUser(
        keycloak_id=existing_user.keycloak_id,
        username=DEV_USER_USERNAME,
        email=DEV_USER_EMAIL,
        role="admin",
        agent_ids=existing_user.agent_ids or [],
    )
