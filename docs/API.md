# AI Virtual Agent - Backend API Documentation

## Overview

The AI Virtual Agent backend provides a RESTful API built with FastAPI. The API is versioned and currently available at `/api/v1/`.

**Base URL**: `http://localhost:8000/api/v1`

**Interactive API Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

Currently, the API does not require authentication for most endpoints. User management is handled through the `/users` endpoints.

## API Endpoints

### Virtual Agents

Manage AI agents with different capabilities, models, and configurations.

#### List all virtual agents
```http
GET /api/v1/virtual_agents
```

**Response**: `200 OK`
```json
[
  {
    "id": "customer-support-agent",
    "name": "Customer Support Agent",
    "model_name": "meta-llama/Llama-3.2-3B-Instruct",
    "prompt": "You are a helpful customer support agent...",
    "tools": [],
    "knowledge_base_ids": ["docs-kb"],
    "vector_store_ids": ["docs-kb-v1"],
    "template_name": null,
    "suite_name": null,
    "category": null,
    "created_at": "2024-10-31T10:00:00Z",
    "updated_at": "2024-10-31T10:00:00Z"
  }
]
```

#### Get a specific virtual agent
```http
GET /api/v1/virtual_agents/{agent_id}
```

**Parameters**:
- `agent_id` (path): Unique identifier for the agent

**Response**: `200 OK`
```json
{
  "id": "customer-support-agent",
  "name": "Customer Support Agent",
  "model_name": "meta-llama/Llama-3.2-3B-Instruct",
  "prompt": "You are a helpful customer support agent...",
  "tools": [],
  "knowledge_base_ids": ["docs-kb"],
  "vector_store_ids": ["docs-kb-v1"],
  "input_shields": [],
  "output_shields": [],
  "template_id": null,
  "template_name": null,
  "suite_id": null,
  "suite_name": null,
  "category": null,
  "sampling_strategy": null,
  "temperature": null,
  "top_p": null,
  "top_k": null,
  "max_tokens": null,
  "repetition_penalty": null,
  "max_infer_iters": null,
  "created_at": "2024-10-31T10:00:00Z",
  "updated_at": "2024-10-31T10:00:00Z"
}
```

#### Create a new virtual agent
```http
POST /api/v1/virtual_agents
```

**Request Body**:
```json
{
  "name": "New Agent",
  "model_name": "meta-llama/Llama-3.2-3B-Instruct",
  "prompt": "You are a helpful assistant...",
  "tools": [],
  "knowledge_base_ids": [],
  "input_shields": [],
  "output_shields": [],
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 2048
}
```

**Response**: `201 Created`

**Error Responses**:
- `409 Conflict`: Agent with this ID already exists

#### Update a virtual agent
```http
PUT /api/v1/virtual_agents/{agent_id}
```

**Request Body**: Same as create

**Response**: `200 OK`

#### Delete a virtual agent
```http
DELETE /api/v1/virtual_agents/{agent_id}
```

**Response**: `204 No Content`

---

### Knowledge Bases

Manage knowledge bases for RAG (Retrieval-Augmented Generation).

#### List all knowledge bases
```http
GET /api/v1/knowledge_bases
```

**Response**: `200 OK`
```json
[
  {
    "vector_store_name": "docs-kb-v1",
    "name": "Documentation KB",
    "version": "v1",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "provider_id": "ollama",
    "source": "S3",
    "status": "ready",
    "created_at": "2024-10-31T10:00:00Z"
  }
]
```

#### Get a specific knowledge base
```http
GET /api/v1/knowledge_bases/{vector_store_name}
```

**Parameters**:
- `vector_store_name` (path): Unique identifier for the knowledge base

**Response**: `200 OK`

#### Create a new knowledge base
```http
POST /api/v1/knowledge_bases
```

**Request Body**:
```json
{
  "vector_store_name": "new-kb-v1",
  "name": "New Knowledge Base",
  "version": "v1",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "provider_id": "ollama",
  "source": "S3",
  "source_configuration": {
    "BUCKET_NAME": "my-bucket",
    "REGION": "us-east-1",
    "ACCESS_KEY_ID": "...",
    "SECRET_ACCESS_KEY": "...",
    "ENDPOINT_URL": "https://s3.amazonaws.com"
  }
}
```

**Response**: `201 Created`

**Error Responses**:
- `409 Conflict`: Knowledge base with this vector_store_name already exists

#### Delete a knowledge base
```http
DELETE /api/v1/knowledge_bases/{vector_store_name}
```

**Response**: `204 No Content`

**Error Responses**:
- `404 Not Found`: Knowledge base not found
- `409 Conflict`: Knowledge base is in use by virtual agents

---

### MCP Servers

Manage Model Context Protocol servers for external tool integration.

#### List all MCP servers
```http
GET /api/v1/mcp_servers
```

