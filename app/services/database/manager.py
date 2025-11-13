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
    
    def _ensure_schema_exists(self):
        """
        Ensure the configured schema exists in the database.
        Creates it if DB_SCHEMA_AUTO_CREATE is enabled.
        """
        if not self.schema:
            # No schema configured, using default public schema
            return
        
        try:
            with self.engine.connect() as connection:
                # Check if schema exists
                result = connection.execute(text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
                ), {"schema": self.schema})
                
                schema_exists = result.fetchone() is not None
                
                if schema_exists:
                    logger.info(f"Schema '{self.schema}' exists and is ready")
                    return
                
                # Schema doesn't exist - check if auto-create is enabled
                auto_create = os.getenv("DB_SCHEMA_AUTO_CREATE", "false").lower() == "true"
                
                if not auto_create:
                    error_msg = (
                        f"Configured schema '{self.schema}' does not exist in database. "
                        f"Set DB_SCHEMA_AUTO_CREATE=true to create automatically or create it manually."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Attempt to create schema
                logger.info(f"Creating schema '{self.schema}'...")
                try:
                    connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
                    connection.commit()
                    logger.info(f"Schema '{self.schema}' created successfully")
                    
                    # Grant USAGE if configured
                    grant_usage = os.getenv("DB_SCHEMA_GRANT_USAGE", "true").lower() == "true"
                    if grant_usage:
                        db_user = os.getenv("DB_USER", "gigaoffice")
                        try:
                            connection.execute(text(f'GRANT USAGE ON SCHEMA "{self.schema}" TO "{db_user}"'))
                            connection.execute(text(f'GRANT CREATE ON SCHEMA "{self.schema}" TO "{db_user}"'))
                            connection.commit()
                            logger.info(f"Granted USAGE and CREATE on schema '{self.schema}' to user '{db_user}'")
                        except SQLAlchemyError as grant_error:
                            # Log warning but don't fail - schema is created
                            logger.warning(f"Could not grant permissions on schema: {grant_error}")
                    
                except SQLAlchemyError as create_error:
                    # Check if error is due to concurrent creation (race condition)
                    if "already exists" in str(create_error).lower() or "duplicate" in str(create_error).lower():
                        logger.warning(f"Schema '{self.schema}' already exists (likely created by another instance)")
                        return
                    
                    # Check if error is due to insufficient permissions
                    if "permission denied" in str(create_error).lower():
                        db_user = os.getenv("DB_USER", "gigaoffice")
                        error_msg = (
                            f"Database user '{db_user}' does not have permission to create schema '{self.schema}'. "
                            f"Grant CREATE privilege or create schema manually."
                        )
                        logger.error(error_msg)
                        raise PermissionError(error_msg) from create_error
                    
                    # Unknown error - re-raise
                    raise
                    
        except (ValueError, PermissionError):
            # Re-raise validation and permission errors
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error ensuring schema exists: {e}")
            raise
   
    def create_tables(self):
        """Создание всех таблиц"""
        try:
            # Ensure schema exists before creating tables
            self._ensure_schema_exists()
            
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
                
                # Handle case where result might be None
                if result is None:
                    version = "Unknown"
                    database_name = "Unknown"
                    current_user = "Unknown"
                    server_addr = "Unknown"
                    server_port = "Unknown"
                else:
                    version = getattr(result, 'version', 'Unknown')
                    database_name = getattr(result, 'database_name', 'Unknown')
                    current_user = getattr(result, 'current_user', 'Unknown')
                    server_addr = getattr(result, 'server_addr', 'Unknown')
                    server_port = getattr(result, 'server_port', 'Unknown')
                
                # Safe access to pool methods with compatibility for SQLAlchemy 2.0
                pool_info = {
                    "pool_size": "Unknown",
                    "checked_out": "Unknown",
                    "overflow": "Unknown"
                }
                
                try:
                    if hasattr(self.engine, 'pool') and self.engine.pool is not None:
                        pool = self.engine.pool
                        # Use getattr to safely access pool methods
                        pool_size_method = getattr(pool, 'size', None)
                        if callable(pool_size_method):
                            pool_info["pool_size"] = str(pool_size_method())
                        
                        # Try different method names for checkedout
                        checkedout_method = getattr(pool, 'checkedout', None)
                        if not callable(checkedout_method):
                            checkedout_method = getattr(pool, 'checked_out', None)  # SQLAlchemy 2.0
                        
                        if callable(checkedout_method):
                            pool_info["checked_out"] = str(checkedout_method())
                        
                        overflow_method = getattr(pool, 'overflow', None)
                        if callable(overflow_method):
                            pool_info["overflow"] = str(overflow_method())
                except Exception as pool_error:
                    logger.warning(f"Could not retrieve pool information: {pool_error}")
                
                return {
                    "version": version,
                    "database_name": database_name,
                    "current_user": current_user,
                    "current_schema": current_schema,
                    "search_path": search_path,
                    "configured_schema": self.schema,
                    "server_addr": server_addr,
                    "server_port": server_port,
                    **pool_info
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}

# Create database manager instance
db_manager = DatabaseManager()