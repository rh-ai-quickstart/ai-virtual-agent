"""
User management API endpoints for authentication and user administration.

This module provides CRUD operations for user accounts, including user creation,
authentication, role management, and profile updates. It handles role-based access
control for the AI Virtual Assistant application.

Key Features:
- User registration and profile management
- Role-based access control (admin, user, etc.)
- User lookup and management operations
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..database import get_db
from ..services.user_service import UserService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


async def get_user_from_headers(headers: dict[str, str], db: AsyncSession):
    username = headers.get("X-Forwarded-User")
    email = headers.get("X-Forwarded-Email")
    if not username and not email:
        username = headers.get("x-forwarded-user")
        email = headers.get("x-forwarded-email")
        if not username and not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
    result = await db.execute(
        select(models.User).where(
            (models.User.username == username) | (models.User.email == email)
        )
    )
    return result.scalar_one_or_none()


# profile endpoint must be declared first in order to function within
# the /api/users context
@router.get("/profile", response_model=schemas.UserRead)
@router.get("/profile/", response_model=schemas.UserRead)
async def read_profile(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Retrieve an authorized user's profile.

    This endpoint fetches an authorized user's profile information.

    Args:
        request: HTTP request details
        db: Database session dependency

    Returns:
        schemas.UserRead: The authorized user's profile

    Raises:
        HTTPException: 401 if the user is not authorized
        HTTPException: 403 if the user is not found
    """
    user = await get_user_from_headers(request.headers, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User not found"
        )
    return user


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UserBase, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account.

    This endpoint registers a new user in the system. The user's role
    determines their access permissions within the application.

    Args:
        user: User creation data including username, email, and role
        db: Database session dependency

    Returns:
        schemas.UserRead: The created user

    Raises:
        HTTPException: If username/email already exists or validation fails
    """
    db_user = models.User(
        username=user.username,
        email=user.email,
        role=user.role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.get("/", response_model=List[schemas.UserRead])
async def read_users(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all user accounts from the database.

    This endpoint returns a list of all registered users with their profile
    information.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.UserRead]: List of all users
    """
    result = await db.execute(select(models.User))
    return result.scalars().all()


@router.get("/{user_id}", response_model=schemas.UserRead)
async def read_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific user by their unique identifier.

    This endpoint fetches a single user's profile information using their UUID.

    Args:
        user_id: The unique identifier of the user to retrieve
        db: Database session dependency

    Returns:
        schemas.UserRead: The requested user profile

    Raises:
        HTTPException: 404 if the user is not found
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=schemas.UserRead)
async def update_user(
    user_id: UUID, user: schemas.UserBase, db: AsyncSession = Depends(get_db)
):
    """
    Update an existing user's profile information.

    This endpoint allows updating user details including username, email,
    and role.

    Args:
        user_id: The unique identifier of the user to update
        user: Updated user data
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user profile

    Raises:
        HTTPException: 404 if the user is not found
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user attributes
    for key, value in user.model_dump(exclude_unset=True).items():
        setattr(db_user, key, value)

    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a user account from the system.

    This endpoint permanently removes a user account and all associated data.
    Use with caution as this operation cannot be undone.

    Args:
        user_id: The unique identifier of the user to delete
        db: Database session dependency

    Raises:
        HTTPException: 404 if the user is not found

    Returns:
        None: 204 No Content on successful deletion
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(db_user)
    await db.commit()
    return None


@router.post("/{user_id}/agents", response_model=schemas.UserRead)
async def update_user_agents(
    user_id: UUID,
    agent_assignment: schemas.UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
):
    """
    Add agents to a user's assignment list.

    This endpoint assigns existing agents from LlamaStack to the specified user.
    The system prevents duplicate agent assignments by checking if the user
    already has the agent ID assigned.

    Args:
        user_id: The unique identifier of the user
        agent_assignment: Object containing the list of agent IDs to assign
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user profile with new agent assignments

    Raises:
        HTTPException: 404 if the user is not found
        HTTPException: 404 if any of the specified agents don't exist in LlamaStack
    """
    # Get the user from database
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get current user agent assignments
    current_agent_ids = getattr(db_user, "agent_ids", []) or []

    # Use the service to assign agents
    updated_agent_ids = await UserService.assign_agents_to_user(
        user_agent_ids=current_agent_ids,
        requested_agent_ids=agent_assignment.agent_ids,
    )

    # Update user's agent assignments with the updated agent IDs
    setattr(db_user, "agent_ids", updated_agent_ids)

    await db.commit()
    await db.refresh(db_user)

    log.info(f"Updated agents for user {str(db_user.username)}: {updated_agent_ids}")
    return db_user


@router.get("/{user_id}/agents", response_model=List[str])
async def get_user_agents(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve the list of agents assigned to a specific user.

    This endpoint returns the list of virtual assistant agent IDs that are
    currently assigned to the specified user.

    Args:
        user_id: The unique identifier of the user
        db: Database session dependency

    Returns:
        List[str]: List of agent IDs assigned to the user

    Raises:
        HTTPException: 404 if the user is not found
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User agents not found")

    # Return agent_ids list, or empty list if None
    return db_user.agent_ids or []


@router.delete("/{user_id}/agents", response_model=schemas.UserRead)
async def remove_user_agents(
    user_id: UUID,
    agent_assignment: schemas.UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove agents from a user's assignment list.

    This endpoint removes specified agents from a user's assignment list.
    Since agents are now shared across users, no cleanup of agents is performed.

    Args:
        user_id: The unique identifier of the user
        agent_assignment: Object containing the list of agent IDs to remove
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user profile with remaining agent assignments

    Raises:
        HTTPException: 404 if the user is not found
    """
    # Get the user from database
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get current user agent assignments
    current_agent_ids = getattr(db_user, "agent_ids", []) or []

    # Use the service to remove agents
    remaining_agent_ids = await UserService.remove_agents_from_user(
        current_agent_ids=current_agent_ids,
        agents_to_remove=agent_assignment.agent_ids,
    )

    # Update user's agent assignments with the remaining agent IDs
    setattr(db_user, "agent_ids", remaining_agent_ids)

    await db.commit()
    await db.refresh(db_user)

    log.info(
        f"Removed agents from {str(db_user.username)}: {agent_assignment.agent_ids}"
    )
    log.info(f"Remaining agents: {remaining_agent_ids}")
    return db_user
