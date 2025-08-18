# Store Inventory API Development Guide

Development setup for the standalone FastAPI inventory management service.

## Development Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Git

### Local Environment Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository>
   cd mcpservers/store-inventory-api
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**
   ```bash
   # Using podman compose (recommended)
podman compose -f ../compose.yaml up -d postgresql
   # Database 'store_db' will be created automatically

   # Or manually (if not using compose):
   # First start PostgreSQL, then create database:
   psql -h localhost -U postgres -c "CREATE DATABASE store_db;"

   export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/store_db"
   ```

4. **Run the API**
   ```bash
   uvicorn main:app --port 8002 --reload
   ```

5. **Verify Installation**
   ```bash
   curl http://localhost:8002/health
   curl http://localhost:8002/docs  # Interactive documentation
   ```

## Project Structure

```
store-inventory-api/
├── main.py               # FastAPI application
├── models.py             # Pydantic data models
├── database.py           # SQLAlchemy database models
├── crud.py               # Database operations
├── requirements.txt      # Python dependencies
├── Containerfile         # Container build instructions
├── populate_db.sql       # Sample data
└── helm/                 # Kubernetes deployment
```

## Development Workflow

### Running with Auto-Reload
```bash
# Development server with auto-reload
uvicorn main:app --port 8002 --reload --log-level debug

# Custom host and port
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# With environment variables
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/testdb" \
uvicorn main:app --port 8002 --reload
```

### Database Operations

```bash
# Reset database
python -c "
import asyncio
from database import create_db_and_tables
asyncio.run(create_db_and_tables())
"

# Populate with sample data
psql $DATABASE_URL -f populate_db.sql

# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM products;"
```

### Interactive API Testing
```bash
# Open interactive docs
open http://localhost:8002/docs

# Test endpoints with curl
curl http://localhost:8002/products/
curl -X POST http://localhost:8002/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Product", "price": 10.0, "inventory": 5}'
```

## Architecture Details

### FastAPI Application Structure

```mermaid
graph TB
    subgraph "FastAPI App"
        Router[API Routes]
        Middleware[Middleware Stack]
        Validation[Pydantic Validation]
    end

    subgraph "Business Layer"
        CRUD[CRUD Operations]
        Models[Data Models]
    end

    subgraph "Data Layer"
        DB[SQLAlchemy ORM]
        Pool[Connection Pool]
        PG[(PostgreSQL)]
    end

    Router --> Validation
    Validation --> CRUD
    CRUD --> Models
    Models --> DB
    DB --> Pool
    Pool --> PG
```

### Database Schema
```sql
-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description TEXT,
    inventory INTEGER DEFAULT 0,
    price NUMERIC(10,2) NOT NULL DEFAULT 0.00
);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    customer_identifier VARCHAR NOT NULL
);
```

## Adding New Features

### Adding New API Endpoint

1. **Add Route** (in `main.py`)
   ```python
   @app.get("/products/categories/")
   async def get_product_categories(db: AsyncSession = Depends(database.get_db)):
       """Get all unique product categories."""
       categories = await crud.get_product_categories(db)
       return categories
   ```

2. **Add CRUD Operation** (in `crud.py`)
   ```python
   async def get_product_categories(db: AsyncSession) -> List[str]:
       """Get distinct product categories."""
       result = await db.execute(
           select(database.ProductDB.category).distinct()
       )
       return [row[0] for row in result.fetchall()]
   ```

3. **Update Database Model** (if needed, in `database.py`)
   ```python
   class ProductDB(Base):
       # ... existing fields
       category = Column(String, nullable=True)  # New field
   ```

4. **Update Pydantic Models** (in `models.py`)
   ```python
   class ProductBase(BaseModel):
       # ... existing fields
       category: Optional[str] = None  # New field
   ```

5. **Add Tests**
   ```python
   def test_get_product_categories(client):
       response = client.get("/products/categories/")
       assert response.status_code == 200
       assert isinstance(response.json(), list)
   ```

### Database Migrations

If using Alembic for migrations:
```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add category to products"

# Apply migration
alembic upgrade head
```

## Testing Strategy

### Unit Tests
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from main import app

client = TestClient(app)

