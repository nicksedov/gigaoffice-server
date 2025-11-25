"""
Kafka Service Data Models
Defines shared data structures and enumerations for Kafka service
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict


class ErrorType(Enum):
    """Классификация ошибок создания топиков"""
    EXPECTED = "expected"  # Нормальное состояние, не требует внимания
    RETRIABLE = "retriable"  # Временная ошибка, можно повторить
    FATAL = "fatal"  # Критическая ошибка, требует вмешательства


@dataclass
class TopicConfig:
    """Конфигурация топика"""
    name: str
    num_partitions: int
    replication_factor: int


@dataclass
class QueueMessage:
    """Сообщение в очереди"""
    id: str
    user_id: int
    priority: int
    query: str
    input_range: str
    category: str
    input_data: Optional[List[Dict]] = None
    created_at: float = field(default_factory=time.time)
