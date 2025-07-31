"""
SQLAlchemy database models for the AI Virtual Agent Kickstart application.

This module defines the database schema and relationships for:
- Users and authentication
- Chat sessions and conversation history
- Knowledge bases and document storage
- Virtual agents and chat sessions
- MCP servers and tool configurations
- Agent templates and configurations

All models use async SQLAlchemy with PostgreSQL and include
appropriate indexes and relationships for optimal performance.
"""

import enum
import uuid

from sqlalchemy import JSON, TIMESTAMP, Boolean, Column, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RoleEnum(enum.Enum):
    user = "user"
    devops = "devops"
    admin = "admin"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(RoleEnum, name="role"), nullable=False)
    agent_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    knowledge_bases = relationship("KnowledgeBase", back_populates="creator")
    guardrails = relationship("Guardrail", back_populates="creator")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    vector_db_name = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    embedding_model = Column(String(255), nullable=False)
    provider_id = Column(String(255))
    is_external = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=True)
    source = Column(String(255))
    source_configuration = Column(JSON)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    creator = relationship("User", back_populates="knowledge_bases")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String(255), primary_key=True)
    session_state = Column(JSON, default=dict)

    # New fields for sidebar display
    title = Column(String(500), nullable=True)  # Generated summary/title
    agent_name = Column(String(255), nullable=True)  # Agent display name

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Guardrail(Base):
    __tablename__ = "guardrails"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    rules = Column(JSON, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    creator = relationship("User", back_populates="guardrails")


class ModelServer(Base):
    __tablename__ = "model_servers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    provider_name = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=False)
    endpoint_url = Column(String(255), nullable=False)
    token = Column(String(255), nullable=True)


class AgentTypeEnum(enum.Enum):
    REGULAR = "Regular"
    REACT = "ReAct"


class AgentType(Base):
    __tablename__ = "agent_types"
    
    agent_id = Column(String(255), primary_key=True)
    agent_type = Column(Enum(AgentTypeEnum, name="agent_type_enum"), nullable=False, default=AgentTypeEnum.REACT)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
