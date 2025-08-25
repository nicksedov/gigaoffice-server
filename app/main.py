"""
GigaOffice Main Application
Main entry point for the GigaOffice AI service with modular architecture
"""

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
import uvicorn

from app.core.config import settings
from app.api.router import api_router
from app.utils.logger import structured_logger
from app.lifespan import lifespan


# Create FastAPI application with lifespan management
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="GigaOffice AI Service - Modular Architecture",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url="/api/redoc" if settings.environment != "production" else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API router
app.include_router(api_router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors
    
    Args:
        request: FastAPI request object
        exc: Exception that occurred
    
    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception in {request.url.path}: {exc}")
    
    # Log structured error
    structured_logger.log_service_call(
        service="global_handler",
        method="exception_handler",
        duration=0,
        success=False,
        error=str(exc),
        metadata={
            "endpoint": str(request.url.path),
            "method": request.method,
            "client_ip": getattr(request.client, 'host', 'unknown')
        }
    )
    
    # Return appropriate error response
    if settings.environment == "development":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url.path)
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }
        )

# Request middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all incoming requests
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint function
    
    Returns:
        Response from next middleware/endpoint
    """
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log request
    structured_logger.log_api_request(
        endpoint=str(request.url.path),
        method=request.method,
        duration=duration,
        status_code=response.status_code,
        client_ip=getattr(request.client, 'host', 'unknown')
    )
    
    return response

# Health check endpoint (for load balancers)
@app.get("/")
async def root():
    """Root endpoint for basic service availability check"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/api/docs" if settings.environment != "production" else "disabled"
    }

# Application factory function
def create_application() -> FastAPI:
    """
    Application factory function
    
    Returns:
        FastAPI: Configured application instance
    """
    return app

# Main entry point
if __name__ == "__main__":
    # Configure logging
    log_file = os.getenv("LOG_FILE", "logs/gigaoffice.log")
    log_level = os.getenv("LOG_LEVEL", "info")
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Add file logging
    logger.add(
        log_file, 
        rotation="1 day", 
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}"
    )
    
    # Get server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Server configuration: {host}:{port} (workers: {workers}, reload: {reload})")
    
    # Run server
    if workers > 1:
        # Use gunicorn for multiple workers (production)
        logger.warning("Multiple workers specified, but running with uvicorn. Use gunicorn in production.")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload and settings.environment == "development",
        log_level=log_level.lower(),
        access_log=True,
        use_colors=True if settings.environment == "development" else False
    )