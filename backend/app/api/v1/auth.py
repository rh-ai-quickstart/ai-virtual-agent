"""
Authentication endpoints for OAuth/OIDC flow.
"""

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ...core.oauth import KEYCLOAK_BASE_URL, extract_user_from_token, oauth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Get frontend URL for redirects after login
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@router.get("/login")
async def login(request: Request):
    """
    Initiate OAuth login flow.

    Redirects user to Keycloak login page.
    """
    redirect_uri = request.url_for("auth_callback")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    """
    OAuth callback endpoint.

    Keycloak redirects here after successful login with authorization code.
    Exchange code for tokens and create user session.
    """
    try:
        # Exchange authorization code for tokens
        token = await oauth.keycloak.authorize_access_token(request)

        # Extract user info from token
        user_data = extract_user_from_token(token)

        # Store user data in session (user will be created lazily on first API call)
        request.session["user"] = user_data

        # Redirect to frontend immediately (faster!)
        return RedirectResponse(url=FRONTEND_URL, status_code=302)

    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_failed")


@router.get("/logout")
async def logout(request: Request):
    """Logout endpoint - clears session and redirects to Keycloak logout."""
    request.session.clear()
    logout_url = f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/logout?redirect_uri={FRONTEND_URL}"
    return RedirectResponse(url=logout_url)
