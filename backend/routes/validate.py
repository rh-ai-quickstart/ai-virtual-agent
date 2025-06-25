"""Authentication validation endpoints."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from llama_stack.distribution.server.auth_providers import (
    AuthRequest,
    AuthRequestContext,
    AuthResponse,
    User,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.llamastack import (
    get_sa_token,
    get_user_headers_from_request,
    token_to_auth_header,
)
from ..database import get_db
from ..routes.users import get_user_from_headers

router = APIRouter(prefix="/validate", tags=["validate"])

SAR_VALIDATION_URL = "http://localhost:8887/validate-token"
TEST_AUTH_URL = "http://localhost:8887/validate"
REQUEST_TIMEOUT = 10.0


async def make_http_request(
    url: str,
    headers: dict,
    method: str = "GET",
    json_data: dict | None = None,
) -> httpx.Response:
    """Make an HTTP request with proper error handling."""
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(
                    url=url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                response = await client.post(
                    url=url,
                    headers=headers,
                    json=json_data,
                    timeout=REQUEST_TIMEOUT,
                )
            return response
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Authentication service timeout",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service error",
        ) from e


@router.post("", response_model=AuthResponse)
@router.post("/", response_model=AuthResponse)
async def validate(auth_request: AuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Validate a bearer token.

    This endpoint fetches an authorized user's profile information.

    Args:
        auth_request: HTTP request details
        db: Database session dependency

    Returns:
        AuthResponse: The authorized user's profile

    Raises:
        HTTPException: 401 if the user is not authorized
        HTTPException: 403 if the user is not found
    """
    # Prepare headers
    headers = token_to_auth_header(auth_request.api_key)
    user_headers = get_user_headers_from_request(auth_request.request)
    headers.update(user_headers)

    # Make validation request
    response = await make_http_request(SAR_VALIDATION_URL, headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authentication failed: {response.status_code}",
        )

    # Get user from database
    user = await get_user_from_headers(auth_request.request.headers, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User not found"
        )

    return AuthResponse(
        principal=user.username,
        attributes={
            "roles": [user.role],
        },
        message="Authentication successful",
    )


@router.post("/test", response_model=User)
async def validate_with_headers(request: Request) -> User:
    """
    Validate authentication using request headers.

    This endpoint mimics llama-stack authentication request flow.

    Args:
        request: FastAPI request object containing headers

    Returns:
        User: Authenticated user information

    Raises:
        HTTPException: If authentication fails
    """
    # Build the auth request model
    auth_request = AuthRequest(
        api_key=get_sa_token(),
        request=AuthRequestContext(
            path="/",
            headers={
                "x-forwarded-user": request.headers.get("X-Forwarded-User"),
                "x-forwarded-email": request.headers.get("X-Forwarded-Email"),
            },
            params={},
        ),
    )

    # Make validation request
    response = await make_http_request(
        TEST_AUTH_URL, {}, method="POST", json_data=auth_request.model_dump()
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authentication failed: {response.status_code}",
        )

    # Parse and validate the auth response
    try:
        response_data = response.json()
        auth_response = AuthResponse(**response_data)
        return User(auth_response.principal, auth_response.attributes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid authentication response format",
        ) from e