**Response**: `200 OK`
```json
[
  {
    "toolgroup_id": "mcp::github",
    "name": "GitHub MCP Server",
    "description": "Access GitHub repositories and issues",
    "endpoint_url": "http://mcp-github:8080",
    "created_at": "2024-10-31T10:00:00Z"
  }
]
```

#### Discover available MCP servers
```http
GET /api/v1/mcp_servers/discover
```

Discovers MCP servers from environment variables and other sources.

**Response**: `200 OK`
```json
[
  {
    "name": "github",
    "description": "GitHub MCP Server",
    "endpoint_url": "http://mcp-github:8080",
    "source": "env"
  }
]
```

#### Create a new MCP server
```http
POST /api/v1/mcp_servers
```

**Request Body**:
```json
{
  "name": "github",
  "description": "GitHub MCP Server",
  "endpoint_url": "http://mcp-github:8080"
}
```

**Response**: `201 Created`

**Error Responses**:
- `409 Conflict`: MCP server with this name already exists

#### Update an MCP server
```http
PUT /api/v1/mcp_servers/{toolgroup_id}
```

**Response**: `200 OK`

#### Delete an MCP server
```http
DELETE /api/v1/mcp_servers/{toolgroup_id}
```

**Response**: `204 No Content`

---

### Chat Sessions

Manage chat sessions using LlamaStack Conversations API. Sessions store conversation history and are managed by LlamaStack.

#### List chat sessions
```http
GET /api/v1/chat_sessions?agent_id={agent_id}
```

**Query Parameters**:
- `agent_id` (required): Filter by agent ID

**Response**: `200 OK`
```json
[
  {
    "id": "session-123",
    "title": "Customer Support Chat",
    "agent_name": "Support Agent",
    "created_at": "2024-10-31T10:00:00Z",
    "updated_at": "2024-10-31T10:30:00Z"
  }
]
```

#### Get a specific chat session
```http
GET /api/v1/chat_sessions/{session_id}?agent_id={agent_id}&load_messages=true
```

**Query Parameters**:
- `agent_id` (required): Agent ID
- `load_messages` (optional, default: false): Whether to load messages from LlamaStack

**Response**: `200 OK`
```json
{
  "id": "session-123",
  "title": "Customer Support Chat",
  "agent_name": "Support Agent",
  "agent_id": "customer-support-agent",
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "Hello, I need help..."
        }
      ],
      "timestamp": "2024-10-31T10:00:00Z"
    },
    {
      "id": "msg-2",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "I'd be happy to help!"
        }
      ],
      "timestamp": "2024-10-31T10:00:05Z"
    }
  ],
  "created_at": "2024-10-31T10:00:00Z",
  "updated_at": "2024-10-31T10:30:00Z"
}
```

**Notes**:
- Messages are stored in LlamaStack's Conversations API
- Each message has structured content with types: `input_text`, `output_text`, `reasoning`, `tool_call`
- Tool calls and reasoning are preserved in message history

#### Create a new chat session
```http
POST /api/v1/chat_sessions
```

**Request Body**:
```json
{
  "agent_id": "customer-support-agent"
}
```

**Response**: `201 Created`
```json
{
  "id": "session-456",
  "title": "New Conversation",
  "agent_name": "Support Agent",
  "agent_id": "customer-support-agent",
  "created_at": "2024-10-31T11:00:00Z",
  "updated_at": "2024-10-31T11:00:00Z"
}
```

#### Delete a chat session
```http
DELETE /api/v1/chat_sessions/{session_id}?agent_id={agent_id}
```

**Response**: `204 No Content`

**Notes**:
- Deletes the session from both the database and LlamaStack
- All messages in the conversation are permanently deleted

---

### Agent Templates

Pre-configured agent templates for quick deployment.

#### List available templates
```http
GET /api/v1/agent_templates
```

**Response**: `200 OK`
```json
[
  "customer-support",
  "code-assistant",
  "data-analyst"
]
```

#### Get template details
```http
GET /api/v1/agent_templates/{template_name}
```

**Response**: `200 OK`
```json
{
  "name": "Customer Support Agent",
  "persona": "customer-support",
  "prompt": "You are a customer support agent...",
  "model_name": "meta-llama/Llama-3.2-3B-Instruct",
  "tools": [{"toolgroup_id": "builtin::web_search"}],
  "knowledge_base_ids": [],
  "knowledge_base_config": null,
  "demo_questions": [
    "How do I reset my password?",
    "What are your business hours?"
  ]
}
```

#### Initialize agent from template
```http
POST /api/v1/agent_templates/initialize
```

**Request Body**:
```json
{
  "template_name": "customer-support",
  "custom_name": "My Support Agent",
  "model_name": "meta-llama/Llama-3.2-3B-Instruct",
  "include_knowledge_base": true,
  "custom_prompt": "Optional custom prompt override",
  "tools": [],
  "knowledge_base_ids": []
}
```

