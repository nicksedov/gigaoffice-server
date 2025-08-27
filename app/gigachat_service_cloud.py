"""
Cloud GigaChat Service
Реализация GigaChat сервиса для облачного подключения
"""

import os
from langchain_gigachat.chat_models import GigaChat
from loguru import logger
from app.resource_loader import resource_loader
from app.gigachat_service_base import BaseGigaChatService

class CloudGigaChatService(BaseGigaChatService):
    """Сервис для работы с GigaChat через облачное подключение"""
    
    def _init_client(self):
        """Инициализация клиента GigaChat для облачного режима"""
        try:
            config = resource_loader.get_config("gigachat_config")
            
            self.credentials = os.getenv("GIGACHAT_CREDENTIALS")
            self.base_url = os.getenv("GIGACHAT_BASE_URL", config.get("base_url"))
            
            if not self.credentials:
                raise ValueError("GIGACHAT_CREDENTIALS environment variable is required for cloud mode")
            
            self.client = GigaChat(
                credentials=self.credentials,
                base_url=self.base_url,
                scope=self.scope,
                model=self.model,
                verify_ssl_certs=self.verify_ssl_certs,
                timeout=60.0
            )
            
            logger.info("GigaChat client initialized successfully (CLOUD mode)")
            
        except Exception as e:
            logger.error(f"Failed to initialize GigaChat client in cloud mode: {e}")
            raise
