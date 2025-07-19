"""
Pydantic schemas for API request/response validation and serialization.

This module defines all Pydantic models used for data validation, serialization,
and API documentation generation throughout the AI AaaS application.
Each schema group corresponds to a specific domain:

- User schemas: Authentication and user management
- MCPServer schemas: Model Context Protocol server configurations
- KnowledgeBase schemas: Vector database and knowledge base management
- VirtualAssistant schemas: AI agent configuration and management
- Guardrail schemas: Safety and content filtering rules
- ModelServer schemas: External model service configurations

The schemas follow a standard pattern:
- Base: Common fields for creation and updates
- Create: Fields required for resource creation
- Read: Fields returned in API responses (includes metadata)
- Update: Optional fields for resource updates
"""

import enum
from typing import Any, Dict, List, Optional, Union  # Added Dict for Guardrail rules

from pydantic import UUID4, BaseModel, EmailStr


# This should match the Enum in your models.py
class ToolTypeEnumSchema(str, enum.Enum):
    BUILTIN = "builtin"
    MCP_SERVER = "mcp_server"


class RoleEnum(str, enum.Enum):
    user = "user"
    devops = "devops"
    admin = "admin"


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: RoleEnum


class UserRead(UserBase):
    id: UUID4
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


# MCPServer Schemas
class MCPServerBase(BaseModel):
    toolgroup_id: str  # LlamaStack identifier (now PK)
    name: str
    description: Optional[str] = None
    endpoint_url: str
    configuration: Optional[Dict[str, Any]] = None


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerRead(MCPServerBase):
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


# KnowledgeBase Schemas
class KnowledgeBaseBase(BaseModel):
    vector_db_name: str  # LlamaStack identifier (now PK)
    name: str
    version: str
    embedding_model: str
    provider_id: Optional[str] = None
    is_external: bool = False
    source: Optional[str] = None
    source_configuration: Optional[Union[List[str], Dict[str, Any]]] = (
        None  # More specific type
    )


class KnowledgeBaseCreate(KnowledgeBaseBase):

    def pipeline_model_dict(self) -> Dict[str, Any]:
        base = {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "embedding_model": self.embedding_model,
            "vector_db_name": self.vector_db_name
        }
        if self.source == "URL":
            return base | {"urls": self.source_configuration}

        return base | {k.lower(): v for k, v in self.source_configuration.items()}


class KnowledgeBaseRead(KnowledgeBaseBase):
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any
    status: str

    class Config:
        orm_mode = True


# Tool Association Info for VirtualAssistant
class ToolAssociationInfo(BaseModel):
    toolgroup_id: (
        str  # This refers to MCPServer.toolgroup_id or BuiltInTool.toolgroup_id
    )


# VirtualAssistant Schemas
class VirtualAssistantBase(BaseModel):
    name: str
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    input_shields: Optional[List[str]] = []
    output_shields: Optional[List[str]] = []
    temperature: Optional[float] = 0.1
    repetition_penalty: Optional[float] = 1.0
    max_tokens: Optional[int] = 4096
    top_p: Optional[float] = 0.95
    knowledge_base_ids: Optional[List[str]] = (
        []
    )  # Now expecting list of vector_db_names
    tools: Optional[List[ToolAssociationInfo]] = []  # Changed from tool_ids: List[str]
    max_infer_iters: Optional[int] = 10
    enable_session_persistence: Optional[bool] = False


class VirtualAssistantCreate(VirtualAssistantBase):
    pass


class VirtualAssistantUpdate(VirtualAssistantBase):
    name: Optional[str] = None
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    knowledge_base_ids: Optional[List[str]] = (
        None  # Now expecting list of vector_db_names
    )
    tools: Optional[List[ToolAssociationInfo]] = None


class VirtualAssistantRead(VirtualAssistantBase):
    id: str
    metadata: Optional[Dict[str, Any]] = {}  # Add metadata field for persona info

    class Config:
        orm_mode = True


class GuardrailBase(BaseModel):
    name: str
    rules: Dict[str, Any]


class GuardrailCreate(GuardrailBase):
    pass


class GuardrailRead(GuardrailBase):
    id: UUID4
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


# ModelServer Schemas (These seemed largely okay with your models.py)
class ModelServerBase(BaseModel):
    name: str
    provider_name: str
    model_name: str
    endpoint_url: str
    token: Optional[str] = None


class ModelServerCreate(ModelServerBase):
    pass


class ModelServerUpdate(ModelServerBase):
    name: Optional[str] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    endpoint_url: Optional[str] = None
    token: Optional[str] = None


class ModelServerRead(ModelServerBase):
    id: UUID4

    class Config:
        orm_mode = True


# Template Schemas - NEW ADDITION (following existing patterns)
class AgentTemplate(BaseModel):
    """Individual agent configuration within a template"""
    name: str
    description: Optional[str] = None
    model_name: str
    prompt: str
    persona: Optional[str] = None
    tools: List[ToolAssociationInfo] = []
    knowledge_base_ids: List[str] = []
    temperature: Optional[float] = 0.1
    repetition_penalty: Optional[float] = 1.0
    max_tokens: Optional[int] = 4096
    top_p: Optional[float] = 0.95
    max_infer_iters: Optional[int] = 10
    input_shields: Optional[List[str]] = []
    output_shields: Optional[List[str]] = []


class TemplateSuiteBase(BaseModel):
    """Base template suite configuration"""
    id: str
    name: str
    description: str
    category: str  # e.g., "fsi_banking", "us_banking", "wealth_management"
    agents: List[AgentTemplate]
    metadata: Optional[Dict[str, Any]] = {}


class TemplateSuiteCreate(TemplateSuiteBase):
    """Template suite for creation"""
    pass


class TemplateSuiteRead(BaseModel):
    """Template suite for API responses"""
    id: str
    name: str
    description: str
    category: str
    metadata: Dict[str, Any] = {}
    personas: Optional[Dict[str, Any]] = {}  # Add personas data
    industry_id: Optional[str] = None  # Make it optional
    agents: List[AgentTemplate] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TemplateDeployRequest(BaseModel):
    """Request model for deploying template agents"""
    selected_agents: Optional[List[str]] = None  # Agent names to deploy, None = all
    override_settings: Optional[Dict[str, Any]] = None  # Override any agent settings


class TemplateDeployResponse(BaseModel):
    """Response model for template deployment"""
    deployed_agents: List[VirtualAssistantRead]
    failed_agents: List[Dict[str, str]]  # List of {name: error_message}
    template_id: str
    deployment_summary: Dict[str, Any]


class TemplatePersona(BaseModel):
    """Persona configuration within a template"""
    label: str
    description: str
    icon: str
    color: str
    className: str
    avatarBg: str
    avatarIcon: str
    gradient: str
    borderColor: str
    demo_questions: Optional[List[str]] = []
    agents: List[AgentTemplate]


class IndustryRead(BaseModel):
    id: str
    name: str
    description: str
    icon: Optional[str] = None
    color: Optional[str] = None
    template_count: int = 0
    total_agents: int = 0

class TemplateRead(BaseModel):
    id: str
    name: str
    description: str
    category: str
    metadata: Dict[str, Any] = {}
    persona_count: int = 0
    agent_count: int = 0
    industry_id: str

