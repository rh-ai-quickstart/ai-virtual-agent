import logging
from typing import Optional, Any
import json

from fastapi import Request

logger = logging.getLogger(__name__)


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


def get_user_headers_from_request(
    request: Optional[Request],
) -> dict[str, str]:
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

def create_tool_call_trace_entry(item: Any) -> dict:
    """Create trace entry for MCP tool call."""
    args = item.arguments
    if args and isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            pass

    return {
        "type": "tool_call",
        "name": item.name or "tool",
        "server_label": item.server_label,
        "arguments": args,
        "output": item.output,
        "error": item.error,
        "status": "failed" if item.error else "completed",
    }


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


ERROR_NO_RESPONSE_MESSAGE = "Unable to generate a response. Please try rephrasing your question or try again."