"""
Pytest configuration for integration tests.

Simulates browser OAuth flow to authenticate with Keycloak
and obtain session cookies for testing.
"""

import os

import pytest
import requests


@pytest.fixture(scope="session")
def test_backend_url():
    """Get backend URL from environment."""
    return os.getenv("TEST_BACKEND_URL", "http://localhost:8000")


def authenticate_with_keycloak(
    username: str, password: str, test_backend_url: str
) -> requests.Session:
    """
    Authenticate by simulating the browser OAuth flow.

    Args:
        username: Keycloak username
        password: User password
        test_backend_url: Backend API URL

    Returns:
        requests.Session with authenticated session cookie
    """
    from bs4 import BeautifulSoup

    session = requests.Session()

    # Visit /auth/login - backend redirects to Keycloak
    login_response = session.get(f"{test_backend_url}/auth/login", allow_redirects=True)
    if login_response.status_code != 200:
        raise Exception(f"Login redirect failed: {login_response.status_code}")

    # Extract Keycloak cookies (manually set due to localhost cookie domain issues)
    auth_session_id = session.cookies.get("AUTH_SESSION_ID", "")
    kc_restart = session.cookies.get("KC_RESTART", "")

    # Parse the Keycloak login form
    soup = BeautifulSoup(login_response.text, "html.parser")
    form = soup.find("form")
    if not form:
        raise Exception("Could not find login form")

    # Extract all form fields (including hidden ones)
    form_data = {
        input_field.get("name"): input_field.get("value", "")
        for input_field in form.find_all("input")
        if input_field.get("name")
    }
    form_data["username"] = username
    form_data["password"] = password

    # Submit credentials to Keycloak
    auth_response = session.post(
        form.get("action"),
        data=form_data,
        headers={
            "Cookie": f"AUTH_SESSION_ID={auth_session_id}; KC_RESTART={kc_restart}"
        },
        allow_redirects=True,
    )

    if auth_response.status_code != 200:
        raise Exception(f"Authentication failed: {auth_response.status_code}")

    if "session" not in session.cookies:
        raise Exception("No session cookie created")

    return session


@pytest.fixture(scope="session")
def admin_session(test_backend_url) -> requests.Session:
    """Create authenticated session for admin user."""
    return authenticate_with_keycloak("admin", "password", test_backend_url)


@pytest.fixture(scope="session")
def user_session(test_backend_url) -> requests.Session:
    """Create authenticated session for regular user."""
    return authenticate_with_keycloak("testuser", "password", test_backend_url)


@pytest.fixture(scope="session")
def devops_session(test_backend_url) -> requests.Session:
    """Create authenticated session for devops user."""
    return authenticate_with_keycloak("devops", "password", test_backend_url)


# Tavern-specific fixtures to expose session cookies
@pytest.fixture(scope="session")
def admin_session_cookie(admin_session) -> str:
    """Get admin session cookie value for Tavern tests."""
    return admin_session.cookies.get("session", "")


@pytest.fixture(scope="session")
def user_session_cookie(user_session) -> str:
    """Get user session cookie value for Tavern tests."""
    return user_session.cookies.get("session", "")


@pytest.fixture(scope="session")
def devops_session_cookie(devops_session) -> str:
    """Get devops session cookie value for Tavern tests."""
    return devops_session.cookies.get("session", "")


# Tavern variables - make session cookies available to tests
@pytest.fixture(scope="session")
def tavern_vars(admin_session_cookie, user_session_cookie, devops_session_cookie):
    """
    Provide variables that Tavern tests can reference.
    """
    return {
        "admin_session_cookie": admin_session_cookie,
        "user_session_cookie": user_session_cookie,
        "devops_session_cookie": devops_session_cookie,
    }


# Tavern global configuration
@pytest.fixture(scope="session", autouse=True)
def tavern_global_cfg(tavern_vars):
    """Provide session cookie variables to Tavern tests."""
    return {"variables": tavern_vars}
