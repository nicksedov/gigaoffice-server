"""
GigaOffice Service Data Models
Модели данных для промежуточного сервиса GigaOffice
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from enum import Enum

# SQLAlchemy Base
Base = declarative_base()

# Enums
class RequestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"

# SQLAlchemy Models

class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), default=UserRole.USER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Usage statistics
    total_requests = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    monthly_requests = Column(Integer, default=0)
    monthly_tokens_used = Column(Integer, default=0)

class Prompt(Base):
    """Модель предустановленного промпта"""
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template = Column(Text, nullable=False)
    category = Column(String(100))
    language = Column(String(10), default="ru")
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer)  # Reference to User.id

class AIRequest(Base):
    """Модель запроса к ИИ"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    status = Column(String(20), default=RequestStatus.PENDING.value)
    
    # Request data
    input_range = Column(String(50))
    output_range = Column(String(50), nullable=False)
    query_text = Column(Text, nullable=False)
    preset_prompt_id = Column(Integer)  # Reference to Prompt.id
    input_data = Column(JSON)
    
    # Response data
    result_data = Column(JSON)
    error_message = Column(Text)
    
    # Metadata
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float)  # seconds
    gigachat_request_id = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Queue info
    queue_position = Column(Integer)
    priority = Column(Integer, default=0)

class ServiceMetrics(Base):
    """Модель метрик сервиса"""
    __tablename__ = "service_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Request metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    pending_requests = Column(Integer, default=0)
    
    # Performance metrics
    avg_processing_time = Column(Float)  # seconds
    max_processing_time = Column(Float)  # seconds
    min_processing_time = Column(Float)  # seconds
    
    # Token usage
    total_tokens_used = Column(Integer, default=0)
    
    # System metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    
    # GigaChat metrics
    gigachat_errors = Column(Integer, default=0)
    gigachat_avg_response_time = Column(Float)

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
    language: str = Field(default="ru", pattern=r'^[a-z]{2}$')

class PromptResponse(BaseModel):
    """Схема ответа с данными промпта"""
    id: int
    name: str
    description: Optional[str]
    template: str
    category: Optional[str]
    language: str
    is_active: bool
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AIRequestCreate(BaseModel):
    """Схема для создания запроса к ИИ"""
    input_range: Optional[str] = Field(None, max_length=50)
    output_range: str = Field(..., max_length=50)
    query_text: str = Field(..., min_length=1)
    preset_prompt: Optional[str] = None
    input_data: Optional[List[Dict[str, Any]]] = None

class AIRequestResponse(BaseModel):
    """Схема ответа запроса к ИИ"""
    id: int
    status: str
    input_range: Optional[str]
    output_range: str
    query_text: str
    result_data: Optional[List[List[Any]]]
    error_message: Optional[str]
    tokens_used: int
    processing_time: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

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
    redis: bool = True
    
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