def test_create_product():
    response = client.post("/products/", json={
        "name": "Test Product",
        "description": "A test product",
        "inventory": 10,
        "price": 99.99
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["price"] == 99.99

def test_get_products():
    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Integration Tests with Database
```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from database import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_crud_operations(test_db):
    from crud import add_product, get_products
    from models import ProductCreate

    # Create product
    product_data = ProductCreate(name="Test", inventory=5, price=10.0)
    product = await add_product(test_db, product_data)
    assert product.name == "Test"

    # Get products
    products = await get_products(test_db)
    assert len(products) == 1
```

### Performance Tests
```python
import asyncio
import time
import httpx

async def load_test():
    """Simple load test for API endpoints."""
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        tasks = []

        # Create 100 concurrent requests
        for i in range(100):
            task = client.get("http://localhost:8002/products/")
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        success_count = sum(1 for r in responses if r.status_code == 200)
        print(f"Completed {success_count}/100 requests in {end_time - start_time:.2f}s")

# Run load test
asyncio.run(load_test())
```

## Container Development

### Building and Testing
```bash
# Build container
docker build -t store-inventory-api:dev .

# Run with environment
docker run --rm -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:password@host.docker.internal:5432/store_db" \
  store-inventory-api:dev

# Test container health
curl http://localhost:8002/health
```

### Multi-stage Build Optimization
The Containerfile uses multi-stage builds:
```dockerfile
# Builder stage - installs dependencies
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y gcc libpq-dev
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# Final stage - runtime only
FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /home/apiuser/.local
# ... rest of configuration
```

## Debugging

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Test database connectivity
   psql $DATABASE_URL -c "SELECT 1;"

   # Check connection string format
   echo $DATABASE_URL
   # Should be: postgresql+asyncpg://user:password@host:port/database
   ```

2. **Import Errors**
   ```python
   # If you get import errors, check Python path
   import sys
   print(sys.path)

   # Ensure you're in the right directory
   pwd  # Should be in store-inventory/
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using port 8002
   lsof -i :8002

   # Use different port
   uvicorn main:app --port 8003
   ```

### Debug Mode
```python
# Add to main.py for detailed debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable SQL query logging
engine = create_async_engine(DATABASE_URL, echo=True)
```

### API Debugging
```bash
# Enable debug logging
LOG_LEVEL=DEBUG uvicorn main:app --port 8002 --reload

# Test specific endpoints
curl -v http://localhost:8002/products/
curl -X POST -v http://localhost:8002/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Debug Product", "inventory": 1, "price": 1.0}'
```

## Performance Optimization

### Database Optimization
```python
# Optimize connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=300
)

# Add database indexes
# In database.py
class ProductDB(Base):
    name = Column(String, index=True, unique=True)  # Index for searches
    price = Column(Numeric(10, 2), index=True)      # Index for price queries
```

### API Performance
```python
# Add response caching
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@app.get("/products/")
@cache(expire=60)  # Cache for 60 seconds
async def read_products():
    # ... implementation
```

### Monitoring
```python
# Add metrics middleware
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Metrics available at /metrics
```

## Helm Chart Development

### Local Testing
```bash
# Lint chart
helm lint ./helm

# Template rendering
helm template test-release ./helm

# Install with custom values
helm install store-inventory-api-dev ./helm \
  --set image.tag=dev \
  --set postgresql.auth.postgresPassword=devpass

### Custom Values
```yaml
# values-dev.yaml
image:
  repository: store-inventory-api
  tag: dev
  pullPolicy: Never

postgresql:
  auth:
    postgresPassword: devpassword
  primary:
    persistence:
      enabled: false  # For development

resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "500m"
```

## Contributing

### Code Style
- Follow FastAPI best practices
- Use async/await consistently
- Add type hints to all functions
- Include comprehensive docstrings
- Use Pydantic models for validation

### API Design Principles
- RESTful endpoint design
- Consistent error responses
- Proper HTTP status codes
- Clear request/response models
- Comprehensive OpenAPI documentation

### Pull Request Process
1. Add tests for new functionality
2. Update API documentation
3. Ensure all tests pass
4. Update Helm chart if needed
5. Test container builds successfully

This development guide covers the FastAPI-specific aspects of building the Store Inventory API service.
