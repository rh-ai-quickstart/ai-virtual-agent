"""
User management API endpoints for authentication, authorization, and access
control for the AI Virtual Agent Kickstart application.

This module provides CRUD operations for user accounts, including user creation,
authentication, role management, and profile updates. It handles role-based access
control for the AI Virtual Agent Kickstart application.

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
from ..utils.auth_utils import is_local_dev_mode, get_or_create_dev_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


async def get_user_from_headers(headers: dict[str, str], db: AsyncSession):
    """
    Get or create user from OAuth proxy headers.

    SECURITY WARNING: This function trusts that OAuth proxy headers are validated
    and cannot be forged. This assumes:
    1. OAuth proxy is properly configured to validate authentication
    2. Headers like X-Forwarded-User are stripped/reset by OAuth proxy
    3. Direct access to this endpoint bypassing OAuth proxy is blocked

    Suggested security improvements:
    1. Validate OAuth proxy source (e.g., check X-Forwarded-Proto, X-Real-IP)
    2. Use OAuth proxy shared secret or JWT validation
    3. Implement IP allowlisting for OAuth proxy
    4. Add header signature validation
    5. Use mutual TLS between OAuth proxy and backend
    """
    # Check if local development mode is enabled
    if is_local_dev_mode():
        log.info("LOCAL_DEV_ENV_MODE is enabled, using development user")
        return await get_or_create_dev_user(db)
    
    username = headers.get("X-Forwarded-User") or headers.get("x-forwarded-user")
    email = headers.get("X-Forwarded-Email") or headers.get("x-forwarded-email")
    if not username and not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Try to find existing user
    result = await db.execute(
        select(models.User).where(
            (models.User.username == username) | (models.User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    # If user doesn't exist, create them (trusting OAuth proxy validation)
    if not user:
        log.info(
            f"Adding user from OAuth proxy headers: username={username}, email={email}"
        )
        user = models.User(
            username=username,
            email=email,
            role="user",  # Default role - admin can change later
            agent_ids=[],  # No agents initially - admin must assign
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        log.info(f"Successfully created user {user.id} with username '{user.username}'")

    return user


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    FastAPI dependency to get the current authenticated user from OAuth proxy headers.

    Args:
        request: HTTP request containing OAuth proxy headers
        db: Database session dependency

    Returns:
        models.User: The authenticated user

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Log authentication attempt for debugging only
    if log.isEnabledFor(logging.DEBUG):
        forwarded_user = request.headers.get("x-forwarded-user")
        forwarded_email = request.headers.get("x-forwarded-email")
        log.debug(
            f"Authentication attempt - User: {forwarded_user}, Email: {forwarded_email}"
        )

    user = await get_user_from_headers(request.headers, db)

    if user:
        log.info(
            f"User authenticated - ID: {user.id}, Username: {user.username}, "
            f"Role: {user.role}"
        )
    else:
        log.warning("Authentication failed - User not found")

    return user


async def require_admin_role(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    FastAPI dependency to ensure the current user has admin role.

    This dependency should be used on endpoints that require admin privileges.
    It will raise a 403 Forbidden error if the user doesn't have admin role.

    Args:
        current_user: The authenticated user (from get_current_user dependency)

    Returns:
        models.User: The authenticated admin user

    Raises:
        HTTPException: 403 if the user doesn't have admin role
    """
    if current_user.role != models.RoleEnum.admin:
        log.warning(
            f"Access denied - User {current_user.username} (ID: {current_user.id}) "
            f"with role '{current_user.role}' attempted admin operation"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource.",
        )

    log.info(
        f"Admin access granted - User {current_user.username} (ID: {current_user.id})"
    )
    return current_user


