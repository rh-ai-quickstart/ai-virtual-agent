"""
OAuth/OIDC authentication for Keycloak integration.

This module provides OAuth2/OIDC authentication flow for both local development
and production deployments using Keycloak.
"""

import logging
import os
from typing import Optional

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from starlette.config import Config

logger = logging.getLogger(__name__)

# Keycloak configuration from environment
# KEYCLOAK_SERVER_URL: External URL (what browser sees) - used in OAuth metadata
# KEYCLOAK_SERVER_URL_INTERNAL: Internal URL (backend-to-keycloak) - used for API calls
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
KEYCLOAK_SERVER_URL_INTERNAL = os.getenv(
    "KEYCLOAK_SERVER_URL_INTERNAL", KEYCLOAK_SERVER_URL
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "ai-apps")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "ai-virtual-agent")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "ai-virtual-agent-secret")

# Build OAuth URLs
# Use external URL for OAuth metadata (browser needs to access these)
KEYCLOAK_BASE_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
# Use internal URL for backend API calls
KEYCLOAK_BASE_URL_INTERNAL = f"{KEYCLOAK_SERVER_URL_INTERNAL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_METADATA_URL = f"{KEYCLOAK_BASE_URL_INTERNAL}/.well-known/openid-configuration"

# OAuth client configuration
config = Config(
    environ={
        "KEYCLOAK_CLIENT_ID": KEYCLOAK_CLIENT_ID,
        "KEYCLOAK_CLIENT_SECRET": KEYCLOAK_CLIENT_SECRET,
    }
)

oauth = OAuth(config)
oauth.register(
    name="keycloak",
    client_id=KEYCLOAK_CLIENT_ID,
    client_secret=KEYCLOAK_CLIENT_SECRET,
    # Don't use server_metadata_url to avoid issuer mismatch
    # server_metadata_url=KEYCLOAK_METADATA_URL,
    client_kwargs={
        "scope": "openid email profile",
        "token_endpoint_auth_method": "client_secret_post",
    },
    # Manually specify all endpoints
    authorize_url=f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/auth",
    access_token_url=f"{KEYCLOAK_BASE_URL_INTERNAL}/protocol/openid-connect/token",
    userinfo_url=f"{KEYCLOAK_BASE_URL_INTERNAL}/protocol/openid-connect/userinfo",
    jwks_uri=f"{KEYCLOAK_BASE_URL_INTERNAL}/protocol/openid-connect/certs",
    # Set issuer to match what Keycloak returns (external URL)
    issuer=KEYCLOAK_BASE_URL,
)


def get_session_from_request(request: Request) -> Optional[dict]:
    """
    Extract user session from request cookies.

    Args:
        request: FastAPI request object

    Returns:
        Optional[dict]: User session data if valid, None otherwise
    """
    session_data = request.session.get("user")
    return session_data if session_data else None


def extract_user_from_token(token_data: dict) -> dict:
    """
    Extract user information from Keycloak token response.

    Args:
        token_data: Token response from Keycloak containing id_token, access_token, etc.

    Returns:
        dict: User information with username, email, and roles
    """
    id_token = token_data.get("id_token")
    if not id_token:
        raise ValueError("No id_token in token response")

    # Decode without verification (already verified by authlib during token exchange)
    user_info = jwt.decode(id_token, options={"verify_signature": False})

    # Extract roles from realm_access and determine primary role (highest priority)
    realm_roles = user_info.get("realm_access", {}).get("roles", [])

    # Debug logging to see what roles are in the token
    logger.info(
        f"JWT token roles for user {user_info.get('preferred_username')}: {realm_roles}"
    )

    # Check roles in priority order: admin > devops > user
    if "admin" in realm_roles:
        primary_role = "admin"
    elif "devops" in realm_roles:
        primary_role = "devops"
    else:
        primary_role = "user"

    logger.info(f"Assigned primary role: {primary_role}")

    return {
        "username": user_info.get("preferred_username"),
        "email": user_info.get("email"),
        "role": primary_role,
        "access_token": token_data.get("access_token"),
    }
