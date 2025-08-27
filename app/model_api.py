"""
GigaOffice Service Data Models
Модели данных для промежуточного сервиса GigaOffice
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID
from app.model_types import RequestStatus, UserRole

# Pydantic модели
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

class PromptResponse(BaseModel):
    """Схема ответа с данными промпта"""
    id: int
    name: str
    description: Optional[str]
    template: str
    category_id: Optional[int]
    category_name: Optional[str]  # Получаем через relationship
    is_active: bool
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Pydantic Models for API

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    total_requests: int
    total_tokens_used: int
    
    class Config:
        from_attributes = True

class PromptCreate(BaseModel):
    """Схема для создания промпта"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template: str = Field(..., min_length=1)
    category: Optional[str] = None

class AIRequestCreate(BaseModel):
    """Схема для создания запроса к ИИ"""
    input_range: Optional[str] = Field(None, max_length=50)
    query_text: str = Field(..., min_length=1)
    category: Optional[str] = None
    input_data: Optional[List[Dict[str, Any]]] = None

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

class AIResponseCreate(BaseModel):
    ai_request_id: str
    text_response: str
    rating: Optional[bool] = None  # True — хороший, False — плохой, None — не оценено
    comment: Optional[str] = None

class AIResponseOut(BaseModel):
    id: int
    ai_request_id: UUID
    text_response: str
    rating: Optional[bool]
    comment: Optional[str]

class PromptClassificationRequest(BaseModel):
    """Схема для классификации промпта"""
    prompt_text: str = Field(..., min_length=1, description="Текст промпта для классификации")
    include_descriptions: bool = Field(False, description="Включать ли описания категорий в системный промпт")    

class ServiceHealth(BaseModel):
    """Схема для проверки здоровья сервиса"""
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    uptime: float  # seconds
    
    # Service components status
    database: bool = True
    gigachat: bool = True
    kafka: bool = True
    
    # Performance metrics
    active_requests: int = 0
    queue_size: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

class ProcessingStatus(BaseModel):
    """Схема статуса обработки"""
    request_id: int
    status: str
    progress: int = Field(0, ge=0, le=100)  # Percentage
    message: str = ""
    estimated_time: Optional[int] = None  # seconds

class MetricsResponse(BaseModel):
    """Схема ответа с метриками"""
    period: str  # "hour", "day", "week", "month"
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_processing_time: float
    total_tokens_used: int
    
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

class TokenUsage(BaseModel):
    """Схема использования токенов"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: Optional[float] = None  # В рублях

class QueueInfo(BaseModel):
    """Информация об очереди"""
    position: int
    total_in_queue: int
    estimated_wait_time: int  # seconds
    priority: int