**Response**: `200 OK`
```json
{
  "status": "success",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "My Support Agent",
  "persona": "customer-support",
  "knowledge_base_created": true,
  "knowledge_base_name": "customer-support-kb",
  "message": "Agent initialized successfully from template 'customer-support'"
}
```

#### Get suites by category
```http
GET /api/v1/agent_templates/suites/categories
```

**Response**: `200 OK`
```json
{
  "customer_service": ["support-suite", "sales-suite"],
  "development": ["code-suite", "devops-suite"]
}
```

#### Get categories info
```http
GET /api/v1/agent_templates/categories/info
```

**Response**: `200 OK`
```json
{
  "customer_service": {
    "name": "Customer Service Templates",
    "description": "Specialized agents for customer service services.",
    "icon": "customer_service",
    "suite_count": 2
  },
  "development": {
    "name": "Development Templates",
    "description": "Specialized agents for development services.",
    "icon": "development",
    "suite_count": 2
  }
}
```

#### Initialize entire suite
```http
POST /api/v1/agent_templates/initialize-suite/{suite_id}
```

**Response**: `201 Created`

---

### Users

Manage users and their agent assignments.

#### List all users
```http
GET /api/v1/users
```

**Response**: `200 OK`
```json
[
  {
    "id": "user-123",
    "username": "john.doe",
    "email": "john@example.com",
    "created_at": "2024-10-31T10:00:00Z"
  }
]
```

#### Get current user profile
```http
GET /api/v1/users/profile
```

**Response**: `200 OK`

#### Get user by ID
```http
GET /api/v1/users/{user_id}
```

**Response**: `200 OK`

#### Create a new user
```http
POST /api/v1/users
```

**Request Body**:
```json
{
  "username": "jane.doe",
  "email": "jane@example.com",
  "password": "secure-password"
}
```

**Response**: `201 Created`

#### Update user
```http
PUT /api/v1/users/{user_id}
```

**Response**: `200 OK`

#### Delete user
```http
DELETE /api/v1/users/{user_id}
```

**Response**: `204 No Content`

**Error Responses**:
- `400 Bad Request`: Admin cannot delete their own account
- `403 Forbidden`: Regular users cannot delete users

#### Get user's agents
```http
GET /api/v1/users/{user_id}/agents
```

**Response**: `200 OK`
```json
["agent-1", "agent-2"]
```

#### Assign agents to user
```http
POST /api/v1/users/{user_id}/agents
```

**Request Body**:
```json
{
  "agent_ids": ["agent-1", "agent-2"]
}
```

**Response**: `200 OK`

#### Remove agents from user
```http
DELETE /api/v1/users/{user_id}/agents
```

**Request Body**:
```json
{
  "agent_ids": ["agent-1"]
}
```

**Response**: `200 OK`

---

### Tools

List available tools that can be used by agents.

#### List all tool groups
```http
GET /api/v1/tools/
```

**Response**: `200 OK`
```json
[
  {
    "toolgroup_id": "builtin::web_search",
    "name": "Web Search",
    "description": "Search the web for information",
    "provider_id": "tavily"
  },
  {
    "toolgroup_id": "mcp::github",
    "name": "GitHub Tools",
    "description": "Access GitHub repositories and issues",
    "provider_id": "model-context-protocol",
    "endpoint_url": "http://mcp-github:8080"
  }
]
```

#### List LlamaStack tool groups
```http
GET /api/v1/llama_stack/tools
```

**Response**: `200 OK`
```json
[
  {
    "id": "mcp-server-alpha",
    "title": "model-context-protocol",
    "toolgroup_id": "mcp-server-alpha"
  }
]
```

---

### Guardrails

List available safety guardrails.

#### List LLM models
```http
GET /api/v1/llama_stack/llms
```

**Response**: `200 OK`
```json
[
  {
    "model_name": "ollama/llama3.2:1b-instruct-fp16",
    "provider_resource_id": "llama3.2:1b-instruct-fp16",
    "model_type": "llm"
  }
]
```

#### List safety models
```http
GET /api/v1/llama_stack/safety_models
```

**Response**: `200 OK`
```json
[
  {
    "id": "toxicity-checker",
    "name": "llama.guard",
    "model_type": "safety"
  }
]
```

#### List embedding models
```http
GET /api/v1/llama_stack/embedding_models
```

**Response**: `200 OK`
```json
[
  {
    "name": "text-embedding-ada",
    "provider_resource_id": "openai.ada",
    "model_type": "embedding"
  }
]
```

#### List providers
```http
GET /api/v1/llama_stack/providers
```

**Response**: `200 OK`
```json
[
  {
    "provider_id": "ollama",
    "provider_type": "remote::ollama",
    "config": {
      "url": "http://ollama:11434"
    },
    "api": "inference"
  }
]
```

