"""Authentication validation endpoints.

Called by LlamaStack to validate bearer tokens.  The backend is the
sole caller of LlamaStack — it authenticates using the pod's
Kubernetes service-account (SA) token as the bearer token.

Per-user authorization (role checks, ownership) is enforced by the
backend *before* any LlamaStack call is made, so granting admin here
is safe: LlamaStack never receives unauthenticated end-user requests
directly.  Alternatives like minting per-user JWTs or threading user
identity through a header that LlamaStack forwards would add
complexity without meaningful security benefit, since the trust
boundary is between the user and the backend, not between the backend
and LlamaStack.
"""

import hmac
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from llama_stack.core.server.auth_providers import (
    AuthRequest,
    AuthResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.shared_api import get_sa_token
from ...core.auth import get_or_create_dev_user, is_local_dev_mode
from ...database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validate", tags=["validate"])


@router.post("", response_model=AuthResponse)
@router.post("/", response_model=AuthResponse)
async def validate(auth_request: AuthRequest, db: AsyncSession = Depends(get_db)):
    """Validate a bearer token."""
    if is_local_dev_mode():
        dev_user = await get_or_create_dev_user(db)
        return AuthResponse(
            principal=dev_user.username,
            attributes={"roles": [dev_user.role]},
            message="Authentication successful",
        )

    sa_token = get_sa_token()
    if sa_token and hmac.compare_digest(auth_request.api_key or "", sa_token):
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        return AuthResponse(
            principal=admin_username,
            attributes={"roles": ["admin"]},
            message="Authentication successful",
        )

    logger.warning("Validate called without valid SA token")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed: no valid credentials",
    )
