# MCP WebStore User Guide

This guide provides usage examples for both the MCP tools and REST API provided by MCP WebStore.

## Overview

MCP WebStore offers simultaneous deployment of the mcp server and the store api in a single step:
- **MCP Tools**: For AI agents via LlamaStack
- **REST API**: For web applications, mobile apps, and direct HTTP access

Both interfaces access the same data and business logic.

## Getting Started

### Start Both Services
```bash
# Terminal 1: Start Store API
cd mcpservers/mcp-store-api/store
uvicorn main:app --port 8001 --reload

# Terminal 2: Start MCP Server
cd mcpservers/mcp-store-api
STORE_SERVER_URL="http://localhost:8001" python webstore.py
```

### Verify Services
```bash
# Check API documentation
curl http://localhost:8001/docs

# Check API health
curl http://localhost:8001/health

# MCP server will be available on port 8001 (default)
```

## MCP Tools Usage

The MCP tools provide the same functionality as mcp-store-db but through API calls:

### Product Management
```python
# List products
products = await get_products(skip=0, limit=10)

# Search products
results = await search_products(query="laptop")

# Add product
new_product = await add_product(
    name="Gaming Mouse",
    description="RGB gaming mouse",
    inventory=50,
    price=79.99
)

# Get product by ID
product = await get_product_by_id(product_id=1)

# Remove product
removed = await remove_product(product_id=1)
```

### Order Processing
```python
# Place order
order = await order_product(
    product_id=1,
    quantity=2,
    customer_identifier="customer_123"
)
```

## REST API Usage

### Interactive Documentation
Visit `http://localhost:8001/docs` for interactive API documentation with try-it-out functionality.

### Product Endpoints

#### List Products
```bash
# Get all products
curl http://localhost:8001/products/

# With pagination
curl "http://localhost:8001/products/?skip=10&limit=5"
```

Response:
```json
[
  {
    "id": 1,
    "name": "Laptop",
    "description": "High-performance laptop",
    "inventory": 50,
    "price": 999.99
  }
]
```

#### Create Product
```bash
curl -X POST http://localhost:8001/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Keyboard",
    "description": "Bluetooth mechanical keyboard",
    "inventory": 25,
    "price": 129.99
  }'
```

#### Get Product by ID
```bash
curl http://localhost:8001/products/id/1
```

#### Get Product by Name
```bash
curl http://localhost:8001/products/name/Laptop
```

#### Search Products
```bash
# Search by query
curl "http://localhost:8001/products/search/?query=gaming"

# Search with pagination
curl "http://localhost:8001/products/search/?query=laptop&skip=0&limit=5"
```

#### Delete Product
```bash
curl -X DELETE http://localhost:8001/products/1
```

### Order Endpoints

#### Place Order
```bash
curl -X POST http://localhost:8001/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 3,
    "customer_identifier": "customer_456"
  }'
```

Response:
```json
{
  "id": 1,
  "product_id": 1,
  "quantity": 3,
  "customer_identifier": "customer_456"
}
```

## Integration Examples

