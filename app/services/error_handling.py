"""
Comprehensive Error Handling and Retry Service
Advanced error handling, fallback mechanisms, and retry logic for chart generation
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from loguru import logger

T = TypeVar('T')

class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    AI_SERVICE = "ai_service"
    DATABASE = "database"
    KAFKA = "kafka"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Context information for errors"""
    request_id: str
    user_id: Optional[int] = None
    operation: str = ""
    attempt_number: int = 1
    max_attempts: int = 3
    additional_data: Dict[str, Any] = None

@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[type] = None

class ChartErrorHandler:
    """Comprehensive error handler for chart generation services"""
    
    def __init__(self):
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "fallback_activations": 0,
            "retry_attempts": 0,
            "successful_retries": 0
        }
        
        # Default retry configurations by error type
        self.default_retry_configs = {
            ErrorCategory.AI_SERVICE: RetryConfig(max_attempts=3, base_delay=2.0),
            ErrorCategory.DATABASE: RetryConfig(max_attempts=2, base_delay=1.0),
            ErrorCategory.KAFKA: RetryConfig(max_attempts=2, base_delay=3.0),
            ErrorCategory.NETWORK: RetryConfig(max_attempts=4, base_delay=1.0),
            ErrorCategory.TIMEOUT: RetryConfig(max_attempts=2, base_delay=5.0),
            ErrorCategory.VALIDATION: RetryConfig(max_attempts=1),  # No retry for validation errors
            ErrorCategory.RESOURCE: RetryConfig(max_attempts=2, base_delay=10.0),
        }
    
    def categorize_error(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Categorize error for appropriate handling"""
        
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # AI service errors
        if any(term in error_message for term in ['gigachat', 'token', 'authentication', 'rate limit']):
            return ErrorCategory.AI_SERVICE
        
        # Database errors
        if any(term in error_message for term in ['database', 'connection', 'sqlalchemy', 'postgres']):
            return ErrorCategory.DATABASE
        
        # Kafka errors
        if any(term in error_message for term in ['kafka', 'broker', 'partition', 'consumer', 'producer']):
            return ErrorCategory.KAFKA
        
        # Network errors
        if any(term in error_message for term in ['network', 'connection', 'timeout', 'unreachable', 'dns']):
            return ErrorCategory.NETWORK
        
        # Timeout errors
        if 'timeout' in error_message or error_type in ['TimeoutError', 'asyncio.TimeoutError']:
            return ErrorCategory.TIMEOUT
        
        # Validation errors
        if any(term in error_message for term in ['validation', 'invalid', 'missing', 'required']):
            return ErrorCategory.VALIDATION
        
        # Resource errors
        if any(term in error_message for term in ['memory', 'resource', 'limit', 'capacity']):
            return ErrorCategory.RESOURCE
        
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, error: Exception, category: ErrorCategory, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on type and context"""
        
        # Critical errors that affect system functionality
        if category in [ErrorCategory.DATABASE, ErrorCategory.KAFKA] and context.attempt_number >= 2:
            return ErrorSeverity.CRITICAL
        
        # High severity for service failures
        if category == ErrorCategory.AI_SERVICE and context.attempt_number >= 2:
            return ErrorSeverity.HIGH
        
        # Medium severity for network issues
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for validation and known issues
        if category in [ErrorCategory.VALIDATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        fallback_function: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Handle error with appropriate strategy"""
        
        # Update error statistics
        self.error_stats["total_errors"] += 1
        
        # Categorize and assess severity
        category = self.categorize_error(error, context)
        severity = self.determine_severity(error, category, context)
        
        # Update category stats
        self.error_stats["errors_by_category"][category.value] = \
            self.error_stats["errors_by_category"].get(category.value, 0) + 1
        self.error_stats["errors_by_severity"][severity.value] = \
            self.error_stats["errors_by_severity"].get(severity.value, 0) + 1
        
        # Log error with context
        logger.error(
            f"Error in {context.operation} (attempt {context.attempt_number}/{context.max_attempts}): "
            f"{error} | Category: {category.value} | Severity: {severity.value} | Request: {context.request_id}"
        )
        
        # Determine if we should retry
        should_retry = self._should_retry(error, category, context)
        
        error_response = {
            \"success\": False,
            \"error\": str(error),
            \"error_category\": category.value,
            \"error_severity\": severity.value,
            \"request_id\": context.request_id,
            \"attempt_number\": context.attempt_number,
            \"should_retry\": should_retry,
            \"fallback_available\": fallback_function is not None
        }
        
        # Apply fallback if available and retry not appropriate
        if not should_retry and fallback_function:
            try:
                logger.info(f\"Applying fallback for {context.operation} - Request: {context.request_id}\")
                fallback_result = await self._execute_fallback(fallback_function, context)
                error_response[\"fallback_result\"] = fallback_result
                error_response[\"fallback_applied\"] = True
                self.error_stats[\"fallback_activations\"] += 1
            except Exception as fallback_error:
                logger.error(f\"Fallback failed for {context.operation}: {fallback_error}\")
                error_response[\"fallback_error\"] = str(fallback_error)
        
        return error_response
    
    def _should_retry(self, error: Exception, category: ErrorCategory, context: ErrorContext) -> bool:
        \"\"\"Determine if operation should be retried\"\"\"
        
        # Check if we've exceeded max attempts
        if context.attempt_number >= context.max_attempts:
            return False
        
        # Get retry config for this category
        retry_config = self.default_retry_configs.get(category, RetryConfig())
        
        # Never retry validation errors
        if category == ErrorCategory.VALIDATION:
            return False
        
        # Check if this exception type is retryable
        if retry_config.retryable_exceptions:
            if type(error) not in retry_config.retryable_exceptions:
                return False
        
        return True
    
    async def _execute_fallback(self, fallback_function: Callable, context: ErrorContext) -> Any:
        \"\"\"Execute fallback function with error handling\"\"\"
        
        if asyncio.iscoroutinefunction(fallback_function):
            return await fallback_function(context)
        else:
            return fallback_function(context)
    
    def get_retry_delay(self, attempt_number: int, category: ErrorCategory) -> float:
        \"\"\"Calculate delay before retry attempt\"\"\"
        
        retry_config = self.default_retry_configs.get(category, RetryConfig())
        
        # Exponential backoff
        delay = retry_config.base_delay * (retry_config.exponential_base ** (attempt_number - 1))
        delay = min(delay, retry_config.max_delay)
        
        # Add jitter to prevent thundering herd
        if retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def get_error_stats(self) -> Dict[str, Any]:
        \"\"\"Get error handling statistics\"\"\"
        return self.error_stats.copy()
    
    def reset_stats(self):
        \"\"\"Reset error statistics\"\"\"
        self.error_stats = {
            \"total_errors\": 0,
            \"errors_by_category\": {},
            \"errors_by_severity\": {},
            \"fallback_activations\": 0,
            \"retry_attempts\": 0,
            \"successful_retries\": 0
        }

def with_retry_and_fallback(
    max_attempts: int = 3,
    fallback_function: Optional[Callable] = None,
    operation_name: str = \"\"
):
    \"\"\"Decorator for automatic retry and fallback handling\"\"\"
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            context = ErrorContext(
                request_id=kwargs.get('request_id', 'unknown'),
                user_id=kwargs.get('user_id'),
                operation=operation_name or func.__name__,
                max_attempts=max_attempts
            )
            
            last_error = None
            
            for attempt in range(1, max_attempts + 1):
                context.attempt_number = attempt
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        error_handler.error_stats[\"successful_retries\"] += 1
                        logger.info(f\"Retry successful for {context.operation} on attempt {attempt}\")
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    error_handler.error_stats[\"retry_attempts\"] += 1
                    
                    # Handle error and check if we should retry
                    error_response = await error_handler.handle_error(e, context, fallback_function)
                    
                    if not error_response[\"should_retry\"] or attempt == max_attempts:
                        # If fallback was applied successfully, return the fallback result
                        if error_response.get(\"fallback_applied\") and \"fallback_result\" in error_response:
                            return error_response[\"fallback_result\"]
                        
                        # Otherwise, raise the last error
                        raise e
                    
                    # Wait before retry
                    category = ErrorCategory(error_response[\"error_category\"])
                    delay = error_handler.get_retry_delay(attempt, category)
                    logger.info(f\"Retrying {context.operation} in {delay:.2f} seconds (attempt {attempt + 1}/{max_attempts})\")
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            if last_error:
                raise last_error
                
        return wrapper
    return decorator

# Global error handler instance
error_handler = ChartErrorHandler()"