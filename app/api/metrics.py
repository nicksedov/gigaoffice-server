"""
Metrics API Router
Router for service metrics endpoints
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from loguru import logger

from app.model_api import MetricsResponse
from app.gigachat_factory import gigachat_generate_service
from app.kafka_service import kafka_service
from app.fastapi_config import security

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

metrics_router = APIRouter(prefix="/api", tags=["Metrics"])

@metrics_router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    period: str = "day",
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Получение метрик сервиса"""
    try:
        if not current_user or current_user.get("role") not in ["admin", "premium"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        gigachat_stats = gigachat_generate_service.get_usage_statistics()
        kafka_info = kafka_service.get_queue_info()
        
        metrics = MetricsResponse(
            period=period,
            total_requests=kafka_info.get("statistics", {}).get("messages_received", 0),
            successful_requests=kafka_info.get("statistics", {}).get("messages_received", 0) - kafka_info.get("statistics", {}).get("messages_failed", 0),
            failed_requests=kafka_info.get("statistics", {}).get("messages_failed", 0),
            avg_processing_time=kafka_info.get("statistics", {}).get("avg_processing_time", 0),
            total_tokens_used=gigachat_stats.get("total_tokens_used", 0)
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}") 
        raise HTTPException(status_code=500, detail=str(e))