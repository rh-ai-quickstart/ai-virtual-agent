"""
User management API endpoints.
"""

import asyncio
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...core.auth import get_or_create_dev_user, is_local_dev_mode
from ...core.oauth import (
    delete_keycloak_user,
    fetch_keycloak_user,
    fetch_keycloak_user_role,
    fetch_keycloak_users,
)
from ...crud.user import user
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas.user import CurrentUser, UserAgentAssignment, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


async def _find_or_create_user(db: AsyncSession, keycloak_id: UUID):
    """Look up user by keycloak_id, create minimal record if missing."""
    existing = await user.get(db, id=keycloak_id)
    if existing:
        return existing

    logger.info(f"Creating app record for Keycloak user {keycloak_id}")
    try:
        existing = await user.create_user(db, keycloak_id=keycloak_id)
    except IntegrityError:
        await db.rollback()
        existing = await user.get(db, id=keycloak_id)
        if not existing:
            raise

    if settings.AUTO_ASSIGN_AGENTS_TO_USERS:
        try:
            all_agent_ids = set(await virtual_agents.get_all_agent_ids(db))
            current_ids = set(existing.agent_ids or [])
            new_ids = all_agent_ids - current_ids
            if new_ids:
                existing.agent_ids = list(current_ids | new_ids)
                await db.commit()
                await db.refresh(existing)
        except Exception as e:
            logger.error(f"Error assigning agents to user: {e}")
    return existing


async def get_user_from_request(request: Request, db: AsyncSession) -> CurrentUser:
    """Get or create user from Keycloak session or dev defaults."""
    session_user = request.session.get("user") if hasattr(request, "session") else None
    if session_user:
        keycloak_id = session_user.get("keycloak_id")
        username = session_user.get("username")
        email = session_user.get("email")
        role = session_user.get("role", "user")

        if keycloak_id:
            db_user = await _find_or_create_user(db, UUID(keycloak_id))
            return CurrentUser(
                keycloak_id=db_user.keycloak_id,
                username=username or "unknown",
                email=email or "",
                role=role,
                agent_ids=db_user.agent_ids or [],
            )

    # Dev mode defaults
    if is_local_dev_mode():
        return await get_or_create_dev_user(db)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """FastAPI dependency to get the current authenticated user."""
    current_user = await get_user_from_request(request, db)
    logger.info(
        f"User authenticated - keycloak_id: {current_user.keycloak_id}, "
        f"username: {current_user.username}"
    )
    return current_user


async def require_admin_role(current_user: CurrentUser = Depends(get_current_user)):
    """FastAPI dependency to ensure the current user has admin role."""
    if current_user.role != "admin":
        logger.warning(
            f"Access denied - User {current_user.username} attempted admin operation"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource.",
        )
    return current_user


@router.get("/profile", response_model=UserResponse)
async def read_profile(request: Request, db: AsyncSession = Depends(get_db)):
    """Retrieve the current user's profile (token + DB data)."""
    current_user = await get_user_from_request(request, db)
    return UserResponse(
        keycloak_id=current_user.keycloak_id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        agent_ids=current_user.agent_ids,
    )


