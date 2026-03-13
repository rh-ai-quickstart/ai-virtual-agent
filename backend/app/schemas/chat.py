"""
Chat-related schemas.
"""

from typing import List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel


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


class ChatRequest(BaseModel):
    """Schema for chat requests."""

    virtualAgentId: UUID
    message: ChatMessage
    sessionId: Optional[UUID] = None


class TokenUsage(BaseModel):
    """Token usage information for a chat interaction."""

    input_tokens: int
    output_tokens: int
