"""
Chart Validation Service
Validates chart configurations against ONLYOFFICE API specifications
"""

from typing import Dict, Any, Optional, List
from loguru import logger

class ChartValidationError(Exception):
    """Custom exception for chart validation errors"""
    
    def __init__(
        self,
        message: str,
        error_type: str,
        field: str,
        invalid_value: Any,
        expected: Any = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.field = field
        self.invalid_value = invalid_value
        self.expected = expected
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for API response"""
        return {
            "error_type": self.error_type,
            "field": self.field,
            "invalid_value": self.invalid_value,
            "expected": self.expected,
            "suggestion": self.suggestion
        }


class ChartValidator:
    """
    Validator for chart configurations ensuring ONLYOFFICE API compliance.
    
    Validates:
    1. Chart type against ONLYOFFICE ChartType enumeration
    2. Type-specific constraints (e.g., series count for stacked/pie charts)
    """
    
    # Valid ONLYOFFICE chart types (all 29 values)
    VALID_CHART_TYPES = {
        # Bar Charts (Vertical)
        "bar", "barStacked", "barStackedPercent",
        "bar3D", "barStacked3D", "barStackedPercent3D", "barStackedPercent3DPerspective",
        # Horizontal Bar Charts
        "horizontalBar", "horizontalBarStacked", "horizontalBarStackedPercent",
        "horizontalBar3D", "horizontalBarStacked3D", "horizontalBarStackedPercent3D",
        # Line Charts
        "lineNormal", "lineStacked", "lineStackedPercent", "line3D",
        # Pie Charts
        "pie", "pie3D", "doughnut",
        # Scatter & Stock
        "scatter", "stock",
        # Area Charts
        "area", "areaStacked", "areaStackedPercent",
        # Combination Charts
        "comboBarLine", "comboBarLineSecondary", "comboCustom",
        # Special
        "unknown"
    }
    
    # Chart types that require multiple series
    MULTI_SERIES_TYPES = {
        "barStacked", "barStackedPercent",
        "barStacked3D", "barStackedPercent3D", "barStackedPercent3DPerspective",
        "horizontalBarStacked", "horizontalBarStackedPercent",
        "horizontalBarStacked3D", "horizontalBarStackedPercent3D",
        "lineStacked", "lineStackedPercent",
        "areaStacked", "areaStackedPercent",
        "comboBarLine", "comboBarLineSecondary", "comboCustom"
    }
    
    # Chart types that require exactly one series
    SINGLE_SERIES_TYPES = {"pie", "pie3D", "doughnut"}
    
    # Chart types that require exactly 4 series (OHLC format)
    STOCK_TYPES = {"stock"}
    
    def validate_chart_type(self, chart_type: str) -> None:
        """
        Validate chart type against ONLYOFFICE specification.
        
        Args:
            chart_type: Chart type value to validate
            
        Raises:
            ChartValidationError: If chart type is invalid
        """
        if chart_type not in self.VALID_CHART_TYPES:
            raise ChartValidationError(
                message=f"Invalid chart type: {chart_type}",
                error_type="validation_error",
                field="chart_type",
                invalid_value=chart_type,
                expected=sorted(list(self.VALID_CHART_TYPES)),
                suggestion="Use one of the ONLYOFFICE-supported chart types"
            )
        
        # Reject explicit 'unknown' type
        if chart_type == "unknown":
            raise ChartValidationError(
                message="Chart type 'unknown' cannot be explicitly requested",
                error_type="validation_error",
                field="chart_type",
                invalid_value=chart_type,
                expected=sorted(list(self.VALID_CHART_TYPES - {"unknown"})),
                suggestion="Select a specific chart type from the available options"
            )
    
    def validate_series_constraints(
        self,
        chart_type: str,
        y_axis_columns: List[int]
    ) -> None:
        """
        Validate type-specific series count constraints.
        
        Args:
            chart_type: Chart type value
            y_axis_columns: List of Y-axis column indices
            
        Raises:
            ChartValidationError: If constraints are not met
        """
        series_count = len(y_axis_columns)
        
        # Check stacked/combo charts (require at least 2 series)
        if chart_type in self.MULTI_SERIES_TYPES:
            if series_count < 2:
                raise ChartValidationError(
                    message=f"Chart type '{chart_type}' requires at least 2 data series",
                    error_type="constraint_error",
                    field="series_config.y_axis_columns",
                    invalid_value=series_count,
                    expected="At least 2 series",
                    suggestion=f"Add more series to y_axis_columns for {chart_type} charts"
                )
        
        # Check pie/doughnut charts (require exactly 1 series)
        if chart_type in self.SINGLE_SERIES_TYPES:
            if series_count != 1:
                raise ChartValidationError(
                    message=f"Chart type '{chart_type}' requires exactly 1 data series",
                    error_type="constraint_error",
                    field="series_config.y_axis_columns",
                    invalid_value=series_count,
                    expected="Exactly 1 series",
                    suggestion=f"Pie and doughnut charts can only display one data series"
                )
        
        # Check stock charts (require exactly 4 series: OHLC)
        if chart_type in self.STOCK_TYPES:
            if series_count != 4:
                raise ChartValidationError(
                    message=f"Chart type 'stock' requires exactly 4 data series (Open, High, Low, Close)",
                    error_type="constraint_error",
                    field="series_config.y_axis_columns",
                    invalid_value=series_count,
                    expected="Exactly 4 series in OHLC order",
                    suggestion="Stock charts require 4 series: Open, High, Low, Close"
                )
    
    def validate_chart_config(self, chart_data: Dict[str, Any]) -> None:
        """
        Validate complete chart configuration.
        
        Args:
            chart_data: Parsed chart configuration dictionary
            
        Raises:
            ChartValidationError: If validation fails
        """
        # Extract chart type
        chart_type = chart_data.get("chart_type")
        
        if not chart_type:
            raise ChartValidationError(
                message="Missing required field 'chart_type'",
                error_type="validation_error",
                field="chart_type",
                invalid_value=None,
                expected="Valid ONLYOFFICE chart type",
                suggestion="Ensure chart_type is specified in the configuration"
            )
        
        # Validate chart type
        self.validate_chart_type(chart_type)
        
        # Extract series configuration
        series_config = chart_data.get("series_config")
        
        if not series_config:
            raise ChartValidationError(
                message="Missing required field 'series_config'",
                error_type="validation_error",
                field="series_config",
                invalid_value=None,
                expected="Series configuration object",
                suggestion="Ensure series_config is specified in the configuration"
            )
        
        # Extract y_axis_columns
        y_axis_columns = series_config.get("y_axis_columns")
        
        if not y_axis_columns:
            raise ChartValidationError(
                message="Missing required field 'series_config.y_axis_columns'",
                error_type="validation_error",
                field="series_config.y_axis_columns",
                invalid_value=None,
                expected="List of column indices",
                suggestion="Ensure y_axis_columns is specified in series_config"
            )
        
        # Validate series constraints
        self.validate_series_constraints(chart_type, y_axis_columns)
        
        logger.info(f"Chart configuration validated successfully: type={chart_type}, series_count={len(y_axis_columns)}")


# Global validator instance
chart_validator = ChartValidator()
