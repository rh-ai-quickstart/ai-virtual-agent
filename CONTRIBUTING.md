<!-- omit from toc -->
# Contributing to AI Virtual Agent Kickstart

Thank you for your interest in contributing to the AI Virtual Agent Kickstart! This guide will help you get set up for development and understand our contribution process.

<!-- omit from toc -->
## Table of Contents
- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Clone the Repository](#clone-the-repository)
  - [Local Development Setup](#local-development-setup)
    - [1. Database Setup](#1-database-setup)
    - [2. Backend Setup](#2-backend-setup)
    - [3. Frontend Setup](#3-frontend-setup)
    - [4. LlamaStack Setup (Optional)](#4-llamastack-setup-optional)
  - [Container Development Setup](#container-development-setup)
    - [Build Application Container](#build-application-container)
    - [Docker Compose Development](#docker-compose-development)
    - [Container Commands](#container-commands)
    - [Run Containerized Application](#run-containerized-application)
- [Development Environments](#development-environments)
  - [Local Services](#local-services)
  - [Container Development](#container-development)
  - [Service URLs](#service-urls)
- [Development Workflow](#development-workflow)
  - [Making Changes](#making-changes)
  - [Testing](#testing)
    - [Backend Testing](#backend-testing)
    - [Frontend Testing](#frontend-testing)
    - [Integration Testing](#integration-testing)
    - [Code Quality Checks](#code-quality-checks)
  - [Code Style](#code-style)
    - [Python (Backend)](#python-backend)
    - [TypeScript (Frontend)](#typescript-frontend)
- [Architecture \& Documentation](#architecture--documentation)
  - [Key Concepts](#key-concepts)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Getting Logs](#getting-logs)
- [Environment Variables](#environment-variables)
  - [Development Environment Variables](#development-environment-variables)
  - [Container Environment Variables](#container-environment-variables)
- [Contributing Guidelines](#contributing-guidelines)
- [Getting Help](#getting-help)

## Development Setup

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.12+** - Backend development
- **Node.js 18+** - Frontend development
- **PostgreSQL 14+** - Database (or use Docker/Podman)
- **Docker/Podman** - Containerization and services
- **LlamaStack** - AI platform (optional for development, see [LlamaStack docs](https://github.com/meta-llama/llama-stack))

### Clone the Repository

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR-USERNAME/ai-virtual-agent
   cd ai-virtual-agent
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/rh-ai-kickstart/ai-virtual-agent
   ```

### Local Development Setup

This is the recommended setup for active development with fast iteration cycles.

#### 1. Database Setup

Start PostgreSQL and MinIO using Docker Compose:

```bash
podman compose --file compose.yaml up --detach
```

**Optional**: Reset the database if needed:
```bash
podman volume ls
podman compose down && podman volume rm ai-virtual-agent_pgdata
podman compose --file compose.yaml up --detach
```

#### 2. Backend Setup

1. Create and activate a Python virtual environment:

   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Set up pre-commit hooks for code quality:

   ```bash
   cd backend
   pre-commit install
   cd ..
   ```

4. Initialize the database:

   ```bash
   cd backend
   alembic upgrade head
   cd ..
   ```

5. Start the backend server:

   ```bash
   ./venv/bin/uvicorn backend.main:app --reload
   ```

#### 3. Frontend Setup

1. In a new terminal, navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Set up pre-commit hooks for code quality:

   ```bash
   npm run prepare
   ```

4. Start the development server:

   ```bash
   npm run dev
   ```

#### 4. LlamaStack Setup (Optional)

For local AI functionality, start a local LlamaStack server:

```bash
cd scripts/dev/local_llamastack_server/
chmod +x activate_llama_server.sh
bash activate_llama_server.sh
```

### Container Development Setup

Use this setup for testing containerized deployment or when you prefer isolated environments.

#### Build Application Container

```bash
podman build --platform linux/amd64 -t ai-virtual-agent:dev .
```

#### Docker Compose Development

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: ai_virtual_agent
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build:
      context: .
      dockerfile: Containerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://admin:password@postgres:5432/ai_virtual_agent
      LLAMASTACK_URL: http://llamastack:8321
      LOG_LEVEL: DEBUG
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    volumes:
      - ./backend:/app/backend:ro  # Mount for development

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      VITE_API_BASE_URL: http://localhost:8000
      VITE_ENVIRONMENT: development
    depends_on:
      - backend
    volumes:
      - ./frontend/src:/app/src:ro  # Mount for development

  llamastack:
    image: llamastack/llamastack:latest
    ports:
      - "8321:8321"
    volumes:
      - llamastack_data:/app/data

volumes:
  postgres_data:
  minio_data:
  llamastack_data:
```

#### Container Commands

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Stop services
docker-compose -f docker-compose.dev.yml down

# Rebuild and restart
docker-compose -f docker-compose.dev.yml up --build -d
```

#### Run Containerized Application

For testing the built container:

```bash
podman run --platform linux/amd64 --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://admin:password@host.containers.internal:5432/ai_virtual_agent \
  -e LLAMASTACK_URL=http://host.containers.internal:8321 \
  ai-virtual-agent:dev
```

## Development Environments

### Local Services

When running locally, services are available at:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **LlamaStack**: http://localhost:8321 (if running locally)
- **PostgreSQL**: localhost:5432
- **MinIO Console**: http://localhost:9001 (admin/minioadmin123)
- **MinIO S3**: http://localhost:9000

### Container Development

When using Docker Compose, services use internal networking but expose the same ports to your host.

### Service URLs

The development setup provides these endpoints:

| Service | Local | Container | Purpose |
|---------|-------|-----------|---------|
| Frontend | http://localhost:5173 | http://frontend:5173 | React development server |
| Backend | http://localhost:8000 | http://backend:8000 | FastAPI application |
| Database | localhost:5432 | postgres:5432 | PostgreSQL + pgvector |
| Object Storage | localhost:9000 | minio:9000 | MinIO S3-compatible storage |
| LlamaStack | localhost:8321 | llamastack:8321 | AI model serving |

## Development Workflow

### Making Changes

1. Create a new branch for your feature/fix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Test your changes thoroughly (see [Testing](#testing))

4. Commit your changes with descriptive messages:

   ```bash
   git add .
   git commit -m "feat: add new virtual agent configuration option"
   ```

5. Push your branch and create a pull request:

   ```bash
   git push origin feature/your-feature-name
   ```

### Testing

#### Backend Testing

```bash
cd backend

# Run unit tests (when available)
pytest

# Test API endpoints manually
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Test database connection
python -c "import asyncio; from backend.database import engine; print('DB OK')"
```

#### Frontend Testing

```bash
cd frontend

# Run unit tests (when available)
npm test

# Build check
npm run build

# Type checking
npm run type-check
```

#### Integration Testing

Test the full application stack:

1. Start all services (local or container)
2. Verify each component:
   - ✅ Database connectivity
   - ✅ API health endpoints
   - ✅ Frontend loads and connects to backend
   - ✅ Agent creation and management
   - ✅ Knowledge base operations (if LlamaStack available)
   - ✅ Chat functionality (if LlamaStack available)

#### Code Quality Checks

Before submitting a pull request, ensure all code quality checks pass:

**Backend Code Quality:**
```bash
cd backend
# Run all pre-commit hooks
pre-commit run --all-files

# Or run individual checks
black --check .
isort --check .
flake8 .
vulture . --min-confidence=80
```

**Frontend Code Quality:**
```bash
cd frontend
# Check formatting
npm run format:check

# Check linting
npm run lint

# Check TypeScript compilation
npm run build

# Or run all checks together
npm run format:check && npm run lint && npm run build
```

### Code Style

#### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Document functions and classes with docstrings
- Format code with `black` and `isort`
- Lint code with `flake8` and `vulture`

**Pre-commit Hooks Setup:**

We use pre-commit hooks to automatically format and lint code. Set them up once:

```bash
cd backend
pip install -r requirements.txt
pre-commit install
```

**Manual Formatting:**

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Check formatting without making changes
black --check --diff .
isort --check --diff .

# Run all pre-commit hooks manually
pre-commit run --all-files
```

The pre-commit hooks include:
- `black` - Code formatting (88-character line length)
- `isort` - Import sorting (black compatible)
- `flake8` - Linting (E203, W503 ignored for black)
- `vulture` - Dead code detection (80% confidence)
- `trailing-whitespace` - Remove trailing whitespace
- `end-of-file-fixer` - Ensure files end with newline
- `check-yaml` - Validate YAML files
- `check-added-large-files` - Prevent large file commits
- `check-merge-conflict` - Detect merge conflict markers
- `debug-statements` - Detect debug statements

#### TypeScript (Frontend)

- Use TypeScript for all new code
- Follow React hooks patterns and exhaustive dependencies rules
- Use PatternFly components for UI consistency
- Format code with Prettier
- Lint code with ESLint (includes React, TypeScript, and accessibility rules)

**Pre-commit Hooks Setup:**

```bash
cd frontend
npm install
npm run prepare  # Sets up Husky hooks
```

**Manual Formatting and Linting:**

```bash
# Format code with Prettier
npm run format

# Check formatting without making changes
npm run format:check

# Lint code with ESLint
npm run lint

# Auto-fix linting issues where possible
npm run lint:fix

# Build to check for TypeScript compilation errors
npm run build
```

The pre-commit hooks include:
- `prettier --write` - Auto-format all supported files
- `eslint --fix` - Auto-fix linting issues

## Architecture & Documentation

Before making significant changes, familiarize yourself with the system architecture:

- **[Virtual Agents Architecture](docs/virtual-agents-architecture.md)** - Understanding agent lifecycle and chat system
- **[Knowledge Base Architecture](docs/knowledge-base-architecture.md)** - Document processing and RAG implementation
- **[API Reference](docs/api-reference.md)** - Complete API documentation
- **[Installation Guide](INSTALLING.md)** - Production deployment guide

### Key Concepts

- **Virtual Agents**: AI agents managed through LlamaStack
- **Knowledge Bases**: Document collections processed for RAG
- **Sessions**: Persistent chat conversations with context
- **Tools**: Built-in and external capabilities (RAG, web search, MCP servers)
- **LlamaStack Integration**: Core AI platform for model serving and agent management

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check Python version (requires 3.12+)
- Verify PostgreSQL is running and accessible:
   ```bash
   podman ps  # Check that postgres container is up
   psql -h localhost -p 5432 -U admin -d ai_virtual_agent
   ```
- Ensure all environment variables are set
- Check database migrations: `alembic upgrade head`

**Frontend build fails:**
- Check Node.js version (requires 18+)
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Verify backend is running on the expected port
- Check for TypeScript errors: `npm run build`

**Database connection errors:**
- Verify PostgreSQL container is running: `podman ps`
- Check connection string in environment variables
- Ensure database is initialized: `alembic upgrade head`
- Test connection manually:
  ```bash
  psql -h localhost -p 5432 -U admin -d ai_virtual_agent -c "SELECT 1;"
  ```

**LlamaStack integration issues (optional for development):**
- Verify LlamaStack is running and accessible
- Check LLAMASTACK_URL environment variable
- Review LlamaStack logs for errors
- Test endpoint: `curl http://localhost:8321/health`

**Container issues:**
- Check Docker/Podman is running
- Verify port conflicts: `podman ps` or `docker ps`
- Check container logs: `podman logs <container-name>`
- For networking issues, use `host.containers.internal` instead of `localhost`

**Pre-commit hooks failing:**

*Backend (Python):*
- Ensure you're in the backend directory when running hooks
- Install requirements: `pip install -r requirements.txt`
- For black/isort conflicts, run both tools: `black . && isort .`
- For flake8 issues, fix manually or use `autopep8` for simple fixes
- For vulture false positives, add `# noqa: vulture` comment

*Frontend (TypeScript):*
- Ensure you're in the frontend directory
- Install dependencies: `npm install`
- For Prettier issues, run: `npm run format`
- For ESLint issues, try auto-fix first: `npm run lint:fix`
- For TypeScript errors, run: `npm run build` and fix compilation issues

### Getting Logs

**Local Development:**
```bash
# Backend logs are shown in terminal
# Frontend logs are shown in terminal and browser console

# Database logs
podman logs ai-virtual-agent-postgres-1

# MinIO logs
podman logs ai-virtual-agent-minio-1
```

**Container Development:**
```bash
# All service logs
docker-compose -f docker-compose.dev.yml logs -f

# Specific service logs
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

## Environment Variables

### Development Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/ai_virtual_agent

# LlamaStack (optional for development)
LLAMASTACK_URL=http://localhost:8321

# Application
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key
CORS_ORIGINS=["http://localhost:5173"]

# Object Storage (for knowledge base features)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
```

Frontend environment (`.env.local`):
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

### Container Environment Variables

When using Docker Compose, environment variables are configured in the compose file with service networking.

## Contributing Guidelines

1. **Follow the code style** guidelines for your language
   - Backend: PEP 8, black formatting, proper type hints
   - Frontend: Prettier formatting, ESLint rules, TypeScript strict mode

2. **Use pre-commit hooks** - Both backend and frontend have automated code quality checks

3. **Write tests** for new functionality (test frameworks are being established)

4. **Update documentation** when adding features or changing behavior
   - Update API docs for backend changes
   - Update architecture docs for significant changes
   - Update this contributing guide for workflow changes

5. **Keep commits focused** - one logical change per commit

6. **Write clear commit messages** following conventional commit format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `style:` for formatting changes
   - `refactor:` for code refactoring
   - `test:` for adding tests
   - `chore:` for maintenance tasks

7. **Ensure all checks pass** - linting, formatting, type checking, and builds

8. **Test your changes** in both local and container environments when possible

9. **Review your own PR** before requesting review from others

10. **Be responsive** to feedback and update your PR as needed

## Getting Help

- **Documentation**: Check the architecture guides in the `docs/` directory
- **Documentation**: Check the project documentation in the `docs/` folder
- **Discussions**: Join [GitHub Discussions](https://github.com/rh-ai-kickstart/ai-virtual-agent/discussions)
- **Code Review**: Ask questions in pull request comments
- **Local Setup**: Use this guide's troubleshooting section
- **Production Deployment**: See [INSTALLING.md](INSTALLING.md)

Thank you for contributing to AI Virtual Agent Kickstart! 🚀
