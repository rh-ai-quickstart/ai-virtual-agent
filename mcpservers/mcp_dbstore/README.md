# MCP DBStore

An integrated Model Context Protocol (MCP) server with tightly coupled PostgreSQL database for direct inventory management. This server provides AI agents with direct database access for product and order operations.

## Overview

MCP DBStore combines an MCP server with direct database connectivity, offering the simplest architecture for inventory management tools. It's ideal for scenarios where you need straightforward database operations without additional API layers.

## Architecture

```mermaid
graph LR
    subgraph "AI Agent Platform"
        Agent[AI Agent]
        LlamaStack[LlamaStack]
    end

    subgraph "MCP DBStore"
        MCP[MCP Server<br/>Port 8002]
        CRUD[CRUD Operations]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL<br/>Database)]
    end

    Agent --> LlamaStack
    LlamaStack --> MCP
    MCP --> CRUD
    CRUD --> DB

    style MCP fill:#e1f5fe
    style DB fill:#f3e5f5
```

**Port Information:**
- **Container Port**: 8002 (internal service port)
- **Local Development**: 8005 (when using compose.yaml)
- **Kubernetes**: 8002 (standard deployment)

## Features

### 🛠️ **Core Capabilities**
- **Product Management**: Create, read, update, delete products
- **Inventory Tracking**: Real-time inventory level management
- **Order Processing**: Handle customer orders with inventory validation
- **Search Operations**: Query products by name, description, or criteria

### 🔧 **Technical Features**
- **Direct Database Access**: No intermediate API layer
- **Async Operations**: Full async/await support for performance
- **Transaction Safety**: Proper database transaction handling
- **Connection Pooling**: Efficient database connection management

## Quick Start

### Local Development
```bash
# Navigate to directory
cd mcpservers/mcp_dbstore

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database (uncomment mcp-dbstore service in ../compose.yaml for full setup)
# -d flag runs PostgreSQL in background (detached mode)
podman-compose -f ../compose.yaml up -d postgresql

# Alternative: Start and see logs in real-time
# podman-compose -f ../compose.yaml up postgresql

# Database 'store_db' will be created automatically by PostgreSQL container

# Set database URL (optional, defaults work with compose setup)
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/store_db"

# Run the server
python store.py

# Test the server
curl http://localhost:8005/health  # Local port 8005 (maps to container port 8002)
```

### Podman Deployment
```bash
# Build container
podman build -t mcp-dbstore .

# Run with database
podman run -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://user:password@db:5432/store_db" \
  mcp-dbstore
```

### Kubernetes Deployment
```bash
# Deploy with Helm (configure critical options)
helm install mcp-dbstore ./helm \
  --set postgresql.auth.postgresPassword=yourpassword \
  --set postgresql.auth.database=store_db \
  --set image.repository=quay.io/ecosystem-appeng/mcp-dbstore \
  --set image.tag=latest

# Check status
kubectl get pods -l app.kubernetes.io/name=mcp-dbstore

# Test from cluster (port forward and curl)
kubectl port-forward svc/mcp-dbstore 8002:8002 &
curl http://localhost:8002/health
```

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_products` | List all products with pagination | `skip`, `limit` |
| `get_product_by_id` | Get specific product by ID | `product_id` |
| `get_product_by_name` | Get product by exact name | `name` |
| `search_products` | Search products by query | `query`, `skip`, `limit` |
| `add_product` | Create new product | `name`, `description`, `inventory`, `price` |
| `remove_product` | Delete product by ID | `product_id` |
| `order_product` | Place order (reduces inventory) | `product_id`, `quantity`, `customer_identifier` |

## Configuration

### Environment Variables
```bash
# Database connection
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"

# Server settings
MCP_PORT=8002
LOG_LEVEL=INFO
```

### Database Schema
The server automatically creates these tables:
- `products`: Product catalog with inventory
- `orders`: Order history and tracking

## Documentation

- **[Development Guide](DEVGUIDE.md)** - Setup, development, and testing
- **[User Guide](USERGUIDE.md)** - Usage examples and API reference

## Use Cases

### ✅ **Best For**
- Simple inventory management systems
- Direct database access requirements
- Minimal infrastructure complexity
- Development and testing environments
- Single-tenant applications

### ⚠️ **Consider Alternatives When**
- Multiple clients need API access
- Complex business logic is required
- Independent scaling is needed
- REST API access is required

## Performance

- **Throughput**: ~1000 requests/second (typical hardware)
- **Latency**: <10ms for simple queries
- **Memory Usage**: ~50MB base + connection pool
- **Database Connections**: Configurable pool size (default: 10)

## Support

For technical support and development:
- Review the [Development Guide](DEVGUIDE.md)
- Check the [User Guide](USERGUIDE.md) for usage examples
- See the main [MCP Servers documentation](../README.md)
