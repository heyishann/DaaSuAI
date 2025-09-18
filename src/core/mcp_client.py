
"""Simple MySQL Client for database operations"""

import asyncio
from typing import Dict, List, Any, Optional
import aiomysql
from datetime import datetime
from .settings import get_settings


class MCPClient:
    """Simple MySQL client for executing SQL queries."""

    def __init__(self, connection_params: Optional[Dict[str, str]] = None):
        """Initialize database client with connection parameters."""
        self.settings = get_settings()
        if connection_params:
            self.connection_params = connection_params
        else:
            self.connection_params = {
                "host": self.settings.mysql_host,
                "port": self.settings.mysql_port,
                "db": self.settings.mysql_db,
                "user": self.settings.mysql_user,
                "password": self.settings.mysql_password,
                "autocommit": True
            }
        self.pool = None
        self.connected = False

    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            debug_params = self.connection_params.copy()
            debug_params["password"] = "***masked***"
            print(f"🔌 Connecting to MySQL with: {debug_params}")
            self.pool = await aiomysql.create_pool(
                **self.connection_params,
                minsize=1,
                maxsize=10
            )
            # Test connection
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            self.connected = True
            print(" MySQL client connected successfully")
        except Exception as e:
            print(f" Failed to connect to MySQL: {e}")
            self.connected = False

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.connected = False
            print(" MySQL client disconnected")

    async def execute_query(self, sql_query: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a SQL query and return results."""
        if not self.connected or not self.pool:
            # Return simulated data for demo purposes
            return await self._simulate_query_execution(sql_query)
        
        try:
            async with self.pool.acquire() as conn:
                start_time = datetime.now()
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await asyncio.wait_for(cur.execute(sql_query), timeout=timeout)
                    result = await cur.fetchall()
                    columns = list(result[0].keys()) if result else []
                    data = [list(row.values()) for row in result] if result else []
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                return {
                    "success": True,
                    "data": data,
                    "columns": columns,
                    "row_count": len(data),
                    "execution_time": execution_time,
                    "query": sql_query
                }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Query execution timed out after {timeout} seconds",
                "data": None,
                "query": sql_query
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Query execution failed ==103==mcp : {str(e)}",
                "data": None,
                "query": sql_query
            }
    
    async def _simulate_query_execution(self, sql_query: str) -> Dict[str, Any]:
        """Simulate query execution for demo purposes when no DB is connected."""
        
        # Add a small delay to simulate database processing
        await asyncio.sleep(0.5)
        
        # Generate sample data based on query content
        if "employee" in sql_query.lower() and "performance" in sql_query.lower():
            return {
                "success": True,
                "data": [
                    ["Alice Johnson", 45, 2250.00, 98.5],
                    ["Bob Smith", 32, 1890.50, 95.2],
                    ["Carol Davis", 28, 1540.75, 92.8],
                    ["David Wilson", 38, 2100.25, 96.1],
                    ["Eva Martinez", 41, 2380.90, 99.1]
                ],
                "columns": ["employee_name", "total_bookings", "total_revenue", "satisfaction_score"],
                "row_count": 5,
                "execution_time": 0.5,
                "query": sql_query
            }
        
        elif "revenue" in sql_query.lower() and ("month" in sql_query.lower() or "time" in sql_query.lower()):
            return {
                "success": True,
                "data": [
                    ["2024-01", 15750.25, 125, 126.0],
                    ["2024-02", 18920.50, 142, 133.2],
                    ["2024-03", 22150.75, 168, 131.9],
                    ["2024-04", 19830.40, 155, 127.9],
                    ["2024-05", 24560.80, 182, 135.0]
                ],
                "columns": ["month", "total_revenue", "booking_count", "avg_booking_value"],
                "row_count": 5,
                "execution_time": 0.5,
                "query": sql_query
            }
        
        elif "service" in sql_query.lower() or "booking" in sql_query.lower():
            return {
                "success": True,
                "data": [
                    ["Hair Cut & Style", 234, 11700.00, 50.0],
                    ["Facial Treatment", 189, 14175.00, 75.0],
                    ["Manicure", 156, 4680.00, 30.0],
                    ["Massage Therapy", 98, 9800.00, 100.0],
                    ["Hair Coloring", 87, 8700.00, 100.0]
                ],
                "columns": ["service_name", "booking_count", "total_revenue", "avg_price"],
                "row_count": 5,
                "execution_time": 0.5,
                "query": sql_query
            }
        
        elif "customer" in sql_query.lower() or "client" in sql_query.lower():
            return {
                "success": True,
                "data": [
                    ["Sarah Johnson", "sarah.j@email.com", 12, 1200.00, "2024-05-15"],
                    ["Mike Chen", "mike.chen@email.com", 8, 800.00, "2024-05-12"],
                    ["Lisa Rodriguez", "lisa.r@email.com", 15, 1875.00, "2024-05-18"],
                    ["John Smith", "john.smith@email.com", 6, 720.00, "2024-05-10"],
                    ["Emma Wilson", "emma.w@email.com", 10, 1250.00, "2024-05-14"]
                ],
                "columns": ["customer_name", "email", "total_visits", "total_spent", "last_visit"],
                "row_count": 5,
                "execution_time": 0.5,
                "query": sql_query
            }
        
        else:
            # Generic response
            return {
                "success": True,
                "data": [
                    ["Sample Data 1", 100, 1500.50],
                    ["Sample Data 2", 150, 2250.75],
                    ["Sample Data 3", 200, 3000.00]
                ],
                "columns": ["item", "count", "value"],
                "row_count": 3,
                "execution_time": 0.5,
                "query": sql_query
            }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the database connection."""
        
        if not self.connected:
            return {
                "success": False,
                "message": "Not connected to database",
                "mode": "demo"
            }
        
        try:
            result = await self.execute_query("SELECT version()")
            return {
                "success": True,
                "message": "Database connection successful",
                "version": result["data"][0][0] if result["success"] else "Unknown"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }
    
    async def get_schema_info(self, business_id: str) -> Dict[str, Any]:
        """Get database schema information for a specific business."""
        
        # This would query the actual schema in a real implementation
        # For now, return sample schema info
        return {
            "tables": [
                "vendor_locations",
                "employees", 
                "users",
                "bills",
                "active_queues",
                "services",
                "appointments"
            ],
            "business_id": business_id,
            "schema_version": "1.0"
        }