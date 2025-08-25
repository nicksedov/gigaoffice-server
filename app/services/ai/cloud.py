"""
Cloud GigaChat Service
Production implementation for cloud-based GigaChat API
"""

import asyncio
from typing import Optional
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from .base import BaseGigaChatService
from ...core.config import get_settings


class CloudGigaChatService(BaseGigaChatService):
    """Cloud GigaChat service implementation"""
    
    def __init__(self, model: Optional[str] = None, **kwargs):
        super().__init__(model)
        
        # Cloud-specific settings
        self.credentials = self.settings.gigachat_credentials
        if not self.credentials:
            raise ValueError("GigaChat credentials are required for cloud mode")
        
        logger.info(f"Initialized CloudGigaChatService with model: {self.model}")
    
    def _init_client(self):
        """Initialize cloud GigaChat client"""
        try:
            from langchain_community.chat_models import GigaChat
            
            self.client = GigaChat(
                credentials=self.credentials,
                model=self.model,
                scope=self.scope,
                verify_ssl_certs=self.verify_ssl_certs,
                temperature=self.temperature
            )
            
            logger.info("Cloud GigaChat client initialized successfully")
            
        except ImportError as e:
            logger.error("Failed to import GigaChat from langchain_community. Please install: pip install langchain-gigachat")
            raise ImportError("langchain-gigachat package is required for cloud mode") from e
        except Exception as e:
            logger.error(f"Failed to initialize cloud GigaChat client: {e}")
            raise
    
    async def _make_request(self, system_prompt: str, user_prompt: str, 
                          temperature: float, operation: str) -> str:
        """Make request to cloud GigaChat API"""
        self._add_request_time()
        
        try:
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Set temperature for this request if different from default
            if temperature != self.temperature:
                # Note: Some GigaChat implementations may not support per-request temperature
                # This would need to be handled based on the actual API capabilities
                pass
            
            # Make async request
            response = await asyncio.to_thread(self.client.invoke, messages)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Cloud GigaChat request failed: {e}")
            raise
    
    def check_service_health(self) -> dict:
        """Check cloud service health with actual API call"""
        try:
            # Make a simple health check request
            messages = [
                SystemMessage(content="Ты - AI ассистент."),
                HumanMessage(content="Ответь одним словом: 'Работаю'")
            ]
            
            import time
            start_time = time.time()
            response = self.client.invoke(messages)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "mode": "cloud",
                "model": self.model,
                "response_time": response_time,
                "total_tokens_used": self.total_tokens_used,
                "success_rate": (self.successful_requests / max(1, self.request_count)) * 100,
                "rate_limit_available": self._check_rate_limit(),
                "api_response": response.content[:50] if hasattr(response, 'content') else str(response)[:50]
            }
            
        except Exception as e:
            logger.error(f"Cloud GigaChat health check failed: {e}")
            return {
                "status": "unhealthy",
                "mode": "cloud",
                "model": self.model,
                "error": str(e),
                "total_tokens_used": self.total_tokens_used
            }
    
    def get_available_models(self) -> list:
        """Get available cloud models"""
        try:
            # This would depend on the actual GigaChat API capabilities
            # For now, return known models
            return [
                "GigaChat",
                "GigaChat-Pro", 
                "GigaChat-Max"
            ]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return [self.model]
    
    def update_credentials(self, new_credentials: str):
        """Update GigaChat credentials"""
        try:
            self.credentials = new_credentials
            self._init_client()  # Reinitialize client with new credentials
            logger.info("GigaChat credentials updated successfully")
        except Exception as e:
            logger.error(f"Failed to update credentials: {e}")
            raise
    
    def get_quota_info(self) -> dict:
        """Get API quota information (if available)"""
        try:
            # This would need to be implemented based on actual GigaChat API
            # For now, return basic info
            return {
                "requests_remaining": max(0, self.max_requests_per_minute - len(self.request_times)),
                "tokens_used": self.total_tokens_used,
                "reset_time": None  # Would be provided by actual API
            }
        except Exception as e:
            logger.error(f"Failed to get quota info: {e}")
            return {"error": str(e)}