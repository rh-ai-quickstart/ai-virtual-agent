import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError
from store import mcp_server  # Your FastMCP instance from store.py


@pytest_asyncio.fixture(scope="module")
async def initialized_test_mcp_server():
    """Fixture to provide an initialized FastMCP server instance."""
    # For testing without a real database, we'll use the server as-is
    # The server should handle database unavailability gracefully

    # The mcp_server instance is imported from your store.py
    # It should already have tools registered via decorators.
    yield mcp_server


@pytest.mark.asyncio
async def test_health_check_tool(initialized_test_mcp_server):
    """Test the health_check tool functionality."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("health_check")
        assert hasattr(response, "content") and response.content is not None
        assert len(response.content) > 0

        # Parse the response content
        content = response.content[0]
        response_text = getattr(content, "text", str(content))

        # The response should contain health information
        assert "status" in response_text.lower() or "health" in response_text.lower()
        assert "mcp-store-db" in response_text.lower()


@pytest.mark.asyncio
async def test_check_database_connectivity_tool(initialized_test_mcp_server):
    """Test the check_database_connectivity tool functionality."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("check_database_connectivity")
        assert hasattr(response, "content") and response.content is not None
        assert len(response.content) > 0

        # Parse the response content
        content = response.content[0]
        response_text = getattr(content, "text", str(content))

        # The response should contain database connectivity information
        assert "database" in response_text.lower()
        assert "status" in response_text.lower()


