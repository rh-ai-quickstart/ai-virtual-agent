"""Schemas for chat sessions API."""

from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    """Request model for creating new chat sessions."""

    agent_id: UUID
    session_name: Optional[str] = None


class ChatSession(BaseModel):
    """Chat session schema - messages fetched separately via messages endpoint."""

    id: UUID
    title: str
    agent_id: UUID
    conversation_id: Optional[str] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    created_at: str
    updated_at: str


class DeleteSessionResponse(BaseModel):
    """Response for session deletion."""

    message: str


class ConversationMessagesResponse(BaseModel):
    """Response for fetching conversation messages."""

    messages: List[Any] = []
