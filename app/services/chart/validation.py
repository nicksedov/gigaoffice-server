"""
Chart Validation Service
Service for validating chart configurations and responses
"""

from typing import Tuple, List, Dict, Any, Optional
from loguru import logger
from pydantic import ValidationError

from app.models.api.chart import (
    ChartResultResponse, ChartConfig, ChartPosition, 
    ChartStyling, SeriesConfig, ChartType, ChartData
)


class ChartValidationService:
    """Service for comprehensive validation of chart configurations and responses"""
    
    # R7-Office compatibility constraints
    R7_SUPPORTED_CHART_TYPES = {'line', 'column', 'pie', 'scatter', 'area'}
    R7_MAX_SERIES = 10
    R7_MIN_CHART_WIDTH = 100
    R7_MIN_CHART_HEIGHT = 100
    R7_MAX_CHART_WIDTH = 2000
    R7_MAX_CHART_HEIGHT = 1500
    
    def validate_response(self, response: ChartResultResponse) -> Tuple[bool, List[str]]:
        """
        Validate complete ChartResultResponse structure
        
        Args:
            response: ChartResultResponse object to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            # Validate required fields presence
            if response.success is None:
                errors.append("Field 'success' is required")
            
            if not response.status:
                errors.append("Field 'status' is required")
            
            if not response.message:
                errors.append("Field 'message' is required")
            
            # Validate status consistency
            valid_statuses = ['pending', 'processing', 'completed', 'failed']
            if response.status not in valid_statuses:
                errors.append(f"Invalid status '{response.status}'. Must be one of {valid_statuses}")
            
            # Validate success and chart_config consistency
            if response.success and response.chart_config is None:
                errors.append("Successful response must include chart_config")
            
            if response.success and response.status == 'failed':
                errors.append("Response cannot be successful with status 'failed'")
            
            if not response.success and response.status == 'completed':
                errors.append("Failed response cannot have status 'completed'")
            
            # Validate tokens_used
            if response.tokens_used is not None and response.tokens_used < 0:
                errors.append("tokens_used must be non-negative")
            
            # Validate processing_time
            if response.processing_time is not None and response.processing_time < 0:
                errors.append("processing_time must be non-negative")
            
            # Validate chart config if present
            if response.chart_config is not None:
                is_valid, config_errors = self.validate_chart_config(response.chart_config)
                if not is_valid:
                    errors.extend(config_errors)
            
        except Exception as e:
            logger.error(f"Error validating response: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Response validation failed with {len(errors)} errors")
        
        return is_valid, errors
    
    def validate_chart_config(self, config: ChartConfig) -> Tuple[bool, List[str]]:
        """
        Validate ChartConfig structure and business rules
        
        Args:
            config: ChartConfig object to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            # Validate chart type
            if not isinstance(config.chart_type, ChartType):
                errors.append(f"Invalid chart_type: {config.chart_type}")
            
            # Validate title
            if not config.title or len(config.title) == 0:
                errors.append("Chart title is required and cannot be empty")
            
            if len(config.title) > 200:
                errors.append("Chart title must not exceed 200 characters")
            
            # Validate subtitle if present
            if config.subtitle and len(config.subtitle) > 200:
                errors.append("Chart subtitle must not exceed 200 characters")
            
            # Validate series config
            is_valid, series_errors = self.validate_series_config(config.series_config)
            if not is_valid:
                errors.extend(series_errors)
            
            # Validate position
            is_valid, position_errors = self.validate_position(config.position)
            if not is_valid:
                errors.extend(position_errors)
            
            # Validate styling
            is_valid, styling_errors = self.validate_styling(config.styling)
            if not is_valid:
                errors.extend(styling_errors)
            
        except Exception as e:
            logger.error(f"Error validating chart config: {e}")
            errors.append(f"Chart config validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_series_config(
        self, 
        series: SeriesConfig,
        chart_data: Optional[ChartData] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate SeriesConfig structure
        
        Args:
            series: SeriesConfig object to validate
            chart_data: Optional ChartData to validate column indices against
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            # Validate x_axis_column
            if series.x_axis_column < 0:
                errors.append("x_axis_column must be non-negative")
            
            # Validate y_axis_columns
            if not series.y_axis_columns or len(series.y_axis_columns) == 0:
                errors.append("y_axis_columns must contain at least one column index")
            
            for idx, col in enumerate(series.y_axis_columns):
                if col < 0:
                    errors.append(f"y_axis_columns[{idx}] must be non-negative")
            
            # Check for duplicate column indices
            if len(series.y_axis_columns) != len(set(series.y_axis_columns)):
                errors.append("y_axis_columns contains duplicate indices")
            
            # Validate series_names if present
            if series.series_names:
                if len(series.series_names) != len(series.y_axis_columns):
                    errors.append(f"series_names length ({len(series.series_names)}) must match y_axis_columns length ({len(series.y_axis_columns)})")
            
            # Validate against chart_data if provided
            if chart_data:
                total_columns = len(chart_data.chart_data)
                
                if series.x_axis_column >= total_columns:
                    errors.append(f"x_axis_column ({series.x_axis_column}) exceeds available columns ({total_columns})")
                
                for col in series.y_axis_columns:
                    if col >= total_columns:
                        errors.append(f"y_axis_column ({col}) exceeds available columns ({total_columns})")
            
        except Exception as e:
            logger.error(f"Error validating series config: {e}")
            errors.append(f"Series config validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_position(self, position: ChartPosition) -> Tuple[bool, List[str]]:
        """
        Validate ChartPosition structure
        
        Args:
            position: ChartPosition object to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            # Validate x and y coordinates
            if position.x < 0:
                errors.append("Position x must be non-negative")
            
            if position.y < 0:
                errors.append("Position y must be non-negative")
            
            # Validate width and height
            if position.width < 100:
                errors.append("Chart width must be at least 100 pixels")
            
            if position.height < 100:
                errors.append("Chart height must be at least 100 pixels")
            
            if position.width > 2000:
                errors.append("Chart width must not exceed 2000 pixels")
            
            if position.height > 1500:
                errors.append("Chart height must not exceed 1500 pixels")
            
            # Validate anchor_cell format if present
            if position.anchor_cell:
                # Basic validation: should be like "A1", "B10", etc.
                import re
                if not re.match(r'^[A-Z]+\d+$', position.anchor_cell):
                    errors.append(f"Invalid anchor_cell format: {position.anchor_cell}. Expected format like 'A1', 'B10'")
            
        except Exception as e:
            logger.error(f"Error validating position: {e}")
            errors.append(f"Position validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_styling(self, styling: ChartStyling) -> Tuple[bool, List[str]]:
        """
        Validate ChartStyling structure
        
        Args:
            styling: ChartStyling object to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            # Validate font_size
            if styling.font_size < 8:
                errors.append("Font size must be at least 8")
            
            if styling.font_size > 72:
                errors.append("Font size must not exceed 72")
            
            # Validate font_family
            if not styling.font_family or len(styling.font_family) == 0:
                errors.append("Font family is required")
            
            # Validate background_color format if present
            if styling.background_color:
                import re
                if not re.match(r'^#[0-9A-Fa-f]{6}$', styling.background_color):
                    errors.append(f"Invalid background_color format: {styling.background_color}. Expected hex format like '#FF0000'")
            
        except Exception as e:
            logger.error(f"Error validating styling: {e}")
            errors.append(f"Styling validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_r7_office_compatibility(self, config: ChartConfig) -> Tuple[bool, List[str]]:
        """
        Validate R7-Office specific compatibility requirements
        
        Args:
            config: ChartConfig object to validate
            
        Returns:
            Tuple of (is_compatible, list of warning messages)
        """
        warnings = []
        
        try:
            # Check chart type compatibility
            if config.chart_type.value not in self.R7_SUPPORTED_CHART_TYPES:
                warnings.append(f"Chart type '{config.chart_type.value}' may not be fully supported by R7-Office")
            
            # Check series count
            if len(config.series_config.y_axis_columns) > self.R7_MAX_SERIES:
                warnings.append(f"Number of series ({len(config.series_config.y_axis_columns)}) exceeds R7-Office recommended maximum ({self.R7_MAX_SERIES})")
            
            # Check chart dimensions
            if config.position.width < self.R7_MIN_CHART_WIDTH:
                warnings.append(f"Chart width ({config.position.width}) is below R7-Office minimum ({self.R7_MIN_CHART_WIDTH})")
            
            if config.position.height < self.R7_MIN_CHART_HEIGHT:
                warnings.append(f"Chart height ({config.position.height}) is below R7-Office minimum ({self.R7_MIN_CHART_HEIGHT})")
            
            if config.position.width > self.R7_MAX_CHART_WIDTH:
                warnings.append(f"Chart width ({config.position.width}) exceeds R7-Office maximum ({self.R7_MAX_CHART_WIDTH})")
            
            if config.position.height > self.R7_MAX_CHART_HEIGHT:
                warnings.append(f"Chart height ({config.position.height}) exceeds R7-Office maximum ({self.R7_MAX_CHART_HEIGHT})")
            
            # Check for unsupported features
            if config.series_config.smooth_lines and config.chart_type.value not in ['line', 'area']:
                warnings.append(f"Smooth lines are only supported for line and area charts in R7-Office")
            
        except Exception as e:
            logger.error(f"Error validating R7-Office compatibility: {e}")
            warnings.append(f"R7-Office compatibility check error: {str(e)}")
        
        is_compatible = len(warnings) == 0
        
        if warnings:
            logger.info(f"R7-Office compatibility check found {len(warnings)} warnings")
        
        return is_compatible, warnings
    
    def get_validation_summary(self, response: ChartResultResponse) -> Dict[str, Any]:
        """
        Get comprehensive validation summary for a response
        
        Args:
            response: ChartResultResponse object to validate
            
        Returns:
            Dictionary with validation summary
        """
        summary = {
            'is_valid': False,
            'is_r7_office_compatible': False,
            'validation_errors': [],
            'compatibility_warnings': [],
            'response_structure': {
                'has_success': response.success is not None,
                'has_status': bool(response.status),
                'has_message': bool(response.message),
                'has_chart_config': response.chart_config is not None,
                'has_tokens_used': response.tokens_used is not None,
                'has_processing_time': response.processing_time is not None
            }
        }
        
        # Validate response structure
        is_valid, errors = self.validate_response(response)
        summary['is_valid'] = is_valid
        summary['validation_errors'] = errors
        
        # Validate R7-Office compatibility if chart config present
        if response.chart_config:
            is_compatible, warnings = self.validate_r7_office_compatibility(response.chart_config)
            summary['is_r7_office_compatible'] = is_compatible
            summary['compatibility_warnings'] = warnings
        else:
            summary['is_r7_office_compatible'] = True  # No chart to check
        
        return summary
    
    def validate_chart_data(self, chart_data: ChartData) -> Tuple[bool, List[str]]:
        """
        Validate input chart data structure
        
        Args:
            chart_data: ChartData object to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            # Validate data_range
            if not chart_data.data_range:
                errors.append("data_range is required")
            
            # Validate chart_data series
            if not chart_data.chart_data or len(chart_data.chart_data) == 0:
                errors.append("chart_data must contain at least one series")
            
            # Validate each series
            for idx, series in enumerate(chart_data.chart_data):
                if not series.name:
                    errors.append(f"Series {idx}: name is required")
                
                if not series.values or len(series.values) == 0:
                    errors.append(f"Series {idx}: values cannot be empty")
            
            # Check that all series have same length
            if chart_data.chart_data:
                lengths = [len(series.values) for series in chart_data.chart_data]
                if len(set(lengths)) > 1:
                    errors.append(f"All series must have the same number of values. Found: {lengths}")
            
        except Exception as e:
            logger.error(f"Error validating chart data: {e}")
            errors.append(f"Chart data validation error: {str(e)}")
        
        is_valid = len(errors) == 0
        return is_valid, errors


# Global instance
chart_validation_service = ChartValidationService()
