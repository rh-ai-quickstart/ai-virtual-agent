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
from .chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
    ChatSessionWithMessages,
    ContentItem,
    ImageContentItem,
    TextContentItem,
)
from .guardrails import (
    GuardrailCreate,
    GuardrailResponse,
    GuardrailUpdate,
)
from .knowledge_bases import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from .tools import (
    ToolAssociationInfo,
)
from .user import (
    UserAgentAssignment,
    UserCreate,
    UserResponse,
    UserUpdate,
)

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
    "ChatMessageResponse",
    "ChatSessionCreate",
    "ChatSessionUpdate",
    "ChatSessionResponse",
    "ChatSessionWithMessages",
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
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserAgentAssignment",
    # Tool schemas
    "ToolAssociationInfo",
]
