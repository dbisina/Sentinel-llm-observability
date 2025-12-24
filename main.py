"""
LLM Observability Platform - Entry Point

Main entry point for Google Cloud Run deployment.
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the FastAPI app
from app.server import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
