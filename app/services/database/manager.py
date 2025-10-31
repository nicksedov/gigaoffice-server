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
from app.resource_loader import resource_loader

class DatabaseManager:
    """
    Менеджер работы с БД и пулом соединений
    
    Reserved words are retrieved from SQLAlchemy's PostgreSQL dialect
    to ensure synchronization with the database version.
    """
    
    def __init__(self):
        # Приоритет переменных окружения над конфигом
        config = resource_loader.get_config("database_config")
        host = os.getenv("DB_HOST", config.get("host"))
        port = os.getenv("DB_PORT", config.get("port"))
        name = os.getenv("DB_NAME", config.get("name"))
        user = os.getenv("DB_USER", config.get("user"))
        password = os.getenv("DB_PASSWORD", config.get("password"))
        echo_flag = os.getenv("DB_ECHO", str(config.get("echo", False))).lower() == "true"
        
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
        engine_config = {
            "poolclass": QueuePool,
            "pool_size": config.get("pool_size", 20),
            "max_overflow": config.get("max_overflow", 30),
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "echo": echo_flag
        }
        
        # Add schema configuration via connect_args if schema is specified
        if self.schema:
            engine_config["connect_args"] = {
                "options": f"-csearch_path={self.schema},public"
            }
        
        self.engine = create_engine(url, **engine_config)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )
        
        # Retrieve reserved words from SQLAlchemy dialect
        self._reserved_words = self._get_reserved_words()
    
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
        
        # Check if it's a reserved keyword (case-insensitive)
        if self._reserved_words and schema_name.lower() in self._reserved_words:
            error_msg = f"Invalid schema name '{schema_name}': cannot use PostgreSQL reserved keyword"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Schema name '{schema_name}' validated successfully")
        return schema_name
    
    def _get_reserved_words(self) -> set:
        """
        Retrieve PostgreSQL reserved words from SQLAlchemy dialect.
        
        Attempts multiple attribute access patterns to retrieve reserved words
        from the dialect or identifier preparer. Falls back to empty set if
        unavailable, with appropriate logging.
        
        Returns:
            Set of lowercase reserved words, or empty set if unavailable
        """
        try:
            # Try to access dialect's reserved_words
            if hasattr(self.engine.dialect, 'reserved_words'):
                reserved = self.engine.dialect.reserved_words
                if reserved and hasattr(reserved, '__iter__'):
                    result = {word.lower() for word in reserved}
                    logger.info(f"Retrieved {len(result)} reserved words from dialect.reserved_words")
                    return result
            
            # Try to access RESERVED_WORDS (uppercase attribute)
            if hasattr(self.engine.dialect, 'RESERVED_WORDS'):
                reserved = self.engine.dialect.RESERVED_WORDS
                if reserved and hasattr(reserved, '__iter__'):
                    result = {word.lower() for word in reserved}
                    logger.info(f"Retrieved {len(result)} reserved words from dialect.RESERVED_WORDS")
                    return result
            
            # Try to access preparer's reserved words
            if hasattr(self.engine.dialect, 'preparer'):
                preparer = self.engine.dialect.preparer
                if hasattr(preparer, 'reserved_words'):
                    reserved = preparer.reserved_words
                    if reserved and hasattr(reserved, '__iter__'):
                        result = {word.lower() for word in reserved}
                        logger.info(f"Retrieved {len(result)} reserved words from dialect.preparer.reserved_words")
                        return result
            
            # If no attributes found, log warning and return empty set
            logger.warning(
                "Could not retrieve reserved words from SQLAlchemy dialect. "
                "Schema validation will skip reserved word checking. "
                "This may allow reserved keywords as schema names."
            )
            return set()
            
        except Exception as e:
            # Defensive error handling - catch any unexpected errors
            logger.error(
                f"Error retrieving reserved words from dialect: {e}. "
                "Falling back to empty set. Schema validation will be limited."
            )
            return set()
    
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