"""
Shared Type Definitions
Common enums and types used throughout the application
"""

from enum import Enum


class RequestStatus(str, Enum):
    """Status values for AI processing requests"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    """User role definitions"""
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"


class AIServiceMode(str, Enum):
    """AI service deployment modes"""
    DRYRUN = "dryrun"
    CLOUD = "cloud"
    MTLS = "mtls"


class LogLevel(str, Enum):
    """Logging level definitions"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Environment(str, Enum):
    """Application environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class KafkaTopicType(str, Enum):
    """Kafka topic type definitions"""
    REQUESTS = "requests"
    RESPONSES = "responses"
    DLQ = "dlq"  # Dead Letter Queue