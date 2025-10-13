"""
Chart Response Validation Middleware
Middleware for automatic validation of chart generation responses
"""

import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

from app.services.chart.validation import chart_validation_service
from app.services.chart.formatter import response_formatter_service
from app.models.api.chart import ChartResultResponse


class ChartResponseValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate chart generation responses before returning to client"""
    
    def __init__(self, app, validate_enabled: bool = True):
        """
        Initialize the middleware
        
        Args:
            app: FastAPI application
            validate_enabled: Whether to enable validation (can disable for testing)
        """
        super().__init__(app)
        self.validate_enabled = validate_enabled
        self.chart_endpoints = [
            "/api/v1/charts/result/",
            "/api/v1/charts/generate"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch middleware to validate chart responses
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with validation applied
        """
        # Get response from next handler
        response = await call_next(request)
        
        # Only validate chart-related endpoints
        if not self.validate_enabled or not self._is_chart_endpoint(request.url.path):
            return response
        
        # Only validate successful responses (200-299)
        if response.status_code < 200 or response.status_code >= 300:
            return response
        
        # Only validate JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response
        
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            if not body:
                return response
            
            # Parse JSON
            response_data = json.loads(body.decode())
            
            # Validate if it's a ChartResultResponse
            if self._is_chart_result_response(response_data):
                validated_data = await self._validate_chart_response(response_data, request)
                
                # Create new response with validated data
                return JSONResponse(
                    content=validated_data,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            # Return original response if not a chart result
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except Exception as e:
            logger.error(f"Error in chart response validation middleware: {e}")
            # Return original response on error
            return response
    
    def _is_chart_endpoint(self, path: str) -> bool:
        """Check if the request path is a chart-related endpoint"""
        return any(endpoint in path for endpoint in self.chart_endpoints)
    
    def _is_chart_result_response(self, data: dict) -> bool:
        """Check if response data matches ChartResultResponse structure"""
        required_fields = ['success', 'status', 'message']
        return all(field in data for field in required_fields)
    
    async def _validate_chart_response(
        self, 
        response_data: dict,
        request: Request
    ) -> dict:
        """
        Validate chart response data
        
        Args:
            response_data: Response data to validate
            request: Original request
            
        Returns:
            Validated (and potentially modified) response data
        """
        try:
            # Create ChartResultResponse object for validation
            chart_response = response_formatter_service.create_response_from_dict(response_data)
            
            # Perform validation
            validation_summary = chart_validation_service.get_validation_summary(chart_response)
            
            # Log validation results
            if not validation_summary['is_valid']:
                logger.warning(
                    f"Chart response validation failed for {request.url.path}: "
                    f"{validation_summary['validation_errors']}"
                )
            
            if not validation_summary['is_r7_office_compatible']:
                logger.info(
                    f"Chart response has R7-Office compatibility warnings for {request.url.path}: "
                    f"{validation_summary['compatibility_warnings']}"
                )
            
            # Add validation metadata to response
            response_data['_validation'] = {
                'is_valid': validation_summary['is_valid'],
                'is_r7_office_compatible': validation_summary['is_r7_office_compatible'],
                'has_errors': len(validation_summary['validation_errors']) > 0,
                'has_warnings': len(validation_summary['compatibility_warnings']) > 0
            }
            
            # Only include detailed errors in non-production environments
            # (In production, you might want to filter this based on environment variable)
            if validation_summary['validation_errors']:
                response_data['_validation']['errors'] = validation_summary['validation_errors']
            
            if validation_summary['compatibility_warnings']:
                response_data['_validation']['warnings'] = validation_summary['compatibility_warnings']
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error validating chart response: {e}")
            # Return original data if validation fails
            return response_data


class ChartResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log chart generation requests and responses for debugging"""
    
    def __init__(self, app, logging_enabled: bool = True):
        """
        Initialize the logging middleware
        
        Args:
            app: FastAPI application
            logging_enabled: Whether to enable logging
        """
        super().__init__(app)
        self.logging_enabled = logging_enabled
        self.chart_endpoints = [
            "/api/v1/charts/generate",
            "/api/v1/charts/result/",
            "/api/v1/charts/status/"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch middleware to log chart requests/responses
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response (unchanged)
        """
        if not self.logging_enabled or not self._is_chart_endpoint(request.url.path):
            return await call_next(request)
        
        # Log request
        logger.info(f"Chart Request: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response status
        logger.info(
            f"Chart Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code}"
        )
        
        return response
    
    def _is_chart_endpoint(self, path: str) -> bool:
        """Check if the request path is a chart-related endpoint"""
        return any(endpoint in path for endpoint in self.chart_endpoints)
