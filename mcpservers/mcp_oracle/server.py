import asyncio
import structlog
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from .database import get_oracle_connection, settings, test_connection

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
server = Server("mcp-oracle")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="health_check",
            description="Health check endpoint for monitoring Oracle MCP server status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_tpcds_summary", 
            description="Get summary of TPC-DS tables and row counts",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_customer_insights",
            description="Get customer demographic insights from TPC-DS data",
            inputSchema={
                "type": "object", 
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of customers to return (1-10000)",
                        "default": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_sales_analytics",
            description="Get sales analytics from TPC-DS store sales data",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "default": "2020-01-01"
                    },
                    "end_date": {
                        "type": "string", 
                        "description": "End date in YYYY-MM-DD format",
                        "default": "2023-12-31"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of sales records to return (1-50000)",
                        "default": 1000
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_top_selling_products",
            description="Get top-selling products by revenue or quantity",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of products to return (1-100)",
                        "default": 10
                    },
                    "time_period": {
                        "type": "string",
                        "description": "Time period: all, last_year, last_quarter, last_month",
                        "default": "all"
                    },
                    "metric": {
                        "type": "string",
                        "description": "Metric to sort by: revenue or quantity",
                        "default": "revenue"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_inventory_insights",
            description="Get inventory analysis with low stock alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "low_stock_threshold": {
                        "type": "integer",
                        "description": "Threshold for low stock alerts (1-10000)",
                        "default": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_store_performance",
            description="Get store performance analysis and comparison",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="execute_custom_query",
            description="Execute custom SQL queries with safety constraints",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute"
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum number of rows to return (1-10000)",
                        "default": 1000
                    }
                },
                "required": ["sql_query"]
            }
        ),
        Tool(
            name="get_kpi_dashboard",
            description="Get key performance indicators dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "description": "Date range: all, last_month, last_quarter, last_year, ytd",
                        "default": "last_month"
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    if name == "health_check":
        result = await health_check()
    elif name == "get_tpcds_summary":
        result = await get_tpcds_summary()
    elif name == "get_customer_insights":
        limit = arguments.get("limit", 100)
        result = await get_customer_insights(limit)
    elif name == "get_sales_analytics":
        start_date = arguments.get("start_date", "2020-01-01")
        end_date = arguments.get("end_date", "2023-12-31")
        limit = arguments.get("limit", 1000)
        result = await get_sales_analytics(start_date, end_date, limit)
    elif name == "get_top_selling_products":
        limit = arguments.get("limit", 10)
        time_period = arguments.get("time_period", "all")
        metric = arguments.get("metric", "revenue")
        result = await get_top_selling_products(limit, time_period, metric)
    elif name == "get_inventory_insights":
        low_stock_threshold = arguments.get("low_stock_threshold", 100)
        result = await get_inventory_insights(low_stock_threshold)
    elif name == "get_store_performance":
        result = await get_store_performance()
    elif name == "execute_custom_query":
        sql_query = arguments.get("sql_query", "")
        max_rows = arguments.get("max_rows", 1000)
        result = await execute_custom_query(sql_query, max_rows)
    elif name == "get_kpi_dashboard":
        date_range = arguments.get("date_range", "last_month")
        result = await get_kpi_dashboard(date_range)
    else:
        raise ValueError(f"Unknown tool: {name}")
    
    return [TextContent(type="text", text=str(result))]

async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring Oracle MCP server status."""
    try:
        db_healthy = test_connection()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": structlog.processors.TimeStamper(fmt="iso"),
            "database_connection": "ok" if db_healthy else "failed",
            "server_info": {
                "environment": settings.environment,
                "oracle_host": settings.oracle_host,
                "oracle_port": settings.oracle_port,
                "service_name": settings.oracle_service_name
            }
        }
        
        logger.info("Health check performed", **health_status)
        return health_status
        
    except Exception as e:
        error_status = {
            "status": "error",
            "error": str(e),
            "timestamp": structlog.processors.TimeStamper(fmt="iso")
        }
        logger.error("Health check failed", **error_status)
        return error_status

async def get_tpcds_summary() -> Dict[str, Any]:
    """Get summary of TPC-DS tables and row counts."""
    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                # Get TPC-DS table information
                cursor.execute("""
                    SELECT table_name, num_rows 
                    FROM user_tables 
                    WHERE table_name IN (
                        'CUSTOMER', 'STORE_SALES', 'ITEM', 'DATE_DIM',
                        'CUSTOMER_ADDRESS', 'INVENTORY', 'CATALOG_SALES',
                        'WEB_SALES', 'STORE_RETURNS', 'CATALOG_RETURNS',
                        'WEB_RETURNS', 'PROMOTION', 'WAREHOUSE', 'STORE'
                    )
                    ORDER BY num_rows DESC NULLS LAST, table_name
                """)
                
                tables = cursor.fetchall()
                
                table_info = [
                    {
                        "table_name": table_name,
                        "row_count": row_count or 0
                    }
                    for table_name, row_count in tables
                ]
                
                total_rows = sum(info["row_count"] for info in table_info)
                
                result = {
                    "status": "success",
                    "summary": {
                        "total_tables": len(table_info),
                        "total_rows": total_rows,
                        "tables": table_info
                    }
                }
                
                logger.info("TPC-DS summary retrieved", table_count=len(table_info), total_rows=total_rows)
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve TPC-DS summary"
        }
        logger.error("TPC-DS summary failed", error=str(e))
        return error_result

async def get_customer_insights(limit: int = 100) -> Dict[str, Any]:
    """Get customer demographic insights from TPC-DS data."""
    try:
        # Input validation
        if limit <= 0 or limit > 10000:
            return {
                "status": "error",
                "error": "Limit must be between 1 and 10000"
            }
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.c_customer_sk,
                        c.c_salutation,
                        c.c_first_name,
                        c.c_last_name,
                        ca.ca_city,
                        ca.ca_state,
                        cd.cd_gender,
                        cd.cd_marital_status,
                        cd.cd_education_status
                    FROM CUSTOMER c
                    JOIN CUSTOMER_ADDRESS ca ON c.c_current_addr_sk = ca.ca_address_sk
                    JOIN CUSTOMER_DEMOGRAPHICS cd ON c.c_current_cdemo_sk = cd.cd_demo_sk
                    WHERE ROWNUM <= :limit
                    ORDER BY c.c_customer_sk
                """, {"limit": limit})
                
                customers = cursor.fetchall()
                
                customer_data = [
                    {
                        "customer_id": row[0],
                        "name": f"{row[1] or ''} {row[2] or ''} {row[3] or ''}".strip(),
                        "location": f"{row[4] or ''}, {row[5] or ''}".strip(", "),
                        "demographics": {
                            "gender": row[6],
                            "marital_status": row[7],
                            "education": row[8]
                        }
                    }
                    for row in customers
                ]
                
                result = {
                    "status": "success",
                    "data": {
                        "customers": customer_data,
                        "count": len(customer_data),
                        "limit_applied": limit
                    }
                }
                
                logger.info("Customer insights retrieved", customer_count=len(customer_data))
                return result
                
    except Exception as e:
        error_result = {
            "status": "error", 
            "error": str(e),
            "message": "Failed to retrieve customer insights"
        }
        logger.error("Customer insights failed", error=str(e))
        return error_result

