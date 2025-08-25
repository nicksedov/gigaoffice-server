"""
Health Check Endpoints
Application health monitoring and status endpoints
"""

import time
from fastapi import APIRouter
from loguru import logger

from app.models.health import ServiceHealth
from app.core.config import settings
from app.db.session import database_manager
from app.services.ai.factory import gigachat_factory
from app.services.kafka.service import kafka_service

# Create router
router = APIRouter(prefix="/api", tags=["Health"])

# Store application start time
app_start_time = time.time()

@router.get("/health", response_model=ServiceHealth)
async def health_check():
    """
    Comprehensive health check endpoint
    
    Returns:
        ServiceHealth: Complete service status including all components
    """
    try:
        uptime = time.time() - app_start_time
        
        # Check database health
        db_health = database_manager.check_connection()
        
        # Check GigaChat service health
        try:
            gigachat_service = gigachat_factory.get_service("generate")
            gigachat_health = gigachat_service.check_service_health()
            gigachat_status = gigachat_health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"GigaChat health check failed: {e}")
            gigachat_status = False
        
        # Check Kafka service health
        try:
            kafka_health = kafka_service.get_health_status()
            kafka_status = kafka_health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Kafka health check failed: {e}")
            kafka_status = False
        
        # Get queue size
        try:
            queue_info = kafka_service.get_queue_info()
            queue_size = queue_info.get("statistics", {}).get("messages_sent", 0)
        except Exception:
            queue_size = 0
        
        health_status = ServiceHealth(
            status="ok" if all([db_health, gigachat_status, kafka_status]) else "degraded",
            uptime=uptime,
            version=settings.app_version,
            database=db_health,
            gigachat=gigachat_status,
            kafka=kafka_status,
            queue_size=queue_size,
            memory_usage=0.0,  # TODO: Implement actual memory monitoring
            cpu_usage=0.0      # TODO: Implement actual CPU monitoring
        )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ServiceHealth(
            status="error",
            uptime=time.time() - app_start_time,
            version=settings.app_version,
            database=False,
            gigachat=False,
            kafka=False
        )

@router.get("/ping")
async def ping():
    """Simple ping endpoint for basic availability check"""
    return {"status": "pong", "timestamp": time.time()}

@router.get("/version")
async def get_version():
    """Get application version information"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }