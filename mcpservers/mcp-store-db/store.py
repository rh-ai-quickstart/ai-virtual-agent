import asyncio
import datetime
from typing import Any, Dict, List, Optional

import crud
from crud import DatabaseOperationError, DatabaseUnavailableError
from fastmcp import FastMCP, settings
from starlette.requests import Request
from starlette.responses import JSONResponse

import database
import models as PydanticModels

# Initialize FastMCP
mcp_server = FastMCP()

# Set port for FastMCP
settings.port = 8002


@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    """Retrieve a list of products with pagination."""
    try:
        async with database.db_manager.get_session() as db:
            products = await crud.get_products(db, skip=skip, limit=limit)
            return {
                "products": [product.to_dict() for product in products],
                "total": len(products),
                "skip": skip,
                "limit": limit,
            }
    except Exception as e:
        return {
            "error": str(e),
            "products": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
        }


@mcp_server.tool()
async def get_product(product_id: int) -> Dict[str, Any]:
    """Retrieve a specific product by ID."""
    try:
        async with database.db_manager.get_session() as db:
            product = await crud.get_product(db, product_id)
            if product:
                return {
                    "product": product.to_dict(),
                    "found": True,
                }
            else:
                return {
                    "product": None,
                    "found": False,
                    "message": f"Product with ID {product_id} not found",
                }
    except Exception as e:
        return {
            "error": str(e),
            "product": None,
            "found": False,
        }


@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the database.

    Args:
        name: The exact name of the product to retrieve

    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found

    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database "
                "connection and ensure the PostgreSQL service is running."
            )

        db_product = await crud.get_product_by_name(session, name=name)
        result = None
        if db_product:
            result = PydanticModels.Product.model_validate(db_product).model_dump()

        await session.close()
        return result

    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def search_products(
    query: str, skip: int = 0, limit: int = 100
) -> List[Dict[str, Any]]:
    """Searches for products based on a query string (name or description).

    Args:
        query: Search term to match against product names and descriptions
        skip: Number of products to skip (for pagination)
        limit: Maximum products to return (for pagination)

    Returns:
        List of matching product dictionaries, empty list if no matches found

    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database "
                "connection and ensure the PostgreSQL service is running."
            )

        db_products = await crud.search_products(
            session, query=query, skip=skip, limit=limit
        )
        result = [
            PydanticModels.Product.model_validate(p).model_dump() for p in db_products
        ]
        await session.close()
        return result

    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def create_product(
    name: str, description: str, inventory: int, price: float
) -> Dict[str, Any]:
    """Create a new product."""
    try:
        async with database.db_manager.get_session() as db:
            product = await crud.create_product(
                db, name=name, description=description, inventory=inventory, price=price
            )
            return {
                "product": product.to_dict(),
                "created": True,
                "message": "Product created successfully",
            }
    except Exception as e:
        return {
            "error": str(e),
            "product": None,
            "created": False,
        }


@mcp_server.tool()
async def update_product(
    product_id: int,
    name: str = None,
    description: str = None,
    inventory: int = None,
    price: float = None,
) -> Dict[str, Any]:
    """Update an existing product."""
    try:
        async with database.db_manager.get_session() as db:
            product = await crud.update_product(
                db,
                product_id,
                name=name,
                description=description,
                inventory=inventory,
                price=price,
            )
            if product:
                return {
                    "product": product.to_dict(),
                    "updated": True,
                    "message": "Product updated successfully",
                }
            else:
                return {
                    "product": None,
                    "updated": False,
                    "message": f"Product with ID {product_id} not found",
                }
    except Exception as e:
        return {
            "error": str(e),
            "product": None,
            "updated": False,
        }


@mcp_server.tool()
async def delete_product(product_id: int) -> Dict[str, Any]:
    """Delete a product by ID."""
    try:
        async with database.db_manager.get_session() as db:
            success = await crud.delete_product(db, product_id)
            if success:
                return {
                    "deleted": True,
                    "message": f"Product with ID {product_id} deleted successfully",
                }
            else:
                return {
                    "deleted": False,
                    "message": f"Product with ID {product_id} not found",
                }
    except Exception as e:
        return {
            "error": str(e),
            "deleted": False,
        }


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
        ValueError: If product not found, insufficient inventory, or other business
        logic error
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database "
                "connection and ensure the PostgreSQL service is running."
            )

        order_request = PydanticModels.ProductOrderRequest(
            product_id=product_id,
            quantity=quantity,
            customer_identifier=customer_identifier,
        )

        try:
            db_order = await crud.order_product(session, order_details=order_request)
            result = PydanticModels.Order.model_validate(db_order).model_dump()

            await session.commit()
            await session.close()
            return result

        except ValueError:
            await session.rollback()
            await session.close()
            raise
        except Exception:
            await session.rollback()
            await session.close()
            raise

    except ValueError:
        # Re-raise business logic errors
        raise
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def create_order(
    customer_name: str, customer_email: str, product_ids: list[int]
) -> Dict[str, Any]:
    """Create a new order."""
    try:
        async with database.db_manager.get_session() as db:
            order = await crud.create_order(
                db,
                customer_name=customer_name,
                customer_email=customer_email,
                product_ids=product_ids,
            )
            return {
                "order": order.to_dict(),
                "created": True,
                "message": "Order created successfully",
            }
    except Exception as e:
        return {
            "error": str(e),
            "order": None,
            "created": False,
        }


@mcp_server.tool()
async def get_orders(skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    """Retrieve a list of orders with pagination."""
    try:
        async with database.db_manager.get_session() as db:
            orders = await crud.get_orders(db, skip=skip, limit=limit)
            return {
                "orders": [order.to_dict() for order in orders],
                "total": len(orders),
                "skip": skip,
                "limit": limit,
            }
    except Exception as e:
        return {
            "error": str(e),
            "orders": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
        }


@mcp_server.tool()
async def get_order(order_id: int) -> Dict[str, Any]:
    """Retrieve a specific order by ID."""
    try:
        async with database.db_manager.get_session() as db:
            order = await crud.get_order(db, order_id)
            if order:
                return {
                    "order": order.to_dict(),
                    "found": True,
                }
            else:
                return {
                    "order": None,
                    "found": False,
                    "message": f"Order with ID {order_id} not found",
                }
    except Exception as e:
        return {
            "error": str(e),
            "order": None,
            "found": False,
        }


@mcp_server.tool()
async def update_order_status(order_id: int, status: str) -> Dict[str, Any]:
    """Update the status of an order."""
    try:
        async with database.db_manager.get_session() as db:
            order = await crud.update_order_status(db, order_id, status)
            if order:
                return {
                    "order": order.to_dict(),
                    "updated": True,
                    "message": f"Order status updated to {status}",
                }
            else:
                return {
                    "order": None,
                    "updated": False,
                    "message": f"Order with ID {order_id} not found",
                }
    except Exception as e:
        return {
            "error": str(e),
            "order": None,
            "updated": False,
        }


@mcp_server.tool()
async def delete_order(order_id: int) -> Dict[str, Any]:
    """Delete an order by ID."""
    try:
        async with database.db_manager.get_session() as db:
            success = await crud.delete_order(db, order_id)
            if success:
                return {
                    "deleted": True,
                    "message": f"Order with ID {order_id} deleted successfully",
                }
            else:
                return {
                    "deleted": False,
                    "message": f"Order with ID {order_id} not found",
                }
    except Exception as e:
        return {
            "error": str(e),
            "deleted": False,
        }


@mcp_server.tool()
async def health_check() -> Dict[str, Any]:
    """Check the health status of the MCP server and database connectivity."""
    db_state = database.db_manager.get_state()
    db_available = database.db_manager.is_available()
    return {
        "status": "healthy",
        "service": "mcp-store-db",
        "database_status": db_state.value,
        "database_available": db_available,
        "database_url": database.DATABASE_URL,
        "timestamp": str(datetime.datetime.now()),
        "message": "MCP server is running and ready to process requests",
    }


@mcp_server.tool()
async def check_database_connectivity() -> Dict[str, Any]:
    """Check database connectivity and provide status information."""
    db_state = database.db_manager.get_state()
    db_available = database.db_manager.is_available()

    if db_available:
        return {
            "database_status": db_state.value,
            "can_perform_operations": True,
            "recommendation": "No action needed",
        }
    else:
        return {
            "database_status": db_state.value,
            "can_perform_operations": False,
            "recommendation": "Check database connection and configuration",
        }


# Add custom HTTP endpoints using FastMCP
@mcp_server.custom_route("/health", methods=["GET"])
async def health_endpoint(_request: Request) -> JSONResponse:
    """HTTP health check endpoint for container orchestration and monitoring."""
    db_state = database.db_manager.get_state()
    db_available = database.db_manager.is_available()

    return JSONResponse(
        {
            "status": "healthy",  # MCP server is always healthy if running
            "service": "mcp-store-db",
            "database_status": db_state.value,
            "database_available": db_available,
            "database_url": database.DATABASE_URL,
            "message": "MCP server is running and ready to process requests",
        }
    )


@mcp_server.custom_route("/tools", methods=["GET"])
async def tools_endpoint(_request: Request) -> JSONResponse:
    """HTTP endpoint to list all available MCP tools."""
    try:
        tools = await mcp_server.get_tools()
        tool_list = []
        for name, tool in tools.items():
            tool_info = {
                "name": name,
                "description": tool.description or "No description available",
                "input_schema": (
                    tool.input_schema if hasattr(tool, "input_schema") else None
                ),
                "output_schema": (
                    tool.output_schema if hasattr(tool, "output_schema") else None
                ),
                "tags": list(tool.tags) if hasattr(tool, "tags") and tool.tags else [],
                "enabled": tool.enabled if hasattr(tool, "enabled") else True,
            }
            tool_list.append(tool_info)

        return JSONResponse(
            {
                "service": "mcp-store-db",
                "total_tools": len(tool_list),
                "tools": tool_list,
            }
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to retrieve tools: {str(e)}"}, status_code=500
        )


async def run_startup_tasks():
    """Initialize the MCP server and database manager."""
    print("INFO:     MCP_Store_DB Server startup tasks beginning...")

    try:
        await database.db_manager.initialize()
        print("INFO:     MCP_Store_DB database manager initialized successfully.")
    except Exception as e:
        print(f"WARNING:  Database initialization failed: {e}")
        print(
            "INFO:     MCP server will start but database operations will be "
            "unavailable."
        )

    print("INFO:     MCP_Store_DB Server core initialization complete.")


async def run_shutdown_tasks():
    """Cleanup tasks for graceful shutdown."""
    print("INFO:     MCP_Store_DB Server shutdown tasks beginning...")
    await database.db_manager.shutdown()
    print("INFO:     MCP_Store_DB Server shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(run_startup_tasks())
        print("INFO:     Starting MCP_Store_DB FastMCP server on port 8002...")
        mcp_server.run(transport="sse")
    except KeyboardInterrupt:
        print("\nINFO:     Shutdown signal received...")
        asyncio.run(run_shutdown_tasks())
    except Exception as e:
        print(f"ERROR:    Server startup failed: {e}")
        asyncio.run(run_shutdown_tasks())
        raise
