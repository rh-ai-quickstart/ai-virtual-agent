# Contributing to AI Virtual Agent

Thank you for your interest in contributing to the AI Virtual Agent platform! This guide will help you get set up for development and understand our contribution process.

## Table of Contents

- [Contributing to AI Virtual Agent](#contributing-to-ai-virtual-agent)
  - [Table of Contents](#table-of-contents)
  - [Development Setup](#development-setup)
    - [Prerequisites](#prerequisites)
    - [Clone the Repository](#clone-the-repository)
    - [Database Setup](#database-setup)
    - [Backend Setup](#backend-setup)
    - [Frontend Setup](#frontend-setup)
  - [Container Deployment](#container-deployment)
    - [Building Container Images](#building-container-images)
    - [Running Container Images](#running-container-images)
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
  - [Getting Help](#getting-help)
  - [Environment Variables](#environment-variables)
  - [Contributing Guidelines](#contributing-guidelines)

## Development Setup

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.12+** - Backend development
- **Node.js 18+** - Frontend development
- **PostgreSQL 14+** - Database
- **Podman or Docker** - Containerization
- **LlamaStack** - AI platform (see [LlamaStack docs](https://github.com/meta-llama/llama-stack))

### Clone the Repository

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR-USERNAME/ai-virtual-assistant
   cd ai-virtual-assistant
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/RHEcosystemAppEng/ai-virtual-assistant
   ```

### Database Setup

1. Start PostgreSQL using Docker Compose:

   ```bash
   podman compose --file compose.yaml up --detach
   ```

2. **Optional**: Reset the database if needed:

   ```bash
   podman volume ls
   podman compose down && podman volume rm ai-virtual-assistant_pgdata
   podman compose --file compose.yaml up --detach
   ```

### Backend Setup

1. Create and activate a Python virtual environment:

   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip3 install -r backend/requirements.txt
   ```

3. Set up pre-commit hooks for code quality:

   ```bash
   cd backend
   pre-commit install
   cd ..
   ```

   This enables automatic code formatting and linting on each commit.

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

   The backend will be available at `http://localhost:8000`

   - API documentation: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

6. Start Local LLamaStack Server:

   This step is optional, use it if you don't have an active llamastack server.
   Open a new terminal:
   ```bash
   cd local_dev/local_llamastack_server/
   chmod +x activate_llama_server.sh
   bash activate_llama_server.sh
   ```

### Frontend Setup

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

   This enables automatic formatting and linting on each commit via Husky.

4. Start the development server:

   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

## Container Deployment

### Building Container Images

Build the application container:

```bash
podman build --platform linux/amd64 -t quay.io/ecosystem-appeng/ai-virtual-assistant:1.1.0 .
```

### Running Container Images

1. Ensure PostgreSQL is running (see [Database Setup](#database-setup))

2. Run the containerized application:

   ```bash
   podman run --platform linux/amd64 --rm -p 8000:8000 \
     -e DATABASE_URL=postgresql+asyncpg://admin:password@host.containers.internal:5432/ai_virtual_assistant \
     -e LLAMASTACK_URL=http://host.containers.internal:8321 \
     quay.io/ecosystem-appeng/ai-virtual-assistant:1.1.0
   ```

## Development Workflow

### Making Changes

1. Create a new branch for your feature/fix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Test your changes thoroughly

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

TODO

#### Frontend Testing

TODO

#### Integration Testing

Test the full application stack by running both backend and frontend and verifying:

- Agent creation and management
- Knowledge base upload and processing
- Chat functionality with streaming responses
- Session management

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

**Both Will Run Automatically:**
- Backend pre-commit hooks run on `git commit` for Python files
- Frontend pre-commit hooks run on `git commit` for JS/TS files via Husky + lint-staged

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

The pre-commit hooks will automatically run on each commit and include:
- `black` - Code formatting with 88-character line length
- `isort` - Import sorting (configured for black compatibility)
- `flake8` - Linting (E203, W503 ignored for black compatibility)
- `vulture` - Dead code detection (80% confidence threshold)
- `trailing-whitespace` - Remove trailing whitespace
- `end-of-file-fixer` - Ensure files end with newline
- `check-yaml` - Validate YAML files
- `check-added-large-files` - Prevent large file commits
- `check-merge-conflict` - Detect merge conflict markers
- `debug-statements` - Detect debug statements

> [!NOTE]
> Migration files in `migrations/` are excluded from most hooks to preserve auto-generated code.

#### TypeScript (Frontend)

- Use TypeScript for all new code
- Follow React hooks patterns and exhaustive dependencies rules
- Use PatternFly components for UI consistency
- Format code with Prettier
- Lint code with ESLint (includes React, TypeScript, and accessibility rules)

**Pre-commit Hooks Setup:**

The frontend uses Husky and lint-staged for pre-commit hooks. Set them up once:

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

**Code Style Configuration:**

- **Prettier**: Configured for 100-character line width, 2-space indentation, single quotes
- **ESLint**: Includes TypeScript, React, React Hooks, and JSX accessibility rules
- **TypeScript**: Strict mode enabled with comprehensive type checking

The pre-commit hooks (via Husky + lint-staged) will automatically run on each commit and include:
- `prettier --write` - Auto-format all supported file types (JS, TS, JSON, CSS, MD, YAML)
- `eslint --fix` - Auto-fix linting issues in JavaScript/TypeScript files

**Supported File Types for Auto-formatting:**
- JavaScript/TypeScript: `.js`, `.jsx`, `.ts`, `.tsx`
- Styling: `.css`, `.scss`
- Data: `.json`, `.yaml`, `.yml`
- Documentation: `.md`

## Architecture & Documentation

Before making significant changes, familiarize yourself with the system architecture:

- **[Virtual Agents Architecture](docs/virtual-agents-architecture.md)** - Understanding agent lifecycle and chat system
- **[Knowledge Base Architecture](docs/knowledge-base-architecture.md)** - Document processing and RAG implementation
- **[Backend README](backend/README.md)** - API structure and database models

### Key Concepts

- **Virtual Agents**: AI agents managed through LlamaStack
- **Knowledge Bases**: Document collections processed for RAG
- **Sessions**: Persistent chat conversations with context
- **Tools**: Built-in and external capabilities (RAG, web search, MCP servers)

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check Python version (requires 3.12+)
- Verify PostgreSQL is running and accessible
   use:
   ```bash
   podman ps # see that docker.io/library/postgres:15 is up

   # Log in to the DB:
   psql -h localhost -p 5432 -U admin -d ai_virtual_assistant
   ```
- Ensure all environment variables are set

**Frontend build fails:**
- Check Node.js version (requires 18+)
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Verify backend is running on the expected port

**Database connection errors:**
- Verify PostgreSQL container is running: `podman ps`
- Check connection string in environment variables
- Ensure database is initialized: `alembic upgrade head`

**LlamaStack integration issues:**
- Verify LlamaStack is running and accessible
- Check LLAMASTACK_URL environment variable
- Review LlamaStack logs for errors

**Pre-commit hooks failing:**

*Backend (Python):*
- Ensure you're in the backend directory when running hooks
- Install requirements: `pip install -r requirements.txt`
- For black/isort conflicts, run both tools: `black . && isort .`
- For flake8 issues, fix manually or use `autopep8` for simple fixes
- For vulture false positives, add `# noqa: vulture` comment or configure `.vulture.toml`

*Frontend (TypeScript):*
- Ensure you're in the frontend directory
- Install dependencies: `npm install`
- For Prettier issues, run: `npm run format`
- For ESLint issues, try auto-fix first: `npm run lint:fix`
- For TypeScript errors, run: `npm run build` and fix compilation issues
- For React hooks dependencies, follow the ESLint suggestions or use `useCallback`/`useMemo`

**Git commit blocked by hooks:**
```bash
# Skip hooks temporarily (not recommended for main branches)
git commit --no-verify -m "your message"

# Or fix the issues and try again
git add .
git commit -m "your message"
```

### Getting Logs

**Backend logs:**
```bash
# Development server logs are shown in terminal
# For container logs:
podman logs <container-id>
```

**Frontend logs:**
```bash
# Check browser developer console
# Development server logs are shown in terminal
```

**Database logs:**
```bash
podman logs ai-virtual-assistant-postgres-1
```

## Getting Help

- **Documentation**: Check the architecture guides in the `docs/` directory
- **Issues**: Search existing [GitHub Issues](https://github.com/RHEcosystemAppEng/ai-virtual-assistant/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/RHEcosystemAppEng/ai-virtual-assistant/discussions)
- **Code Review**: Ask questions in pull request comments

## Environment Variables

Create a `.env` file in the backend directory for local development:

```env
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/ai_virtual_assistant
LLAMASTACK_URL=http://localhost:8321
```

## Contributing Guidelines

1. **Follow the code style** guidelines for your language
   - Backend: PEP 8, black formatting, proper type hints
   - Frontend: Prettier formatting, ESLint rules, TypeScript strict mode
2. **Use pre-commit hooks** - Both backend and frontend have automated code quality checks
3. **Write tests** for new functionality
4. **Update documentation** when adding features or changing behavior
5. **Keep commits focused** - one logical change per commit
6. **Write clear commit messages** following conventional commit format
7. **Update CHANGELOG** for user-facing changes
8. **Ensure all CI checks pass** - linting, formatting, type checking, and builds
9. **Review code quality** - run `pre-commit run --all-files` (backend) and `npm run lint && npm run format:check` (frontend) before submitting PRs

Thank you for contributing to AI Virtual Agent! 🚀
