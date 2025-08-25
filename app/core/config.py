"""
Core Configuration Module
Application settings and environment management
"""

import os
import time
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import validator
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Info
    app_name: str = "GigaOffice AI Service"
    app_version: str = "1.0.0"
    app_description: str = "Промежуточный сервис для интеграции Р7-офиса с GigaChat"
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Database Settings
    database_url: str = "postgresql://localhost:5432/gigaoffice"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    
    # GigaChat Settings
    gigachat_run_mode: str = "dryrun"  # dryrun, cloud, mtls
    gigachat_credentials: Optional[str] = None
    gigachat_verify_ssl_certs: bool = True
    gigachat_max_tokens: int = 8192
    gigachat_temperature: float = 0.7
    
    # Kafka Settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "gigaoffice-consumers"
    kafka_request_topic: str = "gigaoffice-requests"
    kafka_response_topic: str = "gigaoffice-responses"
    kafka_auto_offset_reset: str = "latest"
    
    # Security Settings
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30
    cors_origins: list = ["*"]
    
    # Rate Limiting
    rate_limit_requests: int = 20
    rate_limit_window: str = "1 minute"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "{time} | {level} | {message}"
    log_file: Optional[str] = None
    
    # Resources
    resources_dir: str = "resources"
    
    # Performance
    max_workers: int = 4
    request_timeout: int = 30
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v
    
    @validator('gigachat_run_mode')
    def validate_gigachat_mode(cls, v):
        if v not in ['dryrun', 'cloud', 'mtls']:
            raise ValueError('GigaChat mode must be dryrun, cloud, or mtls')
        return v
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def resources_path(self) -> Path:
        return Path(self.resources_dir)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class AppState:
    """Application state management"""
    
    def __init__(self):
        self.start_time = time.time()
        self.is_ready = False
        self.components_status: Dict[str, bool] = {
            "database": False,
            "kafka": False,
            "prompts": False,
            "gigachat": False
        }
    
    def mark_component_ready(self, component: str):
        """Mark a component as ready"""
        self.components_status[component] = True
        self.check_readiness()
    
    def mark_component_failed(self, component: str):
        """Mark a component as failed"""
        self.components_status[component] = False
        self.is_ready = False
    
    def check_readiness(self):
        """Check if all components are ready"""
        self.is_ready = all(self.components_status.values())
    
    @property
    def uptime(self) -> float:
        return time.time() - self.start_time


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Export settings instance for direct import
settings = get_settings()

# Global app state instance
app_state = AppState()


# Utility functions
def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource file"""
    settings = get_settings()
    return settings.resources_path / relative_path


def load_config_file(config_name: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    import json
    from loguru import logger
    
    try:
        config_path = get_resource_path(f"config/{config_name}.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"Config file not found: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config {config_name}: {e}")
        return {}