"""Query Executor Agent - Executes SQL queries using MySQL MCP"""

from crewai import Agent, Task, Crew
from typing import Dict, List, Any, Optional
import asyncio
import pandas as pd
from datetime import datetime


class QueryExecutorAgent:
    """CrewAI agent for executing SQL queries via MySQL database client."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.agent = self._create_agent()
        self.mcp_client = None  # Will be injected
        
    def set_mcp_client(self, db_client):
        """Set the database client for database operations."""
        self.mcp_client = db_client
        
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent for query execution."""
        return Agent(
            role="SQL Query Executor",
            goal="Execute SQL queries safely and efficiently against MySQL database",
            backstory="""You are a database operations specialist who ensures queries 
            are executed safely with proper error handling, timeout management, 
            and result formatting for business users.""",
            verbose=True,
            allow_delegation=False,
            llm=self.model_name
        )
    
    async def execute_query(self, sql_query: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute SQL query and return results."""
        
        if not self.mcp_client:
            return {
                "success": False,
                "error": "Database client not configured",
                "data": None,
                "metadata": {}
            }
        
        try:
            # Execute query via database client
            start_time = datetime.now()
            
            # Execute query via database client
            result = await self.mcp_client.execute_query(sql_query, timeout=timeout)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            if result["success"]:
                return {
                    "success": True,
                    "data": result.get("data", []),
                    "columns": result.get("columns", []),
                    "row_count": result.get("row_count", 0),
                    "execution_time": result.get("execution_time", 0),
                    "metadata": {
                        "query": sql_query,
                        "executed_at": start_time.isoformat(),
                        "execution_time_seconds": result.get("execution_time", 0)
                    }
                }
            else:
                return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "metadata": {
                    "query": sql_query,
                    "error_type": type(e).__name__
                }
            }
    
    async def _simulate_query_execution(self, sql_query: str) -> Dict[str, Any]:
        """Simulate query execution for demo purposes."""
        
        # Simulate different types of queries
        if "employee" in sql_query.lower():
            return {
                "columns": ["employee_name", "total_bookings", "total_revenue"],
                "data": [
                    ["Alice Johnson", 45, 2250.00],
                    ["Bob Smith", 32, 1890.50],
                    ["Carol Davis", 28, 1540.75]
                ]
            }
        elif "revenue" in sql_query.lower():
            return {
                "columns": ["month", "total_revenue", "booking_count"],
                "data": [
                    ["2024-01", 15750.25, 125],
                    ["2024-02", 18920.50, 142],
                    ["2024-03", 22150.75, 168]
                ]
            }
        else:
            return {
                "columns": ["result"],
                "data": [["Query executed successfully"]]
            }
    
    def format_results(self, results: Dict[str, Any]) -> str:
        """Format query results for display."""
        
        if not results["success"]:
            return f"Query execution failed: {results.get('error', 'Unknown error')}"
        
        task = Task(
            description=f"""
            Format the following query results for business users:
            
            Data: {results['data']}
            Columns: {results['columns']}
            Row Count: {results['row_count']}
            Execution Time: {results['execution_time']} seconds
            
            Create a clear, readable summary that includes:
            1. Brief description of what the data shows
            2. Key insights or patterns
            3. Properly formatted table or summary
            4. Any notable observations
            """,
            expected_output="Well-formatted business summary of the query results",
            agent=self.agent
        )
        
        # Create a crew to execute the task
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=False
        )
        
        result = crew.kickoff()
        return str(result)
    
    def to_dataframe(self, results: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Convert query results to pandas DataFrame."""
        
        if not results["success"] or not results["data"]:
            return None
        
        try:
            df = pd.DataFrame(results["data"], columns=results["columns"])
            return df
        except Exception as e:
            print(f"Error creating DataFrame: {e}")
            return None