@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_role),
):
    """Retrieve all users (admin only). Merges Keycloak identity with app DB data."""
    try:
        kc_users = await fetch_keycloak_users()
    except Exception as e:
        logger.error(f"Failed to fetch users from Keycloak: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch users from Keycloak",
        )

    db_users = await user.get_multi(db, limit=len(kc_users) or 1000)
    db_user_map = {str(u.keycloak_id): u for u in db_users}

    sem = asyncio.Semaphore(10)

    async def _fetch_role(kid):
        async with sem:
            return await fetch_keycloak_user_role(kid)

    kc_ids = [kc_u.get("id") for kc_u in kc_users]
    roles = await asyncio.gather(*(_fetch_role(kid) for kid in kc_ids))

    result = []
    for kc_user, role in zip(kc_users, roles):
        kc_id = kc_user.get("id")
        db_record = db_user_map.get(kc_id)
        result.append(
            UserResponse(
                keycloak_id=UUID(kc_id),
                username=kc_user.get("username", "unknown"),
                email=kc_user.get("email", ""),
                role=role,
                agent_ids=db_record.agent_ids if db_record else [],
            )
        )
    return result


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a specific user by keycloak_id."""
    if current_user.role != "admin" and current_user.keycloak_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own user data.",
        )

    # If requesting own profile, use token data
    if current_user.keycloak_id == user_id:
        return UserResponse(
            keycloak_id=current_user.keycloak_id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            agent_ids=current_user.agent_ids,
        )

    # Admin viewing another user — fetch from Keycloak
    try:
        kc_user = await fetch_keycloak_user(str(user_id))
    except Exception as e:
        logger.error(f"Failed to fetch user from Keycloak: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY)

    if not kc_user:
        raise HTTPException(status_code=404, detail="User not found in Keycloak")

    db_record = await user.get(db, id=user_id)
    role = await fetch_keycloak_user_role(str(user_id))
    return UserResponse(
        keycloak_id=user_id,
        username=kc_user.get("username", "unknown"),
        email=kc_user.get("email", ""),
        role=role,
        agent_ids=db_record.agent_ids if db_record else [],
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin_role),
):
    """Delete a user from both the app database and Keycloak (admin only)."""
    if current_user.keycloak_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    db_removed = await user.remove(db, id=user_id)

    kc_removed = False
    try:
        kc_removed = await delete_keycloak_user(str(user_id))
    except Exception as e:
        logger.error(f"Failed to delete user {user_id} from Keycloak: {e}")

    if not db_removed and not kc_removed:
        raise HTTPException(status_code=404, detail="User not found")

    return None


def get_unique_agent_ids(
    user_agent_ids: List[UUID], new_agent_ids: List[UUID]
) -> List[UUID]:
    """Return only new unique agent IDs not already assigned."""
    return [aid for aid in new_agent_ids if aid not in user_agent_ids]


async def assign_agents_to_user(
    db: AsyncSession, user_agent_ids: List[UUID], requested_agent_ids: List[UUID]
) -> List[UUID]:
    """Add requested agents to user's agent list, preventing duplicates."""
    for agent_id in requested_agent_ids:
        agent = await virtual_agents.get(db, id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    new_agent_ids = get_unique_agent_ids(user_agent_ids, requested_agent_ids)
    return user_agent_ids + new_agent_ids


def remove_agents_from_user(
    current_agent_ids: List[UUID], agents_to_remove: List[UUID]
) -> List[UUID]:
    """Remove specified agents from user's agent list."""
    return [aid for aid in current_agent_ids if aid not in agents_to_remove]


async def _build_user_response(
    current_user: CurrentUser, user_id: UUID, agent_ids: List[UUID]
) -> UserResponse:
    """Build a UserResponse using token data for self, or Keycloak for another user."""
    if current_user.keycloak_id == user_id:
        return UserResponse(
            keycloak_id=user_id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            agent_ids=agent_ids,
        )

    try:
        kc_user = await fetch_keycloak_user(str(user_id))
        role = await fetch_keycloak_user_role(str(user_id))
        return UserResponse(
            keycloak_id=user_id,
            username=kc_user.get("username", "unknown") if kc_user else "unknown",
            email=kc_user.get("email", "") if kc_user else "",
            role=role,
            agent_ids=agent_ids,
        )
    except Exception:
        return UserResponse(
            keycloak_id=user_id,
            username="unknown",
            email="",
            role="user",
            agent_ids=agent_ids,
        )


@router.get("/{user_id}/agents", response_model=List[UUID])
async def get_user_agents(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve the list of agents assigned to a specific user."""
    if current_user.role != "admin" and current_user.keycloak_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own agent data.",
        )

    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    return target_user.agent_ids or []


@router.post("/{user_id}/agents", response_model=UserResponse)
async def update_user_agents(
    user_id: UUID,
    agent_assignment: UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Add agents to a user's assignment list."""
    if not settings.AUTO_ASSIGN_AGENTS_TO_USERS and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can modify agent assignments.",
        )
    if current_user.role != "admin" and current_user.keycloak_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own agent assignments.",
        )

    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    current_agent_ids = target_user.agent_ids or []
    updated_agent_ids = await assign_agents_to_user(
        db=db,
        user_agent_ids=current_agent_ids,
        requested_agent_ids=agent_assignment.agent_ids,
    )

    target_user.agent_ids = updated_agent_ids
    await user.update(db, db_obj=target_user, obj_in={"agent_ids": updated_agent_ids})

    return await _build_user_response(current_user, user_id, updated_agent_ids)


@router.delete("/{user_id}/agents", response_model=UserResponse)
async def remove_user_agents(
    user_id: UUID,
    agent_assignment: UserAgentAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Remove agents from a user's assignment list."""
    if not settings.AUTO_ASSIGN_AGENTS_TO_USERS and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can modify agent assignments.",
        )
    if current_user.role != "admin" and current_user.keycloak_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own agent assignments.",
        )

    target_user = await user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    current_agent_ids = target_user.agent_ids or []
    remaining_agent_ids = remove_agents_from_user(
        current_agent_ids=current_agent_ids,
        agents_to_remove=agent_assignment.agent_ids,
    )

    target_user.agent_ids = remaining_agent_ids
    await user.update(db, db_obj=target_user, obj_in={"agent_ids": remaining_agent_ids})

    return await _build_user_response(current_user, user_id, remaining_agent_ids)
