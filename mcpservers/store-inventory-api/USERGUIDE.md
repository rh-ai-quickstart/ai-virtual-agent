# Store Inventory API User Guide

Complete usage guide for the standalone FastAPI inventory management service.

## Overview

Store Inventory API provides RESTful endpoints for managing product inventory and orders. It's designed to work with MCP servers, web applications, mobile apps, and any HTTP client.

## Getting Started

### Quick Start
```bash
# Navigate to directory
cd mcpservers/store-inventory-api

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn main:app --port 8002 --reload

# Verify it's running
curl http://localhost:8002/health
```

### Interactive Documentation
Visit `http://localhost:8002/docs` for interactive API documentation with try-it-out functionality.

## API Reference

### Base URL
- **Development**: `http://localhost:8002`
- **Production**: Your deployed endpoint

### Authentication
Currently no authentication required. Add authentication as needed for your environment.

## Endpoints

### System Endpoints

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "store-inventory",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Product Management

#### List Products
```http
GET /products/?skip=0&limit=100
```

**Parameters:**
- `skip` (int, optional): Number of products to skip (default: 0)
- `limit` (int, optional): Maximum products to return (default: 100)

**Example:**
```bash
# Get all products
curl http://localhost:8002/products/

# Get products with pagination
curl "http://localhost:8002/products/?skip=10&limit=5"
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Gaming Laptop",
    "description": "High-performance gaming laptop",
    "inventory": 15,
    "price": 1299.99
  },
  {
    "id": 2,
    "name": "Wireless Mouse",
    "description": "Ergonomic wireless mouse",
    "inventory": 50,
    "price": 29.99
  }
]
```

#### Create Product
```http
POST /products/
```

**Request Body:**
```json
{
  "name": "Product Name",
  "description": "Product description",
  "inventory": 100,
  "price": 49.99
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mechanical Keyboard",
    "description": "RGB mechanical gaming keyboard",
    "inventory": 25,
    "price": 149.99
  }'
```

**Response:**
```json
{
  "id": 3,
  "name": "Mechanical Keyboard",
  "description": "RGB mechanical gaming keyboard",
  "inventory": 25,
  "price": 149.99
}
```

#### Get Product by ID
```http
GET /products/id/{product_id}
```

**Example:**
```bash
curl http://localhost:8002/products/id/1
```

**Response:**
```json
{
  "id": 1,
  "name": "Gaming Laptop",
  "description": "High-performance gaming laptop",
  "inventory": 15,
  "price": 1299.99
}
```

#### Get Product by Name
```http
GET /products/name/{product_name}
```

**Example:**
```bash
curl http://localhost:8002/products/name/Gaming%20Laptop
```

#### Search Products
```http
GET /products/search/?query={search_term}&skip=0&limit=100
```

**Parameters:**
- `query` (str): Search term to match against name and description
- `skip` (int, optional): Pagination offset
- `limit` (int, optional): Maximum results

**Example:**
```bash
# Search for gaming products
curl "http://localhost:8002/products/search/?query=gaming"

# Search with pagination
curl "http://localhost:8002/products/search/?query=mouse&skip=0&limit=5"
```

#### Delete Product
```http
DELETE /products/{product_id}
```

**Example:**
```bash
curl -X DELETE http://localhost:8002/products/3
```

**Response:**
```json
{
  "id": 3,
  "name": "Mechanical Keyboard",
  "description": "RGB mechanical gaming keyboard",
  "inventory": 25,
  "price": 149.99
}
```

### Order Management

#### Place Order
```http
POST /orders/
```

**Request Body:**
```json
{
  "product_id": 1,
  "quantity": 2,
  "customer_identifier": "customer_123"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2,
    "customer_identifier": "john_doe"
  }'
```

**Response:**
```json
{
  "id": 1,
  "product_id": 1,
  "quantity": 2,
  "customer_identifier": "john_doe"
}
```

**Note:** This operation automatically reduces the product's inventory by the ordered quantity.

## Data Models

