# Helm Chart Reorganization

This document describes the reorganization of Helm charts from a centralized structure to component-based organization.

## 🏗️ **New Structure Overview**

Each component now contains its own self-contained Helm chart:

```
mcpservers/
├── mcp_dbstore/
│   ├── helm/                    # MCP server + database (tightly coupled)
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── _helpers.tpl
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── serviceaccount.yaml
│   └── ... (application code)
├── mcp_webstore/
│   ├── helm/                    # MCP server + store API (client-server)
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── _helpers.tpl
│   │       ├── mcp-server-deployment.yaml
│   │       ├── store-api-deployment.yaml
│   │       ├── service.yaml
│   │       └── serviceaccount.yaml
│   └── ... (application code)
├── mcp-store-inventory/
│   ├── helm/                    # Standalone MCP server
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── _helpers.tpl
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── serviceaccount.yaml
│   └── ... (application code)
└── store-inventory/
    ├── helm/                    # Standalone API + database
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    │       ├── _helpers.tpl
    │       ├── configmap.yaml
    │       ├── deployment.yaml
    │       ├── service.yaml
    │       └── serviceaccount.yaml
    └── ... (application code)
```

## 📦 **Component Details**

### 1. **mcp_dbstore** - Integrated MCP + Database
- **Purpose**: MCP server with tightly coupled database
- **Components**: Single deployment with database dependency
- **Port**: 8002
- **Database**: PostgreSQL (integrated via dependency)
- **Image**: `quay.io/ecosystem-appeng/mcp-dbstore`

### 2. **mcp_webstore** - MCP Server + Store API
- **Purpose**: MCP server that communicates with separate store API
- **Components**: Two deployments (MCP server + Store API)
- **Ports**: 8001 (both components)
- **Database**: PostgreSQL (for store API)
- **Images**:
  - `quay.io/ecosystem-appeng/mcp-webstore` (MCP server)
  - `quay.io/ecosystem-appeng/mcp-webstore-api` (Store API)

### 3. **mcp-store-inventory** - Standalone MCP Server
- **Purpose**: Standalone MCP server requiring external store API
- **Components**: Single deployment (MCP server only)
- **Port**: 8003
- **Dependencies**: Requires external store-inventory API
- **Image**: `quay.io/ecosystem-appeng/mcp-store-inventory`

### 4. **store-inventory** - Standalone Store API
- **Purpose**: Standalone store API with database
- **Components**: Single deployment with database dependency
- **Port**: 8002
- **Database**: PostgreSQL (integrated via dependency)
- **Image**: `quay.io/ecosystem-appeng/store-inventory`

## 🔄 **Migration from Centralized Structure**

### **Before:**
```
mcpservers/
└── helm/
    ├── mcp-store-inventory/
    └── store-inventory/
```

### **After:**
```
mcpservers/
├── mcp_dbstore/helm/
├── mcp_webstore/helm/
├── mcp-store-inventory/helm/
└── store-inventory/helm/
```

## 🎯 **Benefits of New Structure**

1. **Component Isolation**: Each component is completely self-contained
2. **Independent Deployment**: Components can be deployed separately without interference
3. **Clear Ownership**: Each team/developer knows exactly which chart belongs to which component
4. **Simplified CI/CD**: Build and deployment pipelines can be component-specific
5. **Better Versioning**: Each component can have independent versioning
6. **Reduced Complexity**: No need to understand the entire system to work on one component

## 🚀 **Deployment Examples**

### Deploy mcp_dbstore (integrated):
```bash
cd mcpservers/mcp_dbstore
helm install mcp-dbstore ./helm
```

### Deploy mcp_webstore (MCP + API):
```bash
cd mcpservers/mcp_webstore
helm install mcp-webstore ./helm
```

### Deploy standalone components:
```bash
# Deploy store API first
cd mcpservers/store-inventory
helm install store-api ./helm

# Then deploy MCP server that connects to it
cd ../mcp-store-inventory
helm install mcp-server ./helm --set env.STORE_API_URL=http://store-api:8002
```

## 📋 **Component Dependencies**

| Component | Dependencies | External Services |
|-----------|-------------|-------------------|
| **mcp_dbstore** | PostgreSQL | None |
| **mcp_webstore** | PostgreSQL | None (self-contained) |
| **mcp-store-inventory** | None | Requires store-inventory API |
| **store-inventory** | PostgreSQL | None |

## ⚙️ **Configuration**

Each component now has its own isolated configuration:

- **Image repositories**: All use `quay.io/ecosystem-appeng/` registry
- **Service naming**: Component-specific service names prevent conflicts
- **Resource allocation**: Tailored to each component's needs
- **Health checks**: Component-appropriate health check configurations
- **Database connections**: Proper service discovery within each component's namespace

This reorganization provides a clean, maintainable, and scalable deployment architecture! 🎉
