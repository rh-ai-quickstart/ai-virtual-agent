# MCP Server Testing Guide

## Overview

This guide provides step-by-step instructions for testing the Model Context Protocol (MCP) server integration in the AI Virtual Agent platform. The MCP server enables agents to access live database information alongside knowledge base data.

## Prerequisites

- [ ] AI Virtual Agent platform is running
- [ ] LlamaStack server is accessible
- [ ] MCP server (`mcp::dbstore`) is configured and running
- [ ] Database contains test data

## Quick Test (2 minutes)

### Step 1: Verify MCP Server Status

1. **Navigate to MCP Servers page:**
   - Go to **Config** → **MCP Servers**
   - Verify `mcp::dbstore` server is listed
   - Check endpoint: `http://mcp-dbstore-standalone:8002/sse`
   - Status should show as active/connected

2. **Test API endpoint:**
   ```bash
   curl -X 'GET' 'http://localhost:8000/api/llama_stack/toolgroups' \
     -H 'accept: application/json' | jq '.[] | select(.provider_id == "model-context-protocol")'
   ```

### Step 2: Create Test Agent

1. **Go to Chat section**
2. **Click "Create New Agent"**
3. **Configure agent:**
   - **Name:** `MCP Test Agent`
   - **Model:** `meta-llama/Llama-3.1-8B-Instruct`
   - **Prompt:** `You are a helpful assistant with access to database information through MCP tools.`
   - **Tools:** Select `mcp::dbstore`
   - **Knowledge Bases:** Leave empty (testing MCP only)

### Step 3: Test Database Access

1. **Start chat with the test agent**
2. **Ask basic database questions:**
   - *"What tables are available in the database?"*
   - *"Show me the database schema"*
   - *"List all records in the products table"*

## Expected Results

### ✅ Success Indicators

- **MCP Server Status:** Shows as active/connected
- **Agent Creation:** Agent is created successfully
- **Tool Discovery:** Agent can discover MCP tools
- **Database Queries:** Agent can query database and return results
- **Response Quality:** Responses include database information

### ❌ Failure Indicators

- **MCP Server Status:** Shows as disconnected or error
- **Agent Creation:** Fails with tool configuration errors
- **Tool Discovery:** Agent cannot find MCP tools
- **Database Queries:** Agent cannot access database
- **Response Quality:** Responses are generic or error messages

## Troubleshooting

### MCP Server Not Connected

**Symptoms:**
- MCP server shows as disconnected
- Agent creation fails
- Tool discovery fails

**Solutions:**
1. **Check MCP server pod:**
   ```bash
   kubectl get pods -n ai-assistant | grep mcp-dbstore
   ```

2. **Check MCP server logs:**
   ```bash
   kubectl logs -n ai-assistant mcp-dbstore-standalone --tail=50
   ```

3. **Restart MCP server:**
   ```bash
   kubectl delete pod -n ai-assistant mcp-dbstore-standalone
   ```

### Database Queries Fail

**Symptoms:**
- Agent responds with "tool not available" errors
- Database queries return empty results
- Agent cannot access database functions

**Solutions:**
1. **Verify database has data:**
   ```bash
   kubectl exec -n ai-assistant mcp-dbstore-standalone -- psql -U postgres -d testdb -c "SELECT * FROM products LIMIT 5;"
   ```

2. **Check MCP server configuration:**
   - Verify database connection string
   - Check if database schema is properly set up

3. **Test MCP server directly:**
   ```bash
   curl -X POST http://mcp-dbstore-standalone:8002/sse \
     -H "Content-Type: application/json" \
     -d '{"method": "tools/list", "params": {}}'
   ```

### Agent Cannot Find MCP Tools

**Symptoms:**
- Agent creation shows no MCP tools available
- Tool selection dropdown is empty
- Agent responds with "no tools available"

**Solutions:**
1. **Check LlamaStack configuration:**
   - Verify `mcp::dbstore` is in tool_groups
   - Check MCP endpoint configuration

2. **Restart LlamaStack:**
   ```bash
   kubectl delete pod -n ai-assistant llamastack-xxx
   ```

3. **Verify tool discovery:**
   ```bash
   curl -X 'GET' 'http://localhost:8000/api/llama_stack/toolgroups' \
     -H 'accept: application/json'
   ```

## Advanced Testing

### Test with Banking Scenario

1. **Create banking agent with MCP tools:**
   - Name: `Banking MCP Agent`
   - Tools: `mcp::dbstore` + knowledge bases
   - Prompt: Banking-specific prompt

2. **Test banking queries:**
   - *"Check the database for customer records for Tech Solutions LLC"*
   - *"Query loan applications from the last 6 months"*
   - *"Find suspicious transaction patterns"*

### Test Integration with RAG

1. **Create hybrid agent:**
   - Tools: `mcp::dbstore` + `builtin::rag`
   - Knowledge Bases: Banking compliance documents

2. **Test combined queries:**
   - *"What are the compliance requirements for this loan application, and check if we have any previous violations in our database?"*
   - *"Show me the fraud detection procedures and query our database for similar cases"*

## Performance Testing

### Response Time

- **Target:** < 5 seconds for database queries
- **Measurement:** Time from question to response
- **Tools:** Browser developer tools, API monitoring

### Concurrent Users

- **Test multiple agents** using MCP tools simultaneously
- **Monitor resource usage** during concurrent queries
- **Check for connection limits** or performance degradation

## Security Testing

### Access Control

- **Verify agent permissions** for database access
- **Test data isolation** between different agents
- **Check audit logs** for database queries

### Data Validation

- **Test SQL injection prevention**
- **Verify query parameter sanitization**
- **Check for sensitive data exposure**

## Monitoring

### Key Metrics

- **MCP Server Status:** Connection health
- **Query Success Rate:** Percentage of successful database queries
- **Response Time:** Average time for database operations
- **Error Rate:** Frequency of MCP-related errors

### Log Analysis

- **MCP Server Logs:** Database connection and query logs
- **Agent Logs:** Tool execution and response logs
- **LlamaStack Logs:** Tool discovery and routing logs

## Best Practices

### For Testing

1. **Start Simple:** Test basic database queries first
2. **Incremental Testing:** Add complexity gradually
3. **Document Results:** Keep track of what works and what doesn't
4. **Test Edge Cases:** Try unusual queries and error conditions

### For Production

1. **Monitor Performance:** Track response times and error rates
2. **Implement Caching:** Cache frequently accessed data
3. **Set Up Alerts:** Monitor for MCP server failures
4. **Regular Testing:** Schedule periodic MCP functionality tests

## Conclusion

This testing guide ensures that the MCP server integration is working correctly and provides a foundation for comprehensive testing of the AI Virtual Agent platform's database access capabilities.

For additional support, refer to:
- [FSI Demo Execution Checklist](FSI_DEMO_EXECUTION_CHECKLIST.md)
- [Virtual Agents Architecture](virtual-agents-architecture.md)
- [Backend API Documentation](backend/README.md) 