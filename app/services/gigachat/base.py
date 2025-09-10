"""
Base GigaChat Service
Базовый класс для всех реализаций GigaChat сервиса
"""

import os
import json
import time
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from app.resource_loader import resource_loader
from app.prompts import prompt_manager
from app.services.gigachat.response_parser import response_parser
from langchain_core.messages import HumanMessage, SystemMessage
from fastapi import HTTPException

class BaseGigaChatService(ABC):
    """Базовый абстрактный класс для GigaChat сервисов"""
    
    def __init__(self, prompt_builder, model=None):
        config = resource_loader.get_config("gigachat_config")
        self.model = model or os.getenv("GIGACHAT_GENERATE_MODEL", config.get("model"))
        self.scope = os.getenv("GIGACHAT_SCOPE", config.get("scope"))
        self.verify_ssl_certs = os.getenv("GIGACHAT_VERIFY_SSL", str(config.get("verify_ssl_certs", False))).lower() == "true"
        
        # Rate limiting settings
        self.max_requests_per_minute = int(os.getenv("GIGACHAT_MAX_REQUESTS_PER_MINUTE", config.get("max_requests_per_minute", 20)))
        self.max_tokens_per_request = int(os.getenv("GIGACHAT_MAX_TOKENS_PER_REQUEST", config.get("max_tokens_per_request", 8192)))
        
        # Request tracking
        self.request_times = []
        self.total_tokens_used = 0
        
        self.prompt_builder = prompt_builder
        self.client = None
        
        # Инициализация клиента (делегируется подклассам)
        self._init_client()
    
    @abstractmethod
    def _init_client(self):
        """Абстрактный метод для инициализации клиента GigaChat"""
        pass
    
    # Общие методы для всех режимов
    def _check_rate_limit(self) -> bool:
        """Проверка лимитов скорости запросов"""
        current_time = time.time()
        self.request_times = [req_time for req_time in self.request_times if current_time - req_time < 60]
        return len(self.request_times) < self.max_requests_per_minute
    
    def _add_request_time(self):
        """Добавление времени запроса для отслеживания лимитов"""
        self.request_times.append(time.time())
    
    def _count_tokens(self, text: str) -> int:
        """Примерный подсчет токенов"""
        return len(text) // 4
        
    async def classify_query(
        self, 
        query: str,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Классификация запроса
        """
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please wait before making another request.")
        else:
            # Получаем категории из базы данных
            categories = await prompt_manager.get_prompt_categories()
            # Подготовка сообщений
            system_prompt = self.prompt_builder.prepare_classifier_system_prompt(categories)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ]
            response = await asyncio.to_thread(self.client.invoke, messages)
            response_content = response.content
            
            # Парсим ответ
            try:
                result = response_parser.parse_object(response_content)
                
                # Валидация результата
                if not isinstance(result, dict):
                    raise ValueError("Expected dictionary response from parser")
                    
                if not all(key in result for key in ['category', 'confidence']):
                    raise ValueError("Invalid response format")
                    
                for category in categories:
                    if result['category'] == category['name']:
                        logger.info((f"Prompt '{query[:50]}' classified as '{category['name']}' with confidence rate {result['confidence']:3f}"))
                        return {
                            "success": True,
                            "query_text": query,
                            "category": category,
                            "confidence": result['confidence']
                        }
                return {
                    "success": True,
                    "query_text": query,
                    "category": { "name": "uncertain" },
                    "confidence": 0
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing classification response: {e}")
                logger.debug(f"Raw response content: {response_content}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse classification response"
                )
 
    def get_available_models(self) -> List[str]:
        """Получение списка доступных моделей"""
        try:
            # Note: This is a placeholder as langchain-gigachat might not expose model listing
            return ["GigaChat", "GigaChat-Pro", "GigaChat-Max"]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return [self.model]
    
    def check_service_health(self) -> Dict[str, Any]:
        """Проверка состояния сервиса GigaChat"""
        try:
            # Simple health check with a minimal request
            start_time = time.time()
            
            messages = [
                SystemMessage(content="Ты - AI ассистент."),
                HumanMessage(content="Ответь одним словом: 'Работаю'")
            ]
            
            response = self.client.invoke(messages)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "model": self.model,
                "total_tokens_used": self.total_tokens_used,
                "requests_in_last_minute": len(self.request_times),
                "rate_limit_available": self._check_rate_limit()
            }
            
        except Exception as e:
            logger.error(f"GigaChat health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model,
                "total_tokens_used": self.total_tokens_used
            }
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Получение статистики использования"""
        current_time = time.time()
        
        # Clean old request times
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < 60
        ]
        
        return {
            "total_tokens_used": self.total_tokens_used,
            "requests_last_minute": len(self.request_times),
            "rate_limit_remaining": max(0, self.max_requests_per_minute - len(self.request_times)),
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_tokens_per_request": self.max_tokens_per_request,
            "model": self.model
        }