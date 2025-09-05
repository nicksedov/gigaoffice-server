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
from slowapi.util import get_remote_address
from loguru import logger
from app.models.types.enums import RequestStatus
from app.models.api.ai_feedback import AIFeedback,AIFeedbackCreate, AIFeedbackOut
from app.models.orm.ai_request import AIRequest
from app.models.orm.ai_feedback import AIFeedback
from app.services.database.session import get_db
# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_services

# Create services in the module where needed
gigachat_classify_service, gigachat_generate_service = create_gigachat_services(prompt_builder)

from app.services.kafka.service import kafka_service
from app.fastapi_config import security

ai_router = APIRouter(prefix="/api", tags=["AI Feedback Processing"])

@ai_router.post("/feedback", response_model=AIFeedbackOut)
async def submit_ai_feedback(feedback: AIFeedbackCreate, db: Session = Depends(get_db)):
    ai_request = db.query(AIRequest).filter_by(id=feedback.ai_request_id).first()
    if not ai_request:
        raise HTTPException(status_code=404, detail="AI request not found")
    
    ai_feedback = AIFeedback(
        ai_request_id=feedback.ai_request_id,
        text_response=feedback.text_response,
        rating=feedback.rating,
        comment=feedback.comment
    )
    db.add(ai_feedback)
    db.commit()
    db.refresh(ai_feedback)
    return ai_feedback