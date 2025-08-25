"""
Prompts Repository
Specialized repository for prompt management operations
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from .base import BaseRepository
from ..models import Prompt, Category
from ...utils.logger import structured_logger


class PromptsRepository(BaseRepository[Prompt]):
    """Repository for prompt management operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, Prompt)
    
    def get_active_prompts(self, skip: int = 0, limit: int = 100) -> List[Prompt]:
        """Get all active prompts"""
        return self.db.query(Prompt).filter(
            Prompt.is_active == True
        ).order_by(Prompt.name).offset(skip).limit(limit).all()
    
    def get_by_category(self, category_id: int, 
                       active_only: bool = True,
                       skip: int = 0, limit: int = 100) -> List[Prompt]:
        """Get prompts by category ID"""
        query = self.db.query(Prompt).filter(Prompt.category_id == category_id)
        
        if active_only:
            query = query.filter(Prompt.is_active == True)
        
        return query.order_by(Prompt.name).offset(skip).limit(limit).all()
    
    def get_by_category_name(self, category_name: str,
                           active_only: bool = True,
                           skip: int = 0, limit: int = 100) -> List[Prompt]:
        """Get prompts by category name"""
        query = self.db.query(Prompt).join(Category).filter(
            Category.name == category_name
        )
        
        if active_only:
            query = query.filter(Prompt.is_active == True)
        
        return query.order_by(Prompt.name).offset(skip).limit(limit).all()
    
    def search_prompts(self, search_term: str, 
                      category_id: Optional[int] = None,
                      active_only: bool = True,
                      skip: int = 0, limit: int = 100) -> List[Prompt]:
        """Search prompts by name, description, or template content"""
        query = self.db.query(Prompt).filter(
            func.lower(Prompt.name).contains(search_term.lower()) |
            func.lower(Prompt.description).contains(search_term.lower()) |
            func.lower(Prompt.template).contains(search_term.lower())
        )
        
        if category_id:
            query = query.filter(Prompt.category_id == category_id)
        
        if active_only:
            query = query.filter(Prompt.is_active == True)
        
        return query.order_by(Prompt.name).offset(skip).limit(limit).all()
    
    def get_by_tags(self, tags: List[str],
                   active_only: bool = True,
                   skip: int = 0, limit: int = 100) -> List[Prompt]:
        """Get prompts that contain any of the specified tags"""
        query = self.db.query(Prompt)
        
        # Filter by tags (assuming tags is stored as JSON array)
        for tag in tags:
            query = query.filter(Prompt.tags.contains([tag]))
        
        if active_only:
            query = query.filter(Prompt.is_active == True)
        
        return query.order_by(Prompt.name).offset(skip).limit(limit).all()
    
    def get_popular_prompts(self, limit: int = 10) -> List[Prompt]:
        """Get most popular prompts by usage count"""
        return self.db.query(Prompt).filter(
            Prompt.is_active == True
        ).order_by(desc(Prompt.usage_count)).limit(limit).all()
    
    def get_recent_prompts(self, limit: int = 10) -> List[Prompt]:
        """Get recently created prompts"""
        return self.db.query(Prompt).filter(
            Prompt.is_active == True
        ).order_by(desc(Prompt.created_at)).limit(limit).all()
    
    def get_highly_rated_prompts(self, min_rating: float = 4.0, 
                                min_ratings: int = 5,
                                limit: int = 10) -> List[Prompt]:
        """Get highly rated prompts"""
        return self.db.query(Prompt).filter(
            and_(
                Prompt.is_active == True,
                Prompt.avg_rating >= min_rating,
                Prompt.total_ratings >= min_ratings
            )
        ).order_by(desc(Prompt.avg_rating)).limit(limit).all()
    
    def increment_usage(self, prompt_id: int) -> Optional[Prompt]:
        """Increment usage count for a prompt"""
        prompt = self.get(prompt_id)
        if prompt:
            prompt.increment_usage()
            self.db.add(prompt)
            self.db.flush()
            self.db.refresh(prompt)
        
        return prompt
    
    def update_rating(self, prompt_id: int, rating: float) -> Optional[Prompt]:
        """Update prompt rating"""
        prompt = self.get(prompt_id)
        if prompt:
            prompt.update_rating(rating)
            self.db.add(prompt)
            self.db.flush()
            self.db.refresh(prompt)
        
        return prompt
    
    def get_by_creator(self, creator_id: int,
                      active_only: bool = True,
                      skip: int = 0, limit: int = 100) -> List[Prompt]:
        """Get prompts created by specific user"""
        query = self.db.query(Prompt).filter(Prompt.created_by == creator_id)
        
        if active_only:
            query = query.filter(Prompt.is_active == True)
        
        return query.order_by(desc(Prompt.created_at)).offset(skip).limit(limit).all()
    
    def duplicate_prompt(self, prompt_id: int, new_name: str,
                        creator_id: int) -> Optional[Prompt]:
        """Create a duplicate of an existing prompt"""
        original = self.get(prompt_id)
        if not original:
            return None
        
        duplicate_data = {
            "name": new_name,
            "description": f"Copy of {original.description or original.name}",
            "template": original.template,
            "category_id": original.category_id,
            "created_by": creator_id,
            "tags": original.tags,
            "expected_input_format": original.expected_input_format,
            "version": "1.0"  # Reset version for new prompt
        }
        
        return self.create(duplicate_data)
    
    def update_template(self, prompt_id: int, new_template: str,
                       version: Optional[str] = None) -> Optional[Prompt]:
        """Update prompt template and optionally version"""
        prompt = self.get(prompt_id)
        if prompt:
            prompt.template = new_template
            if version:
                prompt.version = version
            
            self.db.add(prompt)
            self.db.flush()
            self.db.refresh(prompt)
        
        return prompt
    
    def deactivate_prompt(self, prompt_id: int) -> Optional[Prompt]:
        """Deactivate a prompt (soft delete)"""
        prompt = self.get(prompt_id)
        if prompt:
            prompt.is_active = False
            self.db.add(prompt)
            self.db.flush()
            self.db.refresh(prompt)
        
        return prompt
    
    def get_category_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for each category"""
        results = self.db.query(
            Category.id,
            Category.name,
            Category.display_name,
            func.count(Prompt.id).label('prompt_count'),
            func.avg(Prompt.avg_rating).label('avg_rating'),
            func.sum(Prompt.usage_count).label('total_usage')
        ).outerjoin(Prompt, and_(
            Category.id == Prompt.category_id,
            Prompt.is_active == True
        )).group_by(
            Category.id, Category.name, Category.display_name
        ).all()
        
        return [
            {
                "category_id": result.id,
                "category_name": result.name,
                "display_name": result.display_name,
                "prompt_count": result.prompt_count or 0,
                "avg_rating": float(result.avg_rating or 0),
                "total_usage": result.total_usage or 0
            }
            for result in results
        ]
    
    def get_template_variables(self, prompt_id: int) -> List[str]:
        """Extract template variables from prompt template"""
        prompt = self.get(prompt_id)
        if not prompt:
            return []
        
        import re
        # Find variables in format {variable_name}
        variables = re.findall(r'\{(\w+)\}', prompt.template)
        return list(set(variables))  # Remove duplicates
    
    def validate_template(self, template: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prompt template with test data"""
        try:
            # Extract required variables
            import re
            required_vars = set(re.findall(r'\{(\w+)\}', template))
            
            # Check if all required variables are provided
            missing_vars = required_vars - set(test_data.keys())
            
            if missing_vars:
                return {
                    "valid": False,
                    "error": f"Missing variables: {', '.join(missing_vars)}",
                    "required_variables": list(required_vars)
                }
            
            # Try to format the template
            formatted = template.format(**test_data)
            
            return {
                "valid": True,
                "formatted_template": formatted,
                "required_variables": list(required_vars)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "required_variables": []
            }