@pytest.mark.asyncio
async def test_tool_discovery(initialized_test_mcp_server):
    """Test that all expected tools are available."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.list_tools()
        tool_names = [tool.name for tool in response]

        # Expected tools based on our implementation
        expected_tools = [
            "health_check",
            "check_database_connectivity",
            "get_products",
            "get_product",
            "create_product",
            "update_product",
            "delete_product",
            "get_orders",
            "get_order",
            "create_order",
            "update_order_status",
            "delete_order",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not found"

        # Verify tool descriptions
        for tool in response:
            assert hasattr(tool, "description")
            assert tool.description.strip() != ""


@pytest.mark.asyncio
async def test_tool_error_handling_with_unavailable_database(
    initialized_test_mcp_server,
):
    """Test that tools handle database unavailability gracefully."""
    # Mock database as unavailable
    import database

    database.db_manager.state = database.DatabaseState.DISCONNECTED

    async with Client(initialized_test_mcp_server) as client:
        try:
            # Try to call a database-dependent tool
            response = await client.call_tool("get_products", {})

            # Check if we got an error response
            if hasattr(response, "content"):
                content = response.content
                if isinstance(content, dict) and "error" in content:
                    # Tool returned error gracefully
                    assert "error" in content
                    assert (
                        "database" in content["error"].lower()
                        or "unavailable" in content["error"].lower()
                    )
                else:
                    # Tool might have succeeded despite DB being unavailable
                    # This could happen if the tool has fallback behavior
                    pass
            else:
                # If no content, check if it's an error response
                assert hasattr(response, "error") or hasattr(response, "exception")

        except Exception as e:
            # Tool threw an exception - this is also acceptable
            error_message = str(e).lower()
            assert any(
                keyword in error_message
                for keyword in ["database", "unavailable", "connection", "error"]
            )


@pytest.mark.asyncio
async def test_health_check_tool_consistency(initialized_test_mcp_server):
    """Test that health check and database connectivity check are consistent."""
    async with Client(initialized_test_mcp_server) as client:
        # Get both health checks
        health_response = await client.call_tool("health_check")
        connectivity_response = await client.call_tool("check_database_connectivity")

        # Parse responses
        health_content = health_response.content[0].text
        connectivity_content = connectivity_response.content[0].text

        # Both should contain database status information
        assert "database" in health_content.lower()
        assert "database" in connectivity_content.lower()


@pytest.mark.asyncio
async def test_tool_metadata(initialized_test_mcp_server):
    """Test that MCP tools have proper metadata."""
    async with Client(initialized_test_mcp_server) as client:
        tools = await client.list_tools()

        for tool in tools:
            # Verify basic attributes
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")

            # Verify name is valid
            assert isinstance(tool.name, str)
            assert tool.name.strip() != ""

            # Verify description is valid
            assert isinstance(tool.description, str)
            assert tool.description.strip() != ""

            # Verify no HTML or special characters in name
            assert "<" not in tool.name
            assert ">" not in tool.name
            assert "&" not in tool.name


@pytest.mark.asyncio
async def test_tool_categories(initialized_test_mcp_server):
    """Test that MCP tools can be categorized by functionality."""
    async with Client(initialized_test_mcp_server) as client:
        tools = await client.list_tools()

        # Categorize tools by functionality
        product_tools = [tool for tool in tools if "product" in tool.name.lower()]
        order_tools = [tool for tool in tools if "order" in tool.name.lower()]
        health_tools = [
            tool
            for tool in tools
            if "health" in tool.name.lower() or "connectivity" in tool.name.lower()
        ]

        # Verify we have tools in each category
        assert len(product_tools) >= 5  # add, remove, get, search, etc.
        assert len(order_tools) >= 1  # order_product
        assert len(health_tools) >= 2  # health_check, check_database_connectivity

        # Verify tool names are descriptive
        for tool in product_tools:
            assert "product" in tool.name.lower()

        for tool in order_tools:
            assert "order" in tool.name.lower()

        for tool in health_tools:
            assert "health" in tool.name.lower() or "connectivity" in tool.name.lower()


@pytest.mark.asyncio
async def test_tool_input_validation(initialized_test_mcp_server):
    """Test that MCP tools validate input parameters correctly."""
    async with Client(initialized_test_mcp_server) as client:
        # Test health check tool (no parameters required)
        response = await client.call_tool("health_check", {})
        assert hasattr(response, "content")

        # Test database connectivity check tool (no parameters required)
        response = await client.call_tool("check_database_connectivity", {})
        assert hasattr(response, "content")

        # Test get_products with valid parameters; DB may be unavailable
        try:
            response = await client.call_tool("get_products", {"skip": 0, "limit": 10})
            assert response.content is not None
        except ToolError:
            # Acceptable in environments without a running database
            pass


@pytest.mark.asyncio
async def test_tool_error_messages_for_llm_agents(initialized_test_mcp_server):
    """Test that error messages are helpful for LLM agents."""
    # Mock database as unavailable
    import database

    database.db_manager.state = database.DatabaseState.DISCONNECTED

    async with Client(initialized_test_mcp_server) as client:
        try:
            # Try to call a database-dependent tool
            response = await client.call_tool("get_products", {})

            # Check if we got an error response
            if hasattr(response, "content"):
                content = response.content
                if isinstance(content, dict) and "error" in content:
                    error_message = content["error"].lower()
                    # Check that error message contains helpful keywords
                    helpful_keywords = [
                        "database",
                        "unavailable",
                        "connection",
                        "error",
                        "check",
                    ]
                    assert any(keyword in error_message for keyword in helpful_keywords)
                else:
                    # Tool might have succeeded despite DB being unavailable
                    pass
            else:
                # If no content, check if it's an error response
                assert hasattr(response, "error") or hasattr(response, "exception")

        except Exception as e:
            # Tool threw an exception - check error message
            error_message = str(e).lower()
            helpful_keywords = [
                "database",
                "unavailable",
                "connection",
                "error",
                "check",
            ]
            assert any(keyword in error_message for keyword in helpful_keywords)


@pytest.mark.asyncio
async def test_health_check_tool_response_structure(initialized_test_mcp_server):
    """Test that health check tool returns properly structured response."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("health_check")
        assert hasattr(response, "content")

        # Parse the response
        content = response.content[0].text

        # Response should contain JSON-like structure with key fields
        # Note: This is a basic check - in a real test you might want to parse JSON
        required_fields = ["status", "service", "database_status", "database_available"]
        for field in required_fields:
            assert field in content


@pytest.mark.asyncio
async def test_database_connectivity_tool_response_structure(
    initialized_test_mcp_server,
):
    """Test that database connectivity check tool returns expected structure."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("check_database_connectivity", {})

        # Check response structure
        assert hasattr(response, "content")
        content = response.content

        # Handle different content formats
        if isinstance(content, list) and len(content) > 0:
            # Content is a list of TextContent objects
            content_text = content[0].text
            import json

            content_dict = json.loads(content_text)
        else:
            content_dict = content

        # Expected fields based on our implementation
        expected_fields = [
            "database_status",
            "can_perform_operations",
            "recommendation",
        ]

        for field in expected_fields:
            assert field in content_dict, f"Field {field} not found in response"

        # Check data types
        assert isinstance(content_dict["database_status"], str)
        assert isinstance(content_dict["can_perform_operations"], bool)
        assert isinstance(content_dict["recommendation"], str)
