"""
Health and Common API Models
Pydantic models for health checks, metrics, and common responses
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    """Schema for service health check"""
    status: str = Field(..., description="Overall service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field("1.0.0", description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    
    # Component health status
    database: Dict[str, Any] = Field(..., description="Database health status")
    gigachat: Dict[str, Any] = Field(..., description="GigaChat service status")
    kafka: Dict[str, Any] = Field(..., description="Kafka service status")
    prompts: Dict[str, Any] = Field(..., description="Prompt manager status")
    
    # Performance metrics
    active_requests: int = Field(0, description="Currently active requests")
    queue_size: int = Field(0, description="Queue size")
    memory_usage: float = Field(0.0, description="Memory usage percentage")
    cpu_usage: float = Field(0.0, description="CPU usage percentage")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-08-25T10:00:00Z",
                "version": "1.0.0",
                "uptime": 86400.0,
                "database": {
                    "status": "healthy",
                    "response_time": 0.05,
                    "connection_pool": {
                        "size": 20,
                        "checked_out": 5
                    }
                },
                "gigachat": {
                    "status": "healthy",
                    "mode": "cloud",
                    "success_rate": 98.5
                },
                "kafka": {
                    "status": "healthy",
                    "consumer_running": True,
                    "messages_processed": 1500
                },
                "prompts": {
                    "status": "healthy",
                    "cache_hit_rate": 85.0,
                    "total_prompts": 150
                },
                "active_requests": 12,
                "queue_size": 3,
                "memory_usage": 65.5,
                "cpu_usage": 25.3
            }
        }


class ComponentHealth(BaseModel):
    """Schema for individual component health"""
    status: str = Field(..., description="Component status (healthy, degraded, unhealthy)")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional component details")
    last_check: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "response_time": 0.05,
                "error": None,
                "details": {
                    "pool_size": 20,
                    "active_connections": 5
                },
                "last_check": "2024-08-25T10:00:00Z"
            }
        }


class MetricsResponse(BaseModel):
    """Schema for system metrics"""
    period: str = Field(..., description="Metrics period (hour, day, week, month)")
    start_time: datetime
    end_time: datetime
    
    # Request metrics
    total_requests: int = Field(0, description="Total requests in period")
    successful_requests: int = Field(0, description="Successful requests")
    failed_requests: int = Field(0, description="Failed requests")
    avg_processing_time: float = Field(0.0, description="Average processing time in seconds")
    
    # Token usage
    total_tokens_used: int = Field(0, description="Total tokens consumed")
    avg_tokens_per_request: float = Field(0.0, description="Average tokens per request")
    
    # Performance metrics
    avg_response_time: float = Field(0.0, description="Average response time")
    p95_response_time: float = Field(0.0, description="95th percentile response time")
    error_rate: float = Field(0.0, description="Error rate percentage")
    
    # Usage by category
    category_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Top users by usage
    top_users: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "period": "day",
                "start_time": "2024-08-25T00:00:00Z",
                "end_time": "2024-08-25T23:59:59Z",
                "total_requests": 1500,
                "successful_requests": 1465,
                "failed_requests": 35,
                "avg_processing_time": 2.5,
                "total_tokens_used": 150000,
                "avg_tokens_per_request": 100.0,
                "avg_response_time": 2.3,
                "p95_response_time": 5.8,
                "error_rate": 2.3,
                "category_breakdown": [
                    {"category": "analysis", "count": 750, "percentage": 50.0},
                    {"category": "generation", "count": 450, "percentage": 30.0}
                ],
                "top_users": [
                    {"user_id": 1, "username": "john_doe", "requests": 150},
                    {"user_id": 2, "username": "jane_smith", "requests": 120}
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Schema for error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data provided",
                "details": {
                    "field": "query_text",
                    "issue": "Field is required"
                },
                "timestamp": "2024-08-25T10:00:00Z",
                "request_id": "req_123456789"
            }
        }


class SuccessResponse(BaseModel):
    """Schema for successful operation response"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field("Operation completed successfully", description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "User created successfully",
                "data": {
                    "user_id": 123,
                    "username": "john_doe"
                },
                "timestamp": "2024-08-25T10:00:00Z"
            }
        }


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "size": 20
            }
        }


class FilterParams(BaseModel):
    """Schema for filtering parameters"""
    status: Optional[str] = Field(None, description="Filter by status")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    category: Optional[str] = Field(None, description="Filter by category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "date_from": "2024-08-01T00:00:00Z",
                "date_to": "2024-08-31T23:59:59Z",
                "user_id": 1,
                "category": "analysis"
            }
        }


class SortParams(BaseModel):
    """Schema for sorting parameters"""
    field: str = Field("created_at", description="Field to sort by")
    direction: str = Field("desc", pattern=r'^(asc|desc)$', description="Sort direction")
    
    class Config:
        json_schema_extra = {
            "example": {
                "field": "created_at",
                "direction": "desc"
            }
        }


class SearchParams(BaseModel):
    """Schema for search parameters"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")
    exact_match: bool = Field(False, description="Use exact match instead of fuzzy search")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "sales analysis",
                "fields": ["name", "description"],
                "exact_match": False
            }
        }


class BulkOperation(BaseModel):
    """Schema for bulk operations"""
    operation: str = Field(..., description="Bulk operation type")
    items: List[int] = Field(..., min_items=1, max_items=100, description="Item IDs for bulk operation")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "operation": "delete",
                "items": [1, 2, 3, 4, 5],
                "parameters": {
                    "soft_delete": True
                }
            }
        }


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response"""
    operation: str
    total_items: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "operation": "delete",
                "total_items": 5,
                "successful": 4,
                "failed": 1,
                "errors": [
                    {
                        "item_id": 3,
                        "error": "Item not found"
                    }
                ]
            }
        }


class SystemInfo(BaseModel):
    """Schema for system information"""
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment (dev, staging, prod)")
    start_time: datetime = Field(..., description="Service start time")
    build_info: Dict[str, Any] = Field(..., description="Build information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "GigaOffice AI Service",
                "version": "1.0.0",
                "environment": "production",
                "start_time": "2024-08-25T00:00:00Z",
                "build_info": {
                    "commit": "abc123def456",
                    "branch": "main",
                    "build_date": "2024-08-24T20:00:00Z"
                }
            }
        }