#!/usr/bin/env python3
"""
Oracle Analytics FastMCP Server
Following the exact pattern from webstore.py for LlamaStack compatibility
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from database import get_oracle_connection, settings, test_connection

# Initialize FastMCP - following webstore pattern exactly
mcp_server = FastMCP("Oracle Analytics")

@mcp_server.tool()
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring Oracle MCP server status."""
    try:
        db_healthy = test_connection()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database_connection": "ok" if db_healthy else "failed",
            "server_info": {
                "environment": settings.environment,
                "oracle_host": settings.oracle_host,
                "oracle_port": settings.oracle_port,
                "service_name": settings.oracle_service_name
            }
        }
        
        return health_status
        
    except Exception as e:
        error_status = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return error_status

@mcp_server.tool()
async def get_tpcds_summary() -> Dict[str, Any]:
    """Get summary of TPC-DS tables and row counts."""
    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
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
                
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve TPC-DS summary"
        }
        return error_result

@mcp_server.tool()
async def get_customer_insights(limit: int = 100) -> Dict[str, Any]:
    """Get customer demographic insights from TPC-DS data."""
    try:
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
                
                return result
                
    except Exception as e:
        error_result = {
            "status": "error", 
            "error": str(e),
            "message": "Failed to retrieve customer insights"
        }
        return error_result

@mcp_server.tool()
async def get_sales_analytics(
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    limit: int = 1000
) -> Dict[str, Any]:
    """Get sales analytics from TPC-DS store sales data."""
    try:
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
                
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e), 
            "message": "Failed to retrieve sales analytics"
        }
        return error_result

@mcp_server.tool()
async def execute_custom_query(
    sql_query: str,
    max_rows: int = 1000
) -> Dict[str, Any]:
    """Execute custom SQL queries with safety constraints."""
    try:
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
            sql_query = f"SELECT * FROM ({sql_query}) WHERE ROWNUM <= {max_rows}"
        
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
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
                
                return result
                
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Failed to execute custom query"
        }
        return error_result


if __name__ == "__main__":
    # Follow webstore pattern exactly - SSE transport on port 8003
    mcp_server.settings.port = 8003
    mcp_server.settings.host = "0.0.0.0"  # Allow Docker container access
    mcp_server.run(transport="sse")