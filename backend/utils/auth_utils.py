"""
Authentication utilities for local development mode.

This module provides utilities to bypass authentication when LOCAL_DEV_ENV_MODE
is enabled, allowing for easier local development without requiring OAuth
setup.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models

# Ensure .env file is loaded
load_dotenv()

# Development user constants
DEV_USER_USERNAME = "dev-user"
DEV_USER_EMAIL = "dev@localhost.dev"


def is_local_dev_mode() -> bool:
    """
    Check if local development mode is enabled.

    Returns:
        bool: True if LOCAL_DEV_ENV_MODE environment variable is set to 'true'
    """
    return os.getenv("LOCAL_DEV_ENV_MODE", "false").lower() == "true"


async def get_or_create_dev_user(db: AsyncSession) -> models.User:
    """
    Get or create a default development user for local testing.

    Args:
        db: Database session

    Returns:
        models.User: The development user
    """
    dev_username = DEV_USER_USERNAME
    dev_email = DEV_USER_EMAIL

    # Try to find existing dev user
    result = await db.execute(
        select(models.User).where(
            (models.User.username == dev_username) | (models.User.email == dev_email)
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # QUICK TEST MODE: force dev user role to 'user' for UI verification
        # if existing_user.role != models.RoleEnum.user:
        #     existing_user.role = models.RoleEnum.user
        #     await db.commit()
        #     await db.refresh(existing_user)
        return existing_user

    # Create new dev user with all available agents assigned
    dev_user = models.User(
        username=dev_username,
        email=dev_email,
        role=models.RoleEnum.admin,  # Give admin role for full access during development
        # QUICK TEST MODE: force dev user role to 'user' for UI verification
        # role=models.RoleEnum.user,
        agent_ids=[],  # Will be populated when agents are available
    )

    db.add(dev_user)
    await db.commit()
    await db.refresh(dev_user)

    return dev_user


async def ensure_dev_user_has_all_agents(
    db: AsyncSession, available_agent_ids: list[str]
) -> None:
    """
    Ensure the dev user has all available agents assigned (for LOCAL_DEV_ENV_MODE).

    Args:
        db: Database session
        available_agent_ids: List of agent IDs that should be assigned to
                             dev user
    """
    if not is_local_dev_mode() or not available_agent_ids:
        return

    result = await db.execute(
        select(models.User).where(models.User.username == DEV_USER_USERNAME)
    )
    dev_user = result.scalar_one_or_none()

    if not dev_user:
        return

    current_agent_ids = set(dev_user.agent_ids or [])
    new_agent_ids = set(available_agent_ids)

    if current_agent_ids != new_agent_ids:
        dev_user.agent_ids = list(new_agent_ids)
        await db.commit()
        await db.refresh(dev_user)


def get_mock_dev_headers() -> dict[str, str]:
    """
    Get mock headers for development mode.

    Returns:
        dict: Mock headers simulating OAuth proxy headers
    """
    return {
        "X-Forwarded-User": DEV_USER_USERNAME,
        "X-Forwarded-Email": DEV_USER_EMAIL,
    }
