"""
GigaOffice API Routers
Все API эндпоинты для обработки запросов
"""

import uuid
import time
from datetime import datetime
import json
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from model_types import RequestStatus
from model_api import (
    AIRequestCreate, AIResponseCreate, AIResponseOut,
    PromptClassificationRequest,
    ServiceHealth, ProcessingStatus, MetricsResponse
)
from model_orm import AIRequest, AIResponse, Category
from database import get_db, check_database_health
from gigachat_factory import gigachat_service
from kafka_service import kafka_service
from fastapi_config import security, app_start_time
from prompts import prompt_manager

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

# Create routers
health_router = APIRouter(prefix="/api", tags=["Health"])
ai_router = APIRouter(prefix="/api/ai", tags=["AI Processing"])
prompts_router = APIRouter(prefix="/api/prompts", tags=["Prompts"])
metrics_router = APIRouter(prefix="/api", tags=["Metrics"])

# Health endpoints
@health_router.get("/health", response_model=ServiceHealth)
async def health_check():
    """Проверка состояния сервиса"""
    uptime = time.time() - app_start_time
    
    db_health = check_database_health()
    gigachat_health = gigachat_service.check_service_health()
    kafka_health = kafka_service.get_health_status()
    
    health_status = ServiceHealth(
        uptime=uptime,
        database=db_health.get("status") == "healthy",
        gigachat=gigachat_health.get("status") == "healthy",
        kafka=kafka_health.get("status") == "healthy",
        redis=True,
        queue_size=kafka_health.get("statistics", {}).get("messages_sent", 0),
        memory_usage=0.0,
        cpu_usage=0.0
    )
    
    return health_status

# AI Processing endpoints
@ai_router.post("/process", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def process_ai_request(
    request: Request,
    ai_request: AIRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обработка запроса к ИИ"""
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=ai_request.input_range,
            output_range=ai_request.output_range,
            query_text=ai_request.query_text,
            input_data=ai_request.input_data
        )
        db.add(db_request)
        db.commit()
        
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=ai_request.query_text,
            input_range=ai_request.input_range,
            output_range=ai_request.output_range, 
            input_data=ai_request.input_data,
            priority=1 if current_user and current_user.get("role") == "premium" else 0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue request")
        
        return {
            "success": True,
            "request_id": request_id,
            "status": "queued",
            "message": "Запрос добавлен в очередь обработки"
        }
        
    except Exception as e:
        logger.error(f"Error processing AI request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_router.get("/status/{request_id}", response_model=ProcessingStatus)
async def get_processing_status(request_id: str, db: Session = Depends(get_db)):
    """Получение статуса обработки запроса"""
    try:
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        progress_map = {
            RequestStatus.PENDING: 0,
            RequestStatus.PROCESSING: 50,
            RequestStatus.COMPLETED: 100,
            RequestStatus.FAILED: 0,
            RequestStatus.CANCELLED: 0
        }
        
        status = ProcessingStatus(
            request_id=int(request_id) if request_id.isdigit() else 0,
            status=db_request.status,
            progress=progress_map.get(db_request.status, 0),
            message=db_request.error_message or "Обработка в процессе"
        )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_router.get("/result/{request_id}")
async def get_ai_result(request_id: str, db: Session = Depends(get_db)):
    """Получение результата обработки ИИ"""
    try:
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if db_request.status != RequestStatus.COMPLETED:
            return {
                "success": False,
                "status": db_request.status,
                "message": "Запрос еще не завершен"
            }
        
        return {
            "success": True,
            "result": db_request.result_data,
            "tokens_used": db_request.tokens_used,
            "processing_time": db_request.processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@ai_router.post("/response", response_model=AIResponseOut)
async def submit_ai_response(response: AIResponseCreate, db: Session = Depends(get_db)):
    ai_request = db.query(AIRequest).filter_by(id=response.ai_request_id).first()
    if not ai_request:
        raise HTTPException(status_code=404, detail="AI request not found")
    
    ai_response = AIResponse(
        ai_request_id=response.ai_request_id,
        text_response=response.text_response,
        rating=response.rating,
        comment=response.comment
    )
    db.add(ai_response)
    db.commit()
    db.refresh(ai_response)
    return ai_response

# Prompts endpoints
@prompts_router.get("/categories", response_model=Dict[str, Any])
async def get_prompt_categories_endpoint():
    """Получение списка категорий предустановленных промптов с описанием"""
    try:
        categories = await prompt_manager.get_prompt_categories()
        return {
            "status": "success",
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Error getting prompt categories endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@prompts_router.get("/categories/{category_id}", response_model=Dict[str, Any])
async def get_category_details(category_id: int, db: Session = Depends(get_db)):
    """Получение подробной информации о категории"""
    try:
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        prompts = await prompt_manager.get_prompts_by_category(str(category_id))
        
        return {
            "status": "success",
            "category": {
                "id": category.id,
                "name": category.name,
                "display_name": category.display_name,
                "description": category.description,
                "sort_order": category.sort_order,
                "prompt_count": len(prompts)
            },
            "prompts": [
                {
                    "id": prompt.id,
                    "name": prompt.name,
                    "description": prompt.description,
                    "template": prompt.template,
                    "category_id": prompt.category_id
                }
                for prompt in prompts
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@prompts_router.get("/presets", response_model=Dict[str, Any])
async def get_preset_prompts(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получение предустановленных промптов"""
    try:
        if category:
            prompts = await prompt_manager.get_prompts_by_category(category)
        else:
            prompts = await prompt_manager.get_prompts()

        return {
            "status": "success",
            "prompts": [
                {
                    "id": prompt.id,
                    "name": prompt.name,
                    "template": prompt.template,
                    "category_id": prompt.category_id,
                    "category_name": prompt.category_obj.name if prompt.category_obj else None,
                    "category_display_name": prompt.category_obj.display_name if prompt.category_obj else None
                }
                for prompt in prompts
            ]
        }

    except Exception as e:
        logger.error(f"Error getting preset prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@prompts_router.post("/classify", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def classify_prompt(
    request: Request,
    classification_request: PromptClassificationRequest,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Классифицирует пользовательский промпт по предопределенным категориям
    
    Args:
        prompt_text: Текст промпта для классификации
        include_descriptions: Включать описания категорий в системный промпт
    
    Returns:
        Результат классификации с вероятностями для каждой категории
    """
    try:
        result = await gigachat_service.classify_query(classification_request.prompt_text) 
        return result      
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Metrics endpoints
@metrics_router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    period: str = "day",
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Получение метрик сервиса"""
    try:
        if not current_user or current_user.get("role") not in ["admin", "premium"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        gigachat_stats = gigachat_service.get_usage_statistics()
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
