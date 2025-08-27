"""
AI Processing API Router
Router for AI processing endpoints
"""

import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger
from fastapi.security import HTTPAuthorizationCredentials

from app.models.types.enums import RequestStatus
from app.models.api.ai_request import AIRequestCreate, ProcessingStatus
from app.models.api.ai_response import AIResponseCreate, AIResponseOut
from app.models.orm.ai_request import AIRequest
from app.models.orm.ai_response import AIResponse
from app.services.database.session import get_db
# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_services

# Create services in the module where needed
gigachat_classify_service, gigachat_generate_service = create_gigachat_services(prompt_builder)

from app.services.kafka.service import kafka_service
from app.fastapi_config import security

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

ai_router = APIRouter(prefix="/api/ai", tags=["AI Processing"])

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
            query_text=ai_request.query_text,
            category=ai_request.category,
            input_data=ai_request.input_data
        )
        db.add(db_request)
        db.commit()
        
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=ai_request.query_text,
            input_range=ai_request.input_range,
            category=ai_request.category,
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