"""
GigaOffice Service Database Configuration
Настройка подключения к PostgreSQL базе данных
"""

import os
import re
import time
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from app.models.orm.base import Base

class DatabaseManager:
    """
    Менеджер работы с БД и пулом соединений
    
    Reserved words are retrieved from SQLAlchemy's PostgreSQL dialect
    to ensure synchronization with the database version.
    """
    
    def __init__(self):
        # Read all configuration from environment variables
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "gigaoffice")
        user = os.getenv("DB_USER", "gigaoffice")
        password = os.getenv("DB_PASSWORD", "")
        echo_flag = os.getenv("DB_ECHO", "false").lower() == "true"
        
        # Read and validate DB_SCHEMA environment variable
        schema = os.getenv("DB_SCHEMA", "").strip()
        self.schema = self._validate_schema_name(schema) if schema else None
        
        # Log schema configuration
        if self.schema:
            logger.info(f"Database schema configured: {self.schema}")
        else:
            logger.info("Database schema not configured, using default (public)")

        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        
        # Prepare engine configuration with optional schema search_path
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        pool_pre_ping = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
        
        engine_config = {
            "poolclass": QueuePool,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_pre_ping": pool_pre_ping,
            "pool_recycle": pool_recycle,
            "echo": echo_flag
        }
        
        # Add schema configuration via connect_args if schema is specified
        if self.schema:
            engine_config["connect_args"] = {
                "options": f"-c search_path={self.schema},public"
            }
        
        self.engine = create_engine(url, **engine_config)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )
        
    def _validate_schema_name(self, schema_name: str) -> str:
        """
        Validate PostgreSQL schema name to prevent SQL injection and ensure compliance
        with PostgreSQL identifier rules.
        
        Args:
            schema_name: The schema name to validate
            
        Returns:
            The validated schema name
            
        Raises:
            ValueError: If schema name is invalid
        """
        # Check length (PostgreSQL identifier max length is 63)
        if len(schema_name) > 63:
            error_msg = f"Invalid schema name '{schema_name}': exceeds maximum length of 63 characters"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Check format: alphanumeric, underscore, dollar sign only
        # Must not start with a digit
        pattern = r'^[a-zA-Z_$][a-zA-Z0-9_$]*$'
        if not re.match(pattern, schema_name):
            error_msg = f"Invalid schema name '{schema_name}': must contain only alphanumeric characters, underscores, and dollar signs, and cannot start with a digit"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Schema name '{schema_name}' validated successfully")
        return schema_name
    
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
                # Load SQL query from file
                from pathlib import Path
                sql_file_path = Path("resources") / "sql" / "database_info.sql"
                with open(sql_file_path, 'r', encoding='utf-8') as f:
                    sql_query = f.read().strip()
                result = connection.execute(text(sql_query)).fetchone()
                
                # Get current schema
                current_schema_result = connection.execute(text("SELECT current_schema()")).fetchone()
                current_schema = current_schema_result[0] if current_schema_result else None
                
                # Get search_path
                search_path_result = connection.execute(text("SHOW search_path")).fetchone()
                search_path = search_path_result[0] if search_path_result else None
                
                return {
                    "version": result.version,
                    "database_name": result.database_name,
                    "current_user": result.current_user,
                    "current_schema": current_schema,
                    "search_path": search_path,
                    "configured_schema": self.schema,
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