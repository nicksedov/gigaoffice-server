"""AI Request API Models"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID

class AIRequestResponse(BaseModel):
    """Схема ответа запроса к ИИ"""
    id: int
    status: str
    input_range: Optional[str]
    query_text: str
    result_data: Optional[List[List[Any]]]
    error_message: Optional[str]
    tokens_used: int
    processing_time: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class QueueInfo(BaseModel):
    """Информация об очереди"""
    position: int
    total_in_queue: int
    estimated_wait_time: int  # seconds
    priority: int