"""FastAPI application for CrewAI SQL Generator"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import os
from pathlib import Path

from ..core.crew_orchestrator import SQLGenerationCrew
from ..core.mcp_client import MCPClient

# Pydantic models for API
class QueryRequest(BaseModel):
    query: str
    business_id: str
    additional_context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    success: bool
    user_query: str
    business_id: str
    sql_query: Optional[str] = None
    data: Optional[List] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    execution_time: Optional[float] = None
    formatted_summary: Optional[str] = None
    visualizations: Optional[List[Dict]] = None
    validation_info: Optional[Dict] = None
    error: Optional[str] = None
    pipeline_steps: Optional[Dict] = None

class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]
    timestamp: str

# Create FastAPI app
app = FastAPI(
    title="CrewAI SQL Generator",
    description="Natural language to SQL query generation with visualization",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be configured from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
sql_crew = SQLGenerationCrew()
db_client = MCPClient()

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    try:
        # Initialize database client
        await db_client.initialize()
        sql_crew.set_mcp_client(db_client)
        print(" Application startup complete")
    except Exception as e:
        print(f" Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        await db_client.close()
        print(" Application shutdown complete")
    except Exception as e:
        print(f" Shutdown error: {e}")

# Serve static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# API Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface."""
    template_path = Path(__file__).parent.parent / "templates" / "chat.html"
    if template_path.exists():
        with open(template_path, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>CrewAI SQL Generator</title></head>
            <body>
                <h1>CrewAI SQL Generator</h1>
                <p>Chat interface will be available at /chat</p>
                <p>API documentation available at <a href="/docs">/docs</a></p>
            </body>
        </html>
        """)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    
    status = sql_crew.get_pipeline_status()
    validation = await sql_crew.validate_setup()
    
    return HealthResponse(
        status="healthy" if validation["is_valid"] else "degraded",
        components=status,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language query through the complete pipeline."""
    
    try:
        # Validate input
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not request.business_id.strip():
            raise HTTPException(status_code=400, detail="Organization ID is required")
        
        # Process through the pipeline
        result = await sql_crew.process_user_query(
            request.query,
            request.business_id,
            request.additional_context
        )
        
        # Format response
        final_result = result["final_result"]
        
        return QueryResponse(
            success=final_result["success"],
            user_query=request.query,
            business_id=request.business_id,
            sql_query=final_result.get("sql_query"),
            data=final_result.get("data"),
            columns=final_result.get("columns"),
            row_count=final_result.get("row_count"),
            execution_time=final_result.get("execution_time"),
            formatted_summary=final_result.get("formatted_summary"),
            visualizations=final_result.get("visualizations"),
            validation_info=final_result.get("validation_info"),
            error=final_result.get("error"),
            pipeline_steps=result["steps"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/generate-sql")
async def generate_sql_only(request: QueryRequest):
    """Generate SQL query without executing it."""
    
    try:
        sql_query = sql_crew.query_generator.generate_query(
            request.query,
            request.business_id,
            request.additional_context
        )
        
        return {
            "success": True,
            "sql_query": sql_query,
            "user_query": request.query,
            "business_id": request.business_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL generation failed: {str(e)}")

@app.post("/api/validate-sql")
async def validate_sql(sql_query: str, business_id: str):
    """Validate an SQL query."""
    
    try:
        validation_result = sql_crew.query_validator.validate_query(sql_query, business_id)
        return validation_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL validation failed: {str(e)}")

@app.get("/api/status")
async def get_status():
    """Get detailed system status."""
    
    status = sql_crew.get_pipeline_status()
    validation = await sql_crew.validate_setup()
    
    return {
        "pipeline_status": status,
        "validation": validation,
        "db_connected": hasattr(db_client, 'connected') and db_client.connected
    }

# WebSocket support for real-time chat
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            query = data.get("query", "")
            business_id = data.get("business_id", "")
            
            if not query or not business_id:
                await websocket.send_json({
                    "error": "Query and business_id are required"
                })
                continue
            
            # Send processing status
            await websocket.send_json({
                "status": "processing",
                "message": "Processing your query..."
            })
            
            # Process the query
            result = await sql_crew.process_user_query(query, business_id)
            
            # Send the result
            await websocket.send_json({
                "status": "completed",
                "result": result["final_result"]
            })
            
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        await websocket.send_json({
            "error": f"Processing error: {str(e)}"
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)