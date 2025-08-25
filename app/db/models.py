"""
Database ORM Models
Enhanced SQLAlchemy models with improved relationships and validation
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.models.types import RequestStatus, UserRole


# Base class for all ORM models
Base = declarative_base()


class TimestampMixin:
    """Mixin for common timestamp fields"""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base, TimestampMixin):
    """User model with enhanced fields and relationships"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), default=UserRole.USER.value)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    
    # Usage statistics
    total_requests = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    monthly_requests = Column(Integer, default=0)
    monthly_tokens_used = Column(Integer, default=0)
    
    # Usage limits
    daily_request_limit = Column(Integer, default=100)
    monthly_token_limit = Column(Integer, default=10000)
    
    # Relationships
    ai_requests = relationship("AIRequest", back_populates="user", cascade="all, delete-orphan")
    created_prompts = relationship("Prompt", foreign_keys="Prompt.created_by", back_populates="creator")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
    
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value
    
    def can_make_request(self) -> bool:
        return self.is_active and self.monthly_requests < self.monthly_token_limit


class Category(Base, TimestampMixin):
    """Category model for organizing prompts"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Category metadata
    icon = Column(String(255))  # Icon name or URL
    color = Column(String(7))   # Hex color code
    
    # Relationships
    prompts = relationship("Prompt", back_populates="category_obj")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', display_name='{self.display_name}')>"
    
    @property
    def active_prompts_count(self):
        return len([p for p in self.prompts if p.is_active])


class Prompt(Base, TimestampMixin):
    """Prompt template model with versioning support"""
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Prompt metadata
    version = Column(String(20), default="1.0")
    tags = Column(JSON)  # Array of tags
    expected_input_format = Column(JSON)  # Schema for expected input
    
    # Performance metrics
    avg_rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    avg_processing_time = Column(Float, default=0.0)
    
    # Relationships
    category_obj = relationship("Category", back_populates="prompts")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_prompts")
    ai_requests = relationship("AIRequest", back_populates="prompt")
    
    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', category_id={self.category_id})>"
    
    def increment_usage(self):
        self.usage_count += 1
    
    def update_rating(self, new_rating: float):
        if self.total_ratings == 0:
            self.avg_rating = new_rating
        else:
            total_score = self.avg_rating * self.total_ratings + new_rating
            self.avg_rating = total_score / (self.total_ratings + 1)
        self.total_ratings += 1


class AIRequest(Base, TimestampMixin):
    """AI request model with enhanced tracking and relationships"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=True)
    status = Column(String(20), default=RequestStatus.PENDING.value, index=True)
    
    # Request data
    input_range = Column(String(50))
    query_text = Column(Text, nullable=False)
    category = Column(String(50))
    input_data = Column(JSON)
    
    # Response data
    result_data = Column(JSON)
    error_message = Column(Text)
    
    # Metadata and tracking
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float)  # seconds
    gigachat_request_id = Column(String(255))
    
    # Quality metrics
    user_rating = Column(Integer)  # 1-5 rating from user
    user_feedback = Column(Text)
    
    # Timestamps for detailed tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Queue management
    queue_position = Column(Integer)
    priority = Column(Integer, default=0)
    
    # Request context
    client_ip = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    session_id = Column(String(255))
    
    # Relationships
    user = relationship("User", back_populates="ai_requests")
    prompt = relationship("Prompt", back_populates="ai_requests")
    responses = relationship("AIResponse", back_populates="ai_request", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AIRequest(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
    
    @property
    def is_completed(self) -> bool:
        return self.status == RequestStatus.COMPLETED.value
    
    @property
    def is_failed(self) -> bool:
        return self.status == RequestStatus.FAILED.value
    
    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def mark_as_started(self):
        self.status = RequestStatus.PROCESSING.value
        self.started_at = datetime.utcnow()
    
    def mark_as_completed(self, result_data: dict, tokens_used: int = 0):
        self.status = RequestStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        self.result_data = result_data
        self.tokens_used = tokens_used
        if self.started_at:
            self.processing_time = self.duration_seconds
    
    def mark_as_failed(self, error_message: str):
        self.status = RequestStatus.FAILED.value
        self.completed_at = datetime.utcnow()
        self.error_message = error_message


class AIResponse(Base):
    """AI response model for storing multiple responses per request"""
    __tablename__ = "ai_responses"

    id = Column(Integer, primary_key=True, index=True)
    ai_request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False, index=True)
    text_response = Column(Text, nullable=False)
    
    # Quality metrics
    rating = Column(Boolean, nullable=True)  # true=good, false=bad, null=not rated
    comment = Column(Text, nullable=True)
    confidence_score = Column(Float)  # AI confidence in response
    
    # Response metadata
    response_type = Column(String(50), default="text")  # text, json, markdown, etc.
    tokens_used = Column(Integer, default=0)
    model_version = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    ai_request = relationship("AIRequest", back_populates="responses")
    
    def __repr__(self):
        return f"<AIResponse(id={self.id}, ai_request_id={self.ai_request_id}, rating={self.rating})>"


class ServiceMetrics(Base):
    """Service metrics model for monitoring and analytics"""
    __tablename__ = "service_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Request metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    pending_requests = Column(Integer, default=0)
    cancelled_requests = Column(Integer, default=0)
    
    # Performance metrics
    avg_processing_time = Column(Float)  # seconds
    max_processing_time = Column(Float)  # seconds
    min_processing_time = Column(Float)  # seconds
    p95_processing_time = Column(Float)  # 95th percentile
    
    # Token usage
    total_tokens_used = Column(Integer, default=0)
    avg_tokens_per_request = Column(Float, default=0.0)
    
    # System metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    
    # GigaChat specific metrics
    gigachat_errors = Column(Integer, default=0)
    gigachat_avg_response_time = Column(Float)
    gigachat_timeout_count = Column(Integer, default=0)
    
    # Quality metrics
    avg_user_rating = Column(Float)
    total_user_ratings = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ServiceMetrics(id={self.id}, timestamp={self.timestamp}, total_requests={self.total_requests})>"


class AuditLog(Base, TimestampMixin):
    """Audit log model for security and compliance tracking"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(255))
    resource_id = Column(String(50))
    
    # Request context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(255))
    
    # Result and details
    result = Column(String(20))  # success, failed, denied
    details = Column(JSON)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', result='{self.result}')>"