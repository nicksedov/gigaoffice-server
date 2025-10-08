"""
Chart Validation Service
Service for validating chart configurations and R7-Office compatibility
"""

import re
from typing import List, Tuple, Dict, Any, Optional
from loguru import logger

from app.models.api.chart import (
    ChartConfig, ChartType, ColorScheme, LegendPosition, BorderStyle,
    ChartPosition, ChartStyling, SeriesConfig, DataSource
)

class ChartValidationService:
    """Service for validating chart configurations"""
    
    def __init__(self):
        self.r7_office_supported_chart_types = {
            ChartType.COLUMN, ChartType.LINE, ChartType.PIE, ChartType.AREA,
            ChartType.SCATTER, ChartType.BAR, ChartType.DOUGHNUT
        }
        
        self.r7_office_max_dimensions = {
            "max_width": 2000,
            "max_height": 1500,
            "min_width": 100,
            "min_height": 100
        }
        
        self.r7_office_supported_fonts = {
            "Arial", "Times New Roman", "Calibri", "Tahoma", "Verdana"
        }
    
    def validate_chart_config(self, chart_config: ChartConfig) -> Tuple[bool, List[str]]:
        """Validate complete chart configuration"""
        
        errors = []
        
        try:
            # Validate chart type
            type_errors = self._validate_chart_type(chart_config.chart_type)
            errors.extend(type_errors)
            
            # Validate data range
            range_errors = self._validate_data_range(chart_config.data_range)
            errors.extend(range_errors)
            
            # Validate series configuration
            series_errors = self._validate_series_config(chart_config.series_config)
            errors.extend(series_errors)
            
            # Validate position
            position_errors = self._validate_position(chart_config.position)
            errors.extend(position_errors)
            
            # Validate styling
            styling_errors = self._validate_styling(chart_config.styling)
            errors.extend(styling_errors)
            
            # Validate title
            title_errors = self._validate_title(chart_config.title)
            errors.extend(title_errors)
            
        except Exception as e:
            logger.error(f"Error during chart validation: {e}")
            errors.append(f"Validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def validate_r7_office_compatibility(self, chart_config: ChartConfig) -> Tuple[bool, List[str]]:
        """Validate R7-Office API compatibility"""
        
        warnings = []
        
        try:
            # Check chart type support
            if chart_config.chart_type not in self.r7_office_supported_chart_types:
                warnings.append(f"Chart type '{chart_config.chart_type.value}' may not be fully supported in R7-Office")
            
            # Check dimensions
            pos = chart_config.position
            if pos.width > self.r7_office_max_dimensions["max_width"]:
                warnings.append(f"Chart width {pos.width}px exceeds R7-Office maximum of {self.r7_office_max_dimensions['max_width']}px")
            
            if pos.height > self.r7_office_max_dimensions["max_height"]:
                warnings.append(f"Chart height {pos.height}px exceeds R7-Office maximum of {self.r7_office_max_dimensions['max_height']}px")
            
            # Check font compatibility
            if chart_config.styling.font_family not in self.r7_office_supported_fonts:
                warnings.append(f"Font '{chart_config.styling.font_family}' may not be available in R7-Office")
            
            # Check color scheme
            if chart_config.styling.color_scheme == ColorScheme.CUSTOM and not chart_config.styling.custom_colors:
                warnings.append("Custom color scheme selected but no custom colors provided")
            
            # Validate R7-Office specific properties
            r7_props = chart_config.r7_office_properties
            if r7_props:
                prop_warnings = self._validate_r7_office_properties(r7_props)
                warnings.extend(prop_warnings)
                
        except Exception as e:
            logger.error(f"Error during R7-Office compatibility check: {e}")
            warnings.append(f"Compatibility check error: {str(e)}")
        
        # No compatibility issues if no warnings
        return len(warnings) == 0, warnings
    
    def _validate_chart_type(self, chart_type: ChartType) -> List[str]:
        """Validate chart type"""
        errors = []
        
        if not isinstance(chart_type, ChartType):
            errors.append("Invalid chart type")
        
        return errors
    
    def _validate_data_range(self, data_range: str) -> List[str]:
        """Validate R7-Office data range format"""
        errors = []
        
        if not data_range:
            errors.append("Data range cannot be empty")
            return errors
        
        # Basic validation for cell range format (A1:B10)
        range_pattern = r'^[A-Z]+\d+:[A-Z]+\d+$'
        if not re.match(range_pattern, data_range):
            errors.append(f"Data range '{data_range}' is not in valid R7-Office format (e.g., A1:B10)")
        
        # Additional validation
        try:
            if ':' not in data_range:
                errors.append("Data range must contain start and end cells separated by ':'")
            else:
                start_cell, end_cell = data_range.split(':')
                if not self._is_valid_cell_reference(start_cell):
                    errors.append(f"Invalid start cell reference: {start_cell}")
                if not self._is_valid_cell_reference(end_cell):
                    errors.append(f"Invalid end cell reference: {end_cell}")
        except Exception:
            errors.append(f"Invalid data range format: {data_range}")
        
        return errors
    
    def _is_valid_cell_reference(self, cell_ref: str) -> bool:
        """Check if cell reference is valid (e.g., A1, Z10)"""
        if not cell_ref:
            return False
        
        # Must start with letters, end with numbers
        pattern = r'^[A-Z]+\d+$'
        return bool(re.match(pattern, cell_ref))
    
    def _validate_series_config(self, series_config: SeriesConfig) -> List[str]:
        """Validate series configuration"""
        errors = []
        
        # Validate axis columns
        if series_config.x_axis_column < 0:
            errors.append("X-axis column index cannot be negative")
        
        if not series_config.y_axis_columns:
            errors.append("At least one Y-axis column must be specified")
        
        for y_col in series_config.y_axis_columns:
            if y_col < 0:
                errors.append(f"Y-axis column index {y_col} cannot be negative")
        
        # Check for duplicate axis columns
        all_columns = [series_config.x_axis_column] + series_config.y_axis_columns
        if len(all_columns) != len(set(all_columns)):
            errors.append("Column indices cannot be duplicated between X and Y axes")
        
        # Validate series names if provided
        if series_config.series_names:
            if len(series_config.series_names) != len(series_config.y_axis_columns):
                errors.append("Number of series names must match number of Y-axis columns")
        
        return errors
    
    def _validate_position(self, position: ChartPosition) -> List[str]:
        """Validate chart position and dimensions"""
        errors = []
        
        # Check for negative values
        if position.x < 0:
            errors.append("Chart X position cannot be negative")
        
        if position.y < 0:
            errors.append("Chart Y position cannot be negative")
        
        if position.width <= 0:
            errors.append("Chart width must be positive")
        
        if position.height <= 0:
            errors.append("Chart height must be positive")
        
        # Check minimum dimensions for readability
        if position.width < 200:
            errors.append("Chart width should be at least 200px for readability")
        
        if position.height < 150:
            errors.append("Chart height should be at least 150px for readability")
        
        # Validate anchor cell if provided
        if position.anchor_cell:
            if not self._is_valid_cell_reference(position.anchor_cell):
                errors.append(f"Invalid anchor cell reference: {position.anchor_cell}")
        
        return errors
    
    def _validate_styling(self, styling: ChartStyling) -> List[str]:
        """Validate chart styling configuration"""
        errors = []
        
        # Validate colors
        if styling.background_color:
            if not self._is_valid_hex_color(styling.background_color):
                errors.append(f"Invalid background color format: {styling.background_color}")
        
        if styling.custom_colors:
            for i, color in enumerate(styling.custom_colors):
                if not self._is_valid_hex_color(color):
                    errors.append(f"Invalid custom color at index {i}: {color}")
        
        # Validate font size
        if styling.font_size < 6 or styling.font_size > 72:
            errors.append("Font size must be between 6 and 72 points")
        
        # Validate color scheme
        if styling.color_scheme == ColorScheme.CUSTOM and not styling.custom_colors:
            errors.append("Custom color scheme requires custom_colors to be provided")
        
        return errors
    
    def _is_valid_hex_color(self, color: str) -> bool:
        """Validate hex color format"""
        if not color or not color.startswith('#'):
            return False
        
        # Check for valid hex color (3 or 6 digit)
        hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        return bool(re.match(hex_pattern, color))
    
    def _validate_title(self, title: str) -> List[str]:
        """Validate chart title"""
        errors = []
        
        if not title or not title.strip():
            errors.append("Chart title cannot be empty")
        
        if len(title) > 100:
            errors.append("Chart title should not exceed 100 characters")
        
        return errors
    
    def _validate_r7_office_properties(self, properties: Dict[str, Any]) -> List[str]:
        """Validate R7-Office specific properties"""
        warnings = []
        
        # Check for known R7-Office properties
        known_properties = {
            "api_version", "chart_object_name", "enable_animation", 
            "enable_3d", "z_order", "locked", "print_object"
        }
        
        for prop_name in properties:
            if prop_name not in known_properties:
                warnings.append(f"Unknown R7-Office property: {prop_name}")
        
        # Validate specific property values
        if "api_version" in properties:
            if not isinstance(properties["api_version"], str):
                warnings.append("R7-Office api_version should be a string")
        
        if "enable_3d" in properties:
            if not isinstance(properties["enable_3d"], bool):
                warnings.append("R7-Office enable_3d should be a boolean")
        
        return warnings
    
    def validate_data_source(self, data_source: DataSource) -> Tuple[bool, List[str]]:
        """Validate data source for chart generation"""
        errors = []
        
        try:
            # Validate headers
            if not data_source.headers:
                errors.append("Data source must have headers")
            
            # Validate data rows
            if not data_source.data_rows:
                errors.append("Data source must have data rows")
            else:
                # Check data consistency
                expected_columns = len(data_source.headers)
                for i, row in enumerate(data_source.data_rows):
                    if len(row) != expected_columns:
                        errors.append(f"Row {i} has {len(row)} columns, expected {expected_columns}")
            
            # Validate data range
            range_errors = self._validate_data_range(data_source.data_range)
            errors.extend(range_errors)
            
            # Validate worksheet name
            if not data_source.worksheet_name or not data_source.worksheet_name.strip():
                errors.append("Worksheet name cannot be empty")
            
        except Exception as e:
            logger.error(f"Error validating data source: {e}")
            errors.append(f"Data source validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def get_validation_summary(self, chart_config: ChartConfig) -> Dict[str, Any]:
        """Get comprehensive validation summary"""
        
        # Basic validation
        is_valid, validation_errors = self.validate_chart_config(chart_config)
        
        # R7-Office compatibility
        is_compatible, compatibility_warnings = self.validate_r7_office_compatibility(chart_config)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(chart_config, validation_errors, compatibility_warnings)
        
        return {
            "is_valid": is_valid,
            "is_r7_office_compatible": is_compatible,
            "validation_errors": validation_errors,
            "compatibility_warnings": compatibility_warnings,
            "recommendations": recommendations,
            "overall_score": self._calculate_quality_score(is_valid, is_compatible, validation_errors, compatibility_warnings)
        }
    
    def _generate_recommendations(self, chart_config: ChartConfig, errors: List[str], warnings: List[str]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Recommendations based on errors
        if any("width" in error.lower() for error in errors):
            recommendations.append("Consider adjusting chart width for better visibility")
        
        if any("height" in error.lower() for error in errors):
            recommendations.append("Consider adjusting chart height for better proportions")
        
        # Recommendations based on warnings
        if any("font" in warning.lower() for warning in warnings):
            recommendations.append("Consider using standard fonts for better R7-Office compatibility")
        
        if any("color" in warning.lower() for warning in warnings):
            recommendations.append("Consider using standard color schemes for consistent appearance")
        
        # General recommendations
        if chart_config.chart_type == ChartType.PIE and len(chart_config.series_config.y_axis_columns) > 1:
            recommendations.append("Pie charts work best with single data series")
        
        if chart_config.position.width > 800 or chart_config.position.height > 600:
            recommendations.append("Large charts may not display well on smaller screens")
        
        return recommendations
    
    def _calculate_quality_score(self, is_valid: bool, is_compatible: bool, errors: List[str], warnings: List[str]) -> float:
        """Calculate overall quality score (0-1)"""
        
        base_score = 1.0
        
        # Deduct for errors
        if not is_valid:
            base_score -= 0.5
        
        # Deduct for each error
        base_score -= min(0.3, len(errors) * 0.1)
        
        # Deduct slightly for compatibility warnings
        if not is_compatible:
            base_score -= 0.1
        
        # Deduct for each warning
        base_score -= min(0.2, len(warnings) * 0.05)
        
        return max(0.0, base_score)

# Global instance
chart_validation_service = ChartValidationService()