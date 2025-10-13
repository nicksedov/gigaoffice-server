"""Chart Request ORM Model"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.orm.base import Base
from app.models.types.enums import RequestStatus

class ChartRequest(Base):
    """Модель запроса на генерацию диаграммы"""
    __tablename__ = "chart_requests"
    
    id = Column(String(36), primary_key=True, index=True)  # UUID string
    user_id = Column(Integer, index=True)
    status = Column(String(20), default=RequestStatus.PENDING.value)
    
    # Chart-specific request data
    chart_instruction = Column(Text, nullable=False)
    chart_data = Column(JSON, nullable=False)  # DataSource model as JSON
    chart_preferences = Column(JSON)  # ChartPreferences model as JSON
    
    # Generated chart configuration
    chart_config = Column(JSON)  # ChartConfig model as JSON
    chart_type = Column(String(20))  # Denormalized for quick querying
       
    # Response data
    error_message = Column(Text)
    
    # Performance metadata
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