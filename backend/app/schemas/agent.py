"""
Agent-related schemas.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from .base import BaseSchema, TimestampMixin
from .tools import ToolAssociationInfo


class VirtualAgentBase(BaseModel):
    """Base virtual agent config schema."""

    name: str
    runner_type: str = "llamastack"  # "llamastack" | "langgraph" | "crewai"
    model_name: str
    prompt: Optional[str] = None
    tools: Optional[List[ToolAssociationInfo]] = []
    knowledge_base_ids: List[str] = []
    vector_store_ids: List[str] = []
    input_shields: List[str] = []
    output_shields: List[str] = []
    sampling_strategy: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    repetition_penalty: Optional[float] = None
    max_infer_iters: Optional[int] = 100


class VirtualAgentCreate(VirtualAgentBase):
    """Schema for creating a virtual agent config."""

    template_id: Optional[UUID] = None


class VirtualAgentUpdate(BaseModel):
    """Schema for updating a virtual agent config."""

    name: Optional[str] = None
    runner_type: Optional[str] = None
    model_name: Optional[str] = None
    template_id: Optional[UUID] = None
    prompt: Optional[str] = None
    tools: Optional[List[ToolAssociationInfo]] = None
    knowledge_base_ids: Optional[List[str]] = None
    vector_store_ids: Optional[List[str]] = None
    input_shields: Optional[List[str]] = None
    output_shields: Optional[List[str]] = None
    sampling_strategy: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    repetition_penalty: Optional[float] = None
    max_infer_iters: Optional[int] = None


class VirtualAgentInDB(VirtualAgentBase, TimestampMixin, BaseSchema):
    """Schema for virtual agent config as stored in database."""

    id: UUID
    template_id: Optional[UUID] = None


class VirtualAgentResponse(VirtualAgentInDB):
    """Schema for virtual agent config in API responses."""

    template_name: Optional[str] = None
    suite_id: Optional[UUID] = None
    suite_name: Optional[str] = None
    category: Optional[str] = None


class AgentTemplateBase(BaseModel):
    """Base agent template schema."""

    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AgentTemplateCreate(AgentTemplateBase):
    """Schema for creating an agent template."""

    suite_id: UUID


class AgentTemplateUpdate(BaseModel):
    """Schema for updating an agent template."""

    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    suite_id: Optional[UUID] = None


class AgentTemplateInDB(AgentTemplateBase, TimestampMixin, BaseSchema):
    """Schema for agent template as stored in database."""

    id: UUID
    suite_id: UUID


class AgentTemplateResponse(AgentTemplateInDB):
    """Schema for agent template in API responses."""

    pass


class TemplateSuiteBase(BaseModel):
    """Base template suite schema."""

    name: str
    category: str
    description: Optional[str] = None
    icon: Optional[str] = None


class TemplateSuiteCreate(TemplateSuiteBase):
    """Schema for creating a template suite."""

    pass


class TemplateSuiteUpdate(BaseModel):
    """Schema for updating a template suite."""

    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class TemplateSuiteInDB(TemplateSuiteBase, TimestampMixin, BaseSchema):
    """Schema for template suite as stored in database."""

    id: UUID


class TemplateSuiteResponse(TemplateSuiteInDB):
    """Schema for template suite in API responses."""

    templates: List[AgentTemplateResponse] = []
