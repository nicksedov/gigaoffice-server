"""
Enhanced Prompt Manager Service
Improved prompt management with repository pattern integration and advanced caching
"""

import time
import json
import csv
import io
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from cachetools import TTLCache
from loguru import logger

from ...core.config import get_settings, app_state
from ...utils.logger import structured_logger, performance_timer
from ...utils.resource_loader import resource_loader
from ...db.session import get_db_session
from ...db.repositories.prompts import PromptsRepository
from ...db.repositories.users import UsersRepository
from ...db.models import Prompt, Category


class PromptManager:
    """Enhanced prompt manager with repository pattern and advanced features"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Enhanced caching with multiple cache layers
        self.cache = TTLCache(maxsize=2000, ttl=3600)  # 1 hour TTL
        self.short_cache = TTLCache(maxsize=500, ttl=300)  # 5 minute TTL for frequent queries
        
        # Cache hit/miss statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0
        
        # Template processing cache
        self.template_cache = TTLCache(maxsize=100, ttl=1800)  # 30 minute TTL
        
        logger.info("PromptManager initialized with enhanced caching")
    
    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key with prefix and arguments"""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"
    
    def _update_cache_stats(self, hit: bool):
        """Update cache statistics"""
        self.total_requests += 1
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def _get_from_cache(self, cache_key: str, use_short_cache: bool = False) -> Optional[Any]:
        """Get item from appropriate cache"""
        cache = self.short_cache if use_short_cache else self.cache
        
        if cache_key in cache:
            self._update_cache_stats(True)
            return cache[cache_key]
        
        self._update_cache_stats(False)
        return None
    
    def _set_cache(self, cache_key: str, value: Any, use_short_cache: bool = False):
        """Set item in appropriate cache"""
        cache = self.short_cache if use_short_cache else self.cache
        cache[cache_key] = value
    
    async def get_prompt_categories(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all prompt categories with enhanced caching"""
        cache_key = self._get_cache_key("categories", include_inactive)
        cached = self._get_from_cache(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            with performance_timer("get_prompt_categories"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    category_stats = prompts_repo.get_category_statistics()
                    
                    # Filter by active status if needed
                    if not include_inactive:
                        # Additional filtering would be done in the repository method
                        pass
                    
                    self._set_cache(cache_key, category_stats)
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_prompt_categories", 
                        0, True, count=len(category_stats)
                    )
                    
                    return category_stats
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_prompt_categories"})
            logger.error(f"Error getting prompt categories: {e}")
            return []
    
    async def get_prompts(self, 
                         category_id: Optional[int] = None,
                         active_only: bool = True,
                         limit: int = 100,
                         skip: int = 0) -> List[Prompt]:
        """Get prompts with advanced filtering and caching"""
        cache_key = self._get_cache_key("prompts", category_id, active_only, limit, skip)
        cached = self._get_from_cache(cache_key, use_short_cache=True)
        
        if cached is not None:
            return cached
        
        try:
            with performance_timer("get_prompts"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    
                    if category_id:
                        prompts = prompts_repo.get_by_category(
                            category_id, active_only, skip, limit
                        )
                    else:
                        prompts = prompts_repo.get_active_prompts(skip, limit) if active_only else prompts_repo.get_all(skip, limit)
                    
                    self._set_cache(cache_key, prompts, use_short_cache=True)
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_prompts", 
                        0, True, count=len(prompts), category_id=category_id
                    )
                    
                    return prompts
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_prompts"})
            logger.error(f"Error getting prompts: {e}")
            return []
    
    async def get_prompts_by_category(self, 
                                    category_identifier: Union[str, int],
                                    active_only: bool = True,
                                    limit: int = 100,
                                    skip: int = 0) -> List[Prompt]:
        """Get prompts by category name or ID"""
        cache_key = self._get_cache_key("prompts_by_category", category_identifier, active_only, limit, skip)
        cached = self._get_from_cache(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            with performance_timer("get_prompts_by_category"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    
                    if isinstance(category_identifier, int) or str(category_identifier).isdigit():
                        category_id = int(category_identifier)
                        prompts = prompts_repo.get_by_category(category_id, active_only, skip, limit)
                    else:
                        prompts = prompts_repo.get_by_category_name(category_identifier, active_only, skip, limit)
                    
                    self._set_cache(cache_key, prompts)
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_prompts_by_category", 
                        0, True, count=len(prompts), category=category_identifier
                    )
                    
                    return prompts
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_prompts_by_category"})
            logger.error(f"Error getting prompts by category: {e}")
            return []
    
    async def search_prompts(self, 
                           search_term: str,
                           category_id: Optional[int] = None,
                           active_only: bool = True,
                           limit: int = 50,
                           skip: int = 0) -> List[Prompt]:
        """Search prompts by term"""
        # Don't cache search results as they can be very dynamic
        try:
            with performance_timer("search_prompts"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    prompts = prompts_repo.search_prompts(
                        search_term, category_id, active_only, skip, limit
                    )
                    
                    structured_logger.log_service_call(
                        "PromptManager", "search_prompts", 
                        0, True, count=len(prompts), search_term=search_term[:50]
                    )
                    
                    return prompts
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "search_prompts", "search_term": search_term})
            logger.error(f"Error searching prompts: {e}")
            return []
    
    async def get_prompt_by_id(self, prompt_id: int, increment_usage: bool = True) -> Optional[Prompt]:
        """Get prompt by ID with optional usage tracking"""
        try:
            with performance_timer("get_prompt_by_id"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    prompt = prompts_repo.get(prompt_id)
                    
                    if prompt and prompt.is_active and increment_usage:
                        prompts_repo.increment_usage(prompt_id)
                        # Clear related cache entries
                        self._clear_prompt_caches()
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_prompt_by_id", 
                        0, True, prompt_id=prompt_id, found=prompt is not None
                    )
                    
                    return prompt
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_prompt_by_id", "prompt_id": prompt_id})
            logger.error(f"Error getting prompt by ID: {e}")
            return None
    
    async def create_prompt(self,
                          name: str,
                          template: str,
                          description: Optional[str] = None,
                          category_id: Optional[int] = None,
                          created_by: Optional[int] = None,
                          tags: Optional[List[str]] = None) -> Optional[Prompt]:
        """Create new prompt with enhanced features"""
        try:
            with performance_timer("create_prompt"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    
                    # Validate template
                    validation_result = prompts_repo.validate_template(template, {})
                    if not validation_result["valid"]:
                        logger.warning(f"Template validation failed: {validation_result['error']}")
                    
                    prompt_data = {
                        "name": name,
                        "description": description,
                        "template": template,
                        "category_id": category_id,
                        "created_by": created_by,
                        "tags": tags or [],
                        "version": "1.0"
                    }
                    
                    prompt = prompts_repo.create(prompt_data)
                    
                    # Clear cache
                    self._clear_prompt_caches()
                    
                    structured_logger.log_service_call(
                        "PromptManager", "create_prompt", 
                        0, True, prompt_id=prompt.id if prompt else None
                    )
                    
                    logger.info(f"Created new prompt: {name} (ID: {prompt.id if prompt else 'None'})")
                    return prompt
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "create_prompt", "name": name})
            logger.error(f"Error creating prompt: {e}")
            return None
    
    async def update_prompt(self,
                          prompt_id: int,
                          name: Optional[str] = None,
                          template: Optional[str] = None,
                          description: Optional[str] = None,
                          category_id: Optional[int] = None,
                          is_active: Optional[bool] = None,
                          tags: Optional[List[str]] = None) -> Optional[Prompt]:
        """Update existing prompt"""
        try:
            with performance_timer("update_prompt"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    
                    # Prepare update data
                    update_data = {}
                    if name is not None:
                        update_data["name"] = name
                    if template is not None:
                        # Validate new template
                        validation_result = prompts_repo.validate_template(template, {})
                        if not validation_result["valid"]:
                            logger.warning(f"Template validation failed: {validation_result['error']}")
                        update_data["template"] = template
                    if description is not None:
                        update_data["description"] = description
                    if category_id is not None:
                        update_data["category_id"] = category_id
                    if is_active is not None:
                        update_data["is_active"] = is_active
                    if tags is not None:
                        update_data["tags"] = tags
                    
                    # Get existing prompt
                    prompt = prompts_repo.get(prompt_id)
                    if not prompt:
                        return None
                    
                    # Update prompt
                    updated_prompt = prompts_repo.update(prompt, update_data)
                    
                    # Clear cache
                    self._clear_prompt_caches()
                    
                    structured_logger.log_service_call(
                        "PromptManager", "update_prompt", 
                        0, True, prompt_id=prompt_id
                    )
                    
                    logger.info(f"Updated prompt: {prompt_id}")
                    return updated_prompt
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "update_prompt", "prompt_id": prompt_id})
            logger.error(f"Error updating prompt: {e}")
            return None
    
    async def delete_prompt(self, prompt_id: int) -> bool:
        """Soft delete prompt"""
        try:
            with performance_timer("delete_prompt"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    prompt = prompts_repo.deactivate_prompt(prompt_id)
                    
                    success = prompt is not None
                    
                    if success:
                        # Clear cache
                        self._clear_prompt_caches()
                    
                    structured_logger.log_service_call(
                        "PromptManager", "delete_prompt", 
                        0, success, prompt_id=prompt_id
                    )
                    
                    if success:
                        logger.info(f"Deleted prompt: {prompt_id}")
                    
                    return success
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "delete_prompt", "prompt_id": prompt_id})
            logger.error(f"Error deleting prompt: {e}")
            return False
    
    async def get_popular_prompts(self, limit: int = 10) -> List[Prompt]:
        """Get most popular prompts"""
        cache_key = self._get_cache_key("popular_prompts", limit)
        cached = self._get_from_cache(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            with performance_timer("get_popular_prompts"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    prompts = prompts_repo.get_popular_prompts(limit)
                    
                    self._set_cache(cache_key, prompts)
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_popular_prompts", 
                        0, True, count=len(prompts)
                    )
                    
                    return prompts
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_popular_prompts"})
            logger.error(f"Error getting popular prompts: {e}")
            return []
    
    async def get_recent_prompts(self, limit: int = 10) -> List[Prompt]:
        """Get recently created prompts"""
        cache_key = self._get_cache_key("recent_prompts", limit)
        cached = self._get_from_cache(cache_key, use_short_cache=True)
        
        if cached is not None:
            return cached
        
        try:
            with performance_timer("get_recent_prompts"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    prompts = prompts_repo.get_recent_prompts(limit)
                    
                    self._set_cache(cache_key, prompts, use_short_cache=True)
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_recent_prompts", 
                        0, True, count=len(prompts)
                    )
                    
                    return prompts
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_recent_prompts"})
            logger.error(f"Error getting recent prompts: {e}")
            return []
    
    async def get_template_variables(self, prompt_id: int) -> List[str]:
        """Get template variables for a prompt"""
        cache_key = self._get_cache_key("template_vars", prompt_id)
        cached = self._get_from_cache(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            with get_db_session() as db:
                prompts_repo = PromptsRepository(db)
                variables = prompts_repo.get_template_variables(prompt_id)
                
                self._set_cache(cache_key, variables)
                return variables
                
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_template_variables", "prompt_id": prompt_id})
            logger.error(f"Error getting template variables: {e}")
            return []
    
    async def format_prompt_template(self, prompt_id: int, variables: Dict[str, Any]) -> Optional[str]:
        """Format prompt template with variables"""
        try:
            prompt = await self.get_prompt_by_id(prompt_id, increment_usage=False)
            if not prompt:
                return None
            
            # Use template cache
            template_key = f"formatted:{prompt_id}:{hash(str(sorted(variables.items())))}"
            cached = self.template_cache.get(template_key)
            if cached is not None:
                return cached
            
            # Format template
            formatted = prompt.template.format(**variables)
            self.template_cache[template_key] = formatted
            
            return formatted
            
        except Exception as e:
            structured_logger.log_error(e, {"operation": "format_prompt_template", "prompt_id": prompt_id})
            logger.error(f"Error formatting prompt template: {e}")
            return None
    
    async def get_usage_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive usage analytics"""
        cache_key = self._get_cache_key("analytics", days)
        cached = self._get_from_cache(cache_key)
        
        if cached is not None:
            return cached
        
        try:
            with performance_timer("get_usage_analytics"):
                with get_db_session() as db:
                    prompts_repo = PromptsRepository(db)
                    
                    # Get popular prompts
                    popular_prompts = prompts_repo.get_popular_prompts(10)
                    
                    # Get category statistics
                    category_stats = prompts_repo.get_category_statistics()
                    
                    # Get highly rated prompts
                    highly_rated = prompts_repo.get_highly_rated_prompts(min_rating=4.0, limit=5)
                    
                    analytics = {
                        "period_days": days,
                        "cache_statistics": {
                            "total_requests": self.total_requests,
                            "cache_hits": self.cache_hits,
                            "cache_misses": self.cache_misses,
                            "hit_rate_percent": (self.cache_hits / max(1, self.total_requests)) * 100
                        },
                        "popular_prompts": [
                            {
                                "id": prompt.id,
                                "name": prompt.name,
                                "usage_count": prompt.usage_count,
                                "category_id": prompt.category_id,
                                "avg_rating": prompt.avg_rating
                            }
                            for prompt in popular_prompts
                        ],
                        "category_statistics": category_stats,
                        "highly_rated_prompts": [
                            {
                                "id": prompt.id,
                                "name": prompt.name,
                                "avg_rating": prompt.avg_rating,
                                "total_ratings": prompt.total_ratings
                            }
                            for prompt in highly_rated
                        ]
                    }
                    
                    self._set_cache(cache_key, analytics)
                    
                    structured_logger.log_service_call(
                        "PromptManager", "get_usage_analytics", 
                        0, True, days=days
                    )
                    
                    return analytics
                    
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_usage_analytics"})
            logger.error(f"Error getting usage analytics: {e}")
            return {}
    
    async def export_prompts(self, format_type: str = "json", category_id: Optional[int] = None) -> str:
        """Export prompts in JSON or CSV format"""
        try:
            with performance_timer("export_prompts"):
                prompts = await self.get_prompts(category_id=category_id, limit=10000)  # Large limit for export
                
                if format_type.lower() == "json":
                    data = [
                        {
                            "id": prompt.id,
                            "name": prompt.name,
                            "description": prompt.description,
                            "template": prompt.template,
                            "category_id": prompt.category_id,
                            "usage_count": prompt.usage_count,
                            "avg_rating": prompt.avg_rating,
                            "tags": prompt.tags,
                            "version": prompt.version,
                            "created_at": prompt.created_at.isoformat() if prompt.created_at else None
                        }
                        for prompt in prompts
                    ]
                    result = json.dumps(data, ensure_ascii=False, indent=2)
                    
                elif format_type.lower() == "csv":
                    output = io.StringIO()
                    writer = csv.writer(output)
                    
                    # Write header
                    writer.writerow([
                        'ID', 'Name', 'Description', 'Template', 'Category ID', 
                        'Usage Count', 'Avg Rating', 'Tags', 'Version', 'Created At'
                    ])
                    
                    # Write data
                    for prompt in prompts:
                        writer.writerow([
                            prompt.id,
                            prompt.name,
                            prompt.description or "",
                            prompt.template,
                            prompt.category_id or "",
                            prompt.usage_count,
                            prompt.avg_rating,
                            ','.join(prompt.tags) if prompt.tags else "",
                            prompt.version or "",
                            prompt.created_at.isoformat() if prompt.created_at else ""
                        ])
                    
                    result = output.getvalue()
                    
                else:
                    raise ValueError(f"Unsupported format: {format_type}")
                
                structured_logger.log_service_call(
                    "PromptManager", "export_prompts", 
                    0, True, format=format_type, count=len(prompts)
                )
                
                return result
                
        except Exception as e:
            structured_logger.log_error(e, {"operation": "export_prompts", "format": format_type})
            logger.error(f"Error exporting prompts: {e}")
            return ""
    
    def _clear_prompt_caches(self):
        """Clear all prompt-related cache entries"""
        # Clear main cache
        keys_to_remove = [key for key in self.cache.keys() if any(prefix in str(key) for prefix in [
            "prompts", "categories", "popular", "recent", "analytics"
        ])]
        
        for key in keys_to_remove:
            self.cache.pop(key, None)
        
        # Clear short cache
        keys_to_remove = [key for key in self.short_cache.keys() if "prompts" in str(key)]
        for key in keys_to_remove:
            self.short_cache.pop(key, None)
        
        # Clear template cache
        self.template_cache.clear()
        
        logger.debug("Cleared prompt caches")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        hit_rate = (self.cache_hits / max(1, self.total_requests)) * 100
        
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": hit_rate,
            "main_cache_size": len(self.cache),
            "short_cache_size": len(self.short_cache),
            "template_cache_size": len(self.template_cache),
            "main_cache_maxsize": self.cache.maxsize,
            "short_cache_maxsize": self.short_cache.maxsize,
            "template_cache_maxsize": self.template_cache.maxsize
        }
    
    def clear_all_caches(self):
        """Clear all caches (useful for admin operations)"""
        self.cache.clear()
        self.short_cache.clear()
        self.template_cache.clear()
        logger.info("All prompt manager caches cleared")


# Global prompt manager instance
prompt_manager = PromptManager()