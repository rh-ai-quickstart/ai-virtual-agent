"""Authentication validation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from llama_stack.core.server.auth_providers import (
    AuthRequest,
    AuthResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.oauth import get_session_from_request
from ...database import get_db
from .users import get_or_create_user_from_oauth

router = APIRouter(prefix="/validate", tags=["validate"])


async def get_user_from_session(request: Request, db: AsyncSession):
    """Get user from OAuth session."""
    session_data = get_session_from_request(request)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Get or create user from OAuth session data
    user = await get_or_create_user_from_oauth(session_data, db)
    return user


@router.post("", response_model=AuthResponse)
@router.post("/", response_model=AuthResponse)
async def validate(
    _auth_request: AuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate OAuth session authentication."""
    # Get user from OAuth session
    user = await get_user_from_session(request, db)

    return AuthResponse(
        principal=user.username,
        attributes={
            "roles": [user.role],
        },
        message="Authentication successful",
    )
