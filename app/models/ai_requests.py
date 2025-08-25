"""
AI Request API Models
Pydantic models for AI request and response validation
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID

from ..db.models import RequestStatus


class AIRequestCreate(BaseModel):
    """Schema for creating AI request"""
    input_range: Optional[str] = Field(None, max_length=50, description="Input data range")
    query_text: str = Field(..., min_length=1, max_length=10000, description="Query text")
    category: Optional[str] = Field(None, description="Request category")
    input_data: Optional[List[Dict[str, Any]]] = Field(None, description="Additional input data")
    priority: int = Field(0, ge=0, le=10, description="Request priority (0-10)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input_range": "A1:C10",
                "query_text": "Analyze this data and provide insights",
                "category": "analysis",
                "input_data": [{"sheet": "Sheet1", "data": []}],
                "priority": 5
            }
        }


class AIRequestResponse(BaseModel):
    """Schema for AI request response"""
    id: int
    status: str
    input_range: Optional[str]
    query_text: str
    category: Optional[str]
    result_data: Optional[List[List[Any]]]
    error_message: Optional[str]
    tokens_used: int
    processing_time: Optional[float]
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_feedback: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123,
                "status": "completed",
                "input_range": "A1:C10",
                "query_text": "Analyze this data",
                "category": "analysis",
                "result_data": [["Analysis", "Result"], ["Data", "Processed"]],
                "error_message": None,
                "tokens_used": 150,
                "processing_time": 2.5,
                "user_rating": 5,
                "created_at": "2024-08-25T10:00:00Z",
                "completed_at": "2024-08-25T10:00:02Z"
            }
        }


class AIRequestUpdate(BaseModel):
    """Schema for updating AI request"""
    status: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=10)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_feedback: Optional[str] = Field(None, max_length=1000)


class AIResponseCreate(BaseModel):
    """Schema for creating AI response"""
    ai_request_id: int
    text_response: str = Field(..., min_length=1)
    rating: Optional[bool] = Field(None, description="True for good, False for bad, None for not rated")
    comment: Optional[str] = Field(None, max_length=500)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    response_type: str = Field("text", description="Response type: text, json, markdown, etc.")


class AIResponseOut(BaseModel):
    """Schema for AI response output"""
    id: int
    ai_request_id: int
    text_response: str
    rating: Optional[bool]
    comment: Optional[str]
    confidence_score: Optional[float]
    response_type: str
    tokens_used: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AIResponseUpdate(BaseModel):
    """Schema for updating AI response"""
    rating: Optional[bool] = None
    comment: Optional[str] = Field(None, max_length=500)


class ProcessingStatus(BaseModel):
    """Schema for processing status"""
    request_id: int
    status: str
    progress: int = Field(0, ge=0, le=100, description="Percentage complete")
    message: str = ""
    estimated_time: Optional[int] = Field(None, description="Estimated completion time in seconds")
    queue_position: Optional[int] = Field(None, description="Position in processing queue")
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": 123,
                "status": "processing",
                "progress": 75,
                "message": "Analyzing data...",
                "estimated_time": 30,
                "queue_position": 2
            }
        }


class QueueInfo(BaseModel):
    """Schema for queue information"""
    position: int = Field(..., description="Position in queue")
    total_in_queue: int = Field(..., description="Total requests in queue")
    estimated_wait_time: int = Field(..., description="Estimated wait time in seconds")
    priority: int = Field(..., description="Request priority")
    
    class Config:
        json_schema_extra = {
            "example": {
                "position": 3,
                "total_in_queue": 15,
                "estimated_wait_time": 120,
                "priority": 5
            }
        }


class TokenUsage(BaseModel):
    """Schema for token usage information"""
    input_tokens: int = Field(..., description="Tokens used for input")
    output_tokens: int = Field(..., description="Tokens used for output")
    total_tokens: int = Field(..., description="Total tokens used")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost in rubles")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "estimated_cost": 0.75
            }
        }


class AIRequestBatch(BaseModel):
    """Schema for batch AI request processing"""
    requests: List[AIRequestCreate] = Field(..., max_items=10, description="Batch of AI requests")
    batch_priority: int = Field(0, ge=0, le=10, description="Priority for entire batch")
    
    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "query_text": "Analyze sales data",
                        "category": "analysis",
                        "priority": 5
                    },
                    {
                        "query_text": "Generate report summary",
                        "category": "generation",
                        "priority": 3
                    }
                ],
                "batch_priority": 5
            }
        }


class AIRequestBatchResponse(BaseModel):
    """Schema for batch AI request response"""
    batch_id: str
    total_requests: int
    accepted_requests: int
    failed_requests: int
    request_ids: List[int]
    estimated_completion_time: Optional[int] = Field(None, description="Estimated time for batch completion")
    
    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_123456",
                "total_requests": 2,
                "accepted_requests": 2,
                "failed_requests": 0,
                "request_ids": [456, 457],
                "estimated_completion_time": 180
            }
        }


class ClassificationRequest(BaseModel):
    """Schema for prompt classification request"""
    prompt_text: str = Field(..., min_length=1, max_length=5000, description="Text to classify")
    include_descriptions: bool = Field(False, description="Include category descriptions in response")
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt_text": "Create a summary of quarterly sales performance",
                "include_descriptions": True,
                "confidence_threshold": 0.7
            }
        }


class ClassificationResponse(BaseModel):
    """Schema for classification response"""
    category: Dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)
    query_text: str
    success: bool
    alternatives: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative categories with confidence")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": {
                    "name": "generation",
                    "display_name": "Content Generation",
                    "description": "Creating new content based on input"
                },
                "confidence": 0.85,
                "query_text": "Create a summary...",
                "success": True,
                "alternatives": [
                    {
                        "name": "analysis",
                        "confidence": 0.65
                    }
                ]
            }
        }