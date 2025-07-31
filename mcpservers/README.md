# Model Context Protocol (MCP) Servers

Model Context Protocol (MCP) servers provide external tool capabilities to AI agents in the AI Virtual Agent Kickstart. These servers implement standardized interfaces that allow agents to access external data sources and perform complex operations.

## Overview

MCP (Model Context Protocol) is a standard for connecting AI agents to external tools and data sources. In our platform, MCP servers act as bridges between LlamaStack agents and external services, providing capabilities beyond the built-in tools.

## Architecture

```mermaid
graph TD
    subgraph "AI Virtual Agent Kickstart"
        AGENT[LlamaStack Agent]
        LLAMA[LlamaStack Platform]
    end

    subgraph "MCP Server Ecosystem"
        MCPDB[MCP DB Store Server<br/>• Product Database<br/>• Order Management]
        MCPWEB[MCP Web Store Server<br/>• HTTP API Client<br/>• Store Integration]
    end

    subgraph "External Systems"
        STORE[Store API Server<br/>• REST API<br/>• Business Logic]
        DB[(PostgreSQL<br/>Store Database)]
    end

    AGENT --> LLAMA
    LLAMA --> MCPDB
    LLAMA --> MCPWEB
    MCPDB --> DB
    MCPWEB --> STORE
    STORE --> DB
```

## Available MCP Servers

### 1. MCP DB Store Server (`mcp_dbstore/`)

**Purpose**: Direct database access for product and order management
**Protocol**: Database-first approach with direct SQL operations

**Key Features**:
- **Product Management**: Create, read, update, delete products
- **Order Processing**: Handle customer orders and fulfillment
- **Inventory Tracking**: Monitor stock levels and availability
- **Direct Database Access**: Efficient operations through SQLAlchemy

**Available Tools**:
```python
@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]

@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Dict[str, Any]

@mcp_server.tool()
async def create_product(name: str, description: str, price: float, inventory_count: int) -> Dict[str, Any]

@mcp_server.tool()
async def create_order(product_id: int, quantity: int, customer_identifier: str) -> Dict[str, Any]
```

**Database Schema**:
```sql
-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    inventory_count INTEGER DEFAULT 0
);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    customer_identifier VARCHAR NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) CALCULATED
);
```

### 2. MCP Web Store Server (`mcp_webstore/`)

**Purpose**: HTTP API client for external store systems
**Protocol**: RESTful API integration with external services

**Key Features**:
- **API Integration**: Connect to external e-commerce platforms
- **HTTP Client Management**: Async HTTP operations with connection pooling
- **Error Handling**: Robust error management for network operations
- **Flexible Endpoints**: Configurable store server URLs

**Available Tools**:
```python
@mcp_server.tool()
async def get_products() -> List[Dict[str, Any]]

@mcp_server.tool()
async def get_product_details(product_id: int) -> Dict[str, Any]

@mcp_server.tool()
async def place_order(product_id: int, quantity: int, customer_info: Dict) -> Dict[str, Any]
```

**Configuration**:
```bash
# Environment variables
STORE_SERVER_URL=http://localhost:8001  # External store API endpoint
```

## Development Guide

### Creating a New MCP Server

1. **Project Structure**:
   ```
   mcpservers/
   └── mcp_newserver/
       ├── __init__.py
       ├── server.py          # Main MCP server implementation
       ├── models.py          # Pydantic models (optional)
       ├── database.py        # Database setup (if needed)
       ├── requirements.txt   # Python dependencies
       └── Containerfile      # Container configuration
   ```

2. **Basic Server Implementation**:
   ```python
   # server.py
   from mcp.server.fastmcp import FastMCP
   from typing import Dict, Any

   # Initialize MCP server
   mcp_server = FastMCP()

   @mcp_server.tool()
   async def my_tool(param1: str, param2: int = 10) -> Dict[str, Any]:
       """
       Tool description for the AI agent.

       Args:
           param1: Description of first parameter
           param2: Description of second parameter

       Returns:
           Dictionary with operation results
       """
       # Implement tool logic
       result = perform_operation(param1, param2)
       return {"status": "success", "data": result}

   # Additional tools...

   if __name__ == "__main__":
       # Server startup logic
       mcp_server.run()
   ```

