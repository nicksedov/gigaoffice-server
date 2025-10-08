"""
Error Handling Service Tests
Tests for comprehensive error handling and retry mechanisms
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from app.services.error_handling import (
    ChartErrorHandler, ErrorCategory, ErrorSeverity, ErrorContext,
    with_retry_and_fallback, error_handler
)

class TestChartErrorHandler:
    """Test Chart Error Handler"""
    
    def setup_method(self):
        """Setup test method"""
        self.handler = ChartErrorHandler()
        self.handler.reset_stats()  # Start with clean stats
    
    def test_categorize_error_ai_service(self):
        """Test AI service error categorization"""
        context = ErrorContext(request_id="test123", operation="test_op")
        
        # GigaChat error
        error = Exception("GigaChat authentication failed")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.AI_SERVICE
        
        # Token error
        error = Exception("Token limit exceeded")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.AI_SERVICE
    
    def test_categorize_error_database(self):
        """Test database error categorization"""
        context = ErrorContext(request_id="test123", operation="test_op")
        
        error = Exception("Database connection failed")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.DATABASE
        
        error = Exception("SQLAlchemy error occurred")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.DATABASE
    
    def test_categorize_error_kafka(self):
        """Test Kafka error categorization"""
        context = ErrorContext(request_id="test123", operation="test_op")
        
        error = Exception("Kafka broker connection failed")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.KAFKA
        
        error = Exception("Producer send failed")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.KAFKA
    
    def test_categorize_error_validation(self):
        """Test validation error categorization"""
        context = ErrorContext(request_id="test123", operation="test_op")
        
        error = Exception("Validation failed: missing required field")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.VALIDATION
        
        error = Exception("Invalid input data")
        category = self.handler.categorize_error(error, context)
        assert category == ErrorCategory.VALIDATION
    
    def test_determine_severity(self):
        """Test error severity determination"""
        context = ErrorContext(request_id="test123", operation="test_op", attempt_number=1)
        
        # Critical database error on retry
        context.attempt_number = 2
        severity = self.handler.determine_severity(
            Exception("Database error"), ErrorCategory.DATABASE, context
        )
        assert severity == ErrorSeverity.CRITICAL
        
        # High AI service error on retry
        severity = self.handler.determine_severity(
            Exception("AI error"), ErrorCategory.AI_SERVICE, context
        )
        assert severity == ErrorSeverity.HIGH
        
        # Low validation error
        severity = self.handler.determine_severity(
            Exception("Validation error"), ErrorCategory.VALIDATION, context
        )
        assert severity == ErrorSeverity.LOW
    
    @pytest.mark.asyncio
    async def test_handle_error_without_fallback(self):
        """Test error handling without fallback"""
        context = ErrorContext(request_id="test123", operation="test_op")
        error = Exception("Test error")
        
        response = await self.handler.handle_error(error, context)
        
        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["request_id"] == "test123"
        assert response["error_category"] == ErrorCategory.UNKNOWN.value
        assert response["fallback_available"] is False
        assert self.handler.error_stats["total_errors"] == 1
    
    @pytest.mark.asyncio
    async def test_handle_error_with_fallback(self):
        """Test error handling with fallback"""
        async def test_fallback(context):
            return {"fallback_result": "success"}
        
        context = ErrorContext(request_id="test123", operation="test_op")
        error = Exception("Test error")
        
        response = await self.handler.handle_error(error, context, test_fallback)
        
        assert response["success"] is False
        assert response["fallback_applied"] is True
        assert response["fallback_result"]["fallback_result"] == "success"
        assert self.handler.error_stats["fallback_activations"] == 1
    
    @pytest.mark.asyncio
    async def test_handle_error_fallback_failure(self):
        """Test error handling when fallback fails"""
        async def failing_fallback(context):
            raise Exception("Fallback failed")
        
        context = ErrorContext(request_id="test123", operation="test_op")
        error = Exception("Test error")
        
        response = await self.handler.handle_error(error, context, failing_fallback)
        
        assert response["success"] is False
        assert "fallback_error" in response
        assert response["fallback_error"] == "Fallback failed"
    
    def test_should_retry_validation_error(self):
        """Test retry decision for validation errors"""
        context = ErrorContext(request_id="test123", operation="test_op", attempt_number=1, max_attempts=3)
        error = Exception("Validation error")
        
        should_retry = self.handler._should_retry(error, ErrorCategory.VALIDATION, context)
        assert should_retry is False  # Never retry validation errors
    
    def test_should_retry_max_attempts(self):
        """Test retry decision when max attempts reached"""
        context = ErrorContext(request_id="test123", operation="test_op", attempt_number=3, max_attempts=3)
        error = Exception("Network error")
        
        should_retry = self.handler._should_retry(error, ErrorCategory.NETWORK, context)
        assert should_retry is False
    
    def test_should_retry_retryable_error(self):
        """Test retry decision for retryable errors"""
        context = ErrorContext(request_id="test123", operation="test_op", attempt_number=1, max_attempts=3)
        error = Exception("Network timeout")
        
        should_retry = self.handler._should_retry(error, ErrorCategory.NETWORK, context)
        assert should_retry is True
    
    def test_get_retry_delay(self):
        """Test retry delay calculation"""
        # First attempt
        delay = self.handler.get_retry_delay(1, ErrorCategory.NETWORK)
        assert delay >= 0.5 and delay <= 1.5  # Base delay with jitter
        
        # Second attempt (exponential backoff)
        delay = self.handler.get_retry_delay(2, ErrorCategory.NETWORK)
        assert delay >= 1.0 and delay <= 3.0
        
        # Large attempt (should be capped at max_delay)
        delay = self.handler.get_retry_delay(10, ErrorCategory.NETWORK)
        assert delay <= 60.0  # Max delay
    
    def test_get_error_stats(self):
        """Test error statistics retrieval"""
        # Record some errors
        self.handler.error_stats["total_errors"] = 5
        self.handler.error_stats["errors_by_category"]["network"] = 3
        self.handler.error_stats["fallback_activations"] = 2
        
        stats = self.handler.get_error_stats()
        
        assert stats["total_errors"] == 5
        assert stats["errors_by_category"]["network"] == 3
        assert stats["fallback_activations"] == 2
    
    def test_reset_stats(self):
        """Test statistics reset"""
        # Add some stats
        self.handler.error_stats["total_errors"] = 10
        self.handler.error_stats["errors_by_category"]["ai_service"] = 5
        
        self.handler.reset_stats()
        
        assert self.handler.error_stats["total_errors"] == 0
        assert len(self.handler.error_stats["errors_by_category"]) == 0

class TestRetryDecorator:
    """Test retry decorator functionality"""
    
    def setup_method(self):
        """Setup test method"""
        error_handler.reset_stats()
        self.call_count = 0
    
    @pytest.mark.asyncio
    async def test_successful_function_no_retry(self):
        """Test successful function execution without retry"""
        
        @with_retry_and_fallback(max_attempts=3, operation_name="test_function")
        async def successful_function(request_id="test"):
            self.call_count += 1
            return "success"
        
        result = await successful_function()
        
        assert result == "success"
        assert self.call_count == 1
    
    @pytest.mark.asyncio
    async def test_function_with_retry_success(self):
        """Test function that fails then succeeds"""
        
        @with_retry_and_fallback(max_attempts=3, operation_name="test_function")
        async def retry_then_success(request_id="test"):
            self.call_count += 1
            if self.call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await retry_then_success()
        
        assert result == "success"
        assert self.call_count == 3
        assert error_handler.error_stats["successful_retries"] == 1
    
    @pytest.mark.asyncio
    async def test_function_with_max_retries_exceeded(self):
        """Test function that fails all retry attempts"""
        
        @with_retry_and_fallback(max_attempts=2, operation_name="test_function")
        async def always_fail(request_id="test"):
            self.call_count += 1
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception, match="Persistent failure"):
            await always_fail()
        
        assert self.call_count == 2
    
    @pytest.mark.asyncio
    async def test_function_with_fallback(self):
        """Test function with fallback mechanism"""
        
        async def fallback_function(context):
            return "fallback_result"
        
        @with_retry_and_fallback(
            max_attempts=2, 
            operation_name="test_function",
            fallback_function=fallback_function
        )
        async def always_fail(request_id="test"):
            self.call_count += 1
            raise Exception("Persistent failure")
        
        result = await always_fail()
        
        assert result == "fallback_result"
        assert self.call_count == 2
    
    @pytest.mark.asyncio
    async def test_sync_function_with_retry(self):
        """Test synchronous function with retry"""
        
        @with_retry_and_fallback(max_attempts=3, operation_name="test_sync_function")
        def sync_retry_function(request_id="test"):
            self.call_count += 1
            if self.call_count < 2:
                raise Exception("Temporary failure")
            return "sync_success"
        
        result = await sync_retry_function()
        
        assert result == "sync_success"
        assert self.call_count == 2
    
    @pytest.mark.asyncio
    async def test_validation_error_no_retry(self):
        """Test that validation errors are not retried"""
        
        @with_retry_and_fallback(max_attempts=3, operation_name="test_function")
        async def validation_error_function(request_id="test"):
            self.call_count += 1
            raise Exception("Validation failed: invalid input")
        
        with pytest.raises(Exception, match="Validation failed"):
            await validation_error_function()
        
        assert self.call_count == 1  # No retry for validation errors
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry timing with exponential backoff"""
        import time
        
        start_time = time.time()
        
        @with_retry_and_fallback(max_attempts=3, operation_name="test_function")
        async def timing_test_function(request_id="test"):
            self.call_count += 1
            if self.call_count < 3:
                raise Exception("Network timeout")
            return "success"
        
        result = await timing_test_function()
        
        elapsed_time = time.time() - start_time
        assert result == "success"
        assert self.call_count == 3
        # Should have some delay due to retries (at least 1 second total)
        assert elapsed_time >= 1.0

class TestErrorContext:
    """Test ErrorContext functionality"""
    
    def test_error_context_creation(self):
        """Test error context creation"""
        context = ErrorContext(
            request_id="test123",
            user_id=456,
            operation="test_operation",
            attempt_number=2,
            max_attempts=3,
            additional_data={"key": "value"}
        )
        
        assert context.request_id == "test123"
        assert context.user_id == 456
        assert context.operation == "test_operation"
        assert context.attempt_number == 2
        assert context.max_attempts == 3
        assert context.additional_data["key"] == "value"
    
    def test_error_context_defaults(self):
        """Test error context with default values"""
        context = ErrorContext(request_id="test123")
        
        assert context.request_id == "test123"
        assert context.user_id is None
        assert context.operation == ""
        assert context.attempt_number == 1
        assert context.max_attempts == 3
        assert context.additional_data is None