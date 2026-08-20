"""
User-related schemas.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Composite user: token-derived identity + DB-derived app data."""

    keycloak_id: UUID
    username: str
    email: str
    role: str
    agent_ids: List[UUID] = []


class UserResponse(BaseModel):
    """Schema for user in API responses (merged Keycloak + DB data)."""

    keycloak_id: UUID
    username: str
    email: str
    role: str
    agent_ids: List[UUID] = []


class UserUpdate(BaseModel):
    """Schema for updating a user (only agent_ids is updatable)."""

    agent_ids: Optional[List[UUID]] = None


class UserAgentAssignment(BaseModel):
    """Schema for assigning/removing agents to/from a user."""

    agent_ids: List[UUID]
