"""
Base Repository
Common database operations using repository pattern
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc

from ..models import Base
from ...utils.logger import structured_logger

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations"""
    
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    def get(self, id: Any) -> Optional[ModelType]:
        """Get entity by ID"""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "get", "model": self.model.__name__, "id": id})
            raise
    
    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """Get entity by field value"""
        try:
            field = getattr(self.model, field_name)
            return self.db.query(self.model).filter(field == value).first()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "get_by_field", "model": self.model.__name__, "field": field_name})
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination"""
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "get_all", "model": self.model.__name__})
            raise
    
    def get_multi_by_ids(self, ids: List[Any]) -> List[ModelType]:
        """Get multiple entities by IDs"""
        try:
            return self.db.query(self.model).filter(self.model.id.in_(ids)).all()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "get_multi_by_ids", "model": self.model.__name__})
            raise
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create new entity"""
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            self.db.flush()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "create", "model": self.model.__name__})
            raise
    
    def update(self, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update existing entity"""
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.db.add(db_obj)
            self.db.flush()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "update", "model": self.model.__name__})
            raise
    
    def delete(self, id: Any) -> Optional[ModelType]:
        """Delete entity by ID"""
        try:
            obj = self.get(id)
            if obj:
                self.db.delete(obj)
                self.db.flush()
            return obj
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "delete", "model": self.model.__name__, "id": id})
            raise
    
    def count(self, **filters) -> int:
        """Count entities with optional filters"""
        try:
            query = self.db.query(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
            return query.count()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "count", "model": self.model.__name__})
            raise
    
    def exists(self, id: Any) -> bool:
        """Check if entity exists by ID"""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first() is not None
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "exists", "model": self.model.__name__, "id": id})
            raise
    
    def search(self, search_term: str, search_fields: List[str], 
               skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Search entities by term in specified fields"""
        try:
            query = self.db.query(self.model)
            
            search_conditions = []
            for field_name in search_fields:
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    search_conditions.append(field.ilike(f"%{search_term}%"))
            
            if search_conditions:
                query = query.filter(or_(*search_conditions))
            
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "search", "model": self.model.__name__})
            raise
    
    def get_with_filters(self, filters: Dict[str, Any], 
                        skip: int = 0, limit: int = 100,
                        order_by: Optional[str] = None,
                        desc_order: bool = False) -> List[ModelType]:
        """Get entities with complex filters and ordering"""
        try:
            query = self.db.query(self.model)
            
            # Apply filters
            for field, value in filters.items():
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    if isinstance(value, list):
                        query = query.filter(field_attr.in_(value))
                    elif isinstance(value, dict):
                        # Support for range queries
                        if 'gte' in value:
                            query = query.filter(field_attr >= value['gte'])
                        if 'lte' in value:
                            query = query.filter(field_attr <= value['lte'])
                        if 'gt' in value:
                            query = query.filter(field_attr > value['gt'])
                        if 'lt' in value:
                            query = query.filter(field_attr < value['lt'])
                    else:
                        query = query.filter(field_attr == value)
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if desc_order:
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "get_with_filters", "model": self.model.__name__})
            raise
    
    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple entities in bulk"""
        try:
            db_objects = []
            for obj_data in objects:
                db_obj = self.model(**obj_data)
                db_objects.append(db_obj)
                self.db.add(db_obj)
            
            self.db.flush()
            
            for db_obj in db_objects:
                self.db.refresh(db_obj)
            
            return db_objects
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "bulk_create", "model": self.model.__name__})
            raise
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Update multiple entities in bulk"""
        try:
            updated_count = 0
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                
                entity_id = update_data.pop('id')
                result = self.db.query(self.model).filter(self.model.id == entity_id).update(update_data)
                updated_count += result
            
            self.db.flush()
            return updated_count
        except SQLAlchemyError as e:
            structured_logger.log_error(e, {"operation": "bulk_update", "model": self.model.__name__})
            raise