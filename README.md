# Build an AI-powered virtual agent 

Build and deploy a conversational AI virtual agent on Red Hat OpenShift AI to automate customer interactions and provide instant support.

## Detailed description

This platform provides the tools to build and deploy conversational AI agents that can:

- **Access knowledge bases** - Upload documents and create searchable knowledge bases for RAG (Retrieval-Augmented Generation)
- **Use tools** - Integrate web search, databases, and custom tools through the Model Context Protocol (MCP)
- **Apply guardrails** - Built-in safety measures and content filtering
- **Scale in production** - Kubernetes-ready architecture

### Key Features

🤖 **Agent Management** - Create and configure AI agents with different capabilities
📚 **Knowledge Integration** - Document search and question answering via RAG
💬 **Real-time Chat** - Streaming conversations with session history
🔧 **Tool Ecosystem** - Built-in tools plus extensible MCP server support
🛡️ **Safety Controls** - Configurable guardrails and content filtering


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

### Minimum software requirements 

### Required user permissions 


## Deploy

### Cluster Deployment

For production installation on Kubernetes/OpenShift:


```bash
# Navigate to cluster deployment directory
cd deploy/cluster

# Install with interactive prompts for configuration
make install NAMESPACE=your-namespace

# Or set environment variables and install
export NAMESPACE=ai-virtual-agent
export HF_TOKEN=your-huggingface-token
make install
```

🧭 **[Advanced instructions →](#advanced-instructions)
📖 **[Full Installation Guide →](INSTALLING.md)**


## Getting Started Guides

### 👩‍💻 **For Developers**
- **[Local Development Guide](DEVELOPMENT.md)** - Containerized development environment (without cluster)
- **[Contributing Guide](CONTRIBUTING.md)** - Development setup and workflow
- **[Backend API Reference](docs/api-reference.md)** - Complete API documentation
- **[Frontend Architecture](frontend/README.md)** - UI components and patterns

### 🚀 **For Deployment**
- **[Installation Guide](INSTALLING.md)** - Production deployment on Kubernetes
- **[Agent Templates](docs/agent-templates-ingestion.md)** - Pre-built agent configurations
- **[Knowledge Base Setup](docs/knowledge-base-architecture.md)** - Document processing pipeline

### 🔧 **For Integration**
- **[MCP Servers](mcpservers/README.md)** - Building custom tool integrations
- **[Testing Guide](tests/README.md)** - Running integration tests
- **[API Reference](docs/api-reference.md)** - Backend API endpoints

## Example Use Cases

**Customer Support Agent**
```typescript
const agent = await createAgent({
  name: "Support Bot",
  model: "llama3.1-8b-instruct",
  knowledge_bases: ["support-docs"],
  tools: ["builtin::rag", "builtin::web_search"]
});
```

**Domain Expert (Banking)**
```typescript
const expert = await initializeAgentTemplate({
  template: "commercial_banker",
  knowledge_bases: ["banking-regulations"]
});
```

## Advanced instructions

### Project Structure

```
ai-virtual-agent/
├── frontend/           # React UI with PatternFly components
├── backend/            # FastAPI server with PostgreSQL
├── mcpservers/         # Custom MCP tool servers
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

For local development setup:

```bash
# Navigate to local deployment directory
cd deploy/local

# Start all services with Docker Compose
make compose-up

# Or start step-by-step:
# 1. Start database (automatically initializes with permissions)
podman compose up -d
# or with Docker:
# docker-compose up -d

# 2. Start backend
cd ../../backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && alembic upgrade head
uvicorn main:app --reload &

# 3. Start frontend
cd ../frontend && npm install && npm run dev
```

> **Note**: The PostgreSQL database is automatically initialized with proper permissions. Works with both Docker and Podman. No manual database setup needed!

**Access your app:**
- Frontend: http://localhost:5173
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
## Development Commands

**Local Development:**
```bash
cd deploy/local

# Start everything locally with Docker Compose
make compose-up

# Stop all services
make compose-down

# View logs from development services
make compose-logs

# Restart development services
make compose-restart

# Show status of development services
make compose-status
```

**Cluster Deployment:**
```bash
cd deploy/cluster

# Install on cluster
make install NAMESPACE=your-namespace

# Uninstall from cluster
make uninstall NAMESPACE=your-namespace

# Check status
make install-status NAMESPACE=your-namespace
```

> Note: All Makefile targets automatically load environment variables from a `.env` file in the repository root if it exists. No manual `export` is required for common workflows.

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

### Attachments (optional dependency)

If you plan to use file attachments locally or see this error during tests:

```
ImportError: failed to find libmagic. Check your installation
```

install the MIME detection dependency (libmagic) and Python binding:

- macOS (Homebrew):
  - `brew install file`
  - `pip install python-magic`
- Ubuntu/Debian:
  - `sudo apt-get install libmagic1` (or `libmagic-dev`)
  - `pip install python-magic`
- Fedora/RHEL:
  - `sudo dnf install file libmagic`
  - `pip install python-magic`

Notes:
- Unit tests import parts of the attachments stack. Without libmagic installed you can still proceed by installing the packages above.
- If you’re not using attachments in local dev, you can set `DISABLE_ATTACHMENTS=true` in `.env` to skip bucket-related startup paths.


## Community & Support

- **🐛 Issues** - [Report bugs and request features](https://github.com/rh-ai-quickstart/ai-virtual-agent/issues)
- **💬 Discussions** - [Ask questions and share ideas](https://github.com/rh-ai-quickstart/ai-virtual-agent/discussions)
- **🤝 Contributing** - See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- **📚 Documentation** - Browse `/docs` for detailed guides

## License

[MIT License](LICENSE) - Built with ❤️ by the Red Hat Ecosystem App Engineering team
