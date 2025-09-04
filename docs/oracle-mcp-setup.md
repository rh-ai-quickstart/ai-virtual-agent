# Oracle MCP Server Setup Guide

This guide shows how to set up the Oracle MCP server with Oracle 23ai database and register it with the AI Virtual Agent platform.

## Overview

The Oracle MCP server provides business analytics tools for TPC-DS data analysis:

- **health_check** - Server health and database connectivity monitoring
- **get_tpcds_summary** - TPC-DS tables overview and row counts  
- **get_customer_insights** - Customer demographic analysis with configurable limits
- **get_sales_analytics** - Sales transaction analytics with date range filtering
- **execute_custom_query** - Safe custom SQL execution with security constraints

## Prerequisites

1. **Oracle Database**: Oracle 23ai with TPC-DS data loaded and accessible
2. **Database Connection**: Port forwarding or direct connectivity to Oracle database
3. **Oracle Credentials**: Valid system user credentials for Oracle database
4. **Python Environment**: Python 3.8+ with required dependencies
5. **Admin Access**: Admin role in AI Virtual Agent platform for MCP server registration

## Step 1: Setup Oracle Database Connection

### Option A: Local Development with Port Forwarding

If you have Oracle 23ai running in Kubernetes/OpenShift:

```bash
# Get the Oracle pod name
oc get pods -n an-oracle-23ai

# Start port forwarding (keep this running in a separate terminal)
oc port-forward -n an-oracle-23ai oracle23ai-0 1521:1521
```

### Option B: Direct Database Connection

Update the connection details in the Oracle MCP server configuration to point directly to your Oracle database.

## Step 2: Setup Oracle MCP Server

### Get Oracle Database Credentials

First, get the correct Oracle password from your Kubernetes deployment:

```bash
# Get the Oracle password from the secret
oc get secret oracle23ai -n an-oracle-23ai -o jsonpath='{.data.password}' | base64 -d
```

### Configure Oracle MCP Server

1. Navigate to the Oracle MCP server directory:
```bash
cd mcpservers/mcp_oracle
```

2. Create the `.env` file with correct Oracle credentials:
```bash
# Oracle Database Configuration
ORACLE_USER=SYSTEM
ORACLE_PASSWORD=<password_from_secret_above>
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=freepdb1

# MCP Server Configuration  
MCP_SERVER_PORT=8003
MCP_SERVER_HOST=0.0.0.0

# Security Settings
ENVIRONMENT=development

# Logging Configuration
LOG_LEVEL=INFO
```

3. Install dependencies and start the Oracle MCP server:
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the Oracle MCP server (keep this running)
python oracle_fastmcp_server.py
```

The server should start and show:
```
INFO:     Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)
```

### Verify Oracle MCP Server

Test the server is working:
```bash
# Test basic connectivity
curl http://localhost:8003/

