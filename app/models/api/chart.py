"""
Chart Generation API Data Models
Enhanced Pydantic models for chart generation with R7-Office API compatibility
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

# Chart Type Enums
class ChartType(str, Enum):
    """Supported chart types"""
    LINE = "line"
    COLUMN = "column" 
    PIE = "pie"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    SCATTER = "scatter"
    AREA = "area"
    HISTOGRAM = "histogram"

class ColorScheme(str, Enum):
    """Color scheme options for charts"""
    OFFICE = "office"
    MODERN = "modern"
    COLORFUL = "colorful"
    CUSTOM = "custom"

class LegendPosition(str, Enum):
    """Legend position options"""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    NONE = "none"

class BorderStyle(str, Enum):
    """Border style options"""
    NONE = "none"
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"

class ChartSeries(BaseModel):
    name: str = Field(..., description="Series name displayed in the legend")
    values: List[Union[str, int, float]] = Field(..., description="Y-values for the series")
    format: Optional[str] = Field('General', description="Y-values format")

# Core Data Models
class ChartData(BaseModel):
    """Source data for chart generation"""
    data_range: str = Field(..., description="Cell range reference for source data")
    chart_data: List[ChartSeries] = Field(..., description="Data series included in the chart")
    chart_type: str = Field(..., description="Type of chart to generate")
    query_text: str = Field(..., description="Natural language instruction for chart generation")
    

class ChartPosition(BaseModel):
    """Position and size specifications for charts"""
    x: int = Field(..., description="Left position in pixels", ge=0)
    y: int = Field(..., description="Top position in pixels", ge=0)
    width: int = Field(..., description="Chart width in pixels", ge=100)
    height: int = Field(..., description="Chart height in pixels", ge=100)
    anchor_cell: Optional[str] = Field(None, description="Optional R7-Office cell anchor")

class ChartStyling(BaseModel):
    """Chart styling configuration"""
    color_scheme: ColorScheme = Field(default=ColorScheme.OFFICE, description="Color theme")
    font_family: str = Field(default="Arial", description="Font family for chart text")
    font_size: int = Field(default=12, description="Base font size", ge=8, le=72)
    background_color: Optional[str] = Field(None, description="Background color in hex format")
    border_style: BorderStyle = Field(default=BorderStyle.NONE, description="Chart border style")
    legend_position: LegendPosition = Field(default=LegendPosition.BOTTOM, description="Legend placement")

    @field_validator('background_color')
    def validate_background_color(cls, v):
        """Validate hex color format"""
        if v is not None and not v.startswith('#'):
            raise ValueError('Background color must be in hex format starting with #')
        return v

class SeriesConfig(BaseModel):
    """Configuration for chart data series"""
    x_axis_column: int = Field(..., description="Column index for X-axis data", ge=0)
    y_axis_columns: List[int] = Field(..., description="Column indices for Y-axis data")
    series_names: Optional[List[str]] = Field(None, description="Custom names for data series")
    show_data_labels: bool = Field(default=False, description="Whether to show data labels")
    smooth_lines: bool = Field(default=False, description="Apply line smoothing (for line charts)")

class ChartConfig(BaseModel):
    """Complete chart configuration"""
    chart_type: ChartType = Field(..., description="Type of chart to generate")
    title: str = Field(..., description="Main chart title")
    subtitle: Optional[str] = Field(None, description="Optional chart subtitle")
    series_config: SeriesConfig = Field(..., description="Data series configuration")
    position: ChartPosition = Field(..., description="Chart position and size")
    styling: ChartStyling = Field(..., description="Chart styling options")

# Request Models
class ChartGenerationRequest(BaseModel):
    """Request model for chart generation"""
    chart_data: ChartData = Field(..., description="Source data for chart generation")
    chart_type: str = Field(..., description="Type of chart to generate")
    query_text: str = Field(..., description="Natural language instruction for chart generation")

# Response Models
class ChartStatusResponse(BaseModel):
    """Response model for chart generation status"""
    success: bool = Field(..., description="Request success status")
    request_id: str = Field(..., description="Request identifier")
    status: str = Field(..., description="Current processing status")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class ChartResultResponse(BaseModel):
    """Response model for chart generation result
    
    Example:
    ```json
    {
        "success": true,
        "status": "completed",
        "message": "Chart generated successfully",
        "chart_config": {
            "chart_type": "line",
            "title": "Sales Over Time",
            ...
        },
        "tokens_used": 450,
        "processing_time": 1.23
    }
    ```
    """
    success: bool = Field(..., description="Request success status")
    status: str = Field(..., description="Current processing status")
    message: str = Field(..., description="Human-readable status message")
    chart_config: Optional[ChartConfig] = Field(None, description="Generated chart configuration")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used", ge=0)
    processing_time: Optional[float] = Field(None, description="Processing time in seconds", ge=0.0)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status against valid status values"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v
    
    @model_validator(mode='after')
    def validate_success_consistency(self):
        """Validate that success flag matches status and chart_config presence"""
        if self.success and self.chart_config is None:
            raise ValueError('Successful response must include chart_config')
        if self.success and self.status == 'failed':
            raise ValueError('Success cannot be true when status is failed')
        if not self.success and self.status == 'completed':
            raise ValueError('Failed response cannot have status completed')
        return self
    
    def is_successful(self) -> bool:
        """Check if response indicates success"""
        return self.success and self.chart_config is not None
    
    def has_errors(self) -> bool:
        """Check if response has errors"""
        return not self.success or self.status == 'failed'
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of response"""
        return {
            'success': self.success,
            'status': self.status,
            'message': self.message,
            'has_chart': self.chart_config is not None,
            'tokens_used': self.tokens_used or 0,
            'processing_time': self.processing_time or 0.0
        }
