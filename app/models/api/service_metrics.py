"""Service Metrics API Models"""

from typing import Optional
from pydantic import BaseModel

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