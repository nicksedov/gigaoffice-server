"""
Database Repository Pattern
Base repository class for database operations
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

class DatabaseRepository:
    """Базовый класс для репозиториев работы с базой данных"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def commit(self):
        """Коммит транзакции"""
        try:
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Commit error: {e}")
            raise
    
    def rollback(self):
        """Откат транзакции"""
        self.db.rollback()
    
    def refresh(self, obj):
        """Обновление объекта из базы данных"""
        self.db.refresh(obj)
    
    def add(self, obj):
        """Добавление объекта в сессию"""
        self.db.add(obj)
    
    def delete(self, obj):
        """Удаление объекта"""
        self.db.delete(obj)
    
    def execute_raw_sql(self, sql: str, params: dict = None):
        """Выполнение сырого SQL запроса"""
        try:
            return self.db.execute(sql, params or {})
        except SQLAlchemyError as e:
            logger.error(f"Raw SQL execution error: {e}")
            raise