async def get_sales_analytics(
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    limit: int = 1000
) -> Dict[str, Any]:
    """Get sales analytics from TPC-DS store sales data."""
    try:
        # Input validation
        if limit <= 0 or limit > 50000:
            return {
                "status": "error",
                "error": "Limit must be between 1 and 50000"
            }
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        d.d_date,
                        s.s_store_name,
                        i.i_item_desc,
                        ss.ss_quantity,
                        ss.ss_list_price,
                        ss.ss_sales_price,
                        ss.ss_net_paid
                    FROM STORE_SALES ss
                    JOIN DATE_DIM d ON ss.ss_sold_date_sk = d.d_date_sk
                    JOIN STORE s ON ss.ss_store_sk = s.s_store_sk  
                    JOIN ITEM i ON ss.ss_item_sk = i.i_item_sk
                    WHERE d.d_date BETWEEN TO_DATE(:start_date, 'YYYY-MM-DD') 
                                     AND TO_DATE(:end_date, 'YYYY-MM-DD')
                    AND ROWNUM <= :limit
                    ORDER BY d.d_date DESC, ss.ss_net_paid DESC
                """, {
                    "start_date": start_date,
                    "end_date": end_date, 
                    "limit": limit
                })
                
                sales = cursor.fetchall()
                
                sales_data = [
                    {
                        "sale_date": row[0].strftime("%Y-%m-%d") if row[0] else None,
                        "store_name": row[1],
                        "item_description": row[2],
                        "quantity": float(row[3]) if row[3] else 0,
                        "list_price": float(row[4]) if row[4] else 0,
                        "sales_price": float(row[5]) if row[5] else 0,
                        "net_paid": float(row[6]) if row[6] else 0
                    }
                    for row in sales
                ]
                
                # Calculate summary statistics
                total_sales = sum(sale["net_paid"] for sale in sales_data)
                avg_sale = total_sales / len(sales_data) if sales_data else 0
                
                result = {
                    "status": "success",
                    "data": {
                        "sales": sales_data,
                        "summary": {
                            "total_transactions": len(sales_data),
                            "total_sales_amount": round(total_sales, 2),
                            "average_sale_amount": round(avg_sale, 2),
                            "date_range": f"{start_date} to {end_date}"
                        }
                    }
                }
                
                logger.info("Sales analytics retrieved", 
                          transaction_count=len(sales_data), 
                          total_amount=total_sales)
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e), 
            "message": "Failed to retrieve sales analytics"
        }
        logger.error("Sales analytics failed", error=str(e))
        return error_result

async def get_top_selling_products(
    limit: int = 10,
    time_period: str = "all",
    metric: str = "revenue"
) -> Dict[str, Any]:
    """Get top-selling products by revenue or quantity."""
    try:
        # Input validation
        if limit <= 0 or limit > 100:
            return {
                "status": "error",
                "error": "Limit must be between 1 and 100"
            }
        
        if metric not in ["revenue", "quantity"]:
            return {
                "status": "error", 
                "error": "Metric must be 'revenue' or 'quantity'"
            }
        
        # Build date filter
        date_filter = ""
        if time_period == "last_year":
            date_filter = "AND d.d_year = 2023"
        elif time_period == "last_quarter":
            date_filter = "AND d.d_year = 2023 AND d.d_qoy = 4"
        elif time_period == "last_month":
            date_filter = "AND d.d_year = 2023 AND d.d_moy = 12"
        # "all" means no additional filter
        
        order_by = "total_revenue DESC" if metric == "revenue" else "total_quantity DESC"
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT 
                        i.i_item_sk,
                        i.i_item_desc,
                        i.i_category,
                        i.i_brand,
                        SUM(ss.ss_quantity) as total_quantity,
                        SUM(ss.ss_net_paid) as total_revenue,
                        AVG(ss.ss_sales_price) as avg_price,
                        COUNT(*) as transaction_count
                    FROM STORE_SALES ss
                    JOIN ITEM i ON ss.ss_item_sk = i.i_item_sk
                    JOIN DATE_DIM d ON ss.ss_sold_date_sk = d.d_date_sk
                    WHERE 1=1 {date_filter}
                    GROUP BY i.i_item_sk, i.i_item_desc, i.i_category, i.i_brand
                    ORDER BY {order_by}
                    FETCH FIRST :limit ROWS ONLY
                """, {"limit": limit})
                
                products = cursor.fetchall()
                
                product_data = [
                    {
                        "item_id": row[0],
                        "description": row[1],
                        "category": row[2],
                        "brand": row[3],
                        "total_quantity": float(row[4]) if row[4] else 0,
                        "total_revenue": float(row[5]) if row[5] else 0,
                        "average_price": float(row[6]) if row[6] else 0,
                        "transaction_count": int(row[7]) if row[7] else 0
                    }
                    for row in products
                ]
                
                total_revenue = sum(p["total_revenue"] for p in product_data)
                total_quantity = sum(p["total_quantity"] for p in product_data)
                
                result = {
                    "status": "success",
                    "data": {
                        "products": product_data,
                        "summary": {
                            "metric": metric,
                            "time_period": time_period,
                            "total_products": len(product_data),
                            "total_revenue": round(total_revenue, 2),
                            "total_quantity": int(total_quantity)
                        }
                    }
                }
                
                logger.info("Top selling products retrieved", 
                          product_count=len(product_data),
                          metric=metric,
                          time_period=time_period)
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve top selling products"
        }
        logger.error("Top selling products failed", error=str(e))
        return error_result

