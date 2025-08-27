"""AI Process API Models"""

from typing import Optional
from pydantic import BaseModel

class AIProcessResponse(BaseModel):
    """Response model for AI request processing"""
    success: bool
    request_id: str
    status: str
    message: str