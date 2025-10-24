"""
User management API endpoints.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...core.auth import is_local_dev_mode
from ...crud.user import user
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...models import RoleEnum
from ...schemas import UserAgentAssignment, UserCreate, UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


async def get_unique_agent_ids(
    user_agent_ids: List[UUID], new_agent_ids: List[UUID]
) -> List[UUID]:
    """Check for duplicate agent IDs and return only new unique ones."""
    unique_agent_ids = []
    for agent_id in new_agent_ids:
        if agent_id not in user_agent_ids:
            unique_agent_ids.append(agent_id)
        else:
            logger.info(f"Agent {agent_id} already assigned to user, skipping")
    return unique_agent_ids


async def assign_agents_to_user(
    db: AsyncSession, user_agent_ids: List[UUID], requested_agent_ids: List[UUID]
) -> List[UUID]:
    """Add requested agents to user's agent list, preventing duplicates."""
    # Verify all requested agents exist in our VirtualAgent table
    for agent_id in requested_agent_ids:
        agent = await virtual_agents.get(db, id=agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found in VirtualAgent")
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        logger.info(f"Verified agent exists: {agent_id} ({agent.name})")

    # Check for duplicates and get only new unique agent IDs
    new_agent_ids = await get_unique_agent_ids(user_agent_ids, requested_agent_ids)

    # Combine existing and new agent IDs
    all_agent_ids = user_agent_ids + new_agent_ids

    logger.info(f"Added {len(new_agent_ids)} new agents to user")
    return all_agent_ids


async def remove_agents_from_user(
    current_agent_ids: List[UUID], agents_to_remove: List[UUID]
) -> List[UUID]:
    """Remove specified agents from user's agent list."""
    # Calculate remaining agents
    remaining_agent_ids = [
        agent_id for agent_id in current_agent_ids if agent_id not in agents_to_remove
    ]

    logger.info(f"Removed {len(agents_to_remove)} agents from user")
    return remaining_agent_ids


async def get_user_from_headers(headers: dict[str, str], db: AsyncSession):
    """
    Get or create user from OAuth proxy headers.

    SECURITY WARNING: In production, this function trusts that OAuth proxy
    headers are validated and cannot be forged. In local dev mode, headers
    are trusted without OAuth validation for testing purposes.
    """
    username = headers.get("X-Forwarded-User") or headers.get("x-forwarded-user")
    email = headers.get("X-Forwarded-Email") or headers.get("x-forwarded-email")

    # In dev mode, provide defaults if no headers present
    if is_local_dev_mode():
        if not username and not email:
            logger.info("LOCAL_DEV_ENV_MODE: No headers provided, using defaults")
            username = "dev-user"
            email = "dev@localhost.dev"
        else:
            logger.info(
                f"LOCAL_DEV_ENV_MODE: Using headers username={username}, email={email}"
            )
    else:
        # In production, require headers
        if not username and not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    # Try to find existing user
    logger.info(f"Looking up user: username={username}, email={email}")
    existing_user = await user.get_by_username_or_email(
        db, username=username, email=email
    )

    # If user doesn't exist, create them
    if not existing_user:
        # In dev mode, grant admin role to all auto-created users for testing
        role = "admin" if is_local_dev_mode() else "user"
        logger.info(
            f"User not found, creating: username={username}, email={email}, role={role}"
        )
        existing_user = await user.create_user(
            db, username=username, email=email, role=role, agent_ids=[]
        )
        logger.info(f"Successfully created user {existing_user.id}")
    else:
        logger.info(
            f"Found existing user: {existing_user.id} (username={existing_user.username})"
        )

    return existing_user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """FastAPI dependency to get the current authenticated user."""
    if logger.isEnabledFor(logging.DEBUG):
        forwarded_user = request.headers.get("x-forwarded-user")
        forwarded_email = request.headers.get("x-forwarded-email")
        logger.debug(
            f"Authentication attempt - User: {forwarded_user}, Email: {forwarded_email}"
        )

    current_user = await get_user_from_headers(request.headers, db)

    if current_user:
        logger.info(
            f"User authenticated - ID: {current_user.id}, Username: {current_user.username}"
        )
    else:
        logger.warning("Authentication failed - User not found")

    return current_user


async def require_admin_role(current_user=Depends(get_current_user)):
    """FastAPI dependency to ensure the current user has admin role."""
    if current_user.role != RoleEnum.admin:
        logger.warning(
            f"Access denied - User {current_user.username} attempted admin operation"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource.",
        )
    return current_user


@router.get("/profile", response_model=UserResponse)
@router.get("/profile/", response_model=UserResponse)
async def read_profile(request: Request, db: AsyncSession = Depends(get_db)):
    """Retrieve an authorized user's profile."""
    current_user = await get_user_from_headers(request.headers, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User not found"
        )

    # Convert the user for serialization
    user_dict = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "agent_ids": current_user.agent_ids or [],
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }

    return user_dict


