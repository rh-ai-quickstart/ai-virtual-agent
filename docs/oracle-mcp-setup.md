# Oracle MCP Server Setup Guide

This guide shows how to register the Oracle MCP server with the AI Virtual Agent platform using the existing MCP server management interface.

## Overview

The Oracle MCP server provides 9 business analytics tools for TPC-DS data analysis:

- **health_check** - Server health monitoring
- **get_tpcds_summary** - TPC-DS tables and row counts  
- **get_customer_insights** - Customer demographic analysis
- **get_sales_analytics** - Sales transaction analytics
- **get_top_selling_products** - Product performance metrics
- **get_inventory_insights** - Inventory analysis with alerts
- **get_store_performance** - Store performance comparison
- **execute_custom_query** - Safe custom SQL execution
- **get_kpi_dashboard** - Key performance indicators

## Prerequisites

1. **Oracle Database**: Oracle 23ai with TPC-DS data loaded
2. **Oracle MCP Server**: Deployed and running on port 8003
3. **Database Connectivity**: Oracle MCP server can connect to Oracle DB
4. **Admin Access**: Admin role in AI Virtual Agent platform

## Registration Steps

### 1. Access MCP Servers Configuration

1. Log into the AI Virtual Agent platform
2. Navigate to **Configuration > MCP Servers** (admin only)
3. Click the **+** icon to add a new MCP server

### 2. Fill Out Registration Form

Use these exact values in the MCP server registration form:

**Toolgroup ID:**
```
mcp-oracle
```

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
http://oracle-mcp-service:8003
```

**Configuration (JSON):**
```json
{
  "oracle_host": "oracle-service.an-oracle-23ai.svc.cluster.local",
  "oracle_port": "1521",
  "service_name": "FREEPDB1",
  "username": "tpcds",
  "environment": "development"
}
```

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