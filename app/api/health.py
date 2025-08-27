"""
Health API Router
Router for health check endpoints
"""

from fastapi import APIRouter
from typing import Dict, Any
from app.models.api.health import PingResponse, ServiceHealth
from app.fastapi_config import app_start_time
from app.services.database.session import check_database_health
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_services

# Create services in the module where needed
gigachat_classify_service, _ = create_gigachat_services(prompt_builder)

from app.services.kafka.service import kafka_service

health_router = APIRouter(prefix="/api", tags=["Health"])

@health_router.get("/ping", response_model=PingResponse)
async def ping():
    return PingResponse(status="pong")

@health_router.get("/health", response_model=ServiceHealth)
async def health_check():
    """Проверка состояния сервиса"""
    import time
    uptime = time.time() - app_start_time
    
    db_health = check_database_health()
    gigachat_health = gigachat_classify_service.check_service_health()
    kafka_health = kafka_service.get_health_status()
    
    health_status = ServiceHealth(
        uptime=uptime,
        database=db_health.get("status") == "healthy",
        gigachat=gigachat_health.get("status") == "healthy",
        kafka=kafka_health.get("status") == "healthy",
        queue_size=kafka_health.get("statistics", {}).get("messages_sent", 0),
        memory_usage=0.0,
        cpu_usage=0.0
    )
    
    return health_status