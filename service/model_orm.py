from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from datetime import datetime
from model_types import RequestStatus, UserRole

Base = declarative_base()

# Модели для SQLAlchemy

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

class Category(Base):
    """Модель категории промптов"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    prompts = relationship("Prompt", back_populates="category_obj")

class Prompt(Base):
    """Модель предустановленного промпта"""
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer)  # Reference to User.id
    
    # Relationship
    category_obj = relationship("Category", back_populates="prompts")

class AIRequest(Base):
    """Модель запроса к ИИ"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    status = Column(String(20), default=RequestStatus.PENDING.value)
    
    # Request data
    input_range = Column(String(50))
    query_text = Column(Text, nullable=False)
    category = Column(String(50))
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

    responses = relationship("AIResponse", back_populates="ai_request", cascade="all, delete-orphan")

class AIResponse(Base):
    __tablename__ = "ai_responses"

    id = Column(Integer, primary_key=True, index=True)
    ai_request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False, index=True)
    text_response = Column(Text, nullable=False)
    rating = Column(Boolean, nullable=True)  # true=хороший, false=плохой, null=не оценено
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Опционально: связь для удобства доступа к запросу
    ai_request = relationship("AIRequest", back_populates="responses")

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

