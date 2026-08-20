"""
Authentication endpoints for Keycloak OIDC flow.
"""

import logging
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...core.oauth import (
    KEYCLOAK_BASE_URL,
    extract_user_from_token,
    get_jwks,
    oauth,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def _frontend_url_with_params(extra: dict[str, str]) -> str:
    parsed = urlparse(FRONTEND_URL)
    params = parse_qs(parsed.query)
    params.update(extra)
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


@router.get("/login")
async def login(request: Request):
    """Redirect user to Keycloak login page."""
    redirect_uri = request.url_for("auth_callback")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    """Exchange authorization code for tokens and create session."""
    try:
        token = await oauth.keycloak.authorize_access_token(request)
        jwks = await get_jwks()
        user_data = extract_user_from_token(token, jwks=jwks)
        request.session["user"] = user_data
        return RedirectResponse(url=FRONTEND_URL, status_code=302)
    except OAuthError as e:
        logger.error(f"OAuth authentication error: {e}", exc_info=True)
        return RedirectResponse(url=_frontend_url_with_params({"error": "auth_failed"}))
    except Exception as e:
        logger.error(f"Authentication callback failed: {e}", exc_info=True)
        return RedirectResponse(url=_frontend_url_with_params({"error": "auth_failed"}))


@router.get("/account")
async def account():
    """Redirect to Keycloak Account Console."""
    return RedirectResponse(url=f"{KEYCLOAK_BASE_URL}/account")


@router.post("/logout")
async def logout(request: Request):
    """Clear session and return Keycloak logout URL."""
    request.session.clear()
    params = urlencode(
        {
            "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "ai-virtual-agent"),
            "post_logout_redirect_uri": FRONTEND_URL,
        }
    )
    logout_url = f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/logout?{params}"
    return {"logout_url": logout_url}
