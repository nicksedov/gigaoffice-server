"""
GigaOffice Handlers and Main Entry Point
Обработчики сообщений и запуск приложения
"""

import os
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from loguru import logger
import uvicorn

from app.fastapi_config import create_app
from app.api.health import health_router
from app.api.feedback import feedback_router
from app.api.prompts import prompts_router
from app.api.metrics import metrics_router
from app.api.spreadsheets import spreadsheet_router  # Added import for spreadsheet router
from app.api.spreadsheets_v2 import spreadsheet_v2_router  # Added import for V2 spreadsheet router

# Create app and register routers
app = create_app()

# Register routers
app.include_router(health_router)
app.include_router(feedback_router)
app.include_router(prompts_router)
app.include_router(metrics_router)
app.include_router(spreadsheet_router)  # Added registration of spreadsheet router
app.include_router(spreadsheet_v2_router)  # Added registration of V2 spreadsheet router

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )

if __name__ == "__main__":
    # Configure logging
    log_file = os.getenv("LOG_FILE", "logs/gigaoffice.log")
    log_level = os.getenv("LOG_LEVEL", "info")
    logger.add(log_file, rotation="1 day", retention="30 days")
    port = int(os.getenv("PORT", "8000").strip())
    
    # Run server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=log_level
    )