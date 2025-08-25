"""
Models Module

Pydantic models for API request/response validation and shared type definitions.
"""

from .types import RequestStatus, UserRole, AIServiceMode, LogLevel, Environment, KafkaTopicType
from .ai_requests import AIRequestCreate, AIRequestResponse, ProcessingStatus
from .users import UserCreate, UserResponse
from .ai_responses import AIResponseCreate, AIResponseOut, AIResponseUpdate
from .prompts import PromptCreate, PromptResponse, CategoryResponse, PromptClassificationRequest
from .health import ServiceHealth, MetricsResponse, ErrorResponse, SuccessResponse

__all__ = [
    # Types
    "RequestStatus",
    "UserRole", 
    "AIServiceMode",
    "LogLevel",
    "Environment",
    "KafkaTopicType",
    # AI Requests
    "AIRequestCreate",
    "AIRequestResponse",
    "ProcessingStatus",
    # Users
    "UserCreate",
    "UserResponse",
    # AI Responses
    "AIResponseCreate",
    "AIResponseOut",
    "AIResponseUpdate",
    # Prompts
    "PromptCreate",
    "PromptResponse",
    "CategoryResponse",
    "PromptClassificationRequest",
    # Health
    "ServiceHealth",
    "MetricsResponse",
    "ErrorResponse",
    "SuccessResponse"
]