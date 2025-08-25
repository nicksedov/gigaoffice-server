"""
Base GigaChat Service
Enhanced base class for all GigaChat service implementations with improved error handling and monitoring
"""

import os
import time
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from ...core.config import get_settings, load_config_file
from ...utils.logger import structured_logger, performance_timer
from ...utils.resource_loader import resource_loader


class BaseGigaChatService(ABC):
    """Enhanced base abstract class for GigaChat services"""
    
    def __init__(self, model: Optional[str] = None):
        self.settings = get_settings()
        self.config = load_config_file("gigachat_config")
        
        # Model configuration
        self.model = model or self.settings.gigachat_credentials or self.config.get("model", "GigaChat")
        self.scope = self.config.get("scope", "GIGACHAT_API_PERS")
        self.verify_ssl_certs = self.settings.gigachat_verify_ssl_certs
        
        # Rate limiting and performance settings
        self.max_requests_per_minute = int(self.config.get("max_requests_per_minute", self.settings.rate_limit_requests))
        self.max_tokens_per_request = self.settings.gigachat_max_tokens
        self.temperature = self.settings.gigachat_temperature
        
        # Request tracking for rate limiting
        self.request_times = []
        self.total_tokens_used = 0
        
        # Performance metrics
        self.request_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_processing_time = 0.0
        
        # Client instance (to be initialized by subclasses)
        self.client = None
        
        # Initialize client
        self._init_client()
        
        logger.info(f"Initialized {self.__class__.__name__} with model: {self.model}")
    
    @abstractmethod
    def _init_client(self):
        """Abstract method for initializing GigaChat client"""
        pass
    
    def _check_rate_limit(self) -> bool:
        """Check rate limiting constraints"""
        current_time = time.time()
        # Keep only requests from the last minute
        self.request_times = [req_time for req_time in self.request_times if current_time - req_time < 60]
        
        if len(self.request_times) >= self.max_requests_per_minute:
            structured_logger.log_performance_metric(
                "rate_limit_exceeded", 
                len(self.request_times),
                unit="requests"
            )
            return False
        
        return True
    
    def _add_request_time(self):
        """Add request time for rate limiting tracking"""
        self.request_times.append(time.time())
        self.request_count += 1
    
    def _count_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple estimation: ~4 characters per token
        return max(1, len(text) // 4)
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if error should be retried"""
        error_message = str(error).lower()
        
        # Non-retryable errors
        non_retryable = [
            "rate limit exceeded",
            "input too long", 
            "authentication failed",
            "invalid credentials",
            "insufficient permissions",
            "quota exceeded",
            "malformed request"
        ]
        
        for pattern in non_retryable:
            if pattern in error_message:
                return False
        
        # Retryable errors
        retryable = [
            "timeout",
            "connection",
            "network",
            "server error",
            "service unavailable",
            "internal error",
            "failed to parse",
            "temporary",
            "retry"
        ]
        
        for pattern in retryable:
            if pattern in error_message:
                return True
        
        # Default to retryable for unknown errors
        return True
    
    async def classify_query(self, query: str, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Classify user query into categories
        
        Args:
            query: User query text
            temperature: Generation temperature
            
        Returns:
            Classification result with category and confidence
        """
        with performance_timer("classify_query"):
            if not self._check_rate_limit():
                raise Exception("Rate limit exceeded. Please wait before making another request.")
            
            try:
                # Load categories and system prompt
                categories_data = resource_loader.load_json("prompts/prompt_categories.json")
                classifier_prompt = resource_loader.get_prompt_template("user_prompt_classifier")
                
                if not categories_data or not classifier_prompt:
                    raise Exception("Classification resources not available")
                
                # Prepare classification prompt
                categories_text = "\n".join([
                    f"- {cat.get('name', '')}: {cat.get('description', '')}"
                    for cat in categories_data
                ])
                
                system_prompt = classifier_prompt.format(categories=categories_text)
                
                # Make classification request
                result = await self._make_request(
                    system_prompt=system_prompt,
                    user_prompt=query,
                    temperature=temperature,
                    operation="classify"
                )
                
                # Parse and validate classification result
                classification = self._parse_classification_response(result, categories_data)
                
                structured_logger.log_service_call(
                    "GigaChatService", "classify_query", 
                    classification.get("processing_time", 0),
                    True,
                    category=classification.get("category", {}).get("name", "unknown"),
                    confidence=classification.get("confidence", 0)
                )
                
                return classification
                
            except Exception as e:
                structured_logger.log_error(e, {"operation": "classify_query", "query": query[:100]})
                self.failed_requests += 1
                raise
    
    async def process_query(
        self, 
        query: str,
        input_range: Optional[str] = None,
        category: Optional[str] = None,
        input_data: Optional[List[Dict]] = None,
        temperature: float = None
    ) -> Tuple[List[List[Any]], Dict[str, Any]]:
        """
        Process user query with GigaChat
        
        Args:
            query: User query text
            input_range: Input data range
            category: Query category
            input_data: Additional input data
            temperature: Generation temperature
            
        Returns:
            Tuple of (result_data, metadata)
        """
        if temperature is None:
            temperature = self.temperature
            
        max_retries = int(self.config.get("max_retries", 3))
        
        with performance_timer("process_query", query=query[:100], category=category):
            for attempt in range(max_retries):
                try:
                    if not self._check_rate_limit():
                        raise Exception("Rate limit exceeded. Please wait before making another request.")
                    
                    # Prepare system and user prompts
                    system_prompt = self._prepare_system_prompt(category)
                    user_prompt = self._prepare_user_prompt(query, input_range, input_data)
                    
                    # Validate token count
                    total_input_tokens = self._count_tokens(system_prompt + user_prompt)
                    if total_input_tokens > self.max_tokens_per_request:
                        raise Exception(f"Input too long: {total_input_tokens} tokens (max: {self.max_tokens_per_request})")
                    
                    # Make request
                    start_time = time.time()
                    result = await self._make_request(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        operation="process"
                    )
                    
                    processing_time = time.time() - start_time
                    self.total_processing_time += processing_time
                    
                    # Parse result
                    parsed_result = self._parse_process_response(result)
                    
                    if parsed_result is None:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to parse response, retrying... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(1.0 * (attempt + 1))
                            continue
                        else:
                            raise Exception(f"Failed to parse response after {max_retries} attempts")
                    
                    # Calculate tokens and prepare metadata
                    output_tokens = self._count_tokens(str(result))
                    total_tokens = total_input_tokens + output_tokens
                    self.total_tokens_used += total_tokens
                    self.successful_requests += 1
                    
                    metadata = {
                        "processing_time": processing_time,
                        "input_tokens": total_input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "model": self.model,
                        "temperature": temperature,
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                        "attempts": attempt + 1,
                        "max_retries": max_retries
                    }
                    
                    structured_logger.log_service_call(
                        "GigaChatService", "process_query",
                        processing_time, True,
                        tokens=total_tokens, attempts=attempt + 1
                    )
                    
                    return parsed_result, metadata
                    
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    
                    if attempt < max_retries - 1 and self._should_retry_error(e):
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue
                    else:
                        self.failed_requests += 1
                        structured_logger.log_error(e, {
                            "operation": "process_query",
                            "query": query[:100],
                            "attempt": attempt + 1,
                            "max_retries": max_retries
                        })
                        raise
    
    @abstractmethod
    async def _make_request(self, system_prompt: str, user_prompt: str, 
                          temperature: float, operation: str) -> str:
        """Make actual request to GigaChat API (implemented by subclasses)"""
        pass
    
    def _prepare_system_prompt(self, category: Optional[str] = None) -> str:
        """Prepare system prompt based on category"""
        if category:
            # Load category-specific system prompt
            prompt_file = f"system_prompt_{category}.yaml"
            system_prompt = resource_loader.get_prompt_template(prompt_file)
            
            if not system_prompt:
                # Fallback to default system prompt
                system_prompt = resource_loader.get_prompt_template("system_prompt_generation.yaml")
        else:
            system_prompt = resource_loader.get_prompt_template("system_prompt_generation.yaml")
        
        return system_prompt or "You are a helpful AI assistant."
    
    def _prepare_user_prompt(self, query: str, input_range: Optional[str] = None, 
                           input_data: Optional[List[Dict]] = None) -> str:
        """Prepare user prompt with query and optional data"""
        prompt_parts = [query]
        
        if input_range:
            prompt_parts.append(f"Диапазон данных: {input_range}")
        
        if input_data:
            prompt_parts.append(f"Входные данные: {input_data}")
        
        return "\n\n".join(prompt_parts)
    
    def _parse_classification_response(self, response: str, categories: List[Dict]) -> Dict[str, Any]:
        """Parse classification response"""
        try:
            # Try to parse as JSON first
            import json
            result = json.loads(response)
            
            if isinstance(result, dict) and "category" in result:
                # Find matching category
                category_name = result["category"]
                for category in categories:
                    if category.get("name") == category_name:
                        return {
                            "success": True,
                            "category": category,
                            "confidence": result.get("confidence", 0.0),
                            "query_text": result.get("query", "")
                        }
                
                # Category not found, return uncertain
                return {
                    "success": True,
                    "category": {"name": "uncertain", "description": "Uncertain category"},
                    "confidence": 0.0,
                    "query_text": ""
                }
            
        except json.JSONDecodeError:
            # Try to extract category from text response
            for category in categories:
                if category.get("name", "").lower() in response.lower():
                    return {
                        "success": True,
                        "category": category,
                        "confidence": 0.5,  # Lower confidence for text parsing
                        "query_text": ""
                    }
        
        # Fallback to uncertain category
        return {
            "success": True,
            "category": {"name": "uncertain", "description": "Could not determine category"},
            "confidence": 0.0,
            "query_text": ""
        }
    
    def _parse_process_response(self, response: str) -> Optional[List[List[Any]]]:
        """Parse process response (to be enhanced by response parser)"""
        # This is a simplified version - the actual implementation would use
        # the response parser to convert the response into the expected format
        try:
            # For now, return the response as a simple text result
            return [[response]]
        except Exception as e:
            logger.error(f"Failed to parse process response: {e}")
            return None
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get service usage statistics"""
        current_time = time.time()
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        success_rate = (self.successful_requests / max(1, self.request_count)) * 100
        avg_processing_time = self.total_processing_time / max(1, self.successful_requests)
        
        return {
            "total_requests": self.request_count,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": success_rate,
            "total_tokens_used": self.total_tokens_used,
            "avg_processing_time": avg_processing_time,
            "requests_last_minute": len(self.request_times),
            "rate_limit_remaining": max(0, self.max_requests_per_minute - len(self.request_times)),
            "model": self.model,
            "service_type": self.__class__.__name__
        }
    
    def check_service_health(self) -> Dict[str, Any]:
        """Check service health status"""
        try:
            # This would be implemented by subclasses with actual health check
            return {
                "status": "healthy",
                "model": self.model,
                "rate_limit_available": self._check_rate_limit(),
                "total_tokens_used": self.total_tokens_used,
                "success_rate": (self.successful_requests / max(1, self.request_count)) * 100
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model
            }