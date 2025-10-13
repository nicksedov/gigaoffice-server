"""
Response Formatter Service
Service for standardizing and formatting chart response outputs
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.models.api.chart import ChartResultResponse, ChartConfig
from app.models.types.enums import RequestStatus


class ResponseFormatterService:
    """Service for formatting chart responses into standardized JSON"""
    
    def format_response(
        self, 
        response: ChartResultResponse,
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        Format ChartResultResponse to standardized dictionary
        
        Args:
            response: ChartResultResponse object
            include_metadata: Whether to include formatting metadata
            
        Returns:
            Formatted dictionary representation
        """
        try:
            formatted = {
                'success': response.success,
                'status': response.status,
                'message': response.message,
                'chart_config': self.format_chart_config(response.chart_config) if response.chart_config else None,
                'tokens_used': response.tokens_used,
                'processing_time': response.processing_time
            }
            
            if include_metadata:
                formatted['_metadata'] = {
                    'formatted_at': datetime.now().isoformat(),
                    'has_chart': response.chart_config is not None
                }
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return self._create_error_dict(str(e))
    
    def format_chart_config(self, config: ChartConfig) -> Dict[str, Any]:
        """
        Format ChartConfig to dictionary
        
        Args:
            config: ChartConfig object
            
        Returns:
            Formatted dictionary representation
        """
        try:
            return {
                'chart_type': config.chart_type.value if hasattr(config.chart_type, 'value') else str(config.chart_type),
                'title': config.title,
                'subtitle': config.subtitle,
                'series_config': {
                    'x_axis_column': config.series_config.x_axis_column,
                    'y_axis_columns': config.series_config.y_axis_columns,
                    'series_names': config.series_config.series_names,
                    'show_data_labels': config.series_config.show_data_labels,
                    'smooth_lines': config.series_config.smooth_lines
                },
                'position': {
                    'x': config.position.x,
                    'y': config.position.y,
                    'width': config.position.width,
                    'height': config.position.height,
                    'anchor_cell': config.position.anchor_cell
                },
                'styling': {
                    'color_scheme': config.styling.color_scheme.value if hasattr(config.styling.color_scheme, 'value') else str(config.styling.color_scheme),
                    'font_family': config.styling.font_family,
                    'font_size': config.styling.font_size,
                    'background_color': config.styling.background_color,
                    'border_style': config.styling.border_style.value if hasattr(config.styling.border_style, 'value') else str(config.styling.border_style),
                    'legend_position': config.styling.legend_position.value if hasattr(config.styling.legend_position, 'value') else str(config.styling.legend_position)
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting chart config: {e}")
            return {}
    
    def serialize_to_json(
        self, 
        response: ChartResultResponse, 
        pretty: bool = False
    ) -> str:
        """
        Serialize ChartResultResponse to JSON string
        
        Args:
            response: ChartResultResponse object
            pretty: Whether to use pretty printing
            
        Returns:
            JSON string representation
        """
        try:
            formatted = self.format_response(response)
            
            if pretty:
                return json.dumps(formatted, ensure_ascii=False, indent=2)
            else:
                return json.dumps(formatted, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error serializing to JSON: {e}")
            return json.dumps(self._create_error_dict(str(e)))
    
    def format_error_response(
        self, 
        error: Exception,
        status: str = 'failed',
        include_traceback: bool = False
    ) -> ChartResultResponse:
        """
        Create formatted error response
        
        Args:
            error: Exception that occurred
            status: Status to set (default: 'failed')
            include_traceback: Whether to include stack trace in message
            
        Returns:
            ChartResultResponse with error information
        """
        error_message = str(error)
        
        if include_traceback:
            import traceback
            error_message += f"\n\nTraceback:\n{traceback.format_exc()}"
        
        return ChartResultResponse(
            success=False,
            status=status,
            message=f"Error generating chart: {error_message}",
            chart_config=None,
            tokens_used=0,
            processing_time=0.0
        )
    
    def format_success_response(
        self,
        chart_config: ChartConfig,
        tokens_used: int,
        processing_time: float,
        message: Optional[str] = None
    ) -> ChartResultResponse:
        """
        Create formatted success response
        
        Args:
            chart_config: Generated chart configuration
            tokens_used: Number of tokens used
            processing_time: Processing time in seconds
            message: Optional custom message
            
        Returns:
            ChartResultResponse with success information
        """
        return ChartResultResponse(
            success=True,
            status='completed',
            message=message or "Chart generated successfully",
            chart_config=chart_config,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
    
    def validate_json_structure(self, json_str: str) -> bool:
        """
        Validate that a JSON string has valid structure
        
        Args:
            json_str: JSON string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            data = json.loads(json_str)
            
            # Check required fields for ChartResultResponse
            required_fields = ['success', 'status', 'message']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"JSON missing required field: {field}")
                    return False
            
            # If success is true, chart_config should be present
            if data.get('success') and data.get('chart_config') is None:
                logger.warning("Successful response missing chart_config")
                return False
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON structure: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating JSON structure: {e}")
            return False
    
    def parse_ai_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """
        Parse AI-generated response string into structured dict
        
        Args:
            ai_response: Raw AI response string
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Try to extract JSON from response (handle cases where AI adds extra text)
            # Look for JSON object between curly braces
            import re
            
            # Find the first complete JSON object
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON found, try parsing the whole response
            return json.loads(ai_response)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"AI response was: {ai_response[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return None
    
    def create_response_from_dict(self, data: Dict[str, Any]) -> ChartResultResponse:
        """
        Create ChartResultResponse from dictionary (e.g., from AI output)
        
        Args:
            data: Dictionary with response data
            
        Returns:
            ChartResultResponse object
        """
        try:
            # Parse chart_config if present
            chart_config = None
            if data.get('chart_config'):
                chart_config = ChartConfig(**data['chart_config'])
            
            return ChartResultResponse(
                success=data.get('success', False),
                status=data.get('status', 'failed'),
                message=data.get('message', 'No message provided'),
                chart_config=chart_config,
                tokens_used=data.get('tokens_used', 0),
                processing_time=data.get('processing_time', 0.0)
            )
            
        except Exception as e:
            logger.error(f"Error creating response from dict: {e}")
            return self.format_error_response(e)
    
    def _create_error_dict(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error dictionary"""
        return {
            'success': False,
            'status': 'failed',
            'message': f"Formatting error: {error_message}",
            'chart_config': None,
            'tokens_used': 0,
            'processing_time': 0.0
        }
    
    def merge_responses(
        self, 
        responses: list[ChartResultResponse]
    ) -> Dict[str, Any]:
        """
        Merge multiple chart responses into summary
        
        Args:
            responses: List of ChartResultResponse objects
            
        Returns:
            Dictionary with merged summary
        """
        if not responses:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'responses': []
            }
        
        successful = sum(1 for r in responses if r.success)
        failed = len(responses) - successful
        
        total_tokens = sum(r.tokens_used or 0 for r in responses)
        total_time = sum(r.processing_time or 0.0 for r in responses)
        
        return {
            'total': len(responses),
            'successful': successful,
            'failed': failed,
            'total_tokens_used': total_tokens,
            'total_processing_time': total_time,
            'average_processing_time': total_time / len(responses) if responses else 0.0,
            'responses': [self.format_response(r) for r in responses]
        }


# Global instance
response_formatter_service = ResponseFormatterService()