async def get_inventory_insights(low_stock_threshold: int = 100) -> Dict[str, Any]:
    """Get inventory analysis with low stock alerts."""
    try:
        # Input validation
        if low_stock_threshold <= 0 or low_stock_threshold > 10000:
            return {
                "status": "error",
                "error": "Low stock threshold must be between 1 and 10000"
            }
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                # Get inventory insights
                cursor.execute("""
                    SELECT 
                        i.i_item_sk,
                        i.i_item_desc,
                        i.i_category,
                        i.i_brand,
                        inv.inv_quantity_on_hand,
                        w.w_warehouse_name,
                        CASE 
                            WHEN inv.inv_quantity_on_hand <= :threshold THEN 'LOW'
                            WHEN inv.inv_quantity_on_hand <= :threshold * 2 THEN 'MEDIUM'
                            ELSE 'HIGH'
                        END as stock_level
                    FROM INVENTORY inv
                    JOIN ITEM i ON inv.inv_item_sk = i.i_item_sk
                    JOIN WAREHOUSE w ON inv.inv_warehouse_sk = w.w_warehouse_sk
                    ORDER BY inv.inv_quantity_on_hand ASC, i.i_item_desc
                    FETCH FIRST 200 ROWS ONLY
                """, {"threshold": low_stock_threshold})
                
                inventory = cursor.fetchall()
                
                inventory_data = [
                    {
                        "item_id": row[0],
                        "description": row[1],
                        "category": row[2],
                        "brand": row[3],
                        "quantity_on_hand": int(row[4]) if row[4] else 0,
                        "warehouse": row[5],
                        "stock_level": row[6]
                    }
                    for row in inventory
                ]
                
                # Calculate summary statistics
                low_stock_items = [item for item in inventory_data if item["stock_level"] == "LOW"]
                medium_stock_items = [item for item in inventory_data if item["stock_level"] == "MEDIUM"]
                high_stock_items = [item for item in inventory_data if item["stock_level"] == "HIGH"]
                
                total_quantity = sum(item["quantity_on_hand"] for item in inventory_data)
                
                result = {
                    "status": "success",
                    "data": {
                        "inventory": inventory_data,
                        "summary": {
                            "total_items": len(inventory_data),
                            "low_stock_count": len(low_stock_items),
                            "medium_stock_count": len(medium_stock_items),
                            "high_stock_count": len(high_stock_items),
                            "total_quantity": total_quantity,
                            "low_stock_threshold": low_stock_threshold
                        },
                        "alerts": {
                            "low_stock_items": low_stock_items[:10]  # Top 10 urgent items
                        }
                    }
                }
                
                logger.info("Inventory insights retrieved",
                          total_items=len(inventory_data),
                          low_stock_count=len(low_stock_items))
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve inventory insights"
        }
        logger.error("Inventory insights failed", error=str(e))
        return error_result