# Test health check (should return Oracle database status)
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -d '{"method": "health_check", "params": {}}'
```

## Step 3: Register with AI Virtual Agent Platform

### 1. Access MCP Servers Configuration

1. Log into the AI Virtual Agent platform at http://localhost:5173
2. Navigate to **Configuration > MCP Servers** (admin only)
3. Click the **+** icon to add a new MCP server

### 2. Fill Out Registration Form

Use these exact values in the MCP server registration form:

**Name:**
```
Oracle Analytics
```

**Description:**
```
TPC-DS business analytics tools for Oracle Database
```

**Endpoint URL:**
```
http://192.168.2.199:8003/sse
```

**Tool Group ID:**
```
mcp::oracle_analytics
```

**Configuration (JSON):**
```json
{
  "name": "Oracle Analytics",
  "description": "TPC-DS business analytics tools for Oracle Database"
}
```

> **Important Notes:**
> - Use the exact IP address and `/sse` endpoint path as shown above
> - The Tool Group ID must include the `mcp::` prefix
> - The endpoint URL should match your local network IP address (check with `ifconfig` or `ip addr`)

### 3. Submit Registration

1. Click **Create** to register the Oracle MCP server
2. Wait for successful registration confirmation
3. Verify the server appears in the MCP servers list

## Configuration Details

### Oracle Connection Settings

The configuration object supports these Oracle-specific parameters:

- **oracle_host**: Oracle database hostname or service name
- **oracle_port**: Oracle listener port (default: 1521)
- **service_name**: Oracle database service name (e.g., FREEPDB1)
- **username**: Database username (credentials passed via environment variables)
- **environment**: Deployment environment (development/production)

### Security Notes

- **Passwords**: Never include passwords in configuration JSON
- **Environment Variables**: Oracle MCP server uses environment variables for sensitive data
- **TLS**: Use HTTPS endpoint URLs in production
- **Network**: Ensure proper network connectivity between services

## Environment-Specific Configurations

### Development Environment
```json
{
  "oracle_host": "localhost",
  "oracle_port": "1521", 
  "service_name": "freepdb1",
  "username": "tpcds",
  "environment": "development"
}
```

### Production Environment
```json
{
  "oracle_host": "oracle-prod.company.com",
  "oracle_port": "1521",
  "service_name": "PRODPDB1", 
  "username": "analytics_user",
  "environment": "production"
}
```

### Kubernetes Environment
```json
{
  "oracle_host": "oracle-service.an-oracle-23ai.svc.cluster.local",
  "oracle_port": "1521",
  "service_name": "FREEPDB1",
  "username": "tpcds",
  "environment": "development"
}
```

## Verification Steps

### 1. Check Server Status

After registration, verify the Oracle MCP server:

1. Refresh the MCP servers list
2. Confirm "Oracle Analytics" server appears
3. Check endpoint URL shows correctly
4. Verify configuration displays properly

### 2. Test Agent Integration

Create a new agent with Oracle tools:

1. Navigate to **Agents** section
2. Create new agent or edit existing agent
3. In **Available Tools**, select Oracle Analytics tools
4. Save agent configuration

### 3. Test Oracle Queries

Test Oracle MCP functionality through chat:

```
Show me a summary of TPC-DS tables
```

```
Get customer insights for the top 10 customers
```

```
Show me sales analytics for Q4 2023
```

## Troubleshooting

### Common Issues

**Server Not Responding**
- Check Oracle MCP server is running on port 8003
- Verify network connectivity to endpoint URL
- Check Oracle database connectivity

**Authentication Errors**
- Verify Oracle credentials in environment variables
- Check database user permissions
- Confirm service name and connection details

**Tool Not Available in Agent**
- Refresh MCP servers list
- Re-register Oracle MCP server if needed
- Check agent tool configuration

### Log Analysis

Check Oracle MCP server logs for debugging:

```bash
# Check container logs
kubectl logs -f deployment/oracle-mcp-deployment

# Check service status
kubectl get svc oracle-mcp-service

# Test endpoint connectivity
curl http://oracle-mcp-service:8003/health
```

## Advanced Configuration

### Custom Oracle Queries

The Oracle MCP server supports custom SQL queries with safety constraints:

- Only SELECT statements allowed
- Automatic ROWNUM limits applied
- Dangerous keywords blocked
- Input validation enforced

### Performance Tuning

For high-volume analytics:

- Adjust row limits in tool parameters
- Use date range filtering
- Optimize Oracle database indexes
- Monitor query performance

### Security Hardening

Production security recommendations:

- Use TLS/HTTPS endpoints
- Implement network policies
- Rotate database credentials
- Monitor query access logs
- Apply principle of least privilege

## Support

For assistance with Oracle MCP server setup:

1. Check Oracle MCP server documentation
2. Review AI Virtual Agent platform logs
3. Verify Oracle database connectivity
4. Test MCP server endpoints directly

## Related Documentation

- [AI Virtual Agent Platform Documentation](../README.md)
- [MCP Server API Reference](./api-reference.md)
- [Oracle MCP Server Container Deployment](../mcpservers/mcp_oracle/deploy.yaml)