# Refactored MCP Store Inventory Components

This document describes the refactored store inventory system that separates the MCP protocol layer from the business logic layer.

## Architecture Overview

The system has been split into two independent components:

1. **mcp-store-inventory**: Standalone MCP server that provides inventory tools to LLMs
2. **store-inventory**: REST API and database layer that handles the actual business logic

## Components

### 1. MCP Store Inventory Server (`mcp-store-inventory/`)

A lightweight MCP server that:
- Provides inventory management tools to LLMs via MCP protocol
- Connects to the Store Inventory API via HTTP
- Runs on port 8003 by default
- Can be deployed independently as a microservice

**Key Files:**
- `server.py` - Main MCP server implementation
- `requirements.txt` - Python dependencies
- `Containerfile` - Container build instructions

**Available Tools:**
- `get_products()` - List all products with pagination
- `get_product_by_id(product_id)` - Get specific product by ID
- `get_product_by_name(name)` - Get specific product by name
- `search_products(query)` - Search products by name/description
- `add_product(name, description, inventory, price)` - Add new product
- `remove_product(product_id)` - Delete product
- `order_product(product_id, quantity, customer_identifier)` - Place order

### 2. Store Inventory API (`store-inventory/`)

A FastAPI-based REST API that:
- Manages products and orders in PostgreSQL database
- Provides HTTP endpoints for inventory operations
- Runs on port 8002 by default
- Includes database models and CRUD operations

**Key Files:**
- `main.py` - FastAPI application with endpoints
- `models.py` - Pydantic models for API
- `database.py` - SQLAlchemy database models and connection
- `crud.py` - Database operations
- `populate_db.sql` - Sample data for testing

## Deployment

### Kubernetes Deployment

Both components have dedicated Helm charts under `helm/`:

#### MCP Server Helm Chart (`helm/mcp-store-inventory/`)
- Deploys the MCP server as a standalone service
- Configures connection to Store API
- Includes health checks and resource limits
- Service runs on port 8003

#### Store API Helm Chart (`helm/store-inventory/`)
- Deploys the FastAPI application
- Includes PostgreSQL database dependency
- Configures database initialization
- Service runs on port 8002

### Local Development

1. **Start Store API:**
   ```bash
   cd store-inventory
   uvicorn main:app --reload --port 8002
   ```

2. **Start MCP Server:**
   ```bash
   cd mcp-store-inventory
   export STORE_API_URL=http://localhost:8002
   python server.py
   ```

### Container Deployment

Both components include Containerfiles for building Docker images:

```bash
# Build Store API
cd store-inventory
docker build -t store-inventory .

# Build MCP Server
cd mcp-store-inventory
docker build -t mcp-store-inventory .
```

## Configuration

### Environment Variables

**MCP Server:**
- `STORE_API_URL` - URL of the Store Inventory API (default: http://localhost:8002)

**Store API:**
- `DATABASE_URL` - PostgreSQL connection string

## Benefits of This Architecture

1. **Independent Deployment**: MCP server and API can be deployed separately
2. **Scalability**: Each component can be scaled independently based on load
3. **Technology Isolation**: MCP protocol concerns are separated from business logic
4. **Reusability**: The Store API can be used by other clients beyond MCP
5. **Maintainability**: Clear separation of concerns makes the system easier to maintain
6. **Testing**: Each component can be tested in isolation

## Migration from Original Structure

The original `mcp_webstore` and `mcp_dbstore` implementations have been refactored into:

- MCP protocol handling → `mcp-store-inventory`
- Business logic and database → `store-inventory`

Both new components maintain the same functionality and tool signatures as the original implementations.