### Product Model
```json
{
  "id": 1,                    // Auto-generated unique ID
  "name": "Product Name",     // Required, must be unique
  "description": "...",       // Optional description
  "inventory": 100,           // Stock quantity (default: 0)
  "price": 29.99             // Product price (default: 0.0)
}
```

### Order Model
```json
{
  "id": 1,                           // Auto-generated unique ID
  "product_id": 1,                   // Reference to product
  "quantity": 5,                     // Number of items ordered
  "customer_identifier": "cust_123"  // Customer ID or identifier
}
```

## Usage Examples

### JavaScript/Web Application
```javascript
class StoreInventoryAPI {
  constructor(baseURL = 'http://localhost:8002') {
    this.baseURL = baseURL;
  }

  async getProducts(skip = 0, limit = 100) {
    const response = await fetch(`${this.baseURL}/products/?skip=${skip}&limit=${limit}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async createProduct(product) {
    const response = await fetch(`${this.baseURL}/products/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(product)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async searchProducts(query, skip = 0, limit = 100) {
    const url = `${this.baseURL}/products/search/?query=${encodeURIComponent(query)}&skip=${skip}&limit=${limit}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async placeOrder(productId, quantity, customerId) {
    const response = await fetch(`${this.baseURL}/orders/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: productId,
        quantity: quantity,
        customer_identifier: customerId
      })
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
}

// Usage example
const api = new StoreInventoryAPI();

// Load and display products
async function loadProducts() {
  try {
    const products = await api.getProducts();
    console.log('Products:', products);

    // Create new product
    const newProduct = await api.createProduct({
      name: 'USB Cable',
      description: 'High-speed USB-C cable',
      inventory: 100,
      price: 19.99
    });
    console.log('Created:', newProduct);

    // Place order
    const order = await api.placeOrder(newProduct.id, 5, 'web_customer_456');
    console.log('Order placed:', order);

  } catch (error) {
    console.error('API Error:', error);
  }
}

loadProducts();
```

### Python Client
```python
import httpx
import asyncio

class StoreInventoryClient:
    def __init__(self, base_url="http://localhost:8002"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def get_products(self, skip=0, limit=100):
        response = await self.client.get(
            f"{self.base_url}/products/",
            params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def create_product(self, name, description=None, inventory=0, price=0.0):
        product_data = {
            "name": name,
            "description": description,
            "inventory": inventory,
            "price": price
        }
        response = await self.client.post(
            f"{self.base_url}/products/",
            json=product_data
        )
        response.raise_for_status()
        return response.json()

    async def search_products(self, query, skip=0, limit=100):
        response = await self.client.get(
            f"{self.base_url}/products/search/",
            params={"query": query, "skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def place_order(self, product_id, quantity, customer_id):
        order_data = {
            "product_id": product_id,
            "quantity": quantity,
            "customer_identifier": customer_id
        }
        response = await self.client.post(
            f"{self.base_url}/orders/",
            json=order_data
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()

# Usage example
async def main():
    client = StoreInventoryClient()

    try:
        # Get existing products
        products = await client.get_products(limit=5)
        print(f"Found {len(products)} products")

        # Create new product
        new_product = await client.create_product(
            name="Python SDK Test Product",
            description="Created via Python client",
            inventory=20,
            price=99.99
        )
        print(f"Created product: {new_product['name']} (ID: {new_product['id']})")

        # Search for products
        search_results = await client.search_products("test")
        print(f"Search found {len(search_results)} products")

        # Place an order
        if new_product:
            order = await client.place_order(
                product_id=new_product["id"],
                quantity=2,
                customer_id="python_client_test"
            )
            print(f"Placed order: {order}")

    except httpx.HTTPError as e:
        print(f"HTTP Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

# Run the example
asyncio.run(main())
```

### cURL Examples
```bash
#!/bin/bash
# Complete workflow example

API_BASE="http://localhost:8002"

echo "=== Store Inventory API Demo ==="

# 1. Check API health
echo "1. Checking API health..."
curl -s "$API_BASE/health" | jq '.'

# 2. Get current products
echo -e "\n2. Current products:"
curl -s "$API_BASE/products/" | jq '.'

# 3. Create new products
echo -e "\n3. Creating new products..."
LAPTOP=$(curl -s -X POST "$API_BASE/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming Laptop Pro",
    "description": "High-end gaming laptop with RTX graphics",
    "inventory": 10,
    "price": 2499.99
  }' | jq -r '.id')

MOUSE=$(curl -s -X POST "$API_BASE/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming Mouse Elite",
    "description": "Professional gaming mouse with RGB",
    "inventory": 50,
    "price": 89.99
  }' | jq -r '.id')

echo "Created laptop (ID: $LAPTOP) and mouse (ID: $MOUSE)"

# 4. Search products
echo -e "\n4. Searching for gaming products:"
curl -s "$API_BASE/products/search/?query=gaming" | jq '.'

# 5. Place orders
echo -e "\n5. Placing orders..."
curl -s -X POST "$API_BASE/orders/" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": $LAPTOP,
    \"quantity\": 1,
    \"customer_identifier\": \"customer_001\"
  }" | jq '.'

curl -s -X POST "$API_BASE/orders/" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": $MOUSE,
    \"quantity\": 3,
    \"customer_identifier\": \"customer_002\"
  }" | jq '.'

# 6. Check updated inventory
echo -e "\n6. Updated product inventory:"
curl -s "$API_BASE/products/id/$LAPTOP" | jq '.inventory'
curl -s "$API_BASE/products/id/$MOUSE" | jq '.inventory'

echo -e "\nDemo completed!"
```

## Error Handling

### HTTP Status Codes
- `200`: Success
- `201`: Created (for POST requests)
- `404`: Resource not found
- `422`: Validation error (invalid request data)
- `500`: Internal server error

### Error Response Format
```json
{
  "detail": "Error description"
}
```

### Common Errors

#### Product Not Found
```bash
curl http://localhost:8002/products/id/999
# Response: 404 Not Found
{
  "detail": "Product not found"
}
```

#### Validation Errors
```bash
curl -X POST http://localhost:8002/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "", "price": -10}'
# Response: 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

#### Insufficient Inventory
```bash
# Try to order more than available
curl -X POST http://localhost:8002/orders/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1000, "customer_identifier": "test"}'
# Response: 400 Bad Request
{
  "detail": "Not enough inventory available"
}
```

## Performance Considerations

### Pagination
Always use pagination for large datasets:
```bash
# Get products in batches
curl "http://localhost:8002/products/?skip=0&limit=50"
curl "http://localhost:8002/products/?skip=50&limit=50"
```

### Search Optimization
- Use specific search terms for better performance
- Consider implementing caching for frequent searches
- Use database indexes on searchable fields

### Concurrent Requests
The API handles concurrent requests well, but consider:
- Connection pooling in clients
- Rate limiting for production use
- Monitoring for performance bottlenecks

## Deployment

### Environment Variables
```bash
# Database connection
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"

# Server settings
PORT=8002
HOST=0.0.0.0
LOG_LEVEL=INFO
```

### Docker Deployment
```bash
docker run -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@db:5432/store_db" \
  quay.io/ecosystem-appeng/store-inventory-api:latest
```

### Kubernetes with Helm
```bash
helm install store-inventory-api ./helm \
  --set postgresql.auth.postgresPassword=yourpassword
```

## Integration with MCP Servers

The API is designed to work seamlessly with MCP servers:

```mermaid
sequenceDiagram
    participant MCP as MCP Server
    participant API as Store Inventory API
    participant DB as Database

    MCP->>API: GET /products/
    API->>DB: Query products
    DB-->>API: Product data
    API-->>MCP: JSON response

    MCP->>API: POST /orders/
    API->>DB: Create order & update inventory
    DB-->>API: Order confirmation
    API-->>MCP: Order details
```

For development details, see the [Development Guide](DEVGUIDE.md).
