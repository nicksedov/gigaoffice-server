"""Category API Models"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class CategoryResponse(BaseModel):
    """Схема ответа с данными категории"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    prompt_count: int = 0
    
    class Config:
        from_attributes = True