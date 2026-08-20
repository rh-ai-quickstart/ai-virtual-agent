"""
User model - slim table keyed by Keycloak user ID.

Identity (username, email, role) comes from Keycloak tokens/Admin API.
This table only stores the Keycloak sub claim and app-specific data (agent_ids).
"""

from sqlalchemy import ARRAY, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"
    keycloak_id = Column(UUID(as_uuid=True), primary_key=True)
    agent_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    knowledge_bases = relationship("KnowledgeBase", back_populates="creator")
    guardrails = relationship("Guardrail", back_populates="creator")
