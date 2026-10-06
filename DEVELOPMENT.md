# AI Virtual Agent - Development Setup

This document describes how to set up the AI Virtual Agent for local development using containerized services.

## Quick Start (New - Single Command!)

### Prerequisites

Ensure you have the following running on your system:

- **Podman** with podman-compose support
- **Ollama** service running on `localhost:11434`
- **Required Ollama model**: `llama3.2:3b-instruct-fp16` loaded and ready

### Start Development Environment

```bash
# Option 1: Using Makefile (recommended)
make compose-up

# Option 2: Using the script directly
./scripts/start-dev.sh
```

**Note**: First startup takes longer due to image downloads.

That's it! All services will be running:

- **Frontend**: http://localhost:5173 (with hot reload)
- **Backend**: http://localhost:8000 (with hot reload)
- **Database**: postgresql://admin:password@localhost:5432/ai_virtual_agent
- **LlamaStack**: http://localhost:8321
- **S4 S3 API**: http://localhost:7480 (for attachments, optional)
- **S4 UI**: http://localhost:5000 (admin / `S4_AUTH_PASSWORD`)

### Stop Development Environment

```bash
# Option 1: Using Makefile (recommended)
make compose-down

# Option 2: Using the script directly
./scripts/stop-dev.sh
```

## Service Details

### Services Included

1. **PostgreSQL Database** - Persistent storage for application data
2. **LlamaStack** - AI model server with Ollama integration
3. **Backend** - FastAPI server with hot reload
4. **Frontend** - Vite dev server with hot reload
5. **S4** - S3-compatible object storage for attachments (optional, enabled by default)

### Environment Configuration

The development setup uses `.env` for configuration. Copy from the template:

```bash
cp .env.example .env
```

#### Environment Variables

Key development environment variables:

- `LOCAL_DEV_ENV_MODE=true` - **Development mode** (bypasses authentication)
- `ENABLE_ATTACHMENTS=true` - **Enable S4** and attachment features
- `DISABLE_ATTACHMENTS=false` - Backend flag (set automatically)

#### Optional Configurations

Start without attachments (faster startup):
```bash
ENABLE_ATTACHMENTS=false make compose-up
```

Start with authentication enabled (production-like):
```bash
LOCAL_DEV_ENV_MODE=false make compose-up
```

Default configuration:
- **Database**: PostgreSQL on port 5432
- **Backend**: FastAPI on port 8000 with `LOCAL_DEV_ENV_MODE=true`
- **Frontend**: Vite dev server on port 5173
- **LlamaStack**: AI server on port 8321
- **S4**: S3 API on port 7480 with UI on port 5000

### Development Features

- ✅ **Hot Reload**: Both backend and frontend automatically reload on code changes
- ✅ **Network Isolation**: All services run in a dedicated Docker network
- ✅ **Health Checks**: Services wait for dependencies to be ready
- ✅ **Volume Mounts**: Source code is mounted for live editing
- ✅ **Local Dev Mode**: Authentication bypass enabled for development
- ✅ **Persistent Data**: Database data persists between restarts

## Troubleshooting

### Common Issues

1. **Ollama not accessible**
   - Ensure Ollama is running on `localhost:11434`
   - Verify the model `llama3.2:3b-instruct-fp16` is loaded

2. **Port conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :5432 -i :8000 -i :5173 -i :8321

   # Customize ports in .env
   vim .env
   ```

3. **Permission issues**
   ```bash
   # Ensure scripts are executable
   chmod +x scripts/*.sh
   ```

4. **View service logs**
   ```bash
   # All services (using Makefile)
   make compose-logs

   # All services (direct command)
   podman compose -f compose.dev.yaml logs -f

   # Specific service
   podman compose -f compose.dev.yaml logs -f backend
   ```

### Useful Commands

#### Using Makefile (Recommended)

```bash
# View service logs
make compose-logs

# Check service status
make compose-status

# Restart all services
make compose-restart

# Rebuild and restart services
make compose-build

# See all available development commands
make help
```

#### Using podman compose directly

```bash
# Restart a specific service
podman compose -f compose.dev.yaml restart backend

# Rebuild a service
podman compose -f compose.dev.yaml up --build backend

# Access a service shell
podman exec -it ai-va-backend-dev bash

# Remove all data (fresh start)
podman compose -f compose.dev.yaml down --volumes
```

## Migration from Manual Setup

### Before (4 Terminals Required)
```bash
# Terminal 1: Database
podman compose --file compose.yaml up --detach

# Terminal 2: LlamaStack
# LlamaStack is now integrated into the compose setup

# Terminal 3: Backend
source venv/bin/activate && export LOCAL_DEV_ENV_MODE=true && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Frontend
cd frontend && npm install && npm run dev
```

### After (1 Command)
```bash
# Using Makefile (recommended)
make compose-up

# Or using script directly
./scripts/start-dev.sh
```

## When to Rebuild Containers

Use `make compose-build` when you modify:

- **Dependencies**: `backend/requirements.txt` or `frontend/package.json`
- **Container files**: `Containerfile`, `Dockerfile.*`
- **Startup scripts**: `scripts/start-backend-dev.sh`

Code changes in `backend/` and `frontend/` directories use hot reload - no rebuild needed.

## Development Container Commands Reference

The following Makefile targets are available for containerized development:

- `make compose-up` - Start development services (uses .env and compose.dev.yaml)
- `make compose-down` - Stop development services
- `make compose-restart` - Restart development services
- `make compose-logs` - View logs from development services
- `make compose-build` - Rebuild and start development services
- `make compose-status` - Show status of development services

For all available make targets, run `make help`.

## File Organization

The project has been reorganized for better structure:

- **Development compose**: `deploy/local/compose.dev.yaml` (used by make commands)
- **Production compose**: `compose.yaml` (root level for production deployments)
- **Test requirements**: `tests/requirements.txt` (moved from root)
- **Make commands**: Use `make local/<command>` for local development targets

## Next Steps

- Customize `.env` for your specific needs
- Add additional services to `compose.dev.yaml` as needed
- Use the existing `compose.yaml` for production-like testing
- Run `make help` to see all available project commands
