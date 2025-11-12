"""AI Request ORM Model"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float 
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.orm.base import Base
from app.models.types.enums import RequestStatus

class AIRequest(Base):
    """Модель запроса к ИИ"""
    __tablename__ = "ai_requests"
    
    id = Column(String(36), primary_key=True, index=True)  # UUID string
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

    responses = relationship("AIFeedback", back_populates="ai_request", cascade="all, delete-orphan")