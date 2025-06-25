import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Request
from llama_stack_client import AsyncLlamaStackClient

from ..virtual_agents.agent_resource import EnhancedAgentResource

load_dotenv()

LLAMASTACK_URL = os.getenv("LLAMASTACK_URL", "http://localhost:8321")

# Set up logging
logger = logging.getLogger(__name__)


def get_header_case_insensitive(request: Request, header_name: str) -> Optional[str]:
    """
    Get a header value with case-insensitive fallback.

    Args:
        request: FastAPI request object
        header_name: The header name to look for

    Returns:
        Optional[str]: The header value if found, None otherwise
    """
    return request.headers.get(header_name) or request.headers.get(header_name.lower())


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
    )
    if api_key:
        client.api_key = api_key
    client.agents = EnhancedAgentResource(client)
    return client


def get_client_from_request(request: Optional[Request]) -> AsyncLlamaStackClient:
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


def get_user_headers_from_request(request: Optional[Request]) -> dict[str, str]:
    """
    Extract user-related headers from the request.

    Args:
        request: Optional FastAPI request object

    Returns:
        dict[str, str]: Dictionary of user headers
    """
    headers = {}
    if request is None:
        return headers

    # Get user header
    user_header = get_header_case_insensitive(request, "X-Forwarded-User")
    if user_header:
        headers["X-Forwarded-User"] = user_header

    # Get email header
    email_header = get_header_case_insensitive(request, "X-Forwarded-Email")
    if email_header:
        headers["X-Forwarded-Email"] = email_header

    return headers


def get_sync_client() -> AsyncLlamaStackClient:
    """
    Create a sync client with admin credentials.

    Returns:
        AsyncLlamaStackClient: Configured client instance with admin credentials
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

    return get_client(token, headers)


# Create sync client instance
sync_client = get_sync_client()
