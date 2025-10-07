"""Category API Models"""

from typing import Optional, List
from pydantic import BaseModel

class CategoryResponse(BaseModel):
    """Схема ответа с данными категории"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    prompt_count: int = 0
    
    class Config:
        from_attributes = True

class CategoryInfo(BaseModel):
    """Category information model"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_active: bool
    sort_order: int
    prompt_count: int

class PromptCategoriesResponse(BaseModel):
    """Response model for prompt categories endpoint"""
    status: str
    categories: List[CategoryInfo]

class PromptInfo(BaseModel):
    """Prompt information model"""
    id: int
    name: str
    description: Optional[str]
    template: str
    category_id: int

class CategoryDetailsResponse(BaseModel):
    """Response model for category details endpoint"""
    status: str
    category: CategoryInfo
    prompts: List[PromptInfo]