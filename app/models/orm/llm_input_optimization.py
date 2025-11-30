"""LLM Input Optimization ORM Model"""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Computed
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.orm.base import Base


class LLMInputOptimization(Base):
    """Модель для хранения оптимизаций входных данных LLM"""
    __tablename__ = "llm_input_optimizations"
    
    id = Column(String(36), primary_key=True, index=True)  # UUID string
    original_data = Column(JSON, nullable=False)
    optimizations_applied = Column(JSON, nullable=False)
    optimized_data = Column(JSON, nullable=False)
    original_size_bytes = Column(Integer, nullable=False)
    optimized_size_bytes = Column(Integer, nullable=False)
    reduction_percentage = Column(
        Float,
        Computed(
            "CASE WHEN original_size_bytes > 0 "
            "THEN ((original_size_bytes - optimized_size_bytes)::FLOAT / original_size_bytes * 100) "
            "ELSE 0 END"
        )
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship - one optimization can be referenced by multiple AI requests
    ai_requests = relationship("AIRequest", back_populates="optimization")
