"""
AI Processing Endpoints
Endpoints for AI request processing, status tracking, and result retrieval
"""

import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.models.ai_requests import AIRequestCreate, AIRequestResponse, ProcessingStatus
from app.models.ai_responses import AIResponseCreate, AIResponseOut
from app.db.session import get_db
from app.db.models import AIRequest, AIResponse
from app.db.repositories.ai_requests import AIRequestRepository
from app.services.ai.factory import gigachat_factory
from app.services.kafka.service import kafka_service
from app.core.security import security_manager
from app.utils.logger import structured_logger
from app.models.types import RequestStatus

# Create router
router = APIRouter(prefix="/api/ai", tags=["AI Processing"])

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Dependencies
async def get_current_user(request: Request):
    """Get current user from request (simplified implementation)"""
    # TODO: Implement proper authentication
    return {"id": 1, "username": "demo_user", "role": "user"}

async def get_ai_request_repo(db: Session = Depends(get_db)) -> AIRequestRepository:
    """Get AI request repository instance"""
    return AIRequestRepository(db)

@router.post("/process", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def process_ai_request(
    request: Request,
    ai_request: AIRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    ai_repo: AIRequestRepository = Depends(get_ai_request_repo)
):
    """
    Process AI request asynchronously
    
    Args:
        ai_request: AI request data
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        ai_repo: AI request repository
    
    Returns:
        Dict with request ID and status
    """
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        structured_logger.log_api_request(
            endpoint="/api/ai/process",
            method="POST",
            duration=0,
            user_id=str(user_id)
        )
        
        # Create database record
        db_request_data = {
            "id": request_id,
            "user_id": user_id,
            "status": RequestStatus.PENDING,
            "input_range": ai_request.input_range,
            "query_text": ai_request.query_text,
            "category": ai_request.category,
            "input_data": ai_request.input_data,
            "priority": ai_request.priority
        }
        
        db_request = ai_repo.create(db_request_data)
        
        # Determine priority based on user role
        priority = ai_request.priority
        if current_user and current_user.get("role") == "premium":
            priority = max(priority, 5)
        
        # Send to Kafka queue
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=ai_request.query_text,
            input_range=ai_request.input_range,
            category=ai_request.category,
            input_data=ai_request.input_data,
            priority=priority
        )
        
        if not success:
            # Update request status to failed
            ai_repo.update(request_id, {"status": RequestStatus.FAILED})
            raise HTTPException(status_code=500, detail="Failed to queue request")
        
        structured_logger.log_service_call(
            service="kafka",
            method="send_request",
            duration=0,
            success=True,
            metadata={"request_id": request_id}
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "status": "queued",
            "message": "Запрос добавлен в очередь обработки",
            "priority": priority
        }
        
    except Exception as e:
        logger.error(f"Error processing AI request: {e}")
        structured_logger.log_service_call(
            service="ai_processing",
            method="process_request",
            duration=0,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{request_id}", response_model=ProcessingStatus)
async def get_processing_status(
    request_id: str, 
    ai_repo: AIRequestRepository = Depends(get_ai_request_repo)
):
    """
    Get processing status for a specific request
    
    Args:
        request_id: Unique request identifier
        ai_repo: AI request repository
    
    Returns:
        ProcessingStatus: Current status and progress information
    """
    try:
        db_request = ai_repo.get_by_id(request_id)
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Map status to progress percentage
        progress_map = {
            RequestStatus.PENDING: 0,
            RequestStatus.PROCESSING: 50,
            RequestStatus.COMPLETED: 100,
            RequestStatus.FAILED: 0,
            RequestStatus.CANCELLED: 0
        }
        
        # Estimate remaining time based on status
        estimated_time = None
        if db_request.status == RequestStatus.PENDING:
            estimated_time = 30  # 30 seconds estimate
        elif db_request.status == RequestStatus.PROCESSING:
            estimated_time = 15  # 15 seconds estimate
        
        status = ProcessingStatus(
            request_id=int(request_id) if request_id.isdigit() else hash(request_id) % 1000000,
            status=db_request.status,
            progress=progress_map.get(db_request.status, 0),
            message=db_request.error_message or "Обработка в процессе",
            estimated_time=estimated_time
        )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{request_id}", response_model=AIRequestResponse)
async def get_ai_result(
    request_id: str, 
    ai_repo: AIRequestRepository = Depends(get_ai_request_repo)
):
    """
    Get AI processing result
    
    Args:
        request_id: Unique request identifier
        ai_repo: AI request repository
    
    Returns:
        AIRequestResponse: Complete request result with metadata
    """
    try:
        db_request = ai_repo.get_by_id(request_id)
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Convert to response model
        return AIRequestResponse.from_orm(db_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/response", response_model=AIResponseOut)
async def submit_ai_response(
    response: AIResponseCreate, 
    db: Session = Depends(get_db)
):
    """
    Submit feedback response for AI result
    
    Args:
        response: User feedback data
        db: Database session
    
    Returns:
        AIResponseOut: Created response record
    """
    try:
        # Verify AI request exists
        ai_request = db.query(AIRequest).filter_by(id=response.ai_request_id).first()
        if not ai_request:
            raise HTTPException(status_code=404, detail="AI request not found")
        
        # Create response record
        ai_response = AIResponse(
            ai_request_id=response.ai_request_id,
            text_response=response.text_response,
            rating=response.rating,
            comment=response.comment
        )
        db.add(ai_response)
        db.commit()
        db.refresh(ai_response)
        
        structured_logger.log_service_call(
            service="ai_feedback",
            method="submit_response",
            duration=0,
            success=True,
            metadata={"ai_request_id": str(response.ai_request_id)}
        )
        
        return ai_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting AI response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/info")
async def get_queue_info(current_user: Optional[Dict] = Depends(get_current_user)):
    """
    Get current queue information
    
    Returns:
        Dict with queue status and statistics
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        queue_info = kafka_service.get_queue_info()
        return {
            "success": True,
            "queue_info": queue_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel/{request_id}")
async def cancel_ai_request(
    request_id: str,
    current_user: Optional[Dict] = Depends(get_current_user),
    ai_repo: AIRequestRepository = Depends(get_ai_request_repo)
):
    """
    Cancel pending AI request
    
    Args:
        request_id: Request to cancel
        current_user: Current authenticated user
        ai_repo: AI request repository
    
    Returns:
        Dict with cancellation status
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        db_request = ai_repo.get_by_id(request_id)
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Check if user owns the request
        if db_request.user_id != current_user.get("id"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Only allow cancellation of pending requests
        if db_request.status != RequestStatus.PENDING:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel request with status: {db_request.status}"
            )
        
        # Update status to cancelled
        ai_repo.update(request_id, {"status": RequestStatus.CANCELLED})
        
        return {
            "success": True,
            "message": "Request cancelled successfully",
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling AI request: {e}")
        raise HTTPException(status_code=500, detail=str(e))