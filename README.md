# AI Virtual Agent

A comprehensive platform for creating and managing AI-powered virtual agents with knowledge base integration, built on top of LlamaStack.Use this to quickly create AI Virtual Agent for different user personas such as lawyer, accountants and marketers.

To see how it's done, refer to the [installation guide](INSTALLING.md).

## Description

The AI Virtual Agent platform provides a complete solution for building intelligent conversational agents that can access and reason over your organization's knowledge. The system combines modern web technologies with powerful AI capabilities to deliver a seamless experience for both developers and end users.

### Use Cases

- **Customer Support**: Create AI agents with access to product documentation and FAQ databases
- **Internal Knowledge Management**: Build intelligent agents for employee onboarding and information access
- **Document Q&A**: Enable natural language queries over large document collections
- **Multi-modal Assistance**: Combine different AI capabilities through tool integration

## Architecture

The platform consists of several interconnected components:

- **Frontend UI**: Modern React application for user interaction
- **Backend API**: FastAPI server handling business logic and data persistence
- **LlamaStack**: AI platform managing agents, models, and inference
- **Knowledge Processing**: Kubernetes-based document ingestion pipeline
- **Database Layer**: PostgreSQL with vector extension for data storage

![AI Virtual Agent Architecture](docs/images/ai-virtual-agent.jpg)

For detailed architecture information, see:

- [Virtual Agents Architecture Guide](docs/virtual-agents-architecture.md)
- [Knowledge Base Architecture Guide](docs/knowledge-base-architecture.md)

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

## Documentation

- **[Installation Guide](INSTALLING.md)** - Install AI Virtual Agent
- **[Contributing Guide](CONTRIBUTING.md)** - Setup, development, and contribution guidelines
- **[Adding New Templates](docs/ADDING_NEW_TEMPLATES.md)** - Complete guide for creating new agent templates
- **[Template Quick Reference](docs/TEMPLATE_QUICK_REFERENCE.md)** - Quick reference for template creation
- **[Virtual Agents Architecture](docs/virtual-agents-architecture.md)** - How AI agents work in the platform
- **[Knowledge Base Architecture](docs/knowledge-base-architecture.md)** - Document ingestion and RAG system
- **[Backend README](backend/README.md)** - Backend API documentation and features

## Community & Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/RHEcosystemAppEng/ai-virtual-agent/issues)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines

## License

This project is licensed under the [MIT LICENSE](LICENSE) - see the LICENSE file for details.

---

**Built with ❤️ by the Red Hat Ecosystem App Engineering team**