@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db), current_user=Depends(require_admin_role)
):
    """Retrieve all users (admin only)."""
    return await user.get_multi(db)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve a specific user by ID."""
    # Check permissions (admin or self-access)
    if current_user.role != RoleEnum.admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own user data.",
        )

    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    return target_user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_role),
):
    """Create a new user account (admin only)."""
    # Check if user already exists
    existing_user = await user.get_by_username_or_email(
        db, username=user_data.username, email=user_data.email
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username or email already exists.",
        )

    created_user = await user.create(db, obj_in=user_data)

    # Sync all users with all agents if enabled
    if settings.AUTO_ASSIGN_AGENTS_TO_USERS:
        try:
            sync_result = await virtual_agents.sync_all_users_with_all_agents(db)
            logger.info(f"Agent-user sync completed after user creation: {sync_result}")
        except Exception as sync_error:
            logger.error(f"Error syncing agents to new user: {str(sync_error)}")

    return created_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_role),
):
    """Update a user account (admin only)."""
    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    return await user.update(db, db_obj=target_user, obj_in=user_data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_role),
):
    """Delete a user account (admin only)."""
    # Prevent admin from deleting their own account
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    removed = await user.remove(db, id=user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="User not found")
    return None


@router.get("/{user_id}/agents", response_model=List[UUID])
async def get_user_agents(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve the list of agents assigned to a specific user.

    This endpoint returns the list of virtual agent IDs that are
    currently assigned to the specified user.

    **Access Control**:
    - Admin users can view any user's agents
    - Regular users can only view their own agents

    Args:
        user_id: The unique identifier of the user
        db: Database session dependency
        current_user: Authenticated user (injected by dependency)

    Returns:
        List[UUID]: List of agent IDs assigned to the user

    Raises:
        HTTPException: 403 if the user cannot access the requested user's
                       agents
        HTTPException: 404 if the user is not found
    """
    # Check permissions (admin or self-access)
    if current_user.role != RoleEnum.admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own agent data.",
        )

    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return agent_ids list, or empty list if None
    return target_user.agent_ids or []


@router.post("/{user_id}/agents", response_model=UserResponse)
async def update_user_agents(
    user_id: UUID,
    agent_assignment: UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Add agents to a user's assignment list.

    This endpoint assigns existing agents from VirtualAgents to the specified
    user. The system prevents duplicate agent assignments by checking if the user
    already has the agent ID assigned.

    Args:
        user_id: The unique identifier of the user
        agent_assignment: Object containing the list of agent IDs to assign
        db: Database session dependency
        current_user: Authenticated user (injected by dependency)

    Returns:
        UserResponse: The updated user profile with new agent assignments

    Raises:
        HTTPException: 403 if the authenticated user cannot modify this user's agents
        HTTPException: 404 if the user is not found
        HTTPException: 404 if any of the specified agents don't exist in VirtualAgent
    """
    # Check permissions (admin or self-access)
    if current_user.role != RoleEnum.admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own agent assignments.",
        )

    # Get the user from database
    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get current user agent assignments
    current_agent_ids = target_user.agent_ids or []

    # Assign agents to user
    updated_agent_ids = await assign_agents_to_user(
        db=db,
        user_agent_ids=current_agent_ids,
        requested_agent_ids=agent_assignment.agent_ids,
    )

    # Update user's agent assignments with the updated agent IDs
    target_user.agent_ids = updated_agent_ids
    updated_user = await user.update(
        db, db_obj=target_user, obj_in={"agent_ids": updated_agent_ids}
    )

    logger.info(f"Updated agents for user {target_user.username}: {updated_agent_ids}")
    return updated_user


@router.delete("/{user_id}/agents", response_model=UserResponse)
async def remove_user_agents(
    user_id: UUID,
    agent_assignment: UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Remove agents from a user's assignment list.

    This endpoint removes specified agents from a user's assignment list.
    Since agents are now shared across users, no cleanup of agents is performed.

    Args:
        user_id: The unique identifier of the user
        agent_assignment: Object containing the list of agent IDs to remove
        db: Database session dependency
        current_user: Authenticated user (injected by dependency)

    Returns:
        UserResponse: The updated user profile with remaining agent assignments

    Raises:
        HTTPException: 403 if the authenticated user cannot modify this user's agents
        HTTPException: 404 if the user is not found
    """
    # Check permissions (admin or self-access)
    if current_user.role != RoleEnum.admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own agent assignments.",
        )

    # Get the user from database
    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get current user agent assignments
    current_agent_ids = target_user.agent_ids or []

    # Remove agents from user
    remaining_agent_ids = await remove_agents_from_user(
        current_agent_ids=current_agent_ids,
        agents_to_remove=agent_assignment.agent_ids,
    )

    # Update user's agent assignments with the remaining agent IDs
    target_user.agent_ids = remaining_agent_ids
    updated_user = await user.update(
        db, db_obj=target_user, obj_in={"agent_ids": remaining_agent_ids}
    )

    logger.info(
        f"Removed agents from {target_user.username}: {agent_assignment.agent_ids}"
    )
    logger.info(f"Remaining agents: {remaining_agent_ids}")
    return updated_user
