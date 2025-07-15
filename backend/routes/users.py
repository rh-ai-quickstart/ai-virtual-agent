"""
User management API endpoints for authentication and user administration.

This module provides CRUD operations for user accounts, including user creation,
authentication, role management, and profile updates. It handles role-based access
control for the AI Agent Builder application.

Key Features:
- User registration and profile management
- Role-based access control (admin, user, etc.)
- User lookup and management operations
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])


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
    username = request.headers.get("X-Forwarded-User")
    email = request.headers.get("X-Forwarded-Email")
    if not username and not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    result = await db.execute(
        select(models.User).where(
            (models.User.username == username) | (models.User.email == email)
        )
    )
    user = result.scalar_one_or_none()
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
    db_user.username = user.username
    db_user.email = user.email
    db_user.role = user.role
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
