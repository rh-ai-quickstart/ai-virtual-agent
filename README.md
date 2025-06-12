# AI Virtual Assistant

A comprehensive platform for creating and managing AI-powered virtual assistants with knowledge base integration, built on top of LlamaStack.

## Overview

The AI Virtual Assistant platform provides a complete solution for building intelligent conversational agents that can access and reason over your organization's knowledge. The system combines modern web technologies with powerful AI capabilities to deliver a seamless experience for both developers and end users.

### Key Features

- **🤖 Virtual Agent Management**: Create, configure, and manage AI agents with different personalities and capabilities
- **📚 Knowledge Base Integration**: Upload documents and create searchable knowledge bases for RAG (Retrieval-Augmented Generation)
- **💬 Real-time Chat**: Stream-based chat interface with Server-Sent Events for responsive conversations
- **🔧 Tool Integration**: Support for built-in tools (RAG, web search) and external MCP (Model Context Protocol) servers
- **🛡️ Safety & Guardrails**: Configurable input/output shields and safety measures
- **📊 Session Management**: Persistent chat sessions with history and metadata
- **🏗️ Scalable Architecture**: Production-ready deployment with Kubernetes and containerization

### Technology Stack

- **Frontend**: React + TypeScript + PatternFly UI + TanStack Router/Query
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + Alembic
- **AI Platform**: LlamaStack for agent management and inference
- **Vector Storage**: pgvector for knowledge base embeddings
- **Document Processing**: Kubeflow Pipelines + Docling for ingestion
- **Infrastructure**: Kubernetes + Helm + MinIO for object storage

## Architecture

The platform consists of several interconnected components:

- **Frontend UI**: Modern React application for user interaction
- **Backend API**: FastAPI server handling business logic and data persistence
- **LlamaStack**: AI platform managing agents, models, and inference
- **Knowledge Processing**: Kubernetes-based document ingestion pipeline
- **Database Layer**: PostgreSQL with vector extension for data storage

For detailed architecture information, see:

- [Virtual Agents Architecture Guide](docs/virtual-agents-architecture.md)
- [Knowledge Base Architecture Guide](docs/knowledge-base-architecture.md)

## Quick Start

Ready to get started? Check out our [Contributing Guide](CONTRIBUTING.md) for detailed setup instructions, development workflows, and deployment options.

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Podman or Docker
- LlamaStack instance

### Basic Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/RHEcosystemAppEng/ai-virtual-assistant
   cd ai-virtual-assistant
   ```

2. **Follow the setup guide**

   See [CONTRIBUTING.md](CONTRIBUTING.md) for complete setup instructions including:
   - Database configuration
   - Backend server setup
   - Frontend development server
   - Container deployment

## Documentation

- **[Contributing Guide](CONTRIBUTING.md)** - Setup, development, and contribution guidelines
- **[Virtual Agents Architecture](docs/virtual-agents-architecture.md)** - How AI agents work in the platform
- **[Knowledge Base Architecture](docs/knowledge-base-architecture.md)** - Document ingestion and RAG system
- **[Backend README](backend/README.md)** - Backend API documentation and features

## Use Cases

- **Customer Support**: Create AI agents with access to product documentation and FAQ databases
- **Internal Knowledge Management**: Build intelligent assistants for employee onboarding and information access
- **Document Q&A**: Enable natural language queries over large document collections
- **Multi-modal Assistance**: Combine different AI capabilities through tool integration

## Community & Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/RHEcosystemAppEng/ai-virtual-assistant/issues)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines

## License

This project is licensed under the [MIT LICENSE](LICENSE) - see the LICENSE file for details.

---

**Built with ❤️ by the Red Hat Ecosystem App Engineering team**
