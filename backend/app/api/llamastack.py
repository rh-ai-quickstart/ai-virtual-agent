import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import Request
from llama_stack_client import AsyncLlamaStackClient

load_dotenv()

LLAMASTACK_URL = os.getenv("LLAMASTACK_URL", "http://localhost:8321")
LLAMASTACK_TIMEOUT = float(os.getenv("LLAMASTACK_TIMEOUT", "180.0"))

# Set up logging
logger = logging.getLogger(__name__)


def get_sa_token() -> Optional[str]:
    """
    Get the service account token from the Kubernetes service account file.

    Returns:
        Optional[str]: The token if found, None otherwise.
    """
    file_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    try:
        with open(file_path, "r") as file:
            token = file.read().strip()
            return token if token else None
    except FileNotFoundError:
        logger.warning(f"Service account token file not found at '{file_path}'")
        return None
    except Exception as e:
        logger.error(f"Error reading service account token: {e}")
        return None


def get_client(
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


def get_client_from_request(
    _request: Optional[Request] = None,
) -> AsyncLlamaStackClient:
    """
    Create a client configured with authentication from the request context.

    Args:
        _request: Optional FastAPI request object (unused, kept for API compatibility)

    Returns:
        AsyncLlamaStackClient: Configured client instance
    """
    token = get_sa_token()
    headers = {}

    if token:
        headers.update(token_to_auth_header(token))
    else:
        logger.warning("No service account token available")

    return get_client(token, headers)


def token_to_auth_header(token: str) -> dict[str, str]:
    """
    Convert a token to an authorization header.

    Args:
        token: The authentication token

    Returns:
        dict[str, str]: Authorization header dictionary
    """
    if not token.startswith("Bearer "):
        auth_header_value = f"Bearer {token}"
    else:
        auth_header_value = token

    return {"Authorization": auth_header_value}


def get_sync_client() -> AsyncLlamaStackClient:
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

    return get_client(token, headers)


# Create sync client instance
sync_client = get_sync_client()
