"""
GigaOffice FastAPI Main Server
Основной сервер для промежуточного сервиса GigaOffice
"""

import os
import time
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from loguru import logger
import uvicorn

# Local imports
from models import (
    AIRequestCreate, 
    AIResponseCreate, AIResponseOut,
    ServiceHealth,
    ProcessingStatus, MetricsResponse, RequestStatus
)
from database import get_db, get_db_session, init_database, check_database_health
from gigachat_factory import gigachat_service
from kafka_service import kafka_service
from prompts import PromptManager

# Configuration
APP_VERSION = "1.0.0"
APP_NAME = "GigaOffice AI Service"
APP_DESCRIPTION = "Промежуточный сервис для интеграции Р7-офиса с GigaChat"

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer(auto_error=False)

# Global variables
app_start_time = time.time()
prompt_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app"""
    # Startup
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized")
        
        # Initialize prompt manager
        global prompt_manager
        prompt_manager = PromptManager()
        await prompt_manager.get_prompt_categories()
        await prompt_manager.get_prompts()
        logger.info("Prompt manager initialized")
        # Start Kafka service
        await kafka_service.start()
        # Start Kafka consumer
        asyncio.create_task(kafka_service.start_consumer(message_handler))
        logger.info("Kafka consumer started")
        
        # Yield control to FastAPI
        yield
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        # Stop Kafka service
        await kafka_service.cleanup()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Authentication dependency (simplified for demo)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None  # Allow anonymous access for demo
    
    # In production, implement proper JWT token validation
    return {"id": 1, "username": "demo_user", "role": "user"}

# Health check endpoint
@app.get("/api/health", response_model=ServiceHealth)
async def health_check():
    """Проверка состояния сервиса"""
    uptime = time.time() - app_start_time
    
    # Check all service components
    db_health = check_database_health()
    gigachat_health = gigachat_service.check_service_health()
    kafka_health = kafka_service.get_health_status()
    
    health_status = ServiceHealth(
        uptime=uptime,
        database=db_health.get("status") == "healthy",
        gigachat=gigachat_health.get("status") == "healthy",
        kafka=kafka_health.get("status") == "healthy",
        redis=True,  # Placeholder
        queue_size=kafka_health.get("statistics", {}).get("messages_sent", 0),
        memory_usage=0.0,  # Would implement with psutil
        cpu_usage=0.0  # Would implement with psutil
    )
    
    return health_status

# AI Processing endpoints
@app.post("/api/ai/process", response_model=Dict[str, Any])
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
        # Generate request ID
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Save request to database
        from models import AIRequest
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
        
        # Send to Kafka queue for processing
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

@app.get("/api/ai/status/{request_id}", response_model=ProcessingStatus)
async def get_processing_status(request_id: str, db: Session = Depends(get_db)):
    """Получение статуса обработки запроса"""
    try:
        from models import AIRequest
        
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Calculate progress based on status
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

@app.get("/api/ai/result/{request_id}")
async def get_ai_result(request_id: str, db: Session = Depends(get_db)):
    """Получение результата обработки ИИ"""
    try:
        from models import AIRequest
        
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

# Insert API
@app.post("/api/ai/response", response_model=AIResponseOut)
async def submit_ai_response(response: AIResponseCreate, db: Session = Depends(get_db)):
    from models import AIRequest,AIResponse
    # Проверка, что ai_request_id существует
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

@app.get("/api/prompts/categories", response_model=Dict[str, Any])
async def get_prompt_categories_endpoint():
    """
    Получение списка категорий предустановленных промптов с описанием.
    """
    try:
        categories = await prompt_manager.get_prompt_categories()
        return {
            "status": "success",
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Error getting prompt categories endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prompts/categories/{category_id}", response_model=Dict[str, Any])
async def get_category_details(category_id: int, db: Session = Depends(get_db)):
    """
    Получение подробной информации о категории
    """
    try:
        from models import Category
        
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Получаем промпты для этой категории
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

@app.get("/api/prompts/presets", response_model=Dict[str, Any])
async def get_preset_prompts(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получение предустановленных промптов.

    Args:
        category: (необязательно) категория промптов (ID или name), по которой нужно отфильтровать результат.
    """
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

# Metrics endpoints
@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(
    period: str = "day",
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Получение метрик сервиса"""
    try:
        # Check permissions
        if not current_user or current_user.get("role") not in ["admin", "premium"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get GigaChat usage statistics
        gigachat_stats = gigachat_service.get_usage_statistics()
        
        # Get Kafka queue information
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

async def message_handler(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process AI request from Kafka queue"""
    try:
        request_id = message_data["id"]
        query = message_data["query"]
        input_range = message_data["input_range"]
        output_range = message_data["output_range"]
        input_data = message_data["input_data"]
        
        logger.info(f"Processing Kafka message: {request_id}")
        
        # Process with GigaChat
        result, metadata = await gigachat_service.process_query(query, input_range, output_range, input_data)
        
        # Update database
        with get_db_session() as db:
            from models import AIRequest
            db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
            if db_request:
                db_request.status = RequestStatus.COMPLETED
                db_request.result_data = result
                db_request.tokens_used = metadata.get("total_tokens", 0)
                db_request.processing_time = metadata.get("processing_time", 0)
                db_request.completed_at = datetime.now()
                db.commit()
        
        logger.info(f"Request {request_id} processed successfully")
        return {
            "success": True,
            "result": result,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {e}")
        
        # Update database with error
        with get_db_session() as db:
            from models import AIRequest
            db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
            if db_request:
                db_request.status = RequestStatus.FAILED
                db_request.error_message = str(e)
                db.commit()
        return {
            "success": False,
            "error": str(e)
        }

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
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=log_level
    )