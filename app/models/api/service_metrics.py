"""Service Metrics API Models"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

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

class MetricsResponse(BaseModel):
    """Схема ответа с метриками"""
    period: str  # "hour", "day", "week", "month"
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_processing_time: float
    total_tokens_used: int

class TokenUsage(BaseModel):
    """Схема использования токенов"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: Optional[float] = None  # В рублях