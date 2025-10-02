# ToolHive Discovery

The AI Virtual Agent platform includes automatic discovery of MCP (Model Context Protocol) servers deployed via ToolHive, providing seamless integration between your agent platform and ToolHive-managed tool ecosystems.

## Overview

ToolHive Discovery enables:

- **Automatic Detection**: Finds MCP servers deployed through ToolHive without manual configuration
- **Hybrid Management**: Combines manually registered servers with auto-discovered ones
- **Background Sync**: Continuously monitors for new ToolHive deployments
- **Graceful Fallback**: Operates safely without impacting existing functionality

## Configuration

### Environment Variables

Configure ToolHive discovery through environment variables:

```bash
# Enable/disable ToolHive discovery
TOOLHIVE_DISCOVERY_ENABLED=true

# Discovery mode: auto, kubernetes, api, disabled
TOOLHIVE_MODE=auto

# Timeout for discovery operations (seconds)
TOOLHIVE_TIMEOUT=5

# For Kubernetes discovery
TOOLHIVE_NAMESPACE=toolhive-system

# For API discovery
TOOLHIVE_API_URL=https://toolhive.example.com/api
```

### Discovery Modes

#### Auto Mode (Recommended)
```bash
TOOLHIVE_MODE=auto
```
Tries Kubernetes discovery first, falls back to API discovery if needed.

#### Kubernetes Mode
```bash
TOOLHIVE_MODE=kubernetes
TOOLHIVE_NAMESPACE=toolhive-system  # Optional: specific namespace
```
Discovers servers via Kubernetes Custom Resource Definitions (CRDs).

#### API Mode
```bash
TOOLHIVE_MODE=api
TOOLHIVE_API_URL=https://toolhive.example.com/api
```
Discovers servers via ToolHive REST API.

#### Disabled Mode
```bash
TOOLHIVE_MODE=disabled
```
Completely disables ToolHive discovery.

## API Endpoints

### List All Servers (Hybrid)
```http
GET /api/mcp_servers/
```
Returns both manually registered and auto-discovered MCP servers.

**Response includes source indicators:**
```json
[
  {
    "toolgroup_id": "manual-server-1",
    "name": "Custom Tool Server",
    "source": "manual",
    ...
  },
  {
    "toolgroup_id": "toolhive-server-1",
    "name": "Auto-discovered Server",
    "source": "toolhive-kubernetes",
    ...
  }
]
```

### On-Demand Discovery
```http
POST /api/mcp_servers/discover
```
Triggers immediate discovery of ToolHive servers.

### Discovery Status
```http
GET /api/mcp_servers/discovery/status
```
Returns status of ToolHive discovery capabilities.

```json
{
  "discovery_available": true,
  "discovery_mode": "kubernetes",
  "enabled": true,
  "timeout": 5,
  "sync_approach": "on-demand",
  "background_sync": false
}
```

## Server Management

### Auto-Discovered Servers

- **Read-Only**: Auto-discovered servers cannot be modified through the platform
- **Protected Deletion**: Attempting to delete auto-discovered servers returns HTTP 403
- **Automatic Refresh**: Changes in ToolHive are automatically reflected

### Manual Servers

- **Full Control**: Can be created, updated, and deleted normally
- **Persistent**: Remain available regardless of ToolHive status

## Kubernetes Integration

### Required CRDs

The discovery service looks for these Custom Resource Definitions:

- `toolhive.stacklok.dev/v1alpha1/mcpservers`
- `toolhive.stacklok.io/v1/mcpservers`
- `toolhive.stacklok.io/v1/toolhiveservers`
- `mcp.toolhive.io/v1/servers`

### RBAC Requirements

For cluster-wide discovery:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: toolhive-discovery
rules:
- apiGroups: ["toolhive.stacklok.dev", "toolhive.stacklok.io", "mcp.toolhive.io"]
  resources: ["mcpservers", "toolhiveservers", "servers"]
  verbs: ["get", "list"]
```

For namespace-specific discovery:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: toolhive-system
  name: toolhive-discovery
rules:
- apiGroups: ["toolhive.stacklok.dev", "toolhive.stacklok.io", "mcp.toolhive.io"]
  resources: ["mcpservers", "toolhiveservers", "servers"]
  verbs: ["get", "list"]
```

## On-Demand Discovery

The platform uses an on-demand discovery approach that:

1. **Discovers and Registers**: When the frontend requests MCP servers, the system discovers ToolHive servers and registers them with LlamaStack
2. **No Background Sync**: No periodic background processes - discovery happens only when needed
3. **Automatic Registration**: New ToolHive servers are automatically registered with LlamaStack during discovery
4. **Graceful Handling**: Discovery failures don't impact existing functionality

### Discovery Trigger

Discovery happens automatically when:
- Frontend requests the MCP server list (`GET /api/mcp_servers/`)
- Manual discovery is triggered (`POST /api/mcp_servers/discover`)

This approach is more efficient and reduces system overhead compared to periodic background scanning.

## Troubleshooting

### Common Issues

#### Discovery Not Working
1. Check if discovery is enabled: `TOOLHIVE_DISCOVERY_ENABLED=true`
2. Verify discovery mode configuration
3. Check logs for authentication or network errors
4. Test connectivity to ToolHive services

#### Kubernetes Discovery Failed
1. Verify RBAC permissions
2. Check if ToolHive CRDs are installed
3. Confirm namespace configuration
4. Test kubectl access from the pod

#### API Discovery Failed
1. Verify ToolHive API URL is accessible
2. Check authentication credentials
3. Test API connectivity and timeouts
4. Review API response format

### Debug Logging

Enable debug logging for detailed troubleshooting:

```bash
# Set log level to debug
LOG_LEVEL=debug

# Enable specific logger
LOGGER_NAME=backend.services.toolhive_discovery
```

### Health Checks

Monitor discovery health:

```bash
# Check discovery status
curl http://localhost:8000/api/mcp_servers/discovery/status

# Trigger manual discovery
curl -X POST http://localhost:8000/api/mcp_servers/discover

# View recent logs
kubectl logs -l app=ai-virtual-agent-backend --tail=100
```

## Security Considerations

### Access Control
- Discovery services run with minimal required permissions
- Auto-discovered servers are read-only to prevent tampering
- All discovery operations respect existing authentication

### Network Security
- Uses HTTPS for API communications
- Supports certificate validation
- Configurable timeouts prevent hanging connections

### Data Protection
- No sensitive data is stored during discovery
- Server configurations are validated before registration
- Failed discoveries are logged safely without exposing credentials

## Best Practices

### Production Deployment
1. Use specific ToolHive namespaces rather than cluster-wide access
2. Set appropriate timeout values for your network environment
3. Monitor discovery logs for errors and performance
4. Test failover scenarios with ToolHive unavailable

### Development Setup
1. Start with `TOOLHIVE_MODE=disabled` for initial setup
2. Enable discovery after confirming basic functionality
3. Test both manual and auto-discovered server scenarios

### Monitoring
1. Set up alerts for discovery failures
2. Monitor discovery performance and errors
3. Track the count of auto-discovered servers over time
4. Review discovery logs regularly for issues

## Related Documentation

- [MCP Servers Guide](../mcpservers/README.md) - Building custom MCP servers
- [API Reference](api-reference.md) - Complete API documentation
- [Virtual Agents Architecture](virtual-agents-architecture.md) - Platform architecture overview
- [Contributing Guide](../CONTRIBUTING.md) - Development and contribution guidelines
