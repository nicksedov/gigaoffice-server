"""
mTLS GigaChat Service
Реализация GigaChat сервиса для подключения через mTLS
"""

import os
from langchain_gigachat.chat_models import GigaChat
from loguru import logger
from app.resource_loader import resource_loader
from app.services.gigachat.base import BaseGigaChatService

class MtlsGigaChatService(BaseGigaChatService):
    """Сервис для работы с GigaChat через mTLS подключение"""
    
    def _init_client(self):
        """Инициализация клиента GigaChat для mTLS режима"""
        try:
            config = resource_loader.get_config("gigachat_config")
            
            # Получаем параметры для mTLS подключения
            self.base_url = os.getenv("GIGACHAT_BASE_URL", config.get("base_url"))
            self.ca_bundle_file = os.getenv("GIGACHAT_MTLS_CA_BUNDLE_FILE")
            self.cert_file = os.getenv("GIGACHAT_MTLS_CERT_FILE")
            self.key_file = os.getenv("GIGACHAT_MTLS_KEY_FILE")
            self.key_file_password = os.getenv("GIGACHAT_MTLS_KEY_FILE_PASSWORD")
            
            # Проверяем обязательные параметры
            if str(self.verify_ssl_certs).lower() == 'true' and not self.ca_bundle_file:
                raise ValueError("GIGACHAT_MTLS_CA_BUNDLE_FILE environment variable is required for mTLS mode")
            if not self.cert_file:
                raise ValueError("GIGACHAT_MTLS_CERT_FILE environment variable is required for mTLS mode")
            if not self.key_file:
                raise ValueError("GIGACHAT_MTLS_KEY_FILE environment variable is required for mTLS mode")
            
            # Проверяем существование файлов
            if str(self.verify_ssl_certs).lower() == 'true' and not os.path.exists(self.ca_bundle_file):
                raise FileNotFoundError(f"CA bundle file not found: {self.ca_bundle_file}")
            if not os.path.exists(self.cert_file):
                raise FileNotFoundError(f"Certificate file not found: {self.cert_file}")
            if not os.path.exists(self.key_file):
                raise FileNotFoundError(f"Key file not found: {self.key_file}")
            
            # Инициализируем клиент для mTLS режима
            self.client = GigaChat(
                base_url=self.base_url,
                ca_bundle_file=self.ca_bundle_file,
                cert_file=self.cert_file,
                key_file=self.key_file,
                key_file_password=self.key_file_password,
                scope=self.scope,
                model=self.model,
                verify_ssl_certs=self.verify_ssl_certs,
                timeout=60.0
            )
            
            logger.info("GigaChat client initialized successfully (mTLS mode)")
            if str(self.verify_ssl_certs).lower() == 'true':
                logger.info(f"Using CA bundle: {self.ca_bundle_file}")
            logger.info(f"Using certificate: {self.cert_file}")
            logger.info(f"Using key file: {self.key_file}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GigaChat client in mTLS mode: {e}")
            raise