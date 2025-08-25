"""
Prompts Management Endpoints
Endpoints for managing prompt categories, presets, and classification
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.models.prompts import PromptClassificationRequest, CategoryResponse, PromptResponse
from app.db.session import get_db
from app.db.models import Category
from app.db.repositories.prompts import PromptRepository, CategoryRepository
from app.services.ai.factory import gigachat_factory
from app.services.prompts.manager import prompt_manager
from app.utils.logger import structured_logger

# Create router
router = APIRouter(prefix="/api/prompts", tags=["Prompts"])

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Dependencies
async def get_current_user(request: Request):
    """Get current user from request (simplified implementation)"""
    # TODO: Implement proper authentication
    return {"id": 1, "username": "demo_user", "role": "user"}

async def get_prompt_repo(db: Session = Depends(get_db)) -> PromptRepository:
    """Get prompt repository instance"""
    return PromptRepository(db)

async def get_category_repo(db: Session = Depends(get_db)) -> CategoryRepository:
    """Get category repository instance"""
    return CategoryRepository(db)

@router.get("/categories", response_model=Dict[str, Any])
async def get_prompt_categories():
    """
    Get all available prompt categories with descriptions
    
    Returns:
        Dict containing status and list of categories
    """
    try:
        structured_logger.log_api_request(
            endpoint="/api/prompts/categories",
            method="GET",
            duration=0
        )
        
        categories = await prompt_manager.get_prompt_categories()
        
        return {
            "status": "success",
            "count": len(categories),
            "categories": categories
        }
        
    except Exception as e:
        logger.error(f"Error getting prompt categories: {e}")
        structured_logger.log_service_call(
            service="prompts",
            method="get_categories",
            duration=0,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/{category_id}", response_model=Dict[str, Any])
async def get_category_details(
    category_id: int, 
    category_repo: CategoryRepository = Depends(get_category_repo)
):
    """
    Get detailed information about a specific category
    
    Args:
        category_id: Category identifier
        category_repo: Category repository
    
    Returns:
        Dict with category details and associated prompts
    """
    try:
        category = category_repo.get_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        if not category.is_active:
            raise HTTPException(status_code=404, detail="Category not available")
        
        # Get prompts for this category
        prompts = await prompt_manager.get_prompts_by_category(str(category_id))
        
        return {
            "status": "success",
            "category": CategoryResponse.from_orm(category),
            "prompts": [PromptResponse.from_orm(prompt) for prompt in prompts]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presets", response_model=Dict[str, Any])
async def get_preset_prompts(
    category: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0
):
    """
    Get predefined prompts, optionally filtered by category
    
    Args:
        category: Optional category filter
        limit: Maximum number of prompts to return
        offset: Number of prompts to skip
    
    Returns:
        Dict with status and list of prompts
    """
    try:
        structured_logger.log_api_request(
            endpoint="/api/prompts/presets",
            method="GET",
            duration=0,
            metadata={"category": category, "limit": limit}
        )
        
        if category:
            prompts = await prompt_manager.get_prompts_by_category(category)
        else:
            prompts = await prompt_manager.get_prompts()
        
        # Apply pagination
        if offset > 0:
            prompts = prompts[offset:]
        if limit:
            prompts = prompts[:limit]
        
        # Convert to response format
        prompt_data = []
        for prompt in prompts:
            prompt_dict = {
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                "template": prompt.template,
                "category_id": prompt.category_id,
                "usage_count": prompt.usage_count,
                "created_at": prompt.created_at
            }
            
            # Add category information if available
            if hasattr(prompt, 'category_obj') and prompt.category_obj:
                prompt_dict.update({
                    "category_name": prompt.category_obj.name,
                    "category_display_name": prompt.category_obj.display_name
                })
            
            prompt_data.append(prompt_dict)
        
        return {
            "status": "success",
            "count": len(prompt_data),
            "prompts": prompt_data,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": len(prompts) + offset if limit else len(prompt_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting preset prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/classify", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def classify_prompt(
    request: Request,
    classification_request: PromptClassificationRequest,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Classify user prompt into predefined categories
    
    Args:
        request: FastAPI request object
        classification_request: Prompt classification data
        current_user: Current authenticated user
    
    Returns:
        Dict with classification results and confidence scores
    """
    try:
        structured_logger.log_api_request(
            endpoint="/api/prompts/classify",
            method="POST",
            duration=0,
            user_id=str(current_user.get("id")) if current_user else None
        )
        
        # Get classification service
        classify_service = gigachat_factory.get_service("classify")
        
        # Perform classification
        result = await classify_service.classify_query(
            classification_request.prompt_text,
            temperature=0.1
        )
        
        structured_logger.log_service_call(
            service="gigachat_classify",
            method="classify_query",
            duration=0,
            success=result.get("success", False),
            metadata={
                "prompt_length": len(classification_request.prompt_text),
                "confidence": result.get("confidence")
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying prompt: {e}")
        structured_logger.log_service_call(
            service="gigachat_classify",
            method="classify_query",
            duration=0,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/popular", response_model=Dict[str, Any])
async def get_popular_prompts(
    limit: int = 10,
    days: int = 30
):
    """
    Get most popular prompts based on usage statistics
    
    Args:
        limit: Maximum number of prompts to return
        days: Number of days to consider for popularity
    
    Returns:
        Dict with popular prompts and usage statistics
    """
    try:
        analytics = await prompt_manager.get_usage_analytics(days=days)
        
        popular_prompts = analytics.get("most_used_prompts", [])[:limit]
        
        return {
            "status": "success",
            "period_days": days,
            "count": len(popular_prompts),
            "prompts": popular_prompts,
            "category_statistics": analytics.get("category_statistics", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting popular prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_prompts(
    q: str,
    category: Optional[str] = None,
    limit: int = 20
):
    """
    Search prompts by text query
    
    Args:
        q: Search query
        category: Optional category filter
        limit: Maximum results to return
    
    Returns:
        Dict with search results
    """
    try:
        if len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query too short")
        
        # Get prompts to search through
        if category:
            prompts = await prompt_manager.get_prompts_by_category(category)
        else:
            prompts = await prompt_manager.get_prompts()
        
        # Simple text search (case-insensitive)
        search_term = q.lower()
        matching_prompts = []
        
        for prompt in prompts:
            if (search_term in prompt.name.lower() or 
                search_term in (prompt.description or "").lower() or
                search_term in prompt.template.lower()):
                matching_prompts.append({
                    "id": prompt.id,
                    "name": prompt.name,
                    "description": prompt.description,
                    "template": prompt.template[:200] + "..." if len(prompt.template) > 200 else prompt.template,
                    "category_id": prompt.category_id,
                    "usage_count": prompt.usage_count
                })
        
        # Sort by usage count and limit results
        matching_prompts.sort(key=lambda x: x["usage_count"], reverse=True)
        matching_prompts = matching_prompts[:limit]
        
        return {
            "status": "success",
            "query": q,
            "category": category,
            "count": len(matching_prompts),
            "results": matching_prompts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
async def export_prompts(
    format: str = "json",
    category: Optional[str] = None,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Export prompts data
    
    Args:
        format: Export format (json or csv)
        category: Optional category filter
        current_user: Current authenticated user
    
    Returns:
        Exported data in requested format
    """
    try:
        if not current_user or current_user.get("role") not in ["admin", "premium"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
        exported_data = await prompt_manager.export_prompts(format=format)
        
        if not exported_data:
            raise HTTPException(status_code=500, detail="Failed to export data")
        
        # Set appropriate content type
        media_type = "application/json" if format == "json" else "text/csv"
        filename = f"prompts_export.{format}"
        
        from fastapi.responses import Response
        return Response(
            content=exported_data,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))