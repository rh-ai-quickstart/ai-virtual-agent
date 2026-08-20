"""
Schemas package - Pydantic models for request/response validation.
"""

from .agent import (
    AgentTemplateCreate,
    AgentTemplateResponse,
    AgentTemplateUpdate,
    TemplateSuiteCreate,
    TemplateSuiteResponse,
    TemplateSuiteUpdate,
    VirtualAgentCreate,
    VirtualAgentResponse,
    VirtualAgentUpdate,
)
from .agent_templates import (
    AgentTemplate,
    TemplateInitializationRequest,
    TemplateInitializationResponse,
)
from .chat import ChatRequest, ContentItem, ImageContentItem, TextContentItem
from .guardrails import GuardrailCreate, GuardrailResponse, GuardrailUpdate
from .knowledge_bases import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from .tools import ToolAssociationInfo
from .user import CurrentUser, UserAgentAssignment, UserResponse, UserUpdate

__all__ = [
    # Agent schemas
    "VirtualAgentCreate",
    "VirtualAgentUpdate",
    "VirtualAgentResponse",
    "AgentTemplateCreate",
    "AgentTemplateUpdate",
    "AgentTemplateResponse",
    "TemplateSuiteCreate",
    "TemplateSuiteUpdate",
    "TemplateSuiteResponse",
    # Chat schemas
    "ChatRequest",
    "ContentItem",
    "TextContentItem",
    "ImageContentItem",
    # Knowledge schemas
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "GuardrailCreate",
    "GuardrailUpdate",
    "GuardrailResponse",
    # Agent template schemas
    "AgentTemplate",
    "TemplateInitializationRequest",
    "TemplateInitializationResponse",
    # User schemas
    "CurrentUser",
    "UserUpdate",
    "UserResponse",
    "UserAgentAssignment",
    # Tool schemas
    "ToolAssociationInfo",
]
