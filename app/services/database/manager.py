"""
GigaOffice Service Database Configuration
Настройка подключения к PostgreSQL базе данных
"""

import os
import time
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from app.model_orm import Base
from app.resource_loader import resource_loader

class DatabaseManager:
    """Менеджер работы с БД и пулом соединений"""
    def __init__(self):
        # Приоритет переменных окружения над конфигом
        config = resource_loader.get_config("database_config")
        host = os.getenv("DB_HOST", config.get("host"))
        port = os.getenv("DB_PORT", config.get("port"))
        name = os.getenv("DB_NAME", config.get("name"))
        user = os.getenv("DB_USER", config.get("user"))
        password = os.getenv("DB_PASSWORD", config.get("password"))
        echo_flag = os.getenv("DB_ECHO", str(config.get("echo", False))).lower() == "true"

        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        self.engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=config.get("pool_size", 20),
            max_overflow=config.get("max_overflow", 30),
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=echo_flag
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )
    
    def create_tables(self):
        """Создание всех таблиц"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """Удаление всех таблиц (только для тестирования)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except SQLAlchemyError as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    def check_connection(self) -> bool:
        """Проверка подключения к базе данных"""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_db_info(self) -> dict:
        """Получение информации о базе данных"""
        try:
            with self.engine.connect() as connection:
                sql_query = resource_loader.load_sql("sql/database_info.sql")
                result = connection.execute(text(sql_query)).fetchone()
                return {
                    "version": result.version,
                    "database_name": result.database_name,
                    "current_user": result.current_user,
                    "server_addr": result.server_addr,
                    "server_port": result.server_port,
                    "pool_size": self.engine.pool.size(),
                    "checked_out": self.engine.pool.checkedout(),
                    "overflow": self.engine.pool.overflow(),
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}

# Create database manager instance
db_manager = DatabaseManager()