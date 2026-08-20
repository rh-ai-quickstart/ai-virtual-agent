"""
OAuth/OIDC authentication for Keycloak integration.

This module provides OAuth2/OIDC authentication flow for both local development
and production deployments using Keycloak.
"""

import asyncio
import logging
import os
import time
from typing import Optional

import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.jose import JsonWebKey
from authlib.jose import jwt as authlib_jwt
from starlette.config import Config

logger = logging.getLogger(__name__)

ROLE_PRIORITY = ("admin", "devops")


def resolve_primary_role(roles) -> str:
    """Return the highest-priority role found, defaulting to 'user'."""
    for role in ROLE_PRIORITY:
        if role in roles:
            return role
    return "user"


# Keycloak configuration from environment
# KEYCLOAK_SERVER_URL: External URL (what browser sees) - used in OAuth metadata
# KEYCLOAK_SERVER_URL_INTERNAL: Internal URL (backend-to-keycloak) - used for API calls
_LOCAL_DEV = os.getenv("LOCAL_DEV_ENV_MODE", "false").lower() == "true"

KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
KEYCLOAK_SERVER_URL_INTERNAL = os.getenv(
    "KEYCLOAK_SERVER_URL_INTERNAL", KEYCLOAK_SERVER_URL
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "ai-apps")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "ai-virtual-agent")
KEYCLOAK_CLIENT_SECRET = os.getenv(
    "KEYCLOAK_CLIENT_SECRET",
    "ai-virtual-agent-secret" if _LOCAL_DEV else "",
)
if not _LOCAL_DEV and not KEYCLOAK_CLIENT_SECRET:
    logging.getLogger(__name__).warning(
        "KEYCLOAK_CLIENT_SECRET is not set — OIDC authentication will fail"
    )

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


_JWKS_TTL = 300
_jwks_cache: dict = {}
_jwks_lock = asyncio.Lock()


async def get_jwks() -> dict:
    """Fetch and cache the Keycloak JWKS (refreshed every 5 minutes)."""
    if _jwks_cache.get("keys") and time.monotonic() < _jwks_cache.get("_expires_at", 0):
        return _jwks_cache
    async with _jwks_lock:
        if _jwks_cache.get("keys") and time.monotonic() < _jwks_cache.get(
            "_expires_at", 0
        ):
            return _jwks_cache
        jwks_url = f"{KEYCLOAK_BASE_URL_INTERNAL}/protocol/openid-connect/certs"
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache.clear()
            _jwks_cache.update(resp.json())
            _jwks_cache["_expires_at"] = time.monotonic() + _JWKS_TTL
    return _jwks_cache


def extract_user_from_token(token_data: dict, jwks: dict) -> dict:
    """
    Extract user information from Keycloak token response.

    Args:
        token_data: Token response from Keycloak containing id_token, access_token, etc.
        jwks: JWKS for signature verification (from get_jwks()).

    Returns:
        dict: User information with username, email, and roles
    """
    id_token = token_data.get("id_token")
    if not id_token:
        raise ValueError("No id_token in token response")

    claims = authlib_jwt.decode(id_token, JsonWebKey.import_key_set(jwks))
    claims.options = {
        "iss": {"essential": True, "value": KEYCLOAK_BASE_URL},
        "aud": {"essential": True, "value": KEYCLOAK_CLIENT_ID},
    }
    claims.validate()
    user_info = dict(claims)

    # Extract roles from realm_access and determine primary role (highest priority)
    realm_roles = user_info.get("realm_access", {}).get("roles", [])

    logger.debug(
        f"JWT token roles for user {user_info.get('preferred_username')}: {realm_roles}"
    )

    primary_role = resolve_primary_role(realm_roles)

    logger.debug(f"Assigned primary role: {primary_role}")

    return {
        "keycloak_id": user_info.get("sub"),
        "username": user_info.get("preferred_username"),
        "email": user_info.get("email"),
        "role": primary_role,
    }


_admin_token_cache: dict = {}
_admin_token_lock = asyncio.Lock()


async def get_keycloak_admin_token() -> str:
    """Get an admin token using client credentials grant, cached until near expiry."""
    if _admin_token_cache.get("token") and time.monotonic() < _admin_token_cache.get(
        "expires_at", 0
    ):
        return _admin_token_cache["token"]

    async with _admin_token_lock:
        if _admin_token_cache.get(
            "token"
        ) and time.monotonic() < _admin_token_cache.get("expires_at", 0):
            return _admin_token_cache["token"]

        token_url = f"{KEYCLOAK_BASE_URL_INTERNAL}/protocol/openid-connect/token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                },
            )
            response.raise_for_status()
            data = response.json()

        expires_in = data.get("expires_in", 300)
        _admin_token_cache["token"] = data["access_token"]
        _admin_token_cache["expires_at"] = time.monotonic() + expires_in - 30
        return data["access_token"]


async def fetch_keycloak_users() -> list[dict]:
    """Fetch all users from Keycloak Admin API, paginating to cover the full realm."""
    token = await get_keycloak_admin_token()
    admin_url = f"{KEYCLOAK_SERVER_URL_INTERNAL}/admin/realms/{KEYCLOAK_REALM}/users"
    all_users: list[dict] = []
    first = 0
    page_size = 500

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                admin_url,
                params={"first": first, "max": page_size},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            users = response.json()
            if not users:
                break
            all_users.extend(users)
            if len(users) < page_size:
                break
            first += page_size

    return all_users


async def fetch_keycloak_user(user_id: str) -> Optional[dict]:
    """Fetch a single user by ID from Keycloak Admin API."""
    token = await get_keycloak_admin_token()
    admin_url = (
        f"{KEYCLOAK_SERVER_URL_INTERNAL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(
            admin_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


async def delete_keycloak_user(user_id: str) -> bool:
    """Delete a user from Keycloak. Returns True if deleted, False if not found."""
    token = await get_keycloak_admin_token()
    admin_url = (
        f"{KEYCLOAK_SERVER_URL_INTERNAL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}"
    )
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            admin_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True


async def fetch_keycloak_user_role(user_id: str) -> str:
    """Fetch realm role mappings for a user and return the highest-priority role."""
    token = await get_keycloak_admin_token()
    url = (
        f"{KEYCLOAK_SERVER_URL_INTERNAL}/admin/realms/{KEYCLOAK_REALM}"
        f"/users/{user_id}/role-mappings/realm"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            return "user"
        roles = {r["name"] for r in response.json()}
    return resolve_primary_role(roles)
