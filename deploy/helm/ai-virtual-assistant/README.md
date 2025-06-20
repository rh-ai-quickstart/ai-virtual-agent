# AI Virtual Assistant Helm Chart

A comprehensive Helm chart for deploying the AI Virtual Assistant platform with integrated MCP servers on Kubernetes.

## Overview

This chart deploys a complete AI Virtual Assistant stack including:

- **AI Virtual Assistant**: Main application with chat interface
- **MCP DBStore**: Integrated product inventory management server
- **Llama Stack**: LLM inference and orchestration
- **Vector Database**: PostgreSQL with pgvector extension
- **Object Storage**: MinIO for document storage
- **Knowledge Base**: Document ingestion and processing pipeline

## New: Integrated MCP DBStore

The MCP DBStore is now integrated as a subchart, providing:
- **7 Inventory Tools**: get_products, search_products, add_product, order_product, etc.
- **PostgreSQL Database**: Persistent storage with sample data
- **OpenShift Routes**: External HTTPS access
- **Automatic Registration**: Ready for Llama Stack integration

## Quick Start

```bash
# Install the complete stack
helm install ai-assistant ./deploy/helm/ai-virtual-assistant

# Or with custom values
helm install ai-assistant ./deploy/helm/ai-virtual-assistant \
  --set mcp-dbstore.enabled=true \
  --set mcp-dbstore.route.enabled=true
```

## Configuration

### MCP DBStore Configuration

The MCP DBStore is enabled by default. You can configure it:

```yaml
mcp-dbstore:
  enabled: true  # Enable/disable MCP DBStore
  mcpServer:
    enabled: true
    image:
      repository: ecosystem-appeng/mcp_dbstore
      tag: "1.1.0"
  postgresql:
    enabled: true
    persistence:
      size: 2Gi
  route:
    enabled: true  # Enable OpenShift route for external access
```

### Llama Stack Integration

The MCP DBStore is pre-configured for Llama Stack integration:

```yaml
llama-stack:
  mcp-servers:
    mcp-dbstore:
      uri: http://mcp-dbstore-mcp-server:8002/sse
```

## Accessing Services

### MCP DBStore
```bash
# Port forward to access MCP server
kubectl port-forward svc/ai-assistant-mcp-dbstore-mcp-server 8002:8002

# Test the inventory tools
curl http://localhost:8002/health
```

### Database
```bash
# Access PostgreSQL
kubectl port-forward svc/ai-assistant-mcp-dbstore-postgresql 5432:5432
psql -h localhost -U mcpuser -d store_db
```

## Available MCP Tools

The integrated MCP DBStore provides these tools for AI agents:

| Tool | Description |
|------|-------------|
| `get_products` | Retrieve paginated product list |
| `get_product_by_id` | Get specific product details |
| `search_products` | Search products by query |
| `add_product` | Create new product |
| `remove_product` | Delete product |
| `order_product` | Place order (updates inventory) |
| `get_product_by_name` | Find product by exact name |

## Development

### Building Images

The GitHub workflow automatically builds both images:

```yaml
# .github/workflows/build-and-push.yaml
strategy:
  matrix:
    include:
      - name: ai-virtual-assistant
        context: .
      - name: mcp_dbstore
        context: mcpservers/mcp_dbstore
```

### Local Development

```bash
# Update dependencies
cd deploy/helm/ai-virtual-assistant
helm dependency update

# Test template rendering
helm template . --dry-run

# Install for development
helm install dev-ai-assistant . --set mcp-dbstore.enabled=true
```

## Troubleshooting

### MCP DBStore Issues

```bash
# Check MCP server logs
kubectl logs -f deployment/ai-assistant-mcp-dbstore-mcp-server

# Check PostgreSQL
kubectl logs -f deployment/ai-assistant-mcp-dbstore-postgresql

# Verify database connection
kubectl exec -it deployment/ai-assistant-mcp-dbstore-postgresql -- pg_isready
```

### Dependency Issues

```bash
# Rebuild dependencies
helm dependency update

# Clean and reinstall
helm uninstall ai-assistant
helm install ai-assistant .
```

## Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│   AI Assistant      │    │   MCP DBStore       │
│   (Port 8000)       │    │   (Port 8002)       │
└─────────────────────┘    └─────────────────────┘
           │                         │
           └─────────┬─────────────────┘
                     │
        ┌─────────────────────┐
        │   Llama Stack       │
        │   (Port 8321)       │
        └─────────────────────┘
                     │
        ┌─────────────────────┐
        │   PostgreSQL        │
        │   (Port 5432)       │
        └─────────────────────┘
```

## License

Licensed under the Apache 2.0 License. 