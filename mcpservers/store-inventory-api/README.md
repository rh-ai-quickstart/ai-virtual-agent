# Store Inventory API

A standalone FastAPI service for inventory management, designed to work with MCP servers and other clients. This service provides RESTful endpoints for product and order operations with full OpenAPI documentation.

## Overview

Store Inventory API is a dedicated inventory management service that can serve multiple clients including MCP servers, web applications, and mobile apps. It provides a clean REST interface with comprehensive business logic for product and order management.

## Architecture

```mermaid
graph TB
    subgraph "Client Applications"
        MCP[MCP Servers]
        Web[Web Applications]
        Mobile[Mobile Apps]
        CLI[CLI Tools]
    end

    subgraph "Store Inventory API"
        API[FastAPI Server<br/>Port 8002]
        Logic[Business Logic]
        CRUD[CRUD Operations]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL<br/>Database)]
    end

    MCP --> API
    Web --> API
    Mobile --> API
    CLI --> API

    API --> Logic
    Logic --> CRUD
    CRUD --> DB

    style API fill:#e8f5e9
    style DB fill:#f3e5f5
```

**Port Information:**
- **Container Port**: 8002 (internal service port)
- **Local Development**: 8002 (when using compose.yaml)
- **Kubernetes**: 8002 (standard deployment)

## Features

### 🌐 **REST API**
- **OpenAPI/Swagger**: Interactive documentation at `/docs`
- **JSON API**: Standard REST endpoints with JSON payloads
- **Validation**: Request/response validation with Pydantic
- **Error Handling**: Consistent error responses

### 🔧 **Business Logic**
- **Inventory Management**: Track stock levels automatically
- **Order Processing**: Handle orders with inventory validation
- **Search Capabilities**: Full-text search across products
- **Data Integrity**: Database constraints and validation

### 📊 **Monitoring & Health**
- **Health Checks**: `/health` endpoint for monitoring
- **Database Status**: Connection health verification
- **Metrics Ready**: Structured for observability tools
- **Logging**: Comprehensive request/error logging

## Quick Start

### Local Development
```bash
# Navigate to directory
cd mcpservers/store-inventory-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database (uncomment store-inventory-api service in ../compose.yaml for full setup)
podman compose -f ../compose.yaml up -d postgresql
# Database 'store_db' will be created automatically by PostgreSQL container

# Set database URL (optional, defaults work with compose setup)
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/store_db"

# Run the API server
uvicorn main:app --port 8002 --reload

# Test the API
curl http://localhost:8002/health
curl http://localhost:8002/docs  # Interactive documentation
```

### Podman Deployment
```bash
# Build container
podman build -t store-inventory-api .

# Run with database
podman run -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://user:password@db:5432/store_db" \
  store-inventory-api
```

### Kubernetes Deployment
```bash
# Deploy with Helm (configure critical options)
helm install store-inventory-api ./helm \
  --set postgresql.auth.postgresPassword=yourpassword \
  --set postgresql.auth.database=store_db \
  --set image.repository=quay.io/ecosystem-appeng/store-inventory-api \
  --set image.tag=latest

# Check status
kubectl get pods -l app.kubernetes.io/name=store-inventory-api

# Test from cluster (port forward and curl)
kubectl port-forward svc/store-inventory-api 8002:8002 &
curl http://localhost:8002/health
curl http://localhost:8002/docs
```

## API Endpoints

### Product Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/products/` | List products with pagination |
| `POST` | `/products/` | Create new product |
| `GET` | `/products/id/{product_id}` | Get product by ID |
| `GET` | `/products/name/{product_name}` | Get product by name |
| `GET` | `/products/search/?query={q}` | Search products |
| `DELETE` | `/products/{product_id}` | Delete product |

### Order Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/orders/` | Place order (reduces inventory) |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check endpoint |
| `GET` | `/docs` | Interactive API documentation |
| `GET` | `/redoc` | Alternative API documentation |

## Data Models

### Product Model
```json
{
  "id": 1,
  "name": "Product Name",
  "description": "Product description",
  "inventory": 100,
  "price": 29.99
}
```

### Order Model
```json
{
  "id": 1,
  "product_id": 1,
  "quantity": 5,
  "customer_identifier": "customer_123"
}
```

## Configuration

### Environment Variables
```bash
# Database connection
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"

# Server settings
API_PORT=8002
LOG_LEVEL=INFO
MAX_CONNECTIONS=20

# Optional: Database pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Database Schema
Automatically creates tables on startup:
- `products`: Product catalog with inventory tracking
- `orders`: Order history and customer information

## Documentation

- **[Development Guide](DEVGUIDE.md)** - Setup, development, and testing
- **[User Guide](USERGUIDE.md)** - API usage and examples
- **[Interactive Docs](http://localhost:8002/docs)** - When running locally

## Use Cases

### ✅ **Best For**
- Microservices architectures
- Multi-client inventory systems
- API-first development
- Independent service scaling
- Integration with various frontends
- Mobile app backends

### ⚠️ **Consider Alternatives When**
- Only MCP access is needed (use mcp-store-db)
- If simultaneous deployment of an mcp server is preferred (use mcp-store-api)
- Minimal complexity is required

## Integration Patterns

### **With MCP Servers**
```mermaid
sequenceDiagram
    participant MCP as MCP Server
    participant API as Store Inventory API
    participant DB as Database

    MCP->>API: GET /products/
    API->>DB: SELECT * FROM products
    DB-->>API: Product data
    API-->>MCP: JSON response
    MCP-->>MCP: Convert to MCP format
```

### **With Web Applications**
```javascript
// Frontend integration example
const api = 'http://localhost:8002';

// Get products
const products = await fetch(`${api}/products/`).then(r => r.json());

// Create product
const newProduct = await fetch(`${api}/products/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'New Product',
    description: 'Product description',
    inventory: 100,
    price: 29.99
  })
}).then(r => r.json());
```

## Performance

- **Throughput**: ~1500 requests/second
- **Latency**: <8ms for simple queries
- **Memory Usage**: ~60MB base + connection pool
- **Database Connections**: Configurable pool (default: 10)
- **Concurrent Requests**: Up to 100 concurrent connections

## Monitoring

### Health Check Response
```json
{
  "status": "healthy",
  "service": "store-inventory-api",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Metrics Available
- Request count and latency by endpoint
- Database connection pool utilization
- Error rates by status code
- Active connections and response times

## Security

### Best Practices Implemented
- **Input Validation**: All inputs validated with Pydantic
- **SQL Injection Prevention**: Using SQLAlchemy ORM
- **Error Sanitization**: No sensitive data in error responses
- **Connection Security**: Secure database connections

### Additional Security (Recommended)
- **Authentication**: Add JWT or API key authentication
- **Rate Limiting**: Implement request rate limiting
- **HTTPS**: Use TLS in production
- **Network Security**: Firewall and network policies

## Deployment Considerations

### **Production Checklist**
- [ ] Configure production database
- [ ] Set up connection pooling
- [ ] Enable logging and monitoring
- [ ] Configure health checks
- [ ] Set up backup strategies
- [ ] Implement security measures

### **Scaling Options**
- **Horizontal**: Multiple API instances with load balancer
- **Vertical**: Increase container resources
- **Database**: Read replicas for read-heavy workloads
- **Caching**: Redis for frequently accessed data

## Support

For technical support and development:
- Review the [Development Guide](DEVGUIDE.md)
- Check the [User Guide](USERGUIDE.md) for API usage
- Access interactive docs at `/docs` when running
- See the main [MCP Servers documentation](../README.md)
