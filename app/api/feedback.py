"""
AI Processing API Router
Router for AI processing endpoints
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.api.ai_feedback import AIFeedbackRequest, AIFeedbackResponse
from app.models.orm.ai_request import AIRequest
from app.models.orm.ai_feedback import AIFeedback
from app.services.database.session import get_db
# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder

feedback_router = APIRouter(prefix="/api", tags=["AI Feedback Processing"])

@feedback_router.post("/feedback", response_model=AIFeedbackResponse)
async def submit_ai_feedback(feedback: AIFeedbackRequest, db: Session = Depends(get_db)) -> AIFeedback:
    ai_request: AIRequest | None = db.query(AIRequest).filter_by(id=feedback.ai_request_id).first()
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