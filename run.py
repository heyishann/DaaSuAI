#!/usr/bin/env python3
"""
CrewAI SQL Generator Startup Script

This script starts the FastAPI application with proper configuration.
"""

import uvicorn
import os
from pathlib import Path

def main():
    """Start the CrewAI SQL Generator application."""
    
    # Set the working directory to the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Set Python path
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Load environment variables
    env_file = project_root / '.env'
    if not env_file.exists():
        print("  .env file not found. Using default configuration.")
        print(" Copy .env.example to .env and configure your settings.")
    
    # Start the application
    print(" Starting CrewAI SQL Generator...")
    print(" Chat Interface: http://localhost:8000")
    print(" API Documentation: http://localhost:8000/docs")
    print(" Health Check: http://localhost:8000/health")
    print()
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(project_root / "src")],
        log_level="info"
    )

if __name__ == "__main__":
    main()