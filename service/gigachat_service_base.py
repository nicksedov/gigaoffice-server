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
from resource_loader import resource_loader
from prompts import prompt_manager
from gigachat_response_parser import response_parser
from langchain_core.messages import HumanMessage, SystemMessage
from fastapi import HTTPException

class BaseGigaChatService(ABC):
    """Базовый абстрактный класс для GigaChat сервисов"""
    
    def __init__(self, prompt_builder):
        # Общие настройки для всех режимов
        config = resource_loader.get_config("gigachat_config")
        self.model = os.getenv("GIGACHAT_MODEL", config.get("model"))
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

    async def process_query(
        self, 
        query: str,
        input_range: Optional[str],
        output_range: str,
        category: Optional[str],
        input_data: Optional[List[Dict]] = None,
        temperature: float = 0.1
    ) -> Tuple[List[List[Any]], Dict[str, Any]]:
        """
        Обработка запроса к GigaChat
        
        Args:
            query: Текст запроса
            input_range: диапазон входных данных (опционально)
            output_range: диапазон вывода результата
            category: категория запроса
            input_data: Входные данные (опционально)
            temperature: Температура генерации (0.0 - 1.0)
        
        Returns:
            Tuple[результат, метаданные]
        """
        try:
            # Check rate limits
            if not self._check_rate_limit():
                raise Exception("Rate limit exceeded. Please wait before making another request.")
            
            # Prepare prompts
            system_prompt = self.prompt_builder.prepare_system_prompt()
            user_prompt = self.prompt_builder.prepare_user_prompt(query, input_range, output_range, input_data)
            
            # Count tokens
            total_input_tokens = self._count_tokens(system_prompt + user_prompt)
            if total_input_tokens > self.max_tokens_per_request:
                raise Exception(f"Input too long: {total_input_tokens} tokens (max: {self.max_tokens_per_request})")
            
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Add request time for rate limiting
            self._add_request_time()
            
            # Make request to GigaChat
            start_time = time.time()
            logger.info(f"Sending request to GigaChat: {query[:100]}...")
            
            response = await asyncio.to_thread(self.client.invoke, messages)
            
            processing_time = time.time() - start_time
            
            # Parse response
            response_content = response.content
            output_tokens = self._count_tokens(response_content)
            total_tokens = total_input_tokens + output_tokens
            
            self.total_tokens_used += total_tokens
            
            result_data = response_parser.parse(response_content)
            metadata = {
                "processing_time": processing_time,
                "input_tokens": total_input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "request_id": getattr(response, 'id', None),
                "success": True
            }
            
            logger.info(f"GigaChat request completed successfully in {processing_time:.2f}s, tokens: {total_tokens}")
            
            return result_data, metadata
            
        except Exception as e:
            logger.error(f"GigaChat request failed: {e}")
            
            metadata = {
                "processing_time": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "request_id": None,
                "success": False,
                "error": str(e)
            }
            
            raise Exception(f"GigaChat processing failed: {e}")
    
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
    
    async def process_batch_queries(
        self, 
        queries: List[Dict[str, Any]], 
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Обработка пакета запросов с ограничением параллельности
        
        Args:
            queries: Список запросов [{"id": int, "query": str, "input_data": Optional[List[Dict]]}]
            max_concurrent: Максимальное количество параллельных запросов
        
        Returns:
            Список результатов [{"id": int, "result": List[List[Any]], "metadata": Dict, "error": Optional[str]}]
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_query(query_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result, metadata = await self.process_query(
                        query_data["query"],
                        query_data.get("input_data")
                    )
                    return {
                        "id": query_data["id"],
                        "result": result,
                        "metadata": metadata,
                        "error": None
                    }
                except Exception as e:
                    return {
                        "id": query_data["id"],
                        "result": None,
                        "metadata": None,
                        "error": str(e)
                    }
        
        # Process all queries concurrently
        tasks = [process_single_query(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that weren't caught
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "id": queries[i]["id"],
                    "result": None,
                    "metadata": None,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
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

