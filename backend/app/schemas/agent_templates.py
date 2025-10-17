"""Schemas for agent templates API."""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from .tools import ToolAssociationInfo


class AgentTemplate(BaseModel):
    """Schema for agent template configuration."""

    name: str
    persona: str
    prompt: str
    model_name: str
    tools: List[Dict[str, str]]
    knowledge_base_ids: List[str]
    knowledge_base_config: Optional[Dict] = None
    demo_questions: Optional[List[str]] = None


class TemplateInitializationRequest(BaseModel):
    """Schema for template initialization request.

    Added optional override fields to allow callers (UI) to customize
    the target model, tools, and knowledge bases before deploying from a template.
    """

    template_name: str
    custom_name: Optional[str] = None
    custom_prompt: Optional[str] = None
    include_knowledge_base: bool = True

    # Optional overrides
    model_name: Optional[str] = None
    tools: Optional[List[ToolAssociationInfo]] = None
    knowledge_base_ids: Optional[List[str]] = None


class TemplateInitializationResponse(BaseModel):
    """Schema for template initialization response."""

    agent_id: UUID
    agent_name: str
    persona: str
    knowledge_base_created: bool
    knowledge_base_name: Optional[str] = None
    status: str
    message: str