async def get_store_performance() -> Dict[str, Any]:
    """Get store performance analysis and comparison."""
    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                # Get store performance metrics
                cursor.execute("""
                    SELECT 
                        s.s_store_sk,
                        s.s_store_name,
                        s.s_city,
                        s.s_state,
                        COUNT(DISTINCT ss.ss_ticket_number) as total_transactions,
                        SUM(ss.ss_quantity) as total_quantity_sold,
                        SUM(ss.ss_net_paid) as total_revenue,
                        AVG(ss.ss_net_paid) as avg_transaction_value,
                        COUNT(DISTINCT ss.ss_customer_sk) as unique_customers
                    FROM STORE s
                    LEFT JOIN STORE_SALES ss ON s.s_store_sk = ss.ss_store_sk
                    GROUP BY s.s_store_sk, s.s_store_name, s.s_city, s.s_state
                    ORDER BY total_revenue DESC NULLS LAST
                """)
                
                stores = cursor.fetchall()
                
                store_data = [
                    {
                        "store_id": row[0],
                        "store_name": row[1],
                        "city": row[2],
                        "state": row[3],
                        "total_transactions": int(row[4]) if row[4] else 0,
                        "total_quantity_sold": float(row[5]) if row[5] else 0,
                        "total_revenue": float(row[6]) if row[6] else 0,
                        "avg_transaction_value": float(row[7]) if row[7] else 0,
                        "unique_customers": int(row[8]) if row[8] else 0
                    }
                    for row in stores
                ]
                
                # Calculate performance rankings
                active_stores = [store for store in store_data if store["total_revenue"] > 0]
                total_revenue = sum(store["total_revenue"] for store in active_stores)
                
                for i, store in enumerate(active_stores):
                    store["revenue_rank"] = i + 1
                    store["revenue_share"] = round((store["total_revenue"] / total_revenue * 100), 2) if total_revenue > 0 else 0
                
                result = {
                    "status": "success",
                    "data": {
                        "stores": store_data,
                        "summary": {
                            "total_stores": len(store_data),
                            "active_stores": len(active_stores),
                            "total_revenue": round(total_revenue, 2),
                            "avg_revenue_per_store": round(total_revenue / len(active_stores), 2) if active_stores else 0,
                            "top_performer": active_stores[0] if active_stores else None
                        }
                    }
                }
                
                logger.info("Store performance retrieved",
                          total_stores=len(store_data),
                          active_stores=len(active_stores))
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve store performance"
        }
        logger.error("Store performance failed", error=str(e))
        return error_result

async def execute_custom_query(
    sql_query: str,
    max_rows: int = 1000
) -> Dict[str, Any]:
    """Execute custom SQL queries with safety constraints."""
    try:
        # Input validation
        if max_rows <= 0 or max_rows > 10000:
            return {
                "status": "error",
                "error": "Max rows must be between 1 and 10000"
            }
        
        # Security validation - only allow SELECT statements
        query_upper = sql_query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return {
                "status": "error",
                "error": "Only SELECT queries are allowed"
            }
        
        # Block dangerous keywords
        dangerous_keywords = ["DELETE", "UPDATE", "INSERT", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "status": "error",
                    "error": f"Query contains forbidden keyword: {keyword}"
                }
        
        # Add ROWNUM limit if not present
        if "ROWNUM" not in query_upper and "FETCH" not in query_upper:
            if "WHERE" in query_upper:
                # Insert ROWNUM condition after the first WHERE
                where_pos = sql_query.upper().find("WHERE")
                sql_query = sql_query[:where_pos + 5] + f" ROWNUM <= {max_rows} AND" + sql_query[where_pos + 5:]
            else:
                # Add WHERE clause at the end, before ORDER BY if present
                if "ORDER BY" in query_upper:
                    order_pos = sql_query.upper().find("ORDER BY")
                    sql_query = sql_query[:order_pos] + f" WHERE ROWNUM <= {max_rows} " + sql_query[order_pos:]
                else:
                    sql_query += f" WHERE ROWNUM <= {max_rows}"
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                
                # Fetch data
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                data = [
                    {columns[i]: (row[i].strftime("%Y-%m-%d %H:%M:%S") if hasattr(row[i], 'strftime') else row[i])
                     for i in range(len(columns))}
                    for row in rows
                ]
                
                result = {
                    "status": "success",
                    "data": {
                        "columns": columns,
                        "rows": data,
                        "row_count": len(data),
                        "query": sql_query
                    }
                }
                
                logger.info("Custom query executed",
                          row_count=len(data),
                          column_count=len(columns))
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to execute custom query"
        }
        logger.error("Custom query failed", error=str(e), query=sql_query[:100])
        return error_result

