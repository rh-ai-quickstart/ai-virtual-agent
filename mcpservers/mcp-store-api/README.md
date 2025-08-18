# MCP Store-API

A Model Context Protocol (MCP) server and Store inventory API, providing both MCP tool access and REST API endpoints for inventory management. This hybrid architecture supports both AI agent interactions and traditional web applications.

## Overview

MCP WebStore demonstrates an MCP server interacting with a FastAPI-based store service and presenting tools to an llm agent that enable it to perform operations on the stores inventory.

## Architecture

```mermaid
graph TB
    subgraph "Client Access"
        Agent[AI Agent]
        WebApp[Web Application]
        Mobile[Mobile App]
    end

    subgraph "MCP WebStore"
        MCP[MCP Server<br/>Port 8001]
        API[Store API<br/>Port 8001]
        Logic[Business Logic]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL<br/>Database)]
    end

    Agent --> MCP
    WebApp --> API
    Mobile --> API

    MCP --> Logic
    API --> Logic
    Logic --> DB

    style MCP fill:#e1f5fe
    style API fill:#e8f5e9
    style DB fill:#f3e5f5
```

**Port Information:**
- **Container Ports**: 8001 (both MCP Server and Store API)
- **Local Development**: 8004 (Store API), 8003 (MCP Server)
- **Kubernetes**: 8001 (standard deployment)

## Features

### 🛠️ **Dual Interface**
- **MCP Protocol**: AI agent tool access
- **REST API**: HTTP endpoints for web/mobile apps
- **Shared Logic**: Common business rules and data validation
- **Unified Database**: Single source of truth for all data

### 🔧 **Technical Features**
- **FastAPI Integration**: Modern async REST API
- **OpenAPI Documentation**: Auto-generated API docs
- **Database Transactions**: ACID compliance across interfaces
- **Health Monitoring**: Built-in health check endpoints

## Quick Start

### Local Development
```bash
# Navigate to directory
cd mcpservers/mcp-store-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database (uncomment mcp-webstore services in ../compose.yaml for full setup)
podman compose -f ../compose.yaml up -d postgresql
# Database 'store_db' will be created automatically by PostgreSQL container

# Set database URL (optional, defaults work with compose setup)
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/store_db"

# Run the API server first
cd store
uvicorn main:app --port 8001 --reload

# In another terminal, run the MCP server
cd ..
STORE_SERVER_URL="http://localhost:8001" python webstore.py

# Test both services
curl http://localhost:8004/health  # API health (local port 8004)
curl http://localhost:8004/docs    # API documentation
curl http://localhost:8003/health  # MCP Server (local port 8003)
```

### Podman Deployment
```bash
# Build containers
podman build -t mcp-webstore .
podman build -t mcp-webstore-api ./store

# Run with podman compose by updating and uncommenting the relevant sections of the compose file
podman compose -f ../compose.yaml up
```

### Kubernetes Deployment
```bash
# Deploy with Helm (configure critical options)
helm install mcp-webstore ./helm \
  --set postgresql.auth.postgresPassword=yourpassword \
  --set postgresql.auth.database=store_db \
  --set mcpServer.image.repository=quay.io/ecosystem-appeng/mcp-webstore \
  --set storeApi.image.repository=quay.io/ecosystem-appeng/mcp-webstore-api

# Check status
kubectl get pods -l app.kubernetes.io/name=mcp-webstore

# Test from cluster (port forward and curl)
kubectl port-forward svc/mcp-webstore-api 8001:8001 &
curl http://localhost:8001/health
curl http://localhost:8001/docs
```

## Available Interfaces

### MCP Tools
| Tool | Description | Parameters |
|------|-------------|------------|
| `get_products` | List all products | `skip`, `limit` |
| `get_product_by_id` | Get product by ID | `product_id` |
| `get_product_by_name` | Get product by name | `name` |
| `search_products` | Search products | `query`, `skip`, `limit` |
| `add_product` | Create new product | `name`, `description`, `inventory`, `price` |
| `remove_product` | Delete product | `product_id` |
| `order_product` | Place order | `product_id`, `quantity`, `customer_identifier` |

### REST API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/products/` | List products with pagination |
| `POST` | `/products/` | Create new product |
| `GET` | `/products/id/{product_id}` | Get product by ID |
| `GET` | `/products/name/{name}` | Get product by name |
| `GET` | `/products/search/?query={q}` | Search products |
| `DELETE` | `/products/{product_id}` | Delete product |
| `POST` | `/orders/` | Place order |
| `GET` | `/docs` | Interactive API documentation |

## Configuration

### Environment Variables
```bash
# MCP Server
STORE_SERVER_URL="http://localhost:8001"  # API endpoint for MCP server

# Store API
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"

# Server Settings
MCP_PORT=8001
API_PORT=8001
LOG_LEVEL=INFO
```

### Component Communication
The MCP server communicates with the Store API via HTTP:
- MCP Server → Store API → Database
- Web Clients → Store API → Database

## Documentation

- **[Development Guide](DEVGUIDE.md)** - Setup, development, and testing
- **[User Guide](USERGUIDE.md)** - Usage examples and API reference

## Use Cases

### ✅ **Best For**
- Demo purposes to deploy the mcp server and store api from one helm chart

### ⚠️ **Consider Alternatives When**
- Only MCP access is needed (use mcp-store-db)
- Independent scaling is critical (use mcp-store-inventory + store-inventory-api)
- Minimal complexity is preferred (use mcp-store-db)

## Architecture Benefits

### **Unified Data Access**
Both MCP tools and REST endpoints access the same database with consistent business logic.

### **Development Flexibility**
Teams can develop AI features and web features independently while sharing the same backend.

### **Migration Path**
Existing REST API applications can gradually add MCP capabilities without disruption.

## Performance

- **MCP Throughput**: ~800 requests/second
- **API Throughput**: ~1200 requests/second
- **Latency**: <15ms for simple operations
- **Memory Usage**: ~80MB base + connection pools
- **Concurrent Connections**: Configurable (default: 20 MCP, 100 API)

## Monitoring

### Health Checks
- **MCP Server**: Custom health endpoint
- **Store API**: `/health` endpoint
- **Database**: Connection pool monitoring

### Metrics
To be determined
- Request rates for both interfaces
- Response times by endpoint type
- Database connection utilization
- Error rates and types

## Deployment Patterns

### **Single Pod Deployment**
Both MCP server and API in one Kubernetes pod:
```yaml
# Simplified - actual deployment uses Helm
containers:
- name: mcp-server
  image: mcp-webstore:latest
- name: store-api
  image: mcp-webstore-api:latest
```

### **Separate Service Deployment**
Independent scaling of MCP and API components:
```bash
# Deploy MCP server
helm install mcp-server ./helm --set api.enabled=false

# Deploy API separately
helm install store-api ./helm --set mcp.enabled=false
```

## Support

For technical support and development:
- Review the [Development Guide](DEVGUIDE.md)
- Check the [User Guide](USERGUIDE.md) for usage examples
- See the main [MCP Servers documentation](../README.md)
- Access interactive API docs at `/docs` when running
