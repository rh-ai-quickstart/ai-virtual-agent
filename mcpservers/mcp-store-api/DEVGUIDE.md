# MCP WebStore Development Guide

Development setup and contribution guide for the MCP WebStore hybrid server (MCP + REST API).

## Development Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Git
- Docker (optional)

### Local Environment Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository>
   cd mcpservers/mcp-store-api
   ```

2. **Install Dependencies**
   ```bash
   # MCP server dependencies
   pip install -r requirements.txt

   # Store API dependencies
   cd store
   pip install -r requirements.txt
   cd ..
   ```

3. **Database Setup**
   ```bash
   # Using podman compose (recommended)
   # Use the main compose.yaml file in the parent directory
   podman compose -f ../compose.yaml up -d postgresql

   # Verify database connection
   psql "postgresql://postgres:password@localhost:5432/store_db" -c "SELECT 1;"
   ```

4. **Run Both Components**
   ```bash
   # Terminal 1: Start Store API
   cd store
   uvicorn main:app --port 8001 --reload

   # Terminal 2: Start MCP Server
   cd ..
   STORE_SERVER_URL="http://localhost:8001" python webstore.py
   ```

## Project Structure

```
mcp-store-api/
├── webstore.py           # MCP server (calls Store API)
├── requirements.txt      # MCP server dependencies
├── Containerfile         # MCP server container
├── store/                # Store API component
│   ├── main.py          # FastAPI application
│   ├── models.py        # Pydantic models
│   ├── database.py      # SQLAlchemy models
│   ├── crud.py          # Database operations
│   ├── requirements.txt # API dependencies
│   └── Containerfile    # API container
└── helm/                # Helm chart (deploys both)
```

## Development Workflow

### Running Components

```bash
# Development with auto-reload
# Terminal 1: API server
cd store && uvicorn main:app --port 8001 --reload

# Terminal 2: MCP server
STORE_SERVER_URL="http://localhost:8001" python webstore.py

# Check both services
curl http://localhost:8001/health  # API health
curl http://localhost:8001/docs    # API documentation
# MCP server runs on port 8001 (default)

# Add to LlamaStack
llamastack mcp-server add \
  --name mcp-webstore \
  --url http://localhost:8001 \
  --description "MCP server with store API"
```

### Testing Both Components

```bash
# Test Store API
cd store
pytest tests/ -v

# Test MCP integration
cd ..
python -c "
import asyncio
from webstore import get_products
print(asyncio.run(get_products()))
"
```

## Architecture Details

### Component Communication

```mermaid
sequenceDiagram
    participant Agent
    participant MCP as MCP Server
    participant API as Store API
    participant DB as Database

    Agent->>MCP: get_products()
    MCP->>API: GET /products/
    API->>DB: SELECT * FROM products
    DB-->>API: Product data
    API-->>MCP: JSON response
    MCP-->>Agent: MCP tool response

    Note over MCP,API: HTTP communication
    Note over API,DB: Direct database access
```

### Data Flow
1. **MCP Path**: Agent → MCP Server → HTTP → Store API → Database
2. **API Path**: Client → Store API → Database

## Adding New Features

### Adding MCP Tool + API Endpoint

1. **Add API Endpoint** (in `store/main.py`)
   ```python
   @app.get("/new-endpoint/")
   async def new_endpoint(db: AsyncSession = Depends(database.get_db)):
       # Implementation
       return result
   ```

2. **Add MCP Tool** (in `webstore.py`)
   ```python
   @mcp_server.tool()
   async def new_mcp_tool() -> Dict[str, Any]:
       """Tool description for LLM."""
       return await make_api_request("GET", "/new-endpoint/")
   ```

3. **Add Tests**
   ```python
   # Test API endpoint
   def test_new_endpoint(client):
       response = client.get("/new-endpoint/")
       assert response.status_code == 200

   # Test MCP tool
   async def test_new_mcp_tool():
       result = await new_mcp_tool()
       assert result is not None
   ```

## Container Development

### Building Both Images
```bash
# Build MCP server container
docker build -t mcp-webstore .

# Build Store API container
docker build -t mcp-webstore-api ./store

# Test with docker-compose
cat > docker-compose.dev.yml << EOF
services:
  store-api:
    build: ./store
    ports: ["8001:8001"]
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@db:5432/store_db
    depends_on: [db]

  mcp-server:
    build: .
    ports: ["8002:8002"]
    environment:
      STORE_SERVER_URL: http://store-api:8001
    depends_on: [store-api]

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: store_db
EOF

docker-compose -f docker-compose.dev.yml up
```

## Testing Strategy

### Unit Tests
- Test Store API endpoints independently
- Test MCP tool functions with mocked API responses
- Test database operations

### Integration Tests
- Test MCP → API → Database flow
- Test concurrent access patterns
- Test error propagation

### Example Test Setup
```python
# Test Store API
import pytest
from fastapi.testclient import TestClient
from store.main import app

client = TestClient(app)

def test_get_products():
    response = client.get("/products/")
    assert response.status_code == 200

# Test MCP integration with API
import httpx
import pytest_asyncio
from unittest.mock import patch

@pytest_asyncio.fixture
async def mock_api():
    with patch('webstore.async_client') as mock:
        mock.get.return_value.json.return_value = [{"id": 1}]
        yield mock

async def test_mcp_get_products(mock_api):
    from webstore import get_products
    result = await get_products()
    assert len(result) > 0
```

## Debugging

### Common Issues

1. **API Connection Errors**
   ```bash
   # Check if Store API is running
   curl http://localhost:8001/health

   # Check MCP server logs
   STORE_SERVER_URL="http://localhost:8001" python webstore.py
   ```

2. **Database Connection Issues**
   ```bash
   # Test database from Store API
   cd store
   python -c "
   import asyncio
   from database import create_db_and_tables
   asyncio.run(create_db_and_tables())
   "
   ```

3. **Port Conflicts**
   ```bash
   # Check what's using ports
   lsof -i :8001
   lsof -i :8002

   # Use different ports
   cd store && uvicorn main:app --port 8011
   STORE_SERVER_URL="http://localhost:8011" python webstore.py
   ```

## Helm Chart Development

### Testing Chart
```bash
# Lint chart
helm lint ./helm

# Template rendering
helm template test-release ./helm

# Install with development values
helm install mcp-webstore-dev ./helm \
  --set mcpServer.image.tag=dev \
  --set storeApi.image.tag=dev
```

### Chart Structure
The Helm chart deploys both components:
- MCP Server deployment
- Store API deployment
- Shared PostgreSQL database
- Services for both components

## Performance Optimization

### API Performance
- Use database connection pooling
- Implement response caching
- Optimize database queries
- Monitor API response times

### MCP Performance
- Reuse HTTP connections
- Implement request batching where possible
- Cache frequently accessed data
- Monitor MCP tool response times

## Contributing

### Code Style
- Follow FastAPI best practices for API code
- Use async/await consistently
- Add comprehensive docstrings
- Include type hints

### Pull Request Process
1. Test both MCP and API components
2. Update documentation for both interfaces
3. Ensure Helm chart works correctly
4. Add integration tests if needed

This guide covers the unique aspects of developing the hybrid MCP WebStore architecture.
