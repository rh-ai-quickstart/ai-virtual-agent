"""
Pydantic models for request/response validation and serialization.

This module defines all data schemas used for API request validation,
response serialization, database model conversion, and OpenAPI documentation
and API documentation generation throughout the AI Virtual Agent Quickstart
application.

The schemas ensure type safety, data validation, and consistent API contracts
across all endpoints and integrations.
"""

import enum
from datetime import datetime
from typing import (  # Added Dict for Guardrail rules
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import UUID4, BaseModel


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
    email: str
    role: RoleEnum
    agent_ids: Optional[List[str]] = []


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[RoleEnum] = None
    agent_ids: Optional[List[str]] = None


class UserRead(UserBase):
    id: UUID4
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


class UserAgentAssignment(BaseModel):
    agent_ids: List[str]


# MCPServer Schemas
class MCPServerBase(BaseModel):
    toolgroup_id: str
    name: str
    description: str = ""
    endpoint_url: str
    configuration: Dict[str, Any] = {}


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerRead(MCPServerBase):
    provider_id: str


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
            "vector_db_name": self.vector_db_name,
        }
        if self.source == "URL":
            return base | {"urls": self.source_configuration}

        if isinstance(self.source_configuration, dict):
            return base | {k.lower(): v for k, v in self.source_configuration.items()}
        else:
            return base | {"config": self.source_configuration}


class KnowledgeBaseRead(KnowledgeBaseBase):
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any
    status: str

    class Config:
        orm_mode = True


# Tool Association Info for VirtualAssistant
class ToolAssociationInfo(BaseModel):
    toolgroup_id: str  # MCPServer.toolgroup_id or BuiltInTool.toolgroup_id


# VirtualAssistant Schemas
class VirtualAssistantBase(BaseModel):
    name: str
    agent_type: Optional[str] = "ReAct"
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    input_shields: Optional[List[str]] = []
    output_shields: Optional[List[str]] = []
    temperature: Optional[float] = 0.0
    repetition_penalty: Optional[float] = 1.5
    stop_sequences: Optional[List[str]] = [
        "\n\n",
        "Thank you",
        "I hope this helps",
        "Let me know if you have any other questions",
    ]
    max_tokens: Optional[int] = 512
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 40
    sampling_strategy: Optional[str] = "greedy"
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


# Template Suite Schemas
class TemplateSuiteBase(BaseModel):
    id: str
    name: str
    category: str
    description: Optional[str] = None
    icon: Optional[str] = None


class TemplateSuiteRead(TemplateSuiteBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Agent Template Schemas
class AgentTemplateBase(BaseModel):
    id: str
    suite_id: str
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AgentTemplateRead(AgentTemplateBase):
    created_at: datetime
    updated_at: datetime
    suite: Optional[TemplateSuiteRead] = None

    class Config:
        orm_mode = True


# Agent Metadata Schemas
class AgentMetadataRead(BaseModel):
    agent_id: str
    template_id: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None
    template: Optional[AgentTemplateRead] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class VirtualAssistantRead(VirtualAssistantBase):
    id: str
    # Normalized metadata via relationship
    metadata: Optional[AgentMetadataRead] = None

    # Computed fields for backward compatibility
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    suite_id: Optional[str] = None
    suite_name: Optional[str] = None
    category: Optional[str] = None

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
