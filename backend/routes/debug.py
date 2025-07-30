"""Debug endpoints for development."""

import os
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from backend.utils.auth_utils import is_local_dev_mode
from backend.database import get_db
from backend.routes.users import get_user_from_headers

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
        user = await get_user_from_headers(request.headers, db)
        return {
            "success": True,
            "user": {
                "username": user.username,
                "email": user.email,
                "role": str(user.role),
                "role_value": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "id": str(user.id)
            } if user else None,
            "dev_mode": is_local_dev_mode(),
            "headers": dict(request.headers)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "dev_mode": is_local_dev_mode(),
            "headers": dict(request.headers)
        }


@router.get("/profile-test")
async def debug_profile_test(request: Request, db: AsyncSession = Depends(get_db)):
    """Debug profile endpoint without schema validation."""
    try:
        user = await get_user_from_headers(request.headers, db)
        if not user:
            return {"error": "User not found"}
        
        # Return user data without schema validation
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,  # Use .value to get string representation
            "agent_ids": user.agent_ids or [],
            "created_at": str(user.created_at),
            "updated_at": str(user.updated_at)
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }