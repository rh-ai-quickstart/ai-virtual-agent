# Build an AI-powered virtual agent

[![GitHub release](https://img.shields.io/github/v/release/rh-ai-quickstart/ai-virtual-agent)](https://github.com/rh-ai-quickstart/ai-virtual-agent/releases)
[![Docker Image](https://img.shields.io/badge/quay.io-ai--virtual--agent-blue)](https://quay.io/repository/rh-ai-quickstart/ai-virtual-agent)

Build and deploy a conversational AI virtual agent on Red Hat OpenShift AI to automate customer interactions and provide instant support.

## Detailed description

This platform provides the tools to build and deploy conversational AI agents that can:

- **Access knowledge bases** - Upload documents and create searchable knowledge bases for RAG (Retrieval-Augmented Generation)
- **Use tools** - Integrate web search, databases, and custom tools through the Model Context Protocol (MCP)
- **Apply guardrails** - Built-in safety measures and content filtering
- **Scale in production** - Kubernetes-ready architecture

### Key Features

- 🤖 **Agent Management** - Create and configure AI agents with different capabilities
- 📚 **Knowledge Integration** - Document search and question answering via RAG
- 💬 **Real-time Chat** - Streaming conversations with session history
- 🔧 **Tool Ecosystem** - Built-in tools plus extensible MCP server support
- 🛡️ **Safety Controls** - Configurable guardrails and content filtering


### Architecture Overview

The platform integrates several components:

- **React Frontend** - Web interface for agent and chat management
- **FastAPI Backend** - API server handling business logic and data persistence
- **LlamaStack** - AI platform managing models, agents, and inference
- **PostgreSQL + pgvector** - Data storage with vector search capabilities
- **Kubernetes Pipeline** - Document processing and knowledge base ingestion

![Architecture](docs/images/architecture.png)

📖 **[Detailed Architecture →](docs/virtual-agents-architecture.md)**

## Requirements

### Minimum hardware requirements

For a full working version with local inference:
- **GPU** - Required for running inference locally
- Alternatively, you can deploy without a GPU by using:
  - Remote vLLM deployment
  - Vertex AI

### Minimum software requirements

- **Red Hat OpenShift** - Container orchestration platform
- **Red Hat OpenShift AI** - AI/ML platform for model serving and management
- **oc CLI** - OpenShift command-line tool
- **make** - Build automation tool
- **Hugging Face token** - With access to models (some models require authorization)

### Required user permissions

- **Cluster admin access** - Required for installing ClusterRole resources for OAuth authentication


## Deploy

<!--
### Prerequisites

What needs to go here?

oc login

anything else?


-->

### Cluster Deployment

For production installation on Kubernetes/OpenShift:

```bash
# clone the repository
git clone https://github.com/rh-ai-quickstart/ai-virtual-agent.git

# Navigate to cluster deployment directory
cd deploy/cluster

# Install with interactive prompts for configuration
make install NAMESPACE=your-namespace
```

🧭 **[Advanced instructions →](#advanced-instructions)**

📖 **[Full Installation Guide →](INSTALLING.md)**


### Delete

To remove the application and all associated resources:

```bash
cd deploy/cluster
make uninstall NAMESPACE=your-namespace
```

This will automatically clean up the Helm chart, deployed resources, and PVCs.

## Example Use Case

**Creating a Customer Support Agent with Knowledge Base**

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. Create a knowledge base
kb_response = requests.post(
    f"{BASE_URL}/knowledge_bases",
    json={
        "vector_store_name": "support-docs-v1",
        "name": "Support Documentation",
        "version": "v1",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "provider_id": "ollama",
        "source": "S3"
    }
)
print(f"Knowledge base created: {kb_response.status_code}")

# 2. Create a support agent
agent_response = requests.post(
    f"{BASE_URL}/virtual_agents",
    headers={
        "X-Forwarded-User": "admin",
        "X-Forwarded-Email": "admin@change.me"
    },
    json={
        "name": "Support Agent",
        "model_name": "meta-llama/Llama-3.2-3B-Instruct",
        "prompt": "You are a helpful customer support agent",
        "knowledge_base_ids": ["support-docs-v1"],
        "tools": [{"toolgroup_id": "builtin::web_search"}],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048
    }
)
agent_id = agent_response.json()["id"]
print(f"Agent created: {agent_id}")

# 3. Create a chat session
session_response = requests.post(
    f"{BASE_URL}/chat_sessions",
    json={
        "agent_id": agent_id,
        "session_name": "Customer Support Session"
    }
)
session_id = session_response.json()["id"]
print(f"Chat session created: {session_id}")

# 4. Send a chat message
chat_response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "virtualAgentId": agent_id,
        "sessionId": session_id,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Who is the first president of the United States?"
                }
            ]
        },
        "stream": False
    }
)
answer = chat_response.json()
print(f"Agent response: {answer}")
```

## Advanced instructions

### Getting Started Guides

#### 👩‍💻 **For Developers**
- **[Local Development Guide](DEVELOPMENT.md)** - Containerized development environment (without cluster)
- **[Contributing Guide](CONTRIBUTING.md)** - Development setup and workflow
- **[Backend API Reference](docs/API.md)** - Complete API documentation
- **[Frontend Architecture](frontend/README.md)** - UI components and patterns

#### 🚀 **For Deployment**
- **[Installation Guide](INSTALLING.md)** - Production deployment on Kubernetes
- **[Agent Templates](docs/agent-templates-ingestion.md)** - Pre-built agent configurations
- **[Knowledge Base Setup](docs/knowledge-base-architecture.md)** - Document processing pipeline

#### 🔧 **For Integration**
- **[Testing Guide](tests/README.md)** - Running integration tests
- **[API Reference](docs/API.md)** - Backend API endpoints

### Project Structure

```
ai-virtual-agent/
├── frontend/           # React UI with PatternFly components
├── backend/            # FastAPI server with PostgreSQL
├── docs/               # Architecture and API documentation
├── deploy/
│   ├── cluster/        # Kubernetes/Helm cluster deployment
│   │   ├── helm/       # Helm chart files
│   │   ├── scripts/    # Cluster deployment scripts
│   │   ├── Containerfile # Cluster container image
│   │   └── Makefile    # Cluster deployment commands
│   └── local/          # Local development deployment
│       ├── compose.dev.yaml # Docker Compose for local dev
│       ├── dev/        # Local development configs
│       └── Makefile    # Local development commands
└── tests/              # Integration test suite
```

### Local Development

For local containerized development (without cluster):

📖 **[→ See Local Development Guide](DEVELOPMENT.md)**

> **Note**: Local setup has limited functionality compared to OpenShift AI deployment:
> - No authentication/authorization
> - Knowledge bases not available
> - MCP servers not tested
>
> These features are only available with the full OpenShift AI deployment.

```bash
cd deploy/local