3. **Database Integration** (if needed):
   ```python
   # database.py
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker, declarative_base
   import os

   DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://...")

   engine = create_async_engine(DATABASE_URL, echo=False)
   AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession)
   Base = declarative_base()

   # Database models
   class MyModel(Base):
       __tablename__ = "my_table"
       # ... table definition
   ```

4. **Container Configuration**:
   ```dockerfile
   # Containerfile
   FROM python:3.10-slim

   WORKDIR /app
   COPY ./mcpservers/mcp_newserver/ /app/mcpservers/mcp_newserver/

   ENV PYTHONPATH=/app

   COPY ./mcpservers/mcp_newserver/requirements.txt /app/requirements.txt
   RUN pip install --no-cache-dir -r requirements.txt

   CMD ["python", "-m", "mcpservers.mcp_newserver.server"]
   ```

### Tool Design Patterns

#### 1. CRUD Operations
```python
@mcp_server.tool()
async def create_resource(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new resource"""
    # Validation
    # Database operation
    # Return result

@mcp_server.tool()
async def get_resource(resource_id: int) -> Dict[str, Any]:
    """Retrieve a resource by ID"""
    # Database query
    # Format response

@mcp_server.tool()
async def update_resource(resource_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing resource"""
    # Validation
    # Database update
    # Return updated resource

@mcp_server.tool()
async def delete_resource(resource_id: int) -> Dict[str, Any]:
    """Delete a resource"""
    # Existence check
    # Database deletion
    # Return confirmation
```

#### 2. Search and Filtering
```python
@mcp_server.tool()
async def search_resources(
    query: str = "",
    filters: Dict[str, Any] = None,
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """Search resources with filters and pagination"""
    # Build query
    # Apply filters
    # Return paginated results
```

#### 3. External API Integration
```python
@mcp_server.tool()
async def call_external_api(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make calls to external APIs"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/{endpoint}", params=params)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

### Error Handling Best Practices

```python
@mcp_server.tool()
async def robust_operation(param: str) -> Dict[str, Any]:
    """Example of robust error handling"""
    try:
        # Validate input
        if not param or len(param.strip()) == 0:
            return {
                "status": "error",
                "error_type": "validation",
                "message": "Parameter cannot be empty"
            }

        # Perform operation
        result = await perform_complex_operation(param)

        return {
            "status": "success",
            "data": result,
            "metadata": {"timestamp": datetime.now().isoformat()}
        }

    except ValidationError as e:
        return {
            "status": "error",
            "error_type": "validation",
            "message": f"Invalid input: {str(e)}"
        }
    except ConnectionError as e:
        return {
            "status": "error",
            "error_type": "connection",
            "message": "Failed to connect to external service",
            "details": str(e)
        }
    except Exception as e:
        # Log error for debugging
        logger.error(f"Unexpected error in robust_operation: {str(e)}")
        return {
            "status": "error",
            "error_type": "internal",
            "message": "An unexpected error occurred"
        }
```

## Deployment

### Local Development

1. **Set up environment**:
   ```bash
   cd mcpservers/mcp_dbstore
   pip install -r requirements.txt
   ```

2. **Configure database**:
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/store_db"
   ```

3. **Run the server**:
   ```bash
   python -m mcpservers.mcp_dbstore.store
   ```

### Container Deployment

1. **Build container**:
   ```bash
   podman build -f mcpservers/mcp_dbstore/Containerfile -t mcp-dbstore:latest .
   ```

