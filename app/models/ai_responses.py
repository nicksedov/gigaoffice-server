"""
AI Response API Models
Pydantic models for AI response validation and serialization
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AIResponseCreate(BaseModel):
    """Schema for creating AI response"""
    ai_request_id: int
    text_response: str = Field(..., min_length=1, description="AI generated response text")
    rating: Optional[bool] = Field(None, description="True for good, False for bad, None for not rated")
    comment: Optional[str] = Field(None, max_length=500, description="User feedback comment")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI confidence level")
    response_type: str = Field("text", description="Response type: text, json, markdown, etc.")
    tokens_used: int = Field(0, ge=0, description="Token consumption count")
    model_version: Optional[str] = Field(None, max_length=50, description="AI model version used")

    class Config:
        json_schema_extra = {
            "example": {
                "ai_request_id": 123,
                "text_response": "Based on your data analysis request, here are the key insights...",
                "rating": True,
                "comment": "Very helpful response",
                "confidence_score": 0.92,
                "response_type": "text",
                "tokens_used": 250,
                "model_version": "GigaChat-Pro"
            }
        }


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
    model_version: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 456,
                "ai_request_id": 123,
                "text_response": "Based on your data analysis request, here are the key insights...",
                "rating": True,
                "comment": "Very helpful response",
                "confidence_score": 0.92,
                "response_type": "text",
                "tokens_used": 250,
                "model_version": "GigaChat-Pro",
                "created_at": "2024-08-25T10:00:05Z"
            }
        }


class AIResponseUpdate(BaseModel):
    """Schema for updating AI response"""
    rating: Optional[bool] = None
    comment: Optional[str] = Field(None, max_length=500, description="Updated user feedback comment")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated confidence score")

    class Config:
        json_schema_extra = {
            "example": {
                "rating": False,
                "comment": "Response was not accurate enough",
                "confidence_score": 0.65
            }
        }


class AIResponseBatch(BaseModel):
    """Schema for batch AI response operations"""
    responses: list[AIResponseCreate] = Field(..., max_items=50, description="Batch of AI responses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "responses": [
                    {
                        "ai_request_id": 123,
                        "text_response": "Analysis complete: Revenue increased by 15%",
                        "tokens_used": 120
                    },
                    {
                        "ai_request_id": 124,
                        "text_response": "Generated summary: Q3 performance exceeded expectations",
                        "tokens_used": 85
                    }
                ]
            }
        }