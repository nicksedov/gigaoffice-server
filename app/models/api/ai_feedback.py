"""AI Response API Models"""

from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class AIFeedbackCreate(BaseModel):
    ai_request_id: str
    text_response: str
    rating: Optional[bool] = None  # True — хороший, False — плохой, None — не оценено
    comment: Optional[str] = None

class AIFeedbackOut(BaseModel):
    id: int
    ai_request_id: UUID
    text_response: str
    rating: Optional[bool]
    comment: Optional[str]