async def get_kpi_dashboard(date_range: str = "last_month") -> Dict[str, Any]:
    """Get key performance indicators dashboard."""
    try:
        # Build date filter based on range
        date_filter = ""
        if date_range == "last_month":
            date_filter = "AND d.d_year = 2023 AND d.d_moy = 12"
        elif date_range == "last_quarter":
            date_filter = "AND d.d_year = 2023 AND d.d_qoy = 4"
        elif date_range == "last_year":
            date_filter = "AND d.d_year = 2023"
        elif date_range == "ytd":
            date_filter = "AND d.d_year = 2023"
        # "all" means no filter
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                # Revenue metrics
                cursor.execute(f"""
                    SELECT 
                        SUM(ss.ss_net_paid) as total_revenue,
                        COUNT(DISTINCT ss.ss_ticket_number) as total_transactions,
                        COUNT(DISTINCT ss.ss_customer_sk) as unique_customers,
                        AVG(ss.ss_net_paid) as avg_transaction_value,
                        SUM(ss.ss_quantity) as total_items_sold
                    FROM STORE_SALES ss
                    JOIN DATE_DIM d ON ss.ss_sold_date_sk = d.d_date_sk
                    WHERE 1=1 {date_filter}
                """)
                
                revenue_data = cursor.fetchone()
                
                # Customer metrics
                cursor.execute("""
                    SELECT COUNT(*) as total_customers FROM CUSTOMER
                """)
                total_customers = cursor.fetchone()[0]
                
                # Inventory metrics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_items,
                        SUM(inv_quantity_on_hand) as total_inventory_value
                    FROM INVENTORY
                """)
                inventory_data = cursor.fetchone()
                
                # Store metrics
                cursor.execute("""
                    SELECT COUNT(*) as total_stores FROM STORE
                """)
                total_stores = cursor.fetchone()[0]
                
                # Return metrics
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_returns,
                        SUM(sr.sr_return_amt) as total_return_amount
                    FROM STORE_RETURNS sr
                    JOIN DATE_DIM d ON sr.sr_returned_date_sk = d.d_date_sk
                    WHERE 1=1 {date_filter}
                """)
                return_data = cursor.fetchone()
                
                # Calculate KPIs
                total_revenue = float(revenue_data[0]) if revenue_data[0] else 0
                total_transactions = int(revenue_data[1]) if revenue_data[1] else 0
                unique_customers = int(revenue_data[2]) if revenue_data[2] else 0
                avg_transaction = float(revenue_data[3]) if revenue_data[3] else 0
                total_items_sold = float(revenue_data[4]) if revenue_data[4] else 0
                
                total_returns = int(return_data[0]) if return_data[0] else 0
                total_return_amount = float(return_data[1]) if return_data[1] else 0
                
                return_rate = (total_returns / total_transactions * 100) if total_transactions > 0 else 0
                customer_acquisition_rate = (unique_customers / total_customers * 100) if total_customers > 0 else 0
                
                result = {
                    "status": "success",
                    "data": {
                        "kpis": {
                            "financial": {
                                "total_revenue": round(total_revenue, 2),
                                "avg_transaction_value": round(avg_transaction, 2),
                                "total_return_amount": round(total_return_amount, 2),
                                "net_revenue": round(total_revenue - total_return_amount, 2)
                            },
                            "sales": {
                                "total_transactions": total_transactions,
                                "total_items_sold": int(total_items_sold),
                                "total_returns": total_returns,
                                "return_rate_percent": round(return_rate, 2)
                            },
                            "customers": {
                                "unique_customers": unique_customers,
                                "total_customers": total_customers,
                                "customer_acquisition_rate_percent": round(customer_acquisition_rate, 2),
                                "avg_spend_per_customer": round(total_revenue / unique_customers, 2) if unique_customers > 0 else 0
                            },
                            "operations": {
                                "total_stores": total_stores,
                                "total_inventory_items": int(inventory_data[0]) if inventory_data[0] else 0,
                                "total_inventory_quantity": int(inventory_data[1]) if inventory_data[1] else 0,
                                "revenue_per_store": round(total_revenue / total_stores, 2) if total_stores > 0 else 0
                            }
                        },
                        "date_range": date_range,
                        "generated_at": "2024-01-01"  # Would be current timestamp in real implementation
                    }
                }
                
                logger.info("KPI dashboard generated",
                          date_range=date_range,
                          total_revenue=total_revenue,
                          total_transactions=total_transactions)
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to generate KPI dashboard"
        }
        logger.error("KPI dashboard failed", error=str(e))
        return error_result

async def run_startup_tasks():
    """Startup tasks for MCP Oracle server."""
    logger.info("MCP Oracle Server startup beginning...")
    
    # Test database connectivity
    if test_connection():
        logger.info("Oracle database connectivity verified")
    else:
        logger.error("Oracle database connectivity failed")
        raise Exception("Cannot start server without database connectivity")
    
    logger.info("MCP Oracle Server initialization complete")

async def main():
    """Main server entry point."""
    await run_startup_tasks()
    
    logger.info("Starting MCP Oracle Server with stdio transport")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream,
            InitializationOptions(
                server_name="mcp-oracle",
                server_version="1.0.0"
            )
        )

if __name__ == "__main__":
    asyncio.run(main())