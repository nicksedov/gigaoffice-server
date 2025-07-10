"""
GigaOffice Prompt Manager
Менеджер для работы с предустановленными промптами и популярными запросами
"""

import hashlib
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from loguru import logger

from database import get_db_session
from models import Prompt, AIRequest, RequestStatus

class PromptManager:
    """Менеджер для работы с промптами"""
    
    def __init__(self):
        self.cached_prompts = {}
        self.cache_expiry = {}
        self.cache_duration = 300  # 5 minutes
        
    async def load_prompts(self):
        """Загрузка всех промптов при инициализации"""
        try:
            with get_db_session() as db:
                prompts = db.query(Prompt).filter(Prompt.is_active == True).all()
                
                for prompt in prompts:
                    cache_key = f"{prompt.language}_{prompt.category}"
                    if cache_key not in self.cached_prompts:
                        self.cached_prompts[cache_key] = []
                    self.cached_prompts[cache_key].append(prompt)
                
                logger.info(f"Loaded {len(prompts)} prompts into cache")
                
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            raise
    
    async def get_prompts_by_language(self, language: str = "ru") -> List[Prompt]:
        """Получение промптов по языку"""
        try:
            cache_key = f"lang_{language}"
            
            # Check cache
            if cache_key in self.cached_prompts and cache_key in self.cache_expiry:
                if time.time() < self.cache_expiry[cache_key]:
                    return self.cached_prompts[cache_key]
            
            # Load from database
            with get_db_session() as db:
                prompts = db.query(Prompt).filter(
                    Prompt.language == language,
                    Prompt.is_active == True
                ).order_by(Prompt.usage_count.desc()).all()
                
                # Update cache
                self.cached_prompts[cache_key] = prompts
                self.cache_expiry[cache_key] = time.time() + self.cache_duration
                
                return prompts
                
        except Exception as e:
            logger.error(f"Error getting prompts by language: {e}")
            return []
    
    async def get_prompts_by_category(self, category: str, language: str = "ru") -> List[Prompt]:
        """Получение промптов по категории"""
        try:
            cache_key = f"{language}_{category}"
            
            # Check cache
            if cache_key in self.cached_prompts and cache_key in self.cache_expiry:
                if time.time() < self.cache_expiry[cache_key]:
                    return self.cached_prompts[cache_key]
            
            # Load from database
            with get_db_session() as db:
                prompts = db.query(Prompt).filter(
                    Prompt.category == category,
                    Prompt.language == language,
                    Prompt.is_active == True
                ).order_by(Prompt.usage_count.desc()).all()
                
                # Update cache
                self.cached_prompts[cache_key] = prompts
                self.cache_expiry[cache_key] = time.time() + self.cache_duration
                
                return prompts
                
        except Exception as e:
            logger.error(f"Error getting prompts by category: {e}")
            return []
    
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
        category: str = None,
        language: str = "ru",
        created_by: int = None
    ) -> Optional[Prompt]:
        """Создание нового промпта"""
        try:
            with get_db_session() as db:
                prompt = Prompt(
                    name=name,
                    description=description,
                    template=template,
                    category=category,
                    language=language,
                    created_by=created_by
                )
                
                db.add(prompt)
                db.commit()
                db.refresh(prompt)
                
                # Clear relevant cache
                cache_keys_to_clear = [
                    f"lang_{language}",
                    f"{language}_{category}"
                ]
                
                for key in cache_keys_to_clear:
                    if key in self.cached_prompts:
                        del self.cached_prompts[key]
                    if key in self.cache_expiry:
                        del self.cache_expiry[key]
                
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
        category: str = None,
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
                if category is not None:
                    prompt.category = category
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
    
    async def get_prompt_categories(self, language: str = "ru") -> List[Dict[str, Any]]:
        """Получение категорий промптов"""
        try:
            with get_db_session() as db:
                categories = db.query(
                    Prompt.category,
                    func.count(Prompt.id).label('count')
                ).filter(
                    Prompt.language == language,
                    Prompt.is_active == True,
                    Prompt.category.isnot(None)
                ).group_by(Prompt.category).all()
                
                return [
                    {
                        "category": category,
                        "count": count
                    }
                    for category, count in categories
                ]
                
        except Exception as e:
            logger.error(f"Error getting prompt categories: {e}")
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
    
    def _clear_cache(self):
        """Очистка кэша"""
        self.cached_prompts.clear()
        self.cache_expiry.clear()
    
    async def export_prompts(self, language: str = "ru", format: str = "json") -> str:
        """Экспорт промптов в JSON или CSV"""
        try:
            prompts = await self.get_prompts_by_language(language)
            
            if format.lower() == "json":
                import json
                data = [
                    {
                        "id": prompt.id,
                        "name": prompt.name,
                        "description": prompt.description,
                        "template": prompt.template,
                        "category": prompt.category,
                        "language": prompt.language,
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
                writer.writerow(['ID', 'Name', 'Description', 'Template', 'Category', 'Language', 'Usage Count'])
                
                # Write data
                for prompt in prompts:
                    writer.writerow([
                        prompt.id,
                        prompt.name,
                        prompt.description or "",
                        prompt.template,
                        prompt.category or "",
                        prompt.language,
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