async def check_user_access(
    user_id: UUID, current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Validate that the current user can access the specified user's data.

    This allows:
    - Admin users to access any user's data
    - Regular users to access only their own data

    Args:
        user_id: The UUID of the user being accessed (from path parameter)
        current_user: The authenticated user (from get_current_user dependency)

    Returns:
        models.User: The authenticated user

    Raises:
        HTTPException: 403 if the user cannot access the requested user's data
    """
    # Admin users can access any user's data
    if current_user.role == models.RoleEnum.admin:
        log.debug(
            f"Admin access granted - User {current_user.username} "
            f"(ID: {current_user.id}) accessing user {user_id}"
        )
        return current_user

    # Regular users can only access their own data
    if current_user.id == user_id:
        log.debug(
            f"Self access granted - User {current_user.username} "
            f"(ID: {current_user.id}) accessing own data"
        )
        return current_user

    log.warning(
        f"Access denied - User {current_user.username} (ID: {current_user.id}) "
        f"attempted to access user {user_id}"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. You can only access your own user data.",
    )


# profile endpoint must be declared first in order to function within
# the /api/users context
@router.get("/profile", response_model=schemas.UserRead)
@router.get("/profile/", response_model=schemas.UserRead)
async def read_profile(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Retrieve an authorized user's profile.

    This endpoint fetches an authorized user's profile information from OAuth proxy
    headers. If the user doesn't exist in the database, they are automatically
    created with default settings (no agents assigned).

    Args:
        request: HTTP request details containing OAuth proxy headers
        db: Database session dependency

    Returns:
        schemas.UserRead: The authorized user's profile (existing or newly created)

    Raises:
        HTTPException: 401 if OAuth headers are missing/invalid

    Note:
        Users created via this endpoint will have no agents initially and will
        need an administrator to assign agents before they can use the chat
        functionality.
    """
    user = await get_user_from_headers(request.headers, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User not found"
        )
    
    # Convert the user to a dict for proper serialization
    user_dict = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,  # Convert enum to string value
        "agent_ids": user.agent_ids or [],
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    return user_dict


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserBase,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin_role),
):
    """
    Create a new user account.

    This endpoint registers a new user in the system. The user's role
    determines their access permissions within the application.

    **Admin Access Required**: Only users with admin role can create new users.

    Args:
        user: User creation data including username, email, and role
        db: Database session dependency
        current_user: Authenticated admin user (injected by dependency)

    Returns:
        schemas.UserRead: The created user

    Raises:
        HTTPException: 403 if the current user is not an admin
        HTTPException: 409 if username/email already exists
        HTTPException: 422 if validation fails
    """
    # Check if user already exists
    existing_user = await db.execute(
        select(models.User).where(
            (models.User.username == user.username) | (models.User.email == user.email)
        )
    )
    if existing_user.scalar_one_or_none():
        log.warning(
            f"User creation failed - Admin {current_user.username} attempted to create "
            f"user with existing username/email: {user.username}/{user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username or email already exists.",
        )

    try:
        db_user = models.User(
            username=user.username,
            email=user.email,
            role=user.role,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        log.info(f"Admin {current_user.username} created new user: {db_user.username}")
        return db_user
    except Exception as e:
        await db.rollback()
        log.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account.",
        )


@router.get("/", response_model=List[schemas.UserRead])
async def read_users(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin_role),
):
    """
    Retrieve all user accounts from the database.

    This endpoint returns a list of all registered users with their profile
    information.

    **Admin Access Required**: Only users with admin role can list all users.

    Args:
        db: Database session dependency
        current_user: Authenticated admin user (injected by dependency)

    Returns:
        List[schemas.UserRead]: List of all users

    Raises:
        HTTPException: 403 if the current user is not an admin
    """
    result = await db.execute(select(models.User))
    return result.scalars().all()


@router.get("/{user_id}", response_model=schemas.UserRead)
async def read_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_user_access),
):
    """
    Retrieve a specific user by their unique identifier.

    This endpoint fetches a single user's profile information using their UUID.

    **Access Control**:
    - Admin users can view any user's profile
    - Regular users can only view their own profile

    Args:
        user_id: The unique identifier of the user to retrieve
        db: Database session dependency
        current_user: Authenticated user (injected by dependency)

    Returns:
        schemas.UserRead: The requested user profile

    Raises:
        HTTPException: 403 if the user cannot access the requested profile
        HTTPException: 404 if the user is not found
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=schemas.UserRead)
async def update_user(
    user_id: UUID,
    user: schemas.UserBase,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin_role),
):
    """
    Update an existing user's profile information.

    This endpoint allows updating user details including username, email,
    and role.

    **Admin Access Required**: Only users with admin role can update users.

    Args:
        user_id: The unique identifier of the user to update
        user: Updated user data
        db: Database session dependency
        current_user: Authenticated admin user (injected by dependency)

    Returns:
        schemas.UserRead: The updated user profile

    Raises:
        HTTPException: 403 if the current user is not an admin
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
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin_role),
):
    """
    Delete a user account from the system.

    This endpoint permanently removes a user account and all associated data.
    Use with caution as this operation cannot be undone.

    **Admin Access Required**: Only users with admin role can delete users.

    Args:
        user_id: The unique identifier of the user to delete
        db: Database session dependency
        current_user: Authenticated admin user (injected by dependency)

    Raises:
        HTTPException: 403 if the current user is not an admin
        HTTPException: 404 if the user is not found
        HTTPException: 400 if trying to delete own account

    Returns:
        None: 204 No Content on successful deletion
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        log.warning(
            f"User deletion failed - Admin {current_user.username} attempted to delete "
            f"non-existent user {user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent admin from deleting their own account
    if current_user.id == user_id:
        log.warning(
            f"Self-deletion blocked - Admin {current_user.username} "
            f"attempted to delete own account"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account.",
        )

    try:
        log.info(f"Admin {current_user.username} deleting user: {db_user.username}")
        await db.delete(db_user)
        await db.commit()
        return None
    except Exception as e:
        await db.rollback()
        log.error(f"Failed to delete user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account.",
        )


@router.post("/{user_id}/agents", response_model=schemas.UserRead)
async def update_user_agents(
    user_id: UUID,
    agent_assignment: schemas.UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin_role),
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
async def get_user_agents(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_user_access),
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
        List[str]: List of agent IDs assigned to the user

    Raises:
        HTTPException: 403 if the user cannot access the requested user's agents
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
    current_user: models.User = Depends(require_admin_role),
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
