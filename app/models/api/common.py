"""Common API Models"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class SuccessResponse(BaseModel):
    """Схема успешного ответа"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Dict[str, Any]] = None

# Utility schemas

class PaginationParams(BaseModel):
    """Параметры пагинации"""
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    
class FilterParams(BaseModel):
    """Параметры фильтрации"""
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_id: Optional[int] = None

class SortParams(BaseModel):
    """Параметры сортировки"""
    field: str = "created_at"
    direction: str = Field("desc", pattern=r'^(asc|desc)$')