# Start all services
make compose-up

# Other available commands
make compose-down        # Stop all services
make compose-logs        # View logs
make compose-restart     # Restart services
make compose-status      # Show status
```

**Access your app:**
- Frontend: http://localhost:5173
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Cluster Development

```bash
cd deploy/cluster

# Install on cluster
make install NAMESPACE=your-namespace

# Other available commands
make uninstall NAMESPACE=your-namespace    # Remove application
make install-status NAMESPACE=your-namespace    # Check status
make list-mcps                              # List available MCP servers
```

> **Note**: All Makefile targets automatically load environment variables from a `.env` file in the repository root if it exists.

### Environment setup (.env)

Create a `.env` file in the repository root to configure your local environment. All Makefile targets will dynamically load this file if present:

```bash
cp .env.example .env
# then edit `.env` as needed
```

At minimum, set:

```bash
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/ai_virtual_agent
```

Optional toggles:

```bash
# Skip attachments bucket initialization/access during local dev
DISABLE_ATTACHMENTS=true

# Provide admin bootstrap for Alembic seeding (optional)
# ADMIN_USERNAME=admin
# ADMIN_EMAIL=admin@change.me
```

**Note**: If you're not using attachments in local dev, you can set `DISABLE_ATTACHMENTS=true` in `.env` to skip attachment-related initialization.


## Community & Support

- **🐛 Issues** - [Report bugs and request features](https://github.com/rh-ai-quickstart/ai-virtual-agent/issues)
- **💬 Discussions** - [Ask questions and share ideas](https://github.com/rh-ai-quickstart/ai-virtual-agent/discussions)
- **🤝 Contributing** - See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- **📚 Documentation** - Browse `/docs` for detailed guides

## License

[MIT License](LICENSE) - Built with ❤️ by the Red Hat Ecosystem App Engineering team

## Tags

* **Product:** OpenShift AI
* **Use case:** Conversational agents
* **Business challenge:** Adopt and scale AI
