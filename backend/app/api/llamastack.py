import json
import logging
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Request
from llama_stack_client import AsyncLlamaStackClient
from .shared_api import token_to_auth_header, get_user_headers_from_request, get_sa_token

load_dotenv()

LLAMASTACK_URL = os.getenv("LLAMASTACK_URL", "http://localhost:8321")
LLAMASTACK_TIMEOUT = float(os.getenv("LLAMASTACK_TIMEOUT", "180.0"))

# Set up logging
logger = logging.getLogger(__name__)

def get_llamastack_client(
    api_key: Optional[str], headers: Optional[dict[str, str]] = None
) -> AsyncLlamaStackClient:
    """
    Create an AsyncLlamaStackClient with the given configuration.

    Args:
        api_key: Optional API key for authentication
        headers: Optional headers to include in requests

    Returns:
        AsyncLlamaStackClient: Configured client instance
    """
    client = AsyncLlamaStackClient(
        base_url=LLAMASTACK_URL,
        default_headers=headers or {},
        timeout=httpx.Timeout(LLAMASTACK_TIMEOUT),
    )
    if api_key:
        client.api_key = api_key
    # Enhanced agent resource not needed for current functionality
    return client


def get_llamastack_client_from_request(
    request: Optional[Request],
) -> AsyncLlamaStackClient:
    """
    Create a client configured with authentication from the request context.

    Args:
        request: Optional FastAPI request object

    Returns:
        AsyncLlamaStackClient: Configured client instance
    """
    token = get_sa_token()
    headers = {}

    if token:
        headers.update(token_to_auth_header(token))
    else:
        logger.warning("No service account token available")

    user_headers = get_user_headers_from_request(request)
    headers.update(user_headers)

    return get_llamastack_client(token, headers)


def get_llamastack_sync_client() -> AsyncLlamaStackClient:
    """
    Create a sync client with admin credentials.

    Returns:
        AsyncLlamaStackClient: Configured client instance with admin
                               credentials
    """
    token = get_sa_token()
    headers = {}

    if token:
        headers.update(token_to_auth_header(token))
    else:
        logger.warning("No service account token available for sync client")

    # Get admin username with fallback
    admin_username = os.getenv("ADMIN_USERNAME")
    if admin_username:
        headers["X-Forwarded-User"] = admin_username
    else:
        logger.warning("ADMIN_USERNAME environment variable not set")

    return get_llamastack_client(token, headers)


# Create sync client instance
llamastack_sync_client = get_llamastack_sync_client()

# Aliases for backward compatibility
get_client_from_request = get_llamastack_client_from_request
sync_client = llamastack_sync_client

