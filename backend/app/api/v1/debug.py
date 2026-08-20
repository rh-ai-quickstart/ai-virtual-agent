"""Debug endpoints for development."""

import os

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import is_local_dev_mode
from ...database import get_db
from .users import get_user_from_request

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/env")
async def debug_env():
    """Debug endpoint to check environment variables."""
    return {
        "LOCAL_DEV_ENV_MODE_RAW": os.getenv("LOCAL_DEV_ENV_MODE", "NOT_SET"),
        "LOCAL_DEV_ENV_MODE_FUNC": is_local_dev_mode(),
        "DATABASE_URL_SET": "postgresql" in os.getenv("DATABASE_URL", ""),
        "LLAMASTACK_URL_SET": bool(os.getenv("LLAMASTACK_URL")),
    }


@router.get("/auth")
async def debug_auth(request: Request, db: AsyncSession = Depends(get_db)):
    """Debug endpoint to test authentication flow."""
    try:
        current_user = await get_user_from_request(request, db)
        return {
            "success": True,
            "user": (
                {
                    "keycloak_id": str(current_user.keycloak_id),
                    "username": current_user.username,
                    "email": current_user.email,
                    "role": current_user.role,
                }
                if current_user
                else None
            ),
            "dev_mode": is_local_dev_mode(),
            "headers": dict(request.headers),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "dev_mode": is_local_dev_mode(),
            "headers": dict(request.headers),
        }


@router.get("/profile-test")
async def debug_profile_test(request: Request, db: AsyncSession = Depends(get_db)):
    """Debug profile endpoint without schema validation."""
    try:
        current_user = await get_user_from_request(request, db)
        if not current_user:
            return {"error": "User not found"}

        return {
            "keycloak_id": str(current_user.keycloak_id),
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "agent_ids": current_user.agent_ids or [],
        }
    except Exception as e:
        import traceback

        return {"error": str(e), "traceback": traceback.format_exc()}