---

### Validation

Validate configurations before deployment.

#### Validate agent configuration
```http
POST /api/v1/validate/agent
```

**Request Body**:
```json
{
  "agent_id": "test-agent",
  "model": "meta-llama/Llama-3.2-3B-Instruct",
  "instructions": "You are a test agent"
}
```

**Response**: `200 OK`
```json
{
  "valid": true,
  "errors": []
}
```

---

### Attachments

Handle file uploads for chat sessions.

#### Upload attachment
```http
POST /api/v1/attachments
```

**Request**: `multipart/form-data`
- `file`: File to upload
- `session_id`: Chat session ID

**Response**: `201 Created`
```json
{
  "attachment_id": "att-123",
  "filename": "document.pdf",
  "size": 1024000,
  "mime_type": "application/pdf"
}
```

#### Get attachment
```http
GET /api/v1/attachments/{attachment_id}
```

**Response**: `200 OK` (file download)

---

## Error Responses

All endpoints follow consistent error response format:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 409 Conflict
```json
{
  "detail": "Resource already exists or conflict with current state"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred"
}
```

---

### Chat

Send messages and receive streaming responses using LlamaStack Conversations API.

#### Send a chat message
```http
POST /api/v1/chat
```

**Request Body**:
```json
{
  "virtualAgentId": "customer-support-agent",
  "sessionId": "session-123",
  "message": {
    "role": "user",
    "content": [
      {
        "type": "input_text",
        "text": "Hello, how can you help me?"
      }
    ]
  },
  "stream": true
}
```

**Response**: `200 OK` (Server-Sent Events stream)

The response uses Server-Sent Events (SSE) format with the following event types:

**Output Text Delta** (streaming text chunks):
```
data: {"type":"response.output_text.delta","delta":"Hello! ","item_id":"item-1","content_index":0,"session_id":"session-123"}
```

**Reasoning Text Delta** (model's internal reasoning):
```
data: {"type":"response.reasoning_text.delta","delta":"Let me think about...","item_id":"item-2","content_index":0,"session_id":"session-123"}
```

**Reasoning Complete**:
```
data: {"type":"response.reasoning_text.done","text":"Complete reasoning text","item_id":"item-2","content_index":0,"session_id":"session-123"}
```

**Tool Call Started**:
```
data: {"type":"response.output_item.added","item":{"id":"tool-1","name":"github::get_repo","server_label":"github","type":"mcp_call"},"session_id":"session-123"}
```

**Tool Call Completed**:
```
data: {"type":"response.output_item.done","item":{"id":"tool-1","output":"Repository data...","error":null},"session_id":"session-123"}
```

**Response Completed**:
```
data: {"type":"response.completed","session_id":"session-123"}
```

**Stream End**:
```
data: [DONE]
```

**Error Event**:
```
data: {"type":"error","content":"Error message","session_id":"session-123"}
```

**Notes**:
- Uses `text/event-stream` media type
- All events include `session_id` for session identification
- Tool calls show execution status (in_progress, completed, failed)
- Empty responses trigger a user-friendly warning message

---

## Rate Limiting

Currently, there are no rate limits enforced on API endpoints. This may change in production deployments.

---

## Pagination

List endpoints support pagination through query parameters:

- `page` (default: 1): Page number
- `page_size` (default: 50): Items per page

**Example**:
```http
GET /api/v1/chat_sessions/{session_id}?page=2&page_size=20
```

---

## Additional Resources

- **OpenAPI Specification**: Available at `/openapi.json`
- **Interactive Documentation**: Visit `/docs` for Swagger UI
- **Alternative Documentation**: Visit `/redoc` for ReDoc interface

---

## Examples

### Complete Agent Creation Flow

```bash
# 1. Create a knowledge base
curl -X POST http://localhost:8000/api/v1/knowledge_bases \
  -H "Content-Type: application/json" \
  -d '{
    "vector_store_name": "docs-kb-v1",
    "name": "Documentation",
    "version": "v1",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "provider_id": "ollama",
    "source": "S3",
    "source_configuration": {...}
  }'

# 2. Create an agent
# Note: Requires OAuth authentication via Keycloak session cookie
curl -X POST http://localhost:8000/api/v1/virtual_agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Support Agent",
    "model_name": "meta-llama/Llama-3.2-3B-Instruct",
    "prompt": "You are a helpful support agent",
    "knowledge_base_ids": ["docs-kb-v1"]
  }'

# 3. Create a chat session
curl -X POST http://localhost:8000/api/v1/chat_sessions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "support-agent",
    "session_name": "Support Session 1"
  }'
```

---

## Version History

- **v1.1.0** (Current): Added MCP server management, improved error handling
- **v1.0.0**: Initial release with core functionality
