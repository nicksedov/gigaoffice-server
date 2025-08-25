"""
Dryrun GigaChat Service
Mock implementation for testing and development
"""

import asyncio
import random
import time
from typing import Optional
from loguru import logger

from .base import BaseGigaChatService


class DryrunGigaChatService(BaseGigaChatService):
    """Mock GigaChat service for testing and development"""
    
    def __init__(self, model: Optional[str] = None, **kwargs):
        # Set default model for dryrun
        if model is None:
            model = "GigaChat-Dryrun"
        
        super().__init__(model)
        
        # Dryrun specific settings
        self.simulate_processing_time = kwargs.get('simulate_processing_time', True)
        self.min_response_time = kwargs.get('min_response_time', 0.5)
        self.max_response_time = kwargs.get('max_response_time', 2.0)
        self.error_rate = kwargs.get('error_rate', 0.05)  # 5% error rate for testing
        
        logger.info(f"Initialized DryrunGigaChatService with error_rate={self.error_rate}")
    
    def _init_client(self):
        """Initialize mock client"""
        self.client = "DryrunClient"  # Mock client
        logger.info("Dryrun GigaChat client initialized (mock)")
    
    async def _make_request(self, system_prompt: str, user_prompt: str, 
                          temperature: float, operation: str) -> str:
        """Make mock request with simulated response"""
        self._add_request_time()
        
        # Simulate processing time
        if self.simulate_processing_time:
            processing_time = random.uniform(self.min_response_time, self.max_response_time)
            await asyncio.sleep(processing_time)
        
        # Simulate occasional errors for testing
        if random.random() < self.error_rate:
            error_types = [
                "Network timeout",
                "Service temporarily unavailable", 
                "Rate limit exceeded",
                "Internal server error"
            ]
            raise Exception(f"Simulated error: {random.choice(error_types)}")
        
        # Generate mock response based on operation type
        if operation == "classify":
            return self._generate_classification_response(user_prompt)
        elif operation == "process":
            return self._generate_process_response(user_prompt, system_prompt)
        else:
            return self._generate_generic_response(user_prompt)
    
    def _generate_classification_response(self, query: str) -> str:
        """Generate mock classification response"""
        # Mock classification categories with confidence
        categories = [
            ("analysis", 0.95),
            ("generation", 0.90),
            ("search", 0.85),
            ("transformation", 0.80),
            ("uncertain", 0.30)
        ]
        
        # Simple keyword-based classification for demo
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["анализ", "analyze", "изучи", "разбери"]):
            category, confidence = "analysis", 0.95
        elif any(word in query_lower for word in ["создай", "generate", "напиши", "сгенерируй"]):
            category, confidence = "generation", 0.90
        elif any(word in query_lower for word in ["найди", "search", "поиск", "ищи"]):
            category, confidence = "search", 0.85
        elif any(word in query_lower for word in ["преобразуй", "transform", "конвертируй"]):
            category, confidence = "transformation", 0.80
        else:
            category, confidence = random.choice(categories)
        
        # Add some randomness to confidence
        confidence += random.uniform(-0.1, 0.1)
        confidence = max(0.0, min(1.0, confidence))
        
        return f'{{"category": "{category}", "confidence": {confidence:.2f}, "query": "{query[:50]}"}}'
    
    def _generate_process_response(self, user_prompt: str, system_prompt: str) -> str:
        """Generate mock process response"""
        responses = [
            "Это mock-ответ от GigaChat Dryrun сервиса. Ваш запрос был обработан успешно.",
            "Симуляция обработки запроса завершена. В реальном режиме здесь был бы ответ от GigaChat.",
            "Mock-данные: обработка выполнена в тестовом режиме. Результат сформирован локально.",
            f"Тестовый ответ на запрос: '{user_prompt[:100]}...' выполнен успешно."
        ]
        
        # Select response based on prompt content
        if "таблиц" in user_prompt.lower() or "table" in user_prompt.lower():
            return "Обработка табличных данных выполнена в тестовом режиме. Результат: [[['Колонка 1', 'Колонка 2'], ['Значение 1', 'Значение 2']]]"
        elif "данные" in user_prompt.lower() or "data" in user_prompt.lower():
            return "Анализ данных выполнен в mock-режиме. Результат представлен в формате JSON."
        else:
            return random.choice(responses)
    
    def _generate_generic_response(self, prompt: str) -> str:
        """Generate generic mock response"""
        return f"Mock-ответ для запроса: {prompt[:50]}... (Dryrun режим)"
    
    def check_service_health(self) -> dict:
        """Check dryrun service health"""
        return {
            "status": "healthy",
            "mode": "dryrun",
            "model": self.model,
            "total_tokens_used": self.total_tokens_used,
            "success_rate": (self.successful_requests / max(1, self.request_count)) * 100,
            "error_rate_setting": self.error_rate,
            "simulate_processing_time": self.simulate_processing_time,
            "response_time_range": f"{self.min_response_time}-{self.max_response_time}s"
        }
    
    def get_available_models(self) -> list:
        """Get available mock models"""
        return [
            "GigaChat-Dryrun",
            "GigaChat-Pro-Dryrun", 
            "GigaChat-Max-Dryrun"
        ]
    
    def set_error_rate(self, error_rate: float):
        """Set error rate for testing"""
        self.error_rate = max(0.0, min(1.0, error_rate))
        logger.info(f"Dryrun error rate set to {self.error_rate}")
    
    def set_response_time_range(self, min_time: float, max_time: float):
        """Set response time simulation range"""
        self.min_response_time = max(0.1, min_time)
        self.max_response_time = max(self.min_response_time, max_time)
        logger.info(f"Response time range set to {self.min_response_time}-{self.max_response_time}s")
    
    def enable_processing_simulation(self, enabled: bool = True):
        """Enable or disable processing time simulation"""
        self.simulate_processing_time = enabled
        logger.info(f"Processing time simulation: {'enabled' if enabled else 'disabled'}")