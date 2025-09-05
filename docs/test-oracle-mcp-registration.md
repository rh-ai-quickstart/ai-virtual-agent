# Oracle MCP Server Registration Test

This document outlines the testing process for Oracle MCP server registration using the existing UI.

## Test Scenario

**Objective**: Verify Oracle MCP server can be registered through the standard MCP server UI without any code changes.

## Test Configuration

**Test Data (Following Existing Patterns)**:

```json
{
  "toolgroup_id": "mcp-oracle",
  "name": "Oracle Analytics", 
  "description": "TPC-DS business analytics tools for Oracle Database",
  "endpoint_url": "http://oracle-mcp-service:8003",
  "configuration": {
    "oracle_host": "oracle-service.an-oracle-23ai.svc.cluster.local",
    "oracle_port": "1521",
    "service_name": "FREEPDB1", 
    "username": "tpcds",
    "environment": "development"
  }
}
```

## Test Steps

### 1. Prerequisites Check
- [ ] AI Virtual Agent platform running
- [ ] Oracle MCP server deployed and accessible
- [ ] Admin user access to platform
- [ ] Oracle database connectivity confirmed

### 2. Registration Test via UI
- [ ] Navigate to Configuration > MCP Servers
- [ ] Click + icon to add new server
- [ ] Fill form with test data above
- [ ] Submit registration
- [ ] Verify success response
- [ ] Confirm server appears in list

### 3. Registration Test via API
Using curl or similar tool:

```bash
curl -X POST http://localhost:8000/api/mcp_servers \
  -H "Content-Type: application/json" \
  -d '{
    "toolgroup_id": "mcp-oracle",
    "name": "Oracle Analytics",
    "description": "TPC-DS business analytics tools for Oracle Database", 
    "endpoint_url": "http://oracle-mcp-service:8003",
    "configuration": {
      "oracle_host": "oracle-service.an-oracle-23ai.svc.cluster.local",
      "oracle_port": "1521",
      "service_name": "FREEPDB1",
      "username": "tpcds", 
      "environment": "development"
    }
  }'
```

### 4. Verification Tests
- [ ] List MCP servers shows Oracle server
- [ ] Server details display correctly
- [ ] Configuration JSON appears properly formatted
- [ ] Endpoint URL is accessible
- [ ] Provider ID shows "model-context-protocol"

### 5. Agent Integration Test
- [ ] Create or edit an agent
- [ ] Oracle Analytics tools appear in available tools
- [ ] Can select Oracle tools for agent
- [ ] Agent configuration saves successfully

### 6. Functional Test
Test Oracle MCP functionality through agent chat:

**Test Queries**:
1. "Show me a summary of TPC-DS tables"
2. "Get customer insights for 5 customers"  
3. "Show me top 3 selling products by revenue"

**Expected Results**:
- [ ] Agent responds with Oracle data
- [ ] Queries execute successfully
- [ ] Results format correctly
- [ ] No errors in execution

## Test Results Template

### Registration Test Results

**Date**: ___________  
**Tester**: ___________  
**Platform Version**: ___________

**UI Registration**: ✅ Pass / ❌ Fail  
**API Registration**: ✅ Pass / ❌ Fail  
**Server Listing**: ✅ Pass / ❌ Fail  
**Agent Integration**: ✅ Pass / ❌ Fail  
**Functional Testing**: ✅ Pass / ❌ Fail

**Notes**:
_____________________________________________
_____________________________________________

### Performance Metrics

**Registration Time**: _____ seconds  
**Query Response Time**: _____ seconds  
**Tool Discovery Time**: _____ seconds

## Success Criteria

✅ **PASS**: All tests complete successfully  
- Oracle MCP server registers without errors
- Server appears in UI correctly  
- Agent can use Oracle tools
- Queries return expected data
- No code changes required

❌ **FAIL**: Any test fails or requires code modifications

## Compliance Verification

**Pattern Compliance Check**:
- [ ] Toolgroup ID follows "mcp-*" pattern
- [ ] Endpoint URL matches service pattern
- [ ] Configuration uses standard JSON object
- [ ] No custom UI components required
- [ ] No backend API modifications needed
- [ ] Uses existing MCPServerCreate/Read schemas

## Rollback Plan

If testing reveals issues:

1. **Remove Test Registration**: Delete mcp-oracle from MCP servers list
2. **Clean LlamaStack**: Unregister toolgroup from LlamaStack  
3. **Restore State**: Ensure platform returns to original state
4. **Document Issues**: Log any problems for resolution

## Next Steps

Upon successful testing:

1. **Document Results**: Update this file with test outcomes
2. **Create PR**: Submit documentation changes only
3. **User Training**: Share Oracle MCP setup guide
4. **Monitor Usage**: Track Oracle MCP server adoption

---

**Test Status**: 🟡 Ready for Testing  
**Last Updated**: December 2024  
**Reviewer**: _______________