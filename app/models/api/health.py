"""Health API Models"""

from pydantic import BaseModel, Field
from datetime import datetime

class PingResponse(BaseModel):
    """Response model for ping endpoint"""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)

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