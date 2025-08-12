import os
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP
mcp_server = FastMCP()

# Store API server URL - this will connect to the store-inventory API
STORE_API_URL = os.getenv("STORE_API_URL", "http://localhost:8002")

# HTTP client (using httpx) - provides connection pooling and reuse
async_client = httpx.AsyncClient(base_url=STORE_API_URL)


async def make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Helper function to make API requests to the Store API Server."""
    try:
        response = await async_client.request(
            method, endpoint, params=params, json=json_data
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        # (4xx or 5xx)
        return response.json()
    except httpx.HTTPStatusError as e:
        # Attempt to get more details from the response body if available
        error_detail = (
            e.response.json().get("detail", e.response.text)
            if e.response.content
            else str(e)
        )
        raise ValueError(
            f"API Error: {e.response.status_code} - {error_detail} when calling "
            f"{e.request.method} {e.request.url}"
        ) from e
    except httpx.RequestError as e:
        raise ValueError(
            f"Request Error: Could not connect to Store API Server at "
            f"{e.request.url}. Details: {str(e)}"
        ) from e


@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches a list of all products from the database.

    Args:
        skip: Number of products to skip (for pagination)
        limit: Maximum number of products to return (for pagination)

    Returns:
        List of product dictionaries containing id, name, description,
        inventory, and price
    """
    return await make_api_request(
        "GET", "/products/", params={"skip": skip, "limit": limit}
    )


@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its ID from the database.

    Args:
        product_id: The unique identifier of the product to retrieve

    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found
    """
    try:
        return await make_api_request("GET", f"/products/id/{product_id}")
    except ValueError as e:
        if "404" in str(e):  # crude check for 404
            return None  # Product not found
        raise


@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the database.

    Args:
        name: The exact name of the product to retrieve

    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found
    """
    try:
        return await make_api_request("GET", f"/products/name/{name}")
    except ValueError as e:
        if "404" in str(e):
            return None  # Product not found
        raise


@mcp_server.tool()
async def search_products(
    query: str, skip: int = 0, limit: int = 100
) -> List[Dict[str, Any]]:
    """Searches for products based on a query string (name or description).

    Args:
        query: Search term to match against product names and descriptions
        skip: Number of products to skip (for pagination)
        limit: Maximum number of products to return (for pagination)

    Returns:
        List of matching product dictionaries, empty list if no matches found
    """
    try:
        return await make_api_request(
            "GET",
            "/products/search/",
            params={"query": query, "skip": skip, "limit": limit},
        )
    except ValueError as e:
        if "404" in str(e):  # crude check for 404 when no products found
            return []
        raise


@mcp_server.tool()
async def add_product(
    name: str, description: Optional[str] = None, inventory: int = 0, price: float = 0.0
) -> Dict[str, Any]:
    """Adds a new product to the database.

    Args:
        name: The name of the product (required)
        description: Optional description of the product
        inventory: Initial inventory count (defaults to 0)
        price: Price of the product (defaults to 0.0)

    Returns:
        Created product dictionary with id, name, description, inventory, and price
    """
    payload = {
        "name": name,
        "description": description,
        "inventory": inventory,
        "price": price,
    }
    return await make_api_request("POST", "/products/", json_data=payload)


@mcp_server.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Removes a product from the database by its ID.

    Args:
        product_id: The unique identifier of the product to remove

    Returns:
        Removed product dictionary if found and deleted, None if product not found
    """
    try:
        return await make_api_request("DELETE", f"/products/{product_id}")
    except ValueError as e:
        if "404" in str(e):
            return None  # Product not found
        raise


@mcp_server.tool()
async def order_product(
    product_id: int, quantity: int, customer_identifier: str
) -> Dict[str, Any]:
    """Places an order for a product.
    This involves checking inventory, deducting the quantity from the product's
    inventory, and creating an order record in the database.

    Args:
        product_id: The unique identifier of the product to order
        quantity: The number of items to order
        customer_identifier: Identifier for the customer placing the order

    Returns:
        Created order dictionary with id, product_id, quantity, and customer_identifier

    Raises:
        ValueError: If product not found, insufficient inventory, or other API error
    """
    payload = {
        "product_id": product_id,
        "quantity": quantity,
        "customer_identifier": customer_identifier,
    }
    return await make_api_request("POST", "/orders/", json_data=payload)


# Add a simple health check endpoint for Kubernetes
@mcp_server.custom_route("/health", methods=["GET"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "mcp-store-inventory"}


# Note: FastMCP doesn't support lifecycle events like startup/shutdown
# The async_client is initialized at module level and will be cleaned up
# when the process terminates

if __name__ == "__main__":
    print("INFO:     Starting MCP Store Inventory server...")
    print(f"INFO:     Connecting to Store API at: {STORE_API_URL}")
    mcp_server.settings.port = 8003  # Different port to avoid conflicts
    mcp_server.run(transport="sse")
