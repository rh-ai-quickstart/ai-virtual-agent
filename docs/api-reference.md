<!-- omit from toc -->
# API Reference
Complete reference for the AI Virtual Agent Kickstart backend API. The API is built with FastAPI and provides RESTful endpoints for managing agents, knowledge bases, chat sessions, and more.
<!-- omit from toc -->
## Table of Contents
- [Base URL](#base-url)
- [Interactive Documentation](#interactive-documentation)
- [Authentication](#authentication)
- [Response Format](#response-format)
  - [Success Response](#success-response)
  - [Error Response](#error-response)
- [Error Codes](#error-codes)
- [Virtual Agents API](#virtual-agents-api)
  - [Create Virtual Agent](#create-virtual-agent)
  - [List Virtual Agents](#list-virtual-agents)
  - [Get Virtual Agent](#get-virtual-agent)
  - [Delete Virtual Agent](#delete-virtual-agent)
- [Knowledge Bases API](#knowledge-bases-api)
  - [Create Knowledge Base](#create-knowledge-base)
  - [List Knowledge Bases](#list-knowledge-bases)
  - [Get Knowledge Base](#get-knowledge-base)
  - [Delete Knowledge Base](#delete-knowledge-base)
  - [Sync Knowledge Bases](#sync-knowledge-bases)
- [Chat API](#chat-api)
  - [Start Chat Session](#start-chat-session)
- [Chat Sessions API](#chat-sessions-api)
  - [Create Chat Session](#create-chat-session)
  - [List Chat Sessions](#list-chat-sessions)
  - [Get Chat Session](#get-chat-session)
  - [Delete Chat Session](#delete-chat-session)
- [Users API](#users-api)
  - [Get User Profile](#get-user-profile)
  - [List Users](#list-users)
  - [Create User](#create-user)
- [Tools API](#tools-api)
  - [List Tool Groups](#list-tool-groups)
- [LlamaStack Integration API](#llamastack-integration-api)
  - [List Models](#list-models)
  - [List Vector Databases](#list-vector-databases)
- [MCP Servers API](#mcp-servers-api)
  - [Create MCP Server](#create-mcp-server)
  - [List MCP Servers](#list-mcp-servers)
  - [Delete MCP Server](#delete-mcp-server)

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-backend-domain.com` (replace with your actual backend endpoint)

## Interactive Documentation

The complete OpenAPI/Swagger specification and interactive documentation is available at:

- **Interactive API Docs**: `{base-url}/docs`
- **ReDoc Documentation**: `{base-url}/redoc`
- **OpenAPI JSON**: `{base-url}/openapi.json`

## Authentication

The API uses header-based authentication for user identification:

```http
X-Forwarded-User: username
X-Forwarded-Email: user@example.com
```

Both headers are checked (case-insensitive). At least one must be provided.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "data": { /* response data */ },
  "message": "Success message (optional)"
}
```

### Error Response
```json
{
  "detail": "Error description"
}
```

## Error Codes

| HTTP Status | Description |
|-------------|-------------|
| 400 | Bad request / validation error |
| 401 | Authentication required |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 422 | Unprocessable entity (invalid request data) |
| 500 | Internal server error |
| 502 | Upstream LlamaStack unavailable |

## Virtual Agents API

Virtual agents are managed through LlamaStack and do not have database storage.

### Create Virtual Agent

Create a new AI agent with specified configuration.

```http
POST /api/virtual_assistants
```

**Request Body:**
```json
{
  "name": "Support Assistant",
  "model_name": "llama3.1-8b-instruct",
  "prompt": "You are a helpful support assistant.",
  "knowledge_base_ids": ["support-docs-v1"],
  "tools": [
    {
      "toolgroup_id": "builtin::rag"
    }
  ],
  "sampling_strategy": "greedy",
  "temperature": 0.1,
  "top_p": 0.95,
  "top_k": 40,
  "max_tokens": 4096,
  "repetition_penalty": 1.0,
  "max_infer_iters": 10,
  "input_shields": [],
  "output_shields": []
}
```

**Response:**
```json
{
  "id": "agent-123",
  "name": "Support Assistant",
  "model_name": "llama3.1-8b-instruct",
  "prompt": "You are a helpful support assistant.",
  "knowledge_base_ids": ["support-docs-v1"],
  "tools": [
    {
      "toolgroup_id": "builtin::rag"
    }
  ],
  "sampling_strategy": "greedy",
  "temperature": 0.1,
  "top_p": 0.95,
  "top_k": 40,
  "max_tokens": 4096,
  "repetition_penalty": 1.0,
  "max_infer_iters": 10,
  "input_shields": [],
  "output_shields": []
}
```

### List Virtual Agents

Retrieve all virtual agents from LlamaStack.

```http
GET /api/virtual_assistants
```

**Response:**
```json
[
  {
    "id": "agent-123",
    "name": "Support Assistant",
    "model_name": "llama3.1-8b-instruct",
    "prompt": "You are a helpful support assistant.",
    "knowledge_base_ids": ["support-docs-v1"],
    "tools": [{"toolgroup_id": "builtin::rag"}],
    "input_shields": [],
    "output_shields": []
  }
]
```

### Get Virtual Agent

Retrieve a specific virtual agent by ID.

```http
GET /api/virtual_assistants/{agent_id}
```

**Parameters:**
- `agent_id` (path): The agent identifier

**Response:**
```json
{
  "id": "agent-123",
  "name": "Support Assistant",
  "model_name": "llama3.1-8b-instruct",
  "prompt": "You are a helpful support assistant.",
  "knowledge_base_ids": ["support-docs-v1"],
  "tools": [{"toolgroup_id": "builtin::rag"}],
  "input_shields": [],
  "output_shields": []
}
```

### Delete Virtual Agent

Delete a virtual agent permanently.

```http
DELETE /api/virtual_assistants/{agent_id}
```

**Parameters:**
- `agent_id` (path): The agent identifier

**Response:**
```http
204 No Content
```

## Knowledge Bases API

### Create Knowledge Base

Create a new knowledge base for document storage and RAG functionality.

```http
POST /api/knowledge_bases
```

**Request Body:**
```json
{
  "vector_db_name": "support-docs-v1",
  "name": "Support Documentation",
  "version": "1.0",
  "embedding_model": "all-MiniLM-L6-v2",
  "provider_id": "pgvector",
  "source": "s3",
  "source_configuration": {
    "bucket_name": "support-docs",
    "access_key_id": "minioadmin",
    "secret_access_key": "minioadmin123",
    "endpoint_url": "http://minio:9000"
  }
}
```

**Response:**
```json
{
  "vector_db_name": "support-docs-v1",
  "name": "Support Documentation",
  "version": "1.0",
  "embedding_model": "all-MiniLM-L6-v2",
  "provider_id": "pgvector",
  "is_external": false,
  "source": "s3",
  "source_configuration": {
    "bucket_name": "support-docs",
    "access_key_id": "minioadmin"
  },
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List Knowledge Bases

Retrieve all knowledge bases with computed status.

```http
GET /api/knowledge_bases
```

**Response:**
```json
[
  {
    "vector_db_name": "support-docs-v1",
    "name": "Support Documentation",
    "version": "1.0",
    "embedding_model": "all-MiniLM-L6-v2",
    "provider_id": "pgvector",
    "status": "READY",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

**Status Values:**
- `READY`: Knowledge base is processed and available for use
- `PENDING`: Knowledge base is created but ingestion is in progress
- `ORPHANED`: Vector database exists but metadata is missing

### Get Knowledge Base

Retrieve a specific knowledge base by vector database name.

```http
GET /api/knowledge_bases/{vector_db_name}
```

**Parameters:**
- `vector_db_name` (path): The vector database identifier

**Response:**
```json
{
  "vector_db_name": "support-docs-v1",
  "name": "Support Documentation",
  "version": "1.0",
  "embedding_model": "all-MiniLM-L6-v2",
  "provider_id": "pgvector",
  "status": "READY",
  "source": "s3",
  "source_configuration": {
    "bucket_name": "support-docs"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Delete Knowledge Base

Delete a knowledge base and its associated vector data.

```http
DELETE /api/knowledge_bases/{vector_db_name}
```

**Parameters:**
- `vector_db_name` (path): The vector database identifier

**Response:**
```http
204 No Content
```

### Sync Knowledge Bases

Synchronize knowledge bases between the database and LlamaStack.

```http
POST /api/knowledge_bases/sync
```

**Response:**
```json
[
  {
    "vector_db_name": "support-docs-v1",
    "name": "Support Documentation",
    "status": "READY",
    "synced": true
  }
]
```

## Chat API

### Start Chat Session

Initiate a streaming chat conversation with a virtual agent.

```http
POST /api/llama_stack/chat
```

**Request Body:**
```json
{
  "virtualAssistantId": "agent-123",
  "messages": [
    {
      "role": "user",
      "content": "How do I reset my password?"
    }
  ],
  "sessionId": "session-456"
}
```

**Response:**
Server-Sent Events stream with JSON chunks:

```
data: {"type": "session", "sessionId": "session-456"}

data: {"type": "text", "content": "To reset your password, you can follow these steps:\n\n1. "}

data: {"type": "text", "content": "Go to the login page\n2. "}

data: {"type": "tool", "content": "Using \"builtin::rag\" tool:", "tool": {"name": "builtin::rag"}}

data: {"type": "text", "content": "Click on 'Forgot Password'\n3. "}

data: [DONE]
```

**Message Types:**
- `session`: Session initialization with ID
- `text`: Incremental text content
- `tool`: Tool usage notification
- `error`: Error message

**Notes:**
- `sessionId` is required - session must be created first via `/api/chat_sessions`
- Response is streamed as Server-Sent Events
- Content-Type: `text/event-stream`

## Chat Sessions API

### Create Chat Session

Create a new chat session for an agent.

```http
POST /api/chat_sessions
```

**Request Body:**
```json
{
  "agent_id": "agent-123",
  "session_name": "Support Chat"
}
```

**Notes:**
- `session_name` is optional. If not provided, a unique name will be generated

**Response:**
```json
{
  "id": "session-456",
  "title": "Support Chat",
  "agent_name": "Support Assistant",
  "agent_id": "agent-123",
  "messages": [],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List Chat Sessions

Retrieve all chat sessions for a specific agent.

```http
GET /api/chat_sessions?agent_id={agent_id}&limit={limit}
```

**Query Parameters:**
- `agent_id` (required): Agent ID to filter sessions
- `limit` (optional): Maximum number of sessions (default: 50)

**Response:**
```json
[
  {
    "id": "session-456",
    "title": "Support Chat",
    "agent_name": "Support Assistant",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:45:00Z"
  }
]
```

### Get Chat Session

Retrieve a specific chat session with messages.

```http
GET /api/chat_sessions/{session_id}?agent_id={agent_id}
```

**Parameters:**
- `session_id` (path): The session identifier
- `agent_id` (query, required): The agent identifier

**Response:**
```json
{
  "id": "session-456",
  "title": "Support Chat",
  "agent_name": "Support Assistant",
  "agent_id": "agent-123",
  "messages": [
    {
      "role": "user",
      "content": "How do I reset my password?",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "To reset your password, follow these steps...",
      "timestamp": "2024-01-15T10:30:15Z"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### Delete Chat Session

Delete a chat session and all its messages.

```http
DELETE /api/chat_sessions/{session_id}?agent_id={agent_id}
```

**Parameters:**
- `session_id` (path): The session identifier
- `agent_id` (query, required): The agent identifier

**Response:**
```http
204 No Content
```

## Users API

### Get User Profile

Retrieve the current user's profile information.

```http
GET /api/users/profile
```

**Headers Required:**
```http
X-Forwarded-User: john.doe
X-Forwarded-Email: john.doe@example.com
```

**Response:**
```json
{
  "id": "user-123",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "role": "user",
  "agent_ids": ["agent-123", "agent-456"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List Users

Retrieve all users.

```http
GET /api/users
```

**Response:**
```json
[
  {
    "id": "user-123",
    "username": "john.doe",
    "email": "john.doe@example.com",
    "role": "user",
    "agent_ids": [],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### Create User

Create a new user account.

```http
POST /api/users
```

**Request Body:**
```json
{
  "username": "jane.smith",
  "email": "jane.smith@example.com",
  "role": "user",
  "agent_ids": []
}
```

**Response:**
```json
{
  "id": "user-124",
  "username": "jane.smith",
  "email": "jane.smith@example.com",
  "role": "user",
  "agent_ids": [],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Tools API

### List Tool Groups

Retrieve all available tool groups from LlamaStack.

```http
GET /api/tools
```

**Response:**
```json
[
  {
    "toolgroup_id": "builtin::rag",
    "name": "RAG Tool",
    "description": "Retrieval-Augmented Generation for knowledge bases"
  },
  {
    "toolgroup_id": "mcp-dbstore",
    "name": "Database Store",
    "description": "Product and order management tools",
    "endpoint_url": "http://mcp-dbstore:8003"
  }
]
```

## LlamaStack Integration API

### List Models

Retrieve available LLM models from LlamaStack.

```http
GET /api/llama_stack/llms
```

**Response:**
```json
[
  {
    "model_name": "llama3.1-8b-instruct",
    "provider_resource_id": "meta-llama/Llama-3.1-8B-Instruct",
    "model_type": "llm"
  },
  {
    "model_name": "llama3.2-3b-instruct",
    "provider_resource_id": "meta-llama/Llama-3.2-3B-Instruct",
    "model_type": "llm"
  }
]
```

### List Vector Databases

Retrieve available vector databases from LlamaStack.

```http
GET /api/llama_stack/knowledge_bases
```

**Response:**
```json
[
  {
    "kb_name": "support-docs-v1",
    "provider_resource_id": "pgvector-1",
    "description": "Support documentation knowledge base"
  }
]
```

## MCP Servers API

### Create MCP Server

Create a new MCP (Model Context Protocol) server.

```http
POST /api/mcp_servers
```

**Request Body:**
```json
{
  "toolgroup_id": "mcp-dbstore",
  "name": "Database Store",
  "description": "Product and order management tools",
  "endpoint_url": "http://mcp-dbstore:8003",
  "configuration": {}
}
```

**Response:**
```json
{
  "toolgroup_id": "mcp-dbstore",
  "name": "Database Store",
  "description": "Product and order management tools",
  "endpoint_url": "http://mcp-dbstore:8003",
  "configuration": {},
  "provider_id": "mcp-server-provider"
}
```

### List MCP Servers

Retrieve all MCP servers from LlamaStack.

```http
GET /api/mcp_servers
```

**Response:**
```json
[
  {
    "toolgroup_id": "mcp-dbstore",
    "name": "Database Store",
    "description": "Product and order management tools",
    "endpoint_url": "http://mcp-dbstore:8003",
    "provider_id": "mcp-server-provider"
  }
]
```

### Delete MCP Server

Delete an MCP server by toolgroup ID.

```http
DELETE /api/mcp_servers/{toolgroup_id}
```

**Parameters:**
- `toolgroup_id` (path): The MCP server identifier

**Response:**
```http
204 No Content
```