2. **Run container**:
   ```bash
   podman run -d \
     -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/store_db" \
     -p 8003:8003 \
     mcp-dbstore:latest
   ```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-dbstore
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-dbstore
  template:
    metadata:
      labels:
        app: mcp-dbstore
    spec:
      containers:
      - name: mcp-dbstore
        image: mcp-dbstore:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: connection-string
        ports:
        - containerPort: 8003
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-dbstore-service
spec:
  selector:
    app: mcp-dbstore
  ports:
  - port: 8003
    targetPort: 8003
```

## Integration with LlamaStack

### Tool Registration

MCP servers are automatically discovered and registered with LlamaStack through the tool system:

1. **Server Discovery**: LlamaStack queries available MCP servers
2. **Tool Registration**: Each `@mcp_server.tool()` becomes available to agents
3. **Agent Configuration**: Agents can be configured to use specific MCP server tools

### Agent Usage Example

```python
# Agent configuration with MCP tools
agent_config = {
    "name": "Store Assistant",
    "model": "llama3.1-8b-instruct",
    "instructions": "You are a helpful store assistant with access to product and order systems.",
    "tools": [
        "mcp-dbstore::get_products",
        "mcp-dbstore::create_order",
        "mcp-webstore::get_product_details"
    ]
}
```

### Chat Integration

When an agent uses MCP tools, the conversation flow includes tool calls:

```
User: "What products do you have available?"

Agent: Let me check our current inventory.
[Tool Call: mcp-dbstore::get_products]
[Tool Result: {"status": "success", "data": [...]}]

Based on our current inventory, we have the following products available:
1. Widget A - $29.99 (15 in stock)
2. Widget B - $39.99 (8 in stock)
...
```

## Testing

### Unit Testing

```python
# tests/test_mcp_tools.py
import pytest
from mcpservers.mcp_dbstore.store import get_products, create_product

@pytest.mark.asyncio
async def test_get_products():
    """Test product retrieval"""
    result = await get_products(limit=5)
    assert result["status"] == "success"
    assert len(result["data"]) <= 5

@pytest.mark.asyncio
async def test_create_product():
    """Test product creation"""
    result = await create_product(
        name="Test Product",
        description="Test Description",
        price=19.99,
        inventory_count=10
    )
    assert result["status"] == "success"
    assert result["data"]["name"] == "Test Product"
```

### Integration Testing

```python
# Test MCP server integration with LlamaStack
async def test_mcp_integration():
    """Test that MCP tools work with LlamaStack agents"""
    # Create agent with MCP tools
    agent_config = {...}
    agent = await llamastack_client.agents.create(agent_config)

    # Send message that requires MCP tool usage
    response = await agent.chat("Show me available products")

    # Verify tool was called and response includes product data
    assert "products" in response.content.lower()
```

## Monitoring and Logging

### Logging Configuration

```python
import logging

# Configure logging for MCP server
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@mcp_server.tool()
async def logged_operation(param: str) -> Dict[str, Any]:
    """Operation with comprehensive logging"""
    logger.info(f"Starting operation with param: {param}")

    try:
        result = await perform_operation(param)
        logger.info(f"Operation completed successfully")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        raise
```

### Health Checks

```python
@mcp_server.tool()
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring"""
    try:
        # Check database connectivity
        async with AsyncSessionLocal() as db:
            await db.execute("SELECT 1")

        # Check external service connectivity (if applicable)
        # ...

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "database": "ok",
                "external_service": "ok"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

## Troubleshooting

### Common Issues

**MCP server not connecting:**
```bash
# Check server is running
curl http://localhost:8003/health

# Verify environment variables
echo $DATABASE_URL

# Check logs
docker logs mcp-server-container
```

**Tool registration issues:**
- Verify `@mcp_server.tool()` decorator is used correctly
- Check function signatures match expected types
- Ensure server is discoverable by LlamaStack

**Database connection problems:**
- Verify DATABASE_URL format: `postgresql+asyncpg://user:pass@host:port/db`
- Check database server accessibility
- Verify credentials and permissions

**Performance issues:**
- Monitor database query performance
- Check for connection pool exhaustion
- Review async operation patterns
