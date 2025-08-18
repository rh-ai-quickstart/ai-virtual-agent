# MCP Servers

Model Context Protocol (MCP) servers provide external tool capabilities to AI agents in the AI Virtual Agent Kickstart platform. These servers implement standardized interfaces that allow agents to access external data sources and perform operations beyond built-in tools.

## Available MCP Servers

| Server | Type | Description | Use Case |
|--------|------|-------------|---------|
| [**mcp-store-db**](mcp-store-db/) | Integrated | MCP server with tightly coupled database for direct data access | MCP Server + Database |
| [**mcp-store-api**](mcp-store-api/) | Client-Server | MCP server with separate store API for distributed architecture | MCP Server + Store API |
| [**mcp-store-inventory**](mcp-store-inventory/) | Standalone | Lightweight MCP server requiring external store API | Standalone MCP Server |
| [**store-inventory-api**](store-inventory-api/) | API Service | Standalone FastAPI service for inventory management | Standalone Store API |

## Architecture Overview

```mermaid
graph TB
    subgraph "AI Virtual Agent Platform"
        Agent[AI Agent]
        LlamaStack[LlamaStack]
    end

    subgraph "MCP Servers"
        MCP_DB[mcp-store-db<br/>Integrated]
        MCP_WEB[mcp-store-api<br/>Client-Server]
        MCP_INV[mcp-store-inventory<br/>Standalone]
    end

    subgraph "APIs & Databases"
        WEB_API[mcp-store-api API]
        STORE_API[store-inventory-api API]
        DB1[(PostgreSQL)]
        DB2[(PostgreSQL)]
        DB3[(PostgreSQL)]
    end

    Agent --> LlamaStack
    LlamaStack --> MCP_DB
    LlamaStack --> MCP_WEB
    LlamaStack --> MCP_INV

    MCP_DB --> DB1
    MCP_WEB --> WEB_API
    WEB_API --> DB2
    MCP_INV --> STORE_API
    STORE_API --> DB3
```

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Podman (for containerized deployment)
- Kubernetes + Helm (for cluster deployment)

### Local Development
```bash
# Clone and setup
git clone <repository>
cd mcpservers

# Choose a server to run locally
cd mcp-store-db  # or mcp-store-api, mcp-store-inventory, store-inventory-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database (see Local Development with Compose section below)
podman-compose -f compose.yaml up -d postgresql
# Database 'store_db' will be created automatically

# Run the server
python store.py  # or appropriate main file
```

### Cluster Deployment
```bash
# Deploy with Helm (configure critical options)
cd mcp-store-db  # or any server
helm install my-mcp-server ./helm \
  --set postgresql.auth.postgresPassword=yourpassword \
  --set env.DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"

# For mcp-store-inventory, also set API URL
helm install mcp-inventory mcp-store-inventory/helm \
  --set env.STORE_API_URL="http://store-inventory-api:8002"
```

## Server Comparison

### Use Case Selection Guide

**Choose `mcp-store-db` when:**
- You need simple, direct database access
- Minimal infrastructure complexity is preferred
- Tight coupling between MCP server and data is acceptable

**Choose `mcp-store-api` when:**
- You need both MCP capabilities and REST API access
- Multiple clients will access the same data
- You want API flexibility with MCP integration

**Choose `mcp-store-inventory` + `store-inventory-api` when:**
- You need maximum architectural flexibility
- Independent scaling of MCP and API layers
- Microservices architecture is preferred

### Feature Matrix

| Feature | mcp-store-db | mcp-store-api | mcp-store-inventory | store-inventory-api |
|---------|-------------|--------------|-------------------|-----------------|
| **MCP Protocol** | ✅ | ✅ | ✅ | ❌ |
| **REST API** | ❌ | ✅ | ❌ | ✅ |
| **Database Integration** | Direct | Via API | Via API | Direct |
| **Independent Scaling** | ❌ | ⚠️ Limited | ✅ | ✅ |
| **Deployment Complexity** | Low | Medium | Low | Low |
| **Resource Usage** | Low | Medium | Low | Low |

## Development

### Project Structure
```
mcpservers/
├── mcp-store-db/           # Integrated MCP + Database
├── mcp-store-api/          # MCP + API Bundle
├── mcp-store-inventory/   # Standalone MCP Server
├── store-inventory-api/       # Standalone API Service
└── docs/                  # Shared documentation
```

### Contributing
Each server has its own development guide:
- [mcp-store-db Development Guide](mcp-store-db/DEVGUIDE.md) - Direct database MCP server
- [mcp-store-db User Guide](mcp-store-db/USERGUIDE.md) - Direct database MCP server
- [mcp-store-api Development Guide](mcp-store-api/DEVGUIDE.md) - MCP server with API
- [mcp-store-api User Guide](mcp-store-api/USERGUIDE.md) - MCP server with API
- [mcp-store-inventory Development Guide](mcp-store-inventory/DEVGUIDE.md)
- [store-inventory-api Development Guide](store-inventory-api/DEVGUIDE.md)

## Documentation

