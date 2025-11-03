"""
Cloud GigaChat Service
Реализация GigaChat сервиса для облачного подключения
"""

import os
from langchain_gigachat.chat_models import GigaChat
from loguru import logger
from app.services.gigachat.base import BaseGigaChatService

class CloudGigaChatService(BaseGigaChatService):
    """Сервис для работы с GigaChat через облачное подключение"""
    
    def _init_client(self):
        """Инициализация клиента GigaChat для облачного режима"""
        try:
            self.credentials = os.getenv("GIGACHAT_CREDENTIALS")
            self.base_url = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1")
            self.timeout = float(os.getenv("GIGACHAT_REQUEST_TIMEOUT", "60.0"))
            
            if not self.credentials:
                raise ValueError("GIGACHAT_CREDENTIALS environment variable is required for cloud mode")
            
            self.client = GigaChat(
                credentials=self.credentials,
                base_url=self.base_url,
                scope=self.scope,
                model=self.model,
                verify_ssl_certs=self.verify_ssl_certs,
                timeout=self.timeout
            )
            
            logger.info("GigaChat client initialized successfully (CLOUD mode)")
            
        except Exception as e:
            logger.error(f"Failed to initialize GigaChat client in cloud mode: {e}")
            raise