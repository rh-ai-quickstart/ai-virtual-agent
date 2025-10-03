# AI Virtual Agent - Deployment Scenarios

This document covers the different deployment scenarios for the AI Virtual Agent with MCP server discovery capabilities.

## 🏗️ **Deployment Scenarios**

### 1. **Local Development** (Docker Compose)

**Use Case:** Development, testing, and local experimentation

**Features:**
- ✅ Hot reload for backend and frontend
- ✅ Local database with persistence
- ✅ MCP server discovery from multiple sources
- ✅ Easy debugging and development

**Quick Start:**
```bash
cd deploy/local
make compose-up
```

**MCP Discovery Sources:**
- Environment variables (`MCP_SERVERS`)
- Toolhive API (via port forwarding)
- Default local servers (weather, oracle-sqlcl, inspector)

**Configuration:**
- Edit `deploy/local/.env` for environment variables
- Port forward OpenShift services for Toolhive API access
- Use `make compose-down` to stop services

---

### 2. **Cluster Deployment** (Helm Chart)

**Use Case:** Production, staging, and multi-user environments

**Features:**
- ✅ Scalable deployment with Helm
- ✅ Integrated Toolhive Registry API
- ✅ Production-ready configuration
- ✅ OpenShift/Kubernetes native

**Quick Start:**
```bash
# Deploy with Toolhive Registry enabled (default)
helm install ai-va ./deploy/cluster/helm \
  --namespace your-project \
  --create-namespace

# Deploy without Toolhive Registry
helm install ai-va ./deploy/cluster/helm \
  --namespace your-project \
  --create-namespace \
  --set toolhiveRegistry.enabled=false
```

**MCP Discovery Sources:**
- Toolhive Registry API (automatically deployed)
- Environment variables (configurable)
- Default servers (configurable)

---

## 🔧 **Configuration Options**

### Local Development Configuration

**File:** `deploy/local/.env`

```bash
# MCP Server Discovery
TOOLHIVE_API_URL=http://host.docker.internal:8080  # Port-forwarded Toolhive API
MCP_SERVERS=test-server:9000,custom-server:9001    # Custom servers

# Development Settings
LOCAL_DEV_ENV_MODE=true
DISABLE_ATTACHMENTS=false
```

### Cluster Deployment Configuration

**File:** `deploy/cluster/helm/values.yaml`

```yaml
# Toolhive Registry Configuration
toolhiveRegistry:
  enabled: true  # Enable/disable registry deployment
  
  # Registry API service
  service:
    type: ClusterIP
    port: 8080
    targetPort: 8080
  
  # Registry data (customizable)
  registryData:
    version: "1.0.0"
    servers:
      weather:
        name: weather
        description: Weather information MCP server
        # ... more server configurations
```

---

## 🚀 **Deployment Workflows**

### Local Development Workflow

1. **Start Local Environment:**
   ```bash
   cd deploy/local
   make compose-up
   ```

2. **Port Forward OpenShift Services (Optional):**
   ```bash
   oc port-forward service/mcp-weather-proxy 8001:8000 &
   oc port-forward service/mcp-oracle-sqlcl-proxy 8081:8000 &
   oc port-forward service/toolhive-registry-api 8080:8080 &
   ```

3. **Configure Environment Variables:**
   ```bash
   # Edit deploy/local/.env
   TOOLHIVE_API_URL=http://host.docker.internal:8080
   MCP_SERVERS=test-server:9000,custom-server:9001
   ```

4. **Test MCP Discovery:**
   ```bash
   curl http://localhost:8000/api/v1/mcp_servers/ | jq .
   ```

### Cluster Deployment Workflow

1. **Deploy with Helm:**
   ```bash
   helm install ai-va ./deploy/cluster/helm \
     --namespace your-project \
     --create-namespace
   ```

2. **Verify Deployment:**
   ```bash
   # Check all components
   oc get all -n your-project
   
   # Check MCPRegistry
   oc get mcpregistry -n your-project
   
   # Test registry API
   oc port-forward service/ai-va-registry-api 8080:8080 -n your-project
   curl http://localhost:8080/api/v1beta/registry
   ```

3. **Test MCP Discovery:**
   ```bash
   # Port forward main service
   oc port-forward service/ai-va 8000:8000 -n your-project
   curl http://localhost:8000/api/v1/mcp_servers/ | jq .
   ```

---

## 🔍 **MCP Discovery Sources**

### 1. **Environment Variables**
- **Local:** Set in `deploy/local/.env`
- **Cluster:** Set in Helm values or ConfigMap
- **Format:** `server1:port1,server2:port2` or JSON

### 2. **Toolhive Registry API**
- **Local:** Port-forward OpenShift service
- **Cluster:** Automatically deployed with Helm
- **Endpoint:** `/api/v1beta/registry`

### 3. **Default Servers**
- **Local:** Hardcoded localhost servers
- **Cluster:** Configurable in Helm values
- **Fallback:** Always available for development

---

## 🛠️ **Customization**

### Adding Custom MCP Servers

**Local Development:**
```bash
# Add to deploy/local/.env
MCP_SERVERS=my-server:9000,another-server:9001
```

**Cluster Deployment:**
```yaml
# Add to deploy/cluster/helm/values.yaml
toolhiveRegistry:
  registryData:
    servers:
      my-server:
        name: my-server
        description: My custom MCP server
        image: my-registry/my-mcp-server:latest
        tier: Community
        status: Active
        transport: sse
        tools:
          - my_tool
```

### Disabling Toolhive Registry

**Local Development:**
```bash
# Remove or comment out in deploy/local/.env
# TOOLHIVE_API_URL=
```

**Cluster Deployment:**
```bash
helm upgrade ai-va ./deploy/cluster/helm \
  --set toolhiveRegistry.enabled=false
```

---

## 🔧 **Troubleshooting**

### Local Development Issues

**Problem:** MCP servers not discovered
```bash
# Check environment variables
podman exec ai-va-backend-dev env | grep TOOLHIVE

# Check logs
podman logs ai-va-backend-dev | grep -i "toolhive\|mcp"
```

**Problem:** Toolhive API not accessible
```bash
# Verify port forwarding
oc get pods -n your-project | grep registry
oc port-forward service/toolhive-registry-api 8080:8080 -n your-project
```

### Cluster Deployment Issues

**Problem:** MCPRegistry not processing
```bash
# Check Toolhive operator
oc get pods -n your-project | grep toolhive-operator
oc logs deployment/toolhive-operator -n your-project

# Enable experimental features
oc patch deployment toolhive-operator -n your-project \
  --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/env/2/value", "value": "true"}]'
```

**Problem:** Registry API not accessible
```bash
# Check deployment
oc get deployment ai-va-registry-api -n your-project
oc get service ai-va-registry-api -n your-project

# Check logs
oc logs deployment/ai-va-registry-api -n your-project
```

---

## 📚 **Additional Resources**

- [Local Development Guide](../local/README.md)
- [Toolhive Registry Documentation](./README-toolhive-registry.md)
- [MCP Server Discovery API Documentation](../../README.md#mcp-server-discovery)
- [Helm Chart Values Reference](./helm/values.yaml)
