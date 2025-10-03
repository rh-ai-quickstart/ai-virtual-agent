# Toolhive Registry API Deployment

This directory contains the Kubernetes manifests for deploying the Toolhive Registry API, which provides MCP server discovery functionality.

## Prerequisites

1. **Toolhive Operator**: The Toolhive operator must be installed and running in the cluster with experimental features enabled.
2. **OpenShift/Kubernetes Cluster**: Access to an OpenShift or Kubernetes cluster.

## Deployment Steps

### 1. Enable Experimental Features

First, ensure the Toolhive operator has experimental features enabled:

```bash
oc patch deployment toolhive-operator -n your-project --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/env/2/value", "value": "true"}]'
```

### 2. Deploy Registry Data

Deploy the registry data ConfigMap:

```bash
oc apply -f toolhive-registry-data.yaml
```

### 3. Deploy MCPRegistry Resource

Deploy the MCPRegistry custom resource:

```bash
oc apply -f toolhive-registry.yaml
```

### 4. Deploy Registry API Service

Deploy the registry API service:

```bash
oc apply -f toolhive-registry-api.yaml
```

## Verification

Check that all resources are deployed and running:

```bash
# Check MCPRegistry status
oc get mcpregistry default-registry -n your-project

# Check deployment
oc get deployment toolhive-registry-api -n your-project

# Check service
oc get service toolhive-registry-api -n your-project

# Test API endpoint
oc port-forward service/toolhive-registry-api 8080:8080 -n your-project
curl http://localhost:8080/api/v1beta/registry
```

## Configuration

### Registry Data

The registry data is stored in the `toolhive-registry-data` ConfigMap. To add or modify MCP servers, edit the `registry.json` content in the ConfigMap.

### API Endpoint

The registry API serves MCP server information at:
- `/api/v1beta/registry` - Returns the complete registry data

### Local Development

For local development, port forward the service and configure the backend to use:
```
TOOLHIVE_API_URL=http://host.docker.internal:8080
```

## Troubleshooting

1. **MCPRegistry not processing**: Ensure experimental features are enabled in the Toolhive operator.
2. **API not accessible**: Check that the deployment is running and the service has endpoints.
3. **Registry data not found**: Verify the ConfigMap exists and the MCPRegistry references the correct ConfigMap name and key.

## Files

- `toolhive-registry-data.yaml` - ConfigMap containing MCP server registry data
- `toolhive-registry.yaml` - MCPRegistry custom resource definition
- `toolhive-registry-api.yaml` - Deployment, ConfigMap, and Service for the registry API
