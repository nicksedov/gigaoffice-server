# prompts.py
"""
GigaOffice Prompt Manager
Менеджер для работы с предустановленными промптами и популярными запросами
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload
from loguru import logger
from cachetools import TTLCache

from app.services.database.session import get_db_session
from app.models.orm.prompt import Prompt
from app.models.orm.category import Category

class PromptManager:
    """Менеджер для работы с промптами"""
    
    def __init__(self):
        # TTLCache(maxsize, ttl) - maxsize можно подобрать по объему кэша, ttl в секундах (здесь 1 час)
        self.cache = TTLCache(maxsize=1000, ttl=3600)

    async def get_prompt_categories(self) -> List[Dict[str, Any]]:
        cache_key = "categories_with_description"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with get_db_session() as db:
                categories = db.query(
                    Category.id,
                    Category.name,
                    Category.display_name,
                    Category.description,
                    Category.is_active,
                    Category.sort_order,
                    func.count(Prompt.id).label('prompt_count')
                ).outerjoin(
                    Prompt, (Category.id == Prompt.category_id) & (Prompt.is_active == True)
                ).filter(
                    Category.is_active == True
                ).group_by(
                    Category.id,
                    Category.name,
                    Category.display_name,
                    Category.description,
                    Category.is_active,
                    Category.sort_order
                ).order_by(Category.sort_order).all()

                result = [
                    {
                        "id": category.id,
                        "name": category.name,
                        "display_name": category.display_name,
                        "description": category.description,
                        "is_active": category.is_active,
                        "sort_order": category.sort_order,
                        "prompt_count": category.prompt_count
                    }
                    for category in categories
                ]

                self.cache[cache_key] = result
                return result

        except Exception as e:
            logger.error(f"Error getting prompt categories: {e}")
            return []

    async def get_prompts(self) -> List[Prompt]:
        cache_key = "all_active_prompts"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with get_db_session() as db:
                prompts = db.query(Prompt).options(
                    joinedload(Prompt.category_obj)
                ).filter(
                    Prompt.is_active == True
                ).order_by(Prompt.usage_count.desc()).all()

                for prompt in prompts:
                    if prompt.category_obj:
                        _ = prompt.category_obj.name  # Принудительная загрузка

                self.cache[cache_key] = prompts
                return prompts

        except Exception as e:
            logger.error(f"Error getting prompts: {e}")
            return []

    async def get_prompts_by_category(self, category_identifier: str) -> List[Prompt]:
        cache_key = f"category_{category_identifier}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with get_db_session() as db:
                if category_identifier.isdigit():
                    prompts = db.query(Prompt).options(
                        joinedload(Prompt.category_obj)
                    ).filter(
                        Prompt.category_id == int(category_identifier),
                        Prompt.is_active == True
                    ).order_by(Prompt.usage_count.desc()).all()
                else:
                    prompts = db.query(Prompt).options(
                        joinedload(Prompt.category_obj)
                    ).join(Category).filter(
                        Category.name == category_identifier,
                        Category.is_active == True,
                        Prompt.is_active == True
                    ).order_by(Prompt.usage_count.desc()).all()

                for prompt in prompts:
                    if prompt.category_obj:
                        _ = prompt.category_obj.name  # Принудительная загрузка

                self.cache[cache_key] = prompts
                return prompts

        except Exception as e:
            logger.error(f"Error getting prompts by category: {e}")
            return []
    
    async def get_usage_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Получение аналитики использования промптов"""
        try:
            with get_db_session() as db:
                # Get date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Most used prompts
                most_used = db.query(Prompt).filter(
                    Prompt.is_active == True
                ).order_by(desc(Prompt.usage_count)).limit(10).all()
                
                # Category statistics
                category_stats = db.query(
                    Prompt.category,
                    func.count(Prompt.id).label('count'),
                    func.sum(Prompt.usage_count).label('total_usage')
                ).filter(
                    Prompt.is_active == True,
                    Prompt.category.isnot(None)
                ).group_by(Prompt.category).all()
                
                return {
                    "period_days": days,
                    "most_used_prompts": [
                        {
                            "name": prompt.name,
                            "usage_count": prompt.usage_count,
                            "category": prompt.category
                        }
                        for prompt in most_used
                    ],
                    "category_statistics": [
                        {
                            "category": category,
                            "prompt_count": count,
                            "total_usage": total_usage or 0
                        }
                        for category, count, total_usage in category_stats
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            return {}
    
    # При изменении данных очищаем кэш полностью
    def _clear_cache(self):
        self.cache.clear()

# Global instance
prompt_manager = PromptManager()