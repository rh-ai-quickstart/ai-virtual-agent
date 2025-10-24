"""
Chat-related schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from .base import BaseSchema, TimestampMixin


class TextContentItem(BaseModel):
    """Text content item for LlamaStack format."""

    type: Literal["input_text", "output_text"]
    text: str


class ImageContentItem(BaseModel):
    """Image content item for LlamaStack format."""

    type: Literal["input_image", "output_image"]
    image_url: str


# Union type for content items
ContentItem = Union[TextContentItem, ImageContentItem]


class ChatMessage(BaseModel):
    """Schema for individual chat messages in requests."""

    role: str
    content: List[ContentItem]
    response_id: Optional[str] = None


class ChatMessageResponse(ChatMessage):
    """Schema for chat message in API responses."""

    id: UUID
    session_id: UUID
    timestamp: datetime


class ChatSessionBase(BaseModel):
    """Base chat session schema."""

    title: Optional[str] = None
    session_state: Dict[str, Any] = {}


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a chat session."""

    agent_id: UUID
    session_name: Optional[str] = None


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""

    title: Optional[str] = None
    session_state: Optional[Dict[str, Any]] = None
    agent_id: Optional[UUID] = None


class ChatSessionInDB(ChatSessionBase, TimestampMixin, BaseSchema):
    """Schema for chat session as stored in database."""

    id: UUID
    agent_id: Optional[UUID] = None


class ChatSessionResponse(ChatSessionInDB):
    """Schema for chat session in API responses."""

    agent_name: Optional[str] = None
    last_response_id: Optional[str] = None


class ChatSessionWithMessages(ChatSessionResponse):
    """Schema for chat session with messages."""

    messages: List[ChatMessageResponse] = []


class ChatRequest(BaseModel):
    """Schema for chat requests."""

    virtualAgentId: UUID
    message: ChatMessage
    stream: bool = False
    sessionId: Optional[UUID] = None
