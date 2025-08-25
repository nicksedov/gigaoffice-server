"""
Prompt API Models
Pydantic models for prompt and category management
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class CategoryCreate(BaseModel):
    """Schema for creating category"""
    name: str = Field(..., min_length=1, max_length=50, description="Category unique name")
    display_name: str = Field(..., min_length=1, max_length=255, description="Category display name")
    description: Optional[str] = Field(None, max_length=1000, description="Category description")
    sort_order: int = Field(0, description="Sort order for display")
    icon: Optional[str] = Field(None, max_length=255, description="Icon name or URL")
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$', description="Hex color code")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Category name can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "data_analysis",
                "display_name": "Data Analysis",
                "description": "Prompts for analyzing and interpreting data",
                "sort_order": 10,
                "icon": "chart-bar",
                "color": "#3B82F6"
            }
        }


class CategoryUpdate(BaseModel):
    """Schema for updating category"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    icon: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')


class CategoryResponse(BaseModel):
    """Schema for category response"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    icon: Optional[str]
    color: Optional[str]
    prompt_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "data_analysis",
                "display_name": "Data Analysis",
                "description": "Prompts for analyzing data",
                "is_active": True,
                "sort_order": 10,
                "icon": "chart-bar",
                "color": "#3B82F6",
                "prompt_count": 25,
                "created_at": "2024-08-01T10:00:00Z",
                "updated_at": "2024-08-15T14:30:00Z"
            }
        }


class PromptCreate(BaseModel):
    """Schema for creating prompt"""
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    description: Optional[str] = Field(None, max_length=1000, description="Prompt description")
    template: str = Field(..., min_length=1, max_length=10000, description="Prompt template")
    category_id: Optional[int] = Field(None, description="Category ID")
    tags: Optional[List[str]] = Field(None, max_items=10, description="Prompt tags")
    expected_input_format: Optional[Dict[str, Any]] = Field(None, description="Expected input format schema")
    version: str = Field("1.0", description="Prompt version")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            # Ensure tags are unique and clean
            cleaned_tags = list(set(tag.strip().lower() for tag in v if tag.strip()))
            return cleaned_tags[:10]  # Limit to 10 tags
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Sales Data Analysis",
                "description": "Analyze sales performance data and provide insights",
                "template": "Analyze the following sales data: {data}. Provide insights on {focus_area}.",
                "category_id": 1,
                "tags": ["sales", "analysis", "reporting"],
                "expected_input_format": {
                    "data": "array of objects",
                    "focus_area": "string"
                },
                "version": "1.0"
            }
        }


class PromptUpdate(BaseModel):
    """Schema for updating prompt"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    template: Optional[str] = Field(None, min_length=1, max_length=10000)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
    expected_input_format: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            cleaned_tags = list(set(tag.strip().lower() for tag in v if tag.strip()))
            return cleaned_tags[:10]
        return v


class PromptResponse(BaseModel):
    """Schema for prompt response"""
    id: int
    name: str
    description: Optional[str]
    template: str
    category_id: Optional[int]
    category_name: Optional[str]
    is_active: bool
    usage_count: int
    avg_rating: float
    total_ratings: int
    avg_processing_time: float
    tags: Optional[List[str]]
    expected_input_format: Optional[Dict[str, Any]]
    version: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[int]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Sales Data Analysis",
                "description": "Analyze sales performance data",
                "template": "Analyze the following sales data: {data}",
                "category_id": 1,
                "category_name": "Data Analysis",
                "is_active": True,
                "usage_count": 150,
                "avg_rating": 4.5,
                "total_ratings": 30,
                "avg_processing_time": 2.5,
                "tags": ["sales", "analysis"],
                "version": "1.0",
                "created_at": "2024-08-01T10:00:00Z"
            }
        }


class PromptPublic(BaseModel):
    """Schema for public prompt information"""
    id: int
    name: str
    description: Optional[str]
    category_name: Optional[str]
    usage_count: int
    avg_rating: float
    tags: Optional[List[str]]
    
    class Config:
        from_attributes = True


class PromptValidation(BaseModel):
    """Schema for prompt template validation"""
    template: str = Field(..., description="Prompt template to validate")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test data for validation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template": "Analyze the data: {data} and focus on {aspect}",
                "test_data": {
                    "data": "sample data",
                    "aspect": "trends"
                }
            }
        }


class PromptValidationResponse(BaseModel):
    """Schema for prompt validation response"""
    valid: bool
    required_variables: List[str]
    formatted_template: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "required_variables": ["data", "aspect"],
                "formatted_template": "Analyze the data: sample data and focus on trends",
                "error": None
            }
        }


class PromptUsageStats(BaseModel):
    """Schema for prompt usage statistics"""
    prompt_id: int
    usage_count: int
    avg_rating: float
    total_ratings: int
    avg_processing_time: float
    success_rate: float
    last_used: Optional[datetime]
    popular_variables: List[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt_id": 1,
                "usage_count": 150,
                "avg_rating": 4.5,
                "total_ratings": 30,
                "avg_processing_time": 2.5,
                "success_rate": 95.0,
                "last_used": "2024-08-25T10:00:00Z",
                "popular_variables": [
                    {"variable": "data", "frequency": 150},
                    {"variable": "aspect", "frequency": 120}
                ]
            }
        }


class PromptDuplicate(BaseModel):
    """Schema for duplicating prompt"""
    new_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    modify_template: bool = Field(False, description="Whether to allow template modification")
    
    class Config:
        json_schema_extra = {
            "example": {
                "new_name": "Sales Data Analysis V2",
                "description": "Updated version of sales analysis prompt",
                "modify_template": True
            }
        }


class PromptExport(BaseModel):
    """Schema for prompt export request"""
    format: str = Field("json", regex=r'^(json|csv)$', description="Export format")
    category_id: Optional[int] = Field(None, description="Filter by category")
    include_inactive: bool = Field(False, description="Include inactive prompts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "format": "json",
                "category_id": 1,
                "include_inactive": False
            }
        }


class PromptsListResponse(BaseModel):
    """Schema for prompts list response"""
    prompts: List[PromptResponse]
    total: int
    page: int
    size: int
    total_pages: int
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompts": [
                    {
                        "id": 1,
                        "name": "Sales Analysis",
                        "category_name": "Data Analysis",
                        "usage_count": 150,
                        "avg_rating": 4.5
                    }
                ],
                "total": 50,
                "page": 1,
                "size": 20,
                "total_pages": 3,
                "filters": {"category_id": 1}
            }
        }


class CategoriesListResponse(BaseModel):
    """Schema for categories list response"""
    categories: List[CategoryResponse]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "categories": [
                    {
                        "id": 1,
                        "name": "data_analysis",
                        "display_name": "Data Analysis",
                        "prompt_count": 25
                    }
                ],
                "total": 5
            }
        }