class CategoryRepository(BaseRepository[Category]):
    """Repository for category management operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, Category)
    
    def get_active_categories(self, skip: int = 0, limit: int = 100) -> List[Category]:
        """Get all active categories ordered by sort_order"""
        return self.db.query(Category).filter(
            Category.is_active == True
        ).order_by(Category.sort_order, Category.name).offset(skip).limit(limit).all()
    
    def get_by_name(self, name: str) -> Optional[Category]:
        """Get category by internal name"""
        return self.db.query(Category).filter(
            Category.name == name
        ).first()
    
    def get_by_display_name(self, display_name: str) -> Optional[Category]:
        """Get category by display name"""
        return self.db.query(Category).filter(
            Category.display_name == display_name
        ).first()
    
    def get_with_prompt_count(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get categories with their prompt counts"""
        query = self.db.query(
            Category.id,
            Category.name,
            Category.display_name,
            Category.description,
            Category.sort_order,
            func.count(Prompt.id).label('prompt_count')
        ).outerjoin(Prompt)
        
        if active_only:
            query = query.filter(
                and_(
                    Category.is_active == True,
                    or_(Prompt.is_active == True, Prompt.id.is_(None))
                )
            )
        
        results = query.group_by(
            Category.id, Category.name, Category.display_name, 
            Category.description, Category.sort_order
        ).order_by(Category.sort_order, Category.name).all()
        
        return [
            {
                "id": result.id,
                "name": result.name,
                "display_name": result.display_name,
                "description": result.description,
                "sort_order": result.sort_order,
                "prompt_count": result.prompt_count or 0
            }
            for result in results
        ]
    
    def get_popular_categories(self, limit: int = 10) -> List[Category]:
        """Get categories with highest total prompt usage"""
        results = self.db.query(
            Category,
            func.sum(Prompt.usage_count).label('total_usage')
        ).join(Prompt).filter(
            and_(
                Category.is_active == True,
                Prompt.is_active == True
            )
        ).group_by(Category.id).order_by(
            desc('total_usage')
        ).limit(limit).all()
        
        return [result[0] for result in results]
    
    def get_empty_categories(self) -> List[Category]:
        """Get categories with no active prompts"""
        return self.db.query(Category).outerjoin(Prompt).filter(
            and_(
                Category.is_active == True,
                or_(Prompt.id.is_(None), Prompt.is_active == False)
            )
        ).group_by(Category.id).having(
            func.count(Prompt.id.distinct()) == 0
        ).all()
    
    def update_sort_order(self, category_id: int, sort_order: int) -> Optional[Category]:
        """Update category sort order"""
        category = self.get(category_id)
        if category:
            category.sort_order = sort_order
            self.db.add(category)
            self.db.flush()
            self.db.refresh(category)
        
        return category
    
    def deactivate_category(self, category_id: int) -> Optional[Category]:
        """Deactivate a category (soft delete)"""
        category = self.get(category_id)
        if category:
            category.is_active = False
            self.db.add(category)
            self.db.flush()
            self.db.refresh(category)
        
        return category
    
    def get_category_statistics(self) -> List[Dict[str, Any]]:
        """Get comprehensive statistics for each category"""
        results = self.db.query(
            Category.id,
            Category.name,
            Category.display_name,
            func.count(Prompt.id).label('total_prompts'),
            func.count(func.nullif(Prompt.is_active, False)).label('active_prompts'),
            func.avg(Prompt.avg_rating).label('avg_rating'),
            func.sum(Prompt.usage_count).label('total_usage'),
            func.sum(Prompt.total_ratings).label('total_ratings')
        ).outerjoin(Prompt).group_by(
            Category.id, Category.name, Category.display_name
        ).order_by(Category.sort_order, Category.name).all()
        
        return [
            {
                "category_id": result.id,
                "category_name": result.name,
                "display_name": result.display_name,
                "total_prompts": result.total_prompts or 0,
                "active_prompts": result.active_prompts or 0,
                "avg_rating": float(result.avg_rating or 0),
                "total_usage": result.total_usage or 0,
                "total_ratings": result.total_ratings or 0
            }
            for result in results
        ]