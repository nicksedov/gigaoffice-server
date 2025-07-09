"""
GigaOffice GigaChat Service
Сервис для работы с GigaChat API через langchain-gigachat
"""

import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from resource_loader import resource_loader

class GigaChatService:
    """Сервис для работы с GigaChat API"""
    
    def __init__(self):
        config = resource_loader.get_config("gigachat_config")
        self.credentials = os.getenv("GIGACHAT_CREDENTIALS")
        self.base_url = os.getenv("GIGACHAT_BASE_URL", config.get("base_url"))
        self.scope = os.getenv("GIGACHAT_SCOPE", config.get("scope"))
        self.model = os.getenv("GIGACHAT_MODEL", config.get("model"))
        self.verify_ssl_certs = os.getenv("GIGACHAT_VERIFY_SSL", config.get("verify_ssl_certs")).lower() == "true"
        
        # Rate limiting settings
        self.max_requests_per_minute = int(os.getenv("GIGACHAT_MAX_REQUESTS_PER_MINUTE", config.get("max_requests_per_minute")))
        self.max_tokens_per_request = int(os.getenv("GIGACHAT_MAX_TOKENS_PER_REQUEST", config.get("max_tokens_per_request")))
        
        # Request tracking
        self.request_times = []
        self.total_tokens_used = 0
        
        # Initialize GigaChat client
        self._init_client()
        
    def _init_client(self):
        """Инициализация клиента GigaChat"""
        try:
            if not self.credentials:
                raise ValueError("GIGACHAT_CREDENTIALS environment variable is required")
            
            self.client = GigaChat(
                credentials=self.credentials,
                base_url=self.base_url,
                scope=self.scope,
                model=self.model,
                verify_ssl_certs=self.verify_ssl_certs,
                timeout=60.0
            )
            
            logger.info("GigaChat client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GigaChat client: {e}")
            raise
    
    def _check_rate_limit(self) -> bool:
        """Проверка лимитов скорости запросов"""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < 60
        ]
        
        # Check if we can make a new request
        if len(self.request_times) >= self.max_requests_per_minute:
            return False
        
        return True
    
    def _add_request_time(self):
        """Добавление времени запроса для отслеживания лимитов"""
        self.request_times.append(time.time())
    
    def _count_tokens(self, text: str) -> int:
        """Примерный подсчет токенов (1 токен ≈ 4 символа для русского языка)"""
        return len(text) // 4  # Приблизительная оценка
    
    def _prepare_system_prompt(self) -> str:
        """Подготовка системного промпта для табличных данных"""
        return resource_loader.get_prompt_template("gigachat_system_prompt.txt")
    
    def _prepare_user_prompt(self, query: str, input_data: Optional[List[Dict]] = None) -> str:
        """Подготовка пользовательского промпта"""
        prompt_parts = []
        
        if input_data:
            prompt_parts.append("ИСХОДНЫЕ ДАННЫЕ:")
            prompt_parts.append(json.dumps(input_data, ensure_ascii=False, indent=2))
            prompt_parts.append("")
        
        prompt_parts.append("ЗАДАЧА:")
        prompt_parts.append(query)
        prompt_parts.append("")
        prompt_parts.append("Предоставь ответ в виде JSON массива массивов, готового для вставки в таблицу.")
        
        return "\n".join(prompt_parts)
    
    async def process_query(
        self, 
        query: str, 
        input_data: Optional[List[Dict]] = None,
        temperature: float = 0.1
    ) -> Tuple[List[List[Any]], Dict[str, Any]]:
        """
        Обработка запроса к GigaChat
        
        Args:
            query: Текст запроса
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
            system_prompt = self._prepare_system_prompt()
            user_prompt = self._prepare_user_prompt(query, input_data)
            
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
            
            # Try to parse JSON response
            try:
                # Clean response content
                content = response_content.strip()
                
                # Extract JSON from markdown code blocks if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    start_line = 0
                    end_line = len(lines)
                    
                    for i, line in enumerate(lines):
                        if line.startswith("```"):
                            if start_line == 0:
                                start_line = i + 1
                            else:
                                end_line = i
                                break
                    
                    content = "\n".join(lines[start_line:end_line])
                
                # Parse JSON
                result_data = json.loads(content)
                
                # Validate result format
                if not isinstance(result_data, list):
                    raise ValueError("Result must be a list")
                
                for row in result_data:
                    if not isinstance(row, list):
                        raise ValueError("Each row must be a list")
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                # Fallback: return response as single cell
                result_data = [[response_content]]
            
            # Prepare metadata
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

