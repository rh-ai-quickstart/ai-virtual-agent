"""
Chat-related models: ChatSession and ChatMessage.
"""

import uuid

from sqlalchemy import JSON, TIMESTAMP, Column, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_state = Column(JSON, default=dict)

    # New fields for sidebar display
    title = Column(String(500), nullable=True)  # Generated summary/title
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("virtual_agents.id", ondelete="CASCADE"),
        nullable=True,
    )  # Agent ID
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )  # User ID for session isolation

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship to chat messages
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    # Relationship to virtual agent
    agent = relationship("VirtualAgent")


class ChatMessage(Base):
    """
    Store individual messages in a chat session.

    This provides persistent message storage, allowing us to send full
    conversation context following OpenAI's recommended approach.
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Message metadata
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(JSON, nullable=False)  # List of content items (text, images, etc.)

    # Optional response metadata
    response_id = Column(
        String(255), nullable=True
    )  # LlamaStack response ID for reference

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
