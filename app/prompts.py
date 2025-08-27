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

    async def get_category_by_name(self, category_name: str) -> Optional[Category]:
        """Получение категории по имени"""
        try:
            with get_db_session() as db:
                return db.query(Category).filter(
                    Category.name == category_name,
                    Category.is_active == True
                ).first()
        except Exception as e:
            logger.error(f"Error getting category by name: {e}")
            return None
    
    async def create_category(
        self,
        name: str,
        display_name: str,
        description: str = None,
        sort_order: int = 0
    ) -> Optional[Category]:
        """Создание новой категории"""
        try:
            with get_db_session() as db:
                category = Category(
                    name=name,
                    display_name=display_name,
                    description=description,
                    sort_order=sort_order
                )
                
                db.add(category)
                db.commit()
                db.refresh(category)
                
                # Clear cache
                self._clear_cache()
                
                logger.info(f"Created new category: {name}")
                return category
                
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None
    
    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Получение промпта по ID"""
        try:
            with get_db_session() as db:
                prompt = db.query(Prompt).filter(
                    Prompt.id == prompt_id,
                    Prompt.is_active == True
                ).first()
                
                if prompt:
                    # Increment usage count
                    prompt.usage_count += 1
                    db.commit()
                
                return prompt
                
        except Exception as e:
            logger.error(f"Error getting prompt by ID: {e}")
            return None
    
    async def create_prompt(
        self,
        name: str,
        template: str,
        description: str = None,
        category_id: int = None,
        created_by: int = None
    ) -> Optional[Prompt]:
        """Создание нового промпта"""
        try:
            with get_db_session() as db:
                prompt = Prompt(
                    name=name,
                    description=description,
                    template=template,
                    category_id=category_id,
                    created_by=created_by
                )
                
                db.add(prompt)
                db.commit()
                db.refresh(prompt)
                
                # Clear cache
                self._clear_cache()
                
                logger.info(f"Created new prompt: {name}")
                return prompt
                
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            return None
    
    async def update_prompt(
        self,
        prompt_id: int,
        name: str = None,
        template: str = None,
        description: str = None,
        category_id: int = None,
        is_active: bool = None
    ) -> Optional[Prompt]:
        """Обновление промпта"""
        try:
            with get_db_session() as db:
                prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
                
                if not prompt:
                    return None
                
                # Update fields
                if name is not None:
                    prompt.name = name
                if template is not None:
                    prompt.template = template
                if description is not None:
                    prompt.description = description
                if category_id is not None:
                    prompt.category_id = category_id
                if is_active is not None:
                    prompt.is_active = is_active
                
                prompt.updated_at = datetime.now()
                
                db.commit()
                db.refresh(prompt)
                
                # Clear cache
                self._clear_cache()
                
                logger.info(f"Updated prompt: {prompt_id}")
                return prompt
                
        except Exception as e:
            logger.error(f"Error updating prompt: {e}")
            return None
    
    async def delete_prompt(self, prompt_id: int) -> bool:
        """Удаление промпта (мягкое удаление)"""
        try:
            with get_db_session() as db:
                prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
                
                if not prompt:
                    return False
                
                prompt.is_active = False
                prompt.updated_at = datetime.now()
                
                db.commit()
                
                # Clear cache
                self._clear_cache()
                
                logger.info(f"Deleted prompt: {prompt_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting prompt: {e}")
            return False
    
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

    async def export_prompts(self, format: str = "json") -> str:
        """Экспорт промптов в JSON или CSV"""
        try:
            prompts = await self.get_prompts()
            
            if format.lower() == "json":
                import json
                data = [
                    {
                        "id": prompt.id,
                        "name": prompt.name,
                        "description": prompt.description,
                        "template": prompt.template,
                        "category": prompt.category,
                        "usage_count": prompt.usage_count,
                        "created_at": prompt.created_at.isoformat() if prompt.created_at else None
                    }
                    for prompt in prompts
                ]
                return json.dumps(data, ensure_ascii=False, indent=2)
            
            elif format.lower() == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(['ID', 'Name', 'Description', 'Template', 'Category', 'Usage Count'])
                
                # Write data
                for prompt in prompts:
                    writer.writerow([
                        prompt.id,
                        prompt.name,
                        prompt.description or "",
                        prompt.template,
                        prompt.category or "",
                        prompt.usage_count
                    ])
                
                return output.getvalue()
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting prompts: {e}")
            return ""

# Global instance
prompt_manager = PromptManager()