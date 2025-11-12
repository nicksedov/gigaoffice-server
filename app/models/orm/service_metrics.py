"""Service Metrics ORM Model"""

from sqlalchemy import Column, Integer, DateTime, Float
from sqlalchemy.sql import func
from app.models.orm.base import Base

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