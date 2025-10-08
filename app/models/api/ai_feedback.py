"""AI Response API Models"""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class AIFeedbackRequest(BaseModel):
    ai_request_id: str
    text_response: str
    rating: Optional[bool] = None  # True — хороший, False — плохой, None — не оценено
    comment: Optional[str] = None

class AIFeedbackResponse(BaseModel):
    id: int
    ai_request_id: UUID
    text_response: str
    rating: Optional[bool]
    comment: Optional[str]