### JavaScript/Web Application
```javascript
const API_BASE = 'http://localhost:8001';

class StoreAPI {
  async getProducts(skip = 0, limit = 100) {
    const response = await fetch(`${API_BASE}/products/?skip=${skip}&limit=${limit}`);
    return response.json();
  }

  async createProduct(product) {
    const response = await fetch(`${API_BASE}/products/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(product)
    });
    return response.json();
  }

  async searchProducts(query, skip = 0, limit = 100) {
    const response = await fetch(
      `${API_BASE}/products/search/?query=${encodeURIComponent(query)}&skip=${skip}&limit=${limit}`
    );
    return response.json();
  }

  async placeOrder(productId, quantity, customerId) {
    const response = await fetch(`${API_BASE}/orders/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: productId,
        quantity: quantity,
        customer_identifier: customerId
      })
    });
    return response.json();
  }
}

// Usage
const store = new StoreAPI();

// Load products
const products = await store.getProducts();
console.log('Products:', products);

// Create product
const newProduct = await store.createProduct({
  name: 'Wireless Headphones',
  description: 'Noise-cancelling headphones',
  inventory: 30,
  price: 199.99
});

// Place order
const order = await store.placeOrder(newProduct.id, 2, 'web_customer_123');
```

### Python Client
```python
import httpx
import asyncio

class StoreClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def get_products(self, skip=0, limit=100):
        response = await self.client.get(
            f"{self.base_url}/products/",
            params={"skip": skip, "limit": limit}
        )
        return response.json()

    async def create_product(self, name, description, inventory, price):
        response = await self.client.post(
            f"{self.base_url}/products/",
            json={
                "name": name,
                "description": description,
                "inventory": inventory,
                "price": price
            }
        )
        return response.json()

    async def place_order(self, product_id, quantity, customer_id):
        response = await self.client.post(
            f"{self.base_url}/orders/",
            json={
                "product_id": product_id,
                "quantity": quantity,
                "customer_identifier": customer_id
            }
        )
        return response.json()

# Usage
async def main():
    client = StoreClient()

    # Create product
    product = await client.create_product(
        name="Smart Watch",
        description="Fitness tracking smartwatch",
        inventory=75,
        price=299.99
    )
    print(f"Created product: {product}")

    # Place order
    order = await client.place_order(
        product_id=product["id"],
        quantity=1,
        customer_id="python_client_123"
    )
    print(f"Placed order: {order}")

asyncio.run(main())
```

## Dual Interface Workflow

### E-commerce Application Example

```mermaid
sequenceDiagram
    participant User
    participant WebApp
    participant API as Store API
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant DB as Database

    User->>WebApp: Browse products
    WebApp->>API: GET /products/
    API->>DB: Query products
    DB-->>API: Product data
    API-->>WebApp: JSON response
    WebApp-->>User: Display products

    User->>WebApp: Ask AI for recommendation
    WebApp->>Agent: "Recommend gaming products"
    Agent->>MCP: search_products("gaming")
    MCP->>API: GET /products/search/?query=gaming
    API->>DB: Search query
    DB-->>API: Gaming products
    API-->>MCP: JSON response
    MCP-->>Agent: MCP tool response
    Agent-->>WebApp: AI recommendation
    WebApp-->>User: Show recommendation
```

## Error Handling

### API Errors
```bash
# Product not found
curl http://localhost:8001/products/id/999
# Response: 404 Not Found

# Invalid data
curl -X POST http://localhost:8001/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": ""}'
# Response: 422 Validation Error
```

### MCP Error Propagation
MCP tools will receive API errors and handle them appropriately:
- HTTP 404 → Returns `None` for get operations
- HTTP 422 → Raises validation error
- HTTP 500 → Raises server error

## Monitoring Both Interfaces

### Health Checks
```bash
# API health
curl http://localhost:8001/health

# Database connectivity (through API)
curl http://localhost:8001/health | jq '.database'
```

### Performance Monitoring
- **API Metrics**: Available through FastAPI metrics
- **MCP Metrics**: Monitor through MCP server logs
- **Database**: Monitor connection pool usage

## Best Practices

### When to Use Each Interface

**Use MCP Tools when:**
- Building AI agent interactions
- Need LLM-friendly tool descriptions
- Working within LlamaStack ecosystem

**Use REST API when:**
- Building web/mobile applications
- Need standard HTTP integration
- Working with existing REST clients
- Need detailed API documentation

### Data Consistency
Both interfaces access the same database, ensuring:
- Real-time data consistency
- Shared business logic
- Unified validation rules
- Common error handling

## Configuration

### Environment Variables
```bash
# For MCP Server
STORE_SERVER_URL="http://localhost:8001"  # API endpoint

# For Store API
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"
```

### Production Deployment
Both components can be deployed together or separately:
- **Together**: Single Helm chart with both services
- **Separately**: Independent scaling and deployment

For advanced configuration and development, see the [Development Guide](dev-guide.md).
