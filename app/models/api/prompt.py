"""Prompt API Models"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class PromptResponse(BaseModel):
    """Схема ответа с данными промпта"""
    id: int
    name: str
    description: Optional[str]
    template: str
    category_id: Optional[int]
    category_name: Optional[str]  # Получаем через relationship
    is_active: bool
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromptCreate(BaseModel):
    """Схема для создания промпта"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template: str = Field(..., min_length=1)
    category: Optional[str] = None

class PromptClassificationRequest(BaseModel):
    """Схема для классификации промпта"""
    prompt_text: str = Field(..., min_length=1, description="Текст промпта для классификации")
    include_descriptions: bool = Field(False, description="Включать ли описания категорий в системный промпт")

class PromptInfo(BaseModel):
    """Prompt information model"""
    id: int
    name: str
    description: Optional[str]
    template: str
    category_id: int

class PresetPromptInfo(BaseModel):
    """Preset prompt information model"""
    id: int
    name: str
    template: str
    category_id: int
    category_name: Optional[str]
    category_display_name: Optional[str]

class PromptClassificationResponse(BaseModel):
    """Response model for prompt classification endpoint"""
    success: bool
    query_text: str
    category: str
    confidence: float

class PresetPromptsResponse(BaseModel):
    """Response model for preset prompts endpoint"""
    status: str
    prompts: List[PresetPromptInfo]