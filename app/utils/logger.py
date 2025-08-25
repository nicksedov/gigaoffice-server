"""
Structured Logger Utility
Enhanced logging configuration with structured output and performance tracking
"""

import sys
import time
from typing import Optional, Dict, Any, Union
from pathlib import Path
from loguru import logger
from contextlib import contextmanager

from ..core.config import get_settings


class StructuredLogger:
    """Enhanced structured logger with performance tracking and context management"""
    
    def __init__(self):
        self.settings = get_settings()
        self._setup_logger()
        self._request_contexts = {}
    
    def _setup_logger(self):
        """Configure loguru logger with structured output"""
        # Remove default handler
        logger.remove()
        
        # Console handler with custom format
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stderr,
            format=console_format,
            level=self.settings.log_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
        
        # File handler if configured
        if self.settings.log_file:
            log_path = Path(self.settings.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{extra} | "
                "{message}"
            )
            
            logger.add(
                log_path,
                format=file_format,
                level=self.settings.log_level,
                rotation="100 MB",
                retention="30 days",
                compression="gz",
                serialize=False,
                backtrace=True,
                diagnose=True
            )
    
    def log_api_request(self, endpoint: str, method: str, duration: float, 
                       status_code: int, user_id: Optional[str] = None,
                       request_id: Optional[str] = None, **kwargs):
        """
        Log API request with structured data
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            duration: Request duration in seconds
            status_code: HTTP status code
            user_id: User identifier
            request_id: Request identifier
            **kwargs: Additional context data
        """
        extra_data = {
            "type": "api_request",
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status_code": status_code,
            "user_id": user_id,
            "request_id": request_id,
            **kwargs
        }
        
        level = "INFO"
        if status_code >= 500:
            level = "ERROR"
        elif status_code >= 400:
            level = "WARNING"
        
        logger.bind(**extra_data).log(
            level,
            f"{method} {endpoint} - {status_code} - {duration:.3f}s"
        )
    
    def log_service_call(self, service: str, method: str, duration: float,
                        success: bool, **kwargs):
        """
        Log service call with performance data
        
        Args:
            service: Service name
            method: Method name
            duration: Call duration in seconds
            success: Whether call succeeded
            **kwargs: Additional context data
        """
        extra_data = {
            "type": "service_call",
            "service": service,
            "method": method,
            "duration": duration,
            "success": success,
            **kwargs
        }
        
        level = "INFO" if success else "ERROR"
        status = "SUCCESS" if success else "FAILED"
        
        logger.bind(**extra_data).log(
            level,
            f"{service}.{method} - {status} - {duration:.3f}s"
        )
    
    def log_database_operation(self, operation: str, table: str, duration: float,
                              affected_rows: Optional[int] = None, **kwargs):
        """
        Log database operation
        
        Args:
            operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
            table: Table name
            duration: Operation duration in seconds
            affected_rows: Number of affected rows
            **kwargs: Additional context data
        """
        extra_data = {
            "type": "database_operation",
            "operation": operation,
            "table": table,
            "duration": duration,
            "affected_rows": affected_rows,
            **kwargs
        }
        
        logger.bind(**extra_data).info(
            f"DB {operation} {table} - {duration:.3f}s - {affected_rows or 0} rows"
        )
    
    def log_kafka_message(self, topic: str, operation: str, message_id: Optional[str] = None,
                         duration: Optional[float] = None, success: bool = True, **kwargs):
        """
        Log Kafka message processing
        
        Args:
            topic: Kafka topic
            operation: Operation (produce, consume, process)
            message_id: Message identifier
            duration: Processing duration
            success: Whether operation succeeded
            **kwargs: Additional context data
        """
        extra_data = {
            "type": "kafka_message",
            "topic": topic,
            "operation": operation,
            "message_id": message_id,
            "duration": duration,
            "success": success,
            **kwargs
        }
        
        level = "INFO" if success else "ERROR"
        status = "SUCCESS" if success else "FAILED"
        
        message = f"Kafka {operation} {topic}"
        if message_id:
            message += f" - {message_id}"
        if duration:
            message += f" - {duration:.3f}s"
        message += f" - {status}"
        
        logger.bind(**extra_data).log(level, message)
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                  request_id: Optional[str] = None):
        """
        Log error with context information
        
        Args:
            error: Exception instance
            context: Additional context data
            request_id: Request identifier
        """
        extra_data = {
            "type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "request_id": request_id,
            **(context or {})
        }
        
        logger.bind(**extra_data).error(f"Error: {error}")
    
    def log_performance_metric(self, metric_name: str, value: Union[float, int],
                              unit: str = "ms", **kwargs):
        """
        Log performance metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            **kwargs: Additional context data
        """
        extra_data = {
            "type": "performance_metric",
            "metric": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": time.time(),
            **kwargs
        }
        
        logger.bind(**extra_data).info(f"METRIC {metric_name}: {value}{unit}")
    
    def log_audit_event(self, action: str, user_id: Optional[str] = None,
                       resource: Optional[str] = None, result: str = "success",
                       **kwargs):
        """
        Log audit event for security tracking
        
        Args:
            action: Action performed
            user_id: User identifier
            resource: Resource accessed
            result: Action result (success, failed, denied)
            **kwargs: Additional context data
        """
        extra_data = {
            "type": "audit_event",
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "result": result,
            "timestamp": time.time(),
            **kwargs
        }
        
        level = "WARNING" if result in ["failed", "denied"] else "INFO"
        
        logger.bind(**extra_data).log(
            level,
            f"AUDIT {action} - {user_id or 'anonymous'} - {resource or 'unknown'} - {result}"
        )
    
    @contextmanager
    def performance_timer(self, operation: str, **context):
        """
        Context manager for timing operations
        
        Args:
            operation: Operation name
            **context: Additional context data
        """
        start_time = time.time()
        success = True
        error = None
        
        try:
            yield
        except Exception as e:
            success = False
            error = e
            raise
        finally:
            duration = time.time() - start_time
            
            extra_data = {
                "type": "performance_timer",
                "operation": operation,
                "duration": duration,
                "success": success,
                **context
            }
            
            if error:
                extra_data["error"] = str(error)
            
            level = "INFO" if success else "ERROR"
            status = "SUCCESS" if success else "FAILED"
            
            logger.bind(**extra_data).log(
                level,
                f"TIMER {operation} - {duration:.3f}s - {status}"
            )
    
    def set_request_context(self, request_id: str, **context):
        """
        Set context for a request
        
        Args:
            request_id: Request identifier
            **context: Context data
        """
        self._request_contexts[request_id] = {
            "request_id": request_id,
            "start_time": time.time(),
            **context
        }
    
    def get_request_context(self, request_id: str) -> Dict[str, Any]:
        """Get context for a request"""
        return self._request_contexts.get(request_id, {})
    
    def clear_request_context(self, request_id: str):
        """Clear context for a request"""
        if request_id in self._request_contexts:
            del self._request_contexts[request_id]


# Global logger instance
structured_logger = StructuredLogger()


# Convenience functions
def log_api_request(*args, **kwargs):
    """Log API request"""
    structured_logger.log_api_request(*args, **kwargs)


def log_service_call(*args, **kwargs):
    """Log service call"""
    structured_logger.log_service_call(*args, **kwargs)


def log_error(*args, **kwargs):
    """Log error"""
    structured_logger.log_error(*args, **kwargs)


def performance_timer(*args, **kwargs):
    """Performance timing context manager"""
    return structured_logger.performance_timer(*args, **kwargs)