### User Guides
- [mcp-store-db User Guide](mcp-store-db/USERGUIDE.md) - Direct database MCP server
- [mcp-store-api User Guide](mcp-store-api/USERGUIDE.md) - MCP server with API
- [mcp-store-inventory User Guide](mcp-store-inventory/USERGUIDE.md) - Standalone MCP client
- [store-inventory-api User Guide](store-inventory-api/USERGUIDE.md) - Inventory management API

### Technical Documentation
See individual component documentation for technical details and deployment guides.

## Local Development with Compose

The `compose.yaml` file provides a complete local development environment for all MCP servers.

### Quick Start

```bash
# Start PostgreSQL (required for all components)
# -d flag runs in background (detached mode)
podman compose -f compose.yaml up -d postgresql

# Alternative: Start and see logs in real-time (foreground)
# podman compose -f compose.yaml up postgresql

# Verify database is running
podman compose -f compose.yaml ps
podman compose -f compose.yaml logs postgresql
```

**About the `-d` flag:**
- **`-d postgresql`** = Start only the postgresql service in detached mode (background)
- **`-d`** (without service name) = Start all services in detached mode
- **No `-d` flag** = Start services in foreground (see logs in real-time)

### Component-Specific Setups

#### MCP DBStore (Integrated)
```bash
# Uncomment mcp-dbstore service in compose.yaml, then:
podman compose -f compose.yaml up -d mcp-dbstore

# Test the server
curl http://localhost:8005/health  # Local port 8005
```

#### Store Inventory API (Standalone)
```bash
# Uncomment store-inventory-api service in compose.yaml, then:
podman compose -f compose.yaml up -d store-inventory-api

# Test the API
curl http://localhost:8002/health
curl http://localhost:8002/docs
```

#### MCP Store Inventory + Store API (Microservices)
```bash
# Uncomment both store-inventory-api and mcp-store-inventory services in compose.yaml, then:
podman compose -f compose.yaml up -d store-inventory-api mcp-store-inventory

# Test both services
curl http://localhost:8002/health  # Store API (local port 8002)
curl http://localhost:8001/health  # MCP Server (local port 8001)
```

#### MCP WebStore (Hybrid)
```bash
# Uncomment both mcp-webstore-api and mcp-webstore services in compose.yaml, then:
podman compose -f compose.yaml up -d mcp-webstore-api mcp-webstore

# Test both components
curl http://localhost:8004/health  # Store API (local port 8004)
curl http://localhost:8004/docs    # API documentation
curl http://localhost:8003/health  # MCP Server (local port 8003)
```

### Port Configuration

| Service | Local Port | Container Port | Description |
|---------|------------|----------------|-------------|
| **PostgreSQL** | 5432 | 5432 | Database server |
| **mcp-dbstore** | 8005 | 8002 | Integrated MCP + Database |
| **store-inventory-api** | 8002 | 8002 | Standalone Store API |
| **mcp-store-inventory** | 8001 | 8003 | Standalone MCP Server |
| **mcp-webstore-api** | 8004 | 8001 | Store API component |
| **mcp-webstore** | 8003 | 8001 | MCP Server component |

**Note**:
- **Local Port**: Port on your host machine (unique to avoid conflicts)
- **Container Port**: Port inside the container (can be the same across services)
- **Cluster Deployment**: All services can use the same port (e.g., 8002) as they run in separate pods

**Port Strategy**:
- **Local Development**: Each service gets a unique local port to avoid conflicts
- **Container Internals**: Services use their preferred internal ports (8001, 8002, 8003)
- **Kubernetes**: No port conflicts since each service runs in its own pod/namespace

### Database Configuration

- **Database**: `store_db` (automatically created)
- **User**: `postgres`
- **Password**: `password`
- **Port**: `5432`
- **Connection String**: `postgresql+asyncpg://postgres:password@localhost:5432/store_db`

### Testing Database Connection

```bash
# Using psql (if installed)
psql "postgresql://postgres:password@localhost:5432/store_db" -c "SELECT 1;"

# Using podman exec
podman exec -it mcp-postgresql psql -U postgres -d store_db -c "SELECT 1;"
```

### Cleanup

```bash
# Stop all services
podman compose -f compose.yaml down

# Remove volumes (deletes data)
podman compose -f compose.yaml down -v
```

### Troubleshooting

#### Port Conflicts
If ports are already in use, modify the port mappings in `compose.yaml`:
```yaml
ports:
  - '5433:5432'  # Use different host port for PostgreSQL
  - '8012:8002'  # Use different host port for APIs
```

#### Database Connection Issues
```bash
# Check container status
podman compose -f compose.yaml ps

# View logs
podman compose -f compose.yaml logs postgresql
podman compose -f compose.yaml logs <service-name>

# Test connection
podman exec -it mcp-postgresql pg_isready -U postgres
```

## Support

For issues, questions, or contributions:
1. Check the specific server's documentation
2. Review the development guides for technical details
3. Consult the user guides for usage instructions
4. Use the `compose.yaml` file for local development
5. Create issues in the main repository

## License

This project is licensed under the same terms as the AI Virtual Agent Kickstart platform.
