"""
Prompts API Router
Router for prompt management endpoints
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.models.api.prompt import PromptClassificationRequest, PresetPromptsResponse, PromptClassificationResponse
from app.models.api.category import PromptCategoriesResponse, CategoryDetailsResponse, CategoryInfo, PromptInfo
from app.models.orm.category import Category
from app.services.database.session import get_db
# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_service

# Create services in the module where needed
gigachat_classify_service = create_gigachat_service(prompt_builder, "GIGACHAT_CLASSIFY_MODEL", "GigaChat prompt classification service")

from app.prompts import prompt_manager
from app.fastapi_config import security

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

prompts_router = APIRouter(prefix="/api/prompts", tags=["Prompts"])

@prompts_router.get("/categories", response_model=PromptCategoriesResponse)
async def get_prompt_categories_endpoint():
    """Получение списка категорий предустановленных промптов с описанием"""
    try:
        categories = await prompt_manager.get_prompt_categories()
        category_infos = [
            CategoryInfo(
                id=cat["id"],
                name=cat["name"],
                display_name=cat["display_name"],
                description=cat["description"],
                is_active=cat["is_active"],
                sort_order=cat["sort_order"],
                prompt_count=cat["prompt_count"]
            )
            for cat in categories
        ]
        return PromptCategoriesResponse(
            status="success",
            categories=category_infos
        )
    except Exception as e:
        logger.error(f"Error getting prompt categories endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@prompts_router.get("/categories/{category_id}", response_model=CategoryDetailsResponse)
async def get_category_details(category_id: int, db: Session = Depends(get_db)):
    """Получение подробной информации о категории"""
    try:
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        prompts = await prompt_manager.get_prompts_by_category(str(category_id))
        
        category_info = CategoryInfo(
            id=category.id,
            name=category.name,
            display_name=category.display_name,
            description=category.description,
            is_active=category.is_active,
            sort_order=category.sort_order,
            prompt_count=len(prompts)
        )
        
        prompt_infos = [
            PromptInfo(
                id=prompt.id,
                name=prompt.name,
                description=prompt.description,
                template=prompt.template,
                category_id=prompt.category_id
            )
            for prompt in prompts
        ]
        
        return CategoryDetailsResponse(
            status="success",
            category=category_info,
            prompts=prompt_infos
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@prompts_router.get("/presets", response_model=PresetPromptsResponse)
async def get_preset_prompts(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получение предустановленных промптов"""
    try:
        if category:
            prompts = await prompt_manager.get_prompts_by_category(category)
        else:
            prompts = await prompt_manager.get_prompts()

        preset_prompt_infos = [
            {
                "id": prompt.id,
                "name": prompt.name,
                "template": prompt.template,
                "category_id": prompt.category_id,
                "category_name": prompt.category_obj.name if prompt.category_obj else None,
                "category_display_name": prompt.category_obj.display_name if prompt.category_obj else None
            }
            for prompt in prompts
        ]

        return PresetPromptsResponse(
            status="success",
            prompts=preset_prompt_infos
        )

    except Exception as e:
        logger.error(f"Error getting preset prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@prompts_router.post("/classify", response_model=PromptClassificationResponse)
@limiter.limit("10/minute")
async def classify_prompt(
    request: Request,
    classification_request: PromptClassificationRequest,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Классифицирует пользовательский промпт по предопределенным категориям
    
    Args:
        prompt_text: Текст промпта для классификации
        include_descriptions: Включать описания категорий в системный промпт
    
    Returns:
        Результат классификации с вероятностями для каждой категории
    """
    try:
        result = await gigachat_classify_service.classify_query(classification_request.prompt_text)
        
        # Convert the result to the Pydantic model
        return PromptClassificationResponse(
            success=result["success"],
            query_text=result["query_text"],
            category=result["category"]["name"],
            confidence=result["confidence"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))