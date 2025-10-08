"""
Chart Generation API Data Models
Enhanced Pydantic models for chart generation with R7-Office API compatibility
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Chart Type Enums
class ChartType(str, Enum):
    """Supported chart types with R7-Office compatibility"""
    COLUMN = "column"
    LINE = "line" 
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    BAR = "bar"
    DOUGHNUT = "doughnut"
    RADAR = "radar"

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

# Core Data Models
class DataSource(BaseModel):
    """Source data for chart generation"""
    worksheet_name: str = Field(default="Sheet1", description="Name of the worksheet")
    data_range: str = Field(..., description="R7-Office cell range format (e.g., A1:B10)")
    headers: List[str] = Field(..., description="Column headers from the data")
    data_rows: List[List[Any]] = Field(..., description="Actual data values")
    column_types: Dict[int, str] = Field(default_factory=dict, description="Data type mapping by column index")

    @field_validator('data_range')
    def validate_data_range(cls, v):
        """Validate R7-Office cell range format"""
        if not v:
            raise ValueError("Data range cannot be empty")
        # Basic validation for cell range format (A1:B10)
        if ':' not in v:
            raise ValueError("Data range must be in format 'A1:B10'")
        return v

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
    custom_colors: Optional[List[str]] = Field(None, description="Custom color palette (hex values)")

    @field_validator('background_color')
    def validate_background_color(cls, v):
        """Validate hex color format"""
        if v is not None and not v.startswith('#'):
            raise ValueError('Background color must be in hex format starting with #')
        return v

    @field_validator('custom_colors')
    def validate_custom_colors(cls, v):
        """Validate custom color palette"""
        if v is not None:
            for color in v:
                if not color.startswith('#'):
                    raise ValueError('All custom colors must be in hex format starting with #')
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
    data_range: str = Field(..., description="R7-Office data range format")
    series_config: SeriesConfig = Field(..., description="Data series configuration")
    position: ChartPosition = Field(..., description="Chart position and size")
    styling: ChartStyling = Field(default_factory=ChartStyling, description="Chart styling options")
    r7_office_properties: Dict[str, Any] = Field(default_factory=dict, description="R7-Office specific properties")

class ChartPreferences(BaseModel):
    """Optional chart preferences for AI generation"""
    preferred_chart_types: Optional[List[ChartType]] = Field(None, description="Preferred chart types")
    color_preference: Optional[ColorScheme] = Field(None, description="Preferred color scheme")
    size_preference: Optional[Literal["small", "medium", "large"]] = Field(None, description="Size preference")
    style_preference: Optional[Literal["minimal", "standard", "detailed"]] = Field(None, description="Style preference")

class R7OfficeConfig(BaseModel):
    """R7-Office specific configuration"""
    api_version: str = Field(default="1.0", description="R7-Office API version")
    compatibility_mode: bool = Field(default=True, description="Enable R7-Office compatibility mode")
    custom_properties: Dict[str, Any] = Field(default_factory=dict, description="Custom R7-Office properties")

# Request Models
class ChartGenerationRequest(BaseModel):
    """Request model for chart generation"""
    data_source: DataSource = Field(..., description="Source data for chart generation")
    chart_instruction: str = Field(..., description="Natural language instruction for chart generation")
    chart_preferences: Optional[ChartPreferences] = Field(None, description="Optional chart preferences")
    r7_office_config: Optional[R7OfficeConfig] = Field(None, description="R7-Office specific configuration")

class ChartValidationRequest(BaseModel):
    """Request model for chart configuration validation"""
    chart_config: ChartConfig = Field(..., description="Chart configuration to validate")

# Response Models
class ChartGenerationResponse(BaseModel):
    """Response model for chart generation"""
    success: bool = Field(..., description="Generation success status")
    request_id: str = Field(..., description="Unique request identifier")
    status: str = Field(..., description="Current processing status")
    chart_config: Optional[ChartConfig] = Field(None, description="Generated chart configuration")
    message: str = Field(..., description="Human-readable status message")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used in AI processing")
    processing_time: Optional[float] = Field(None, description="Time taken to process in seconds")

class ChartStatusResponse(BaseModel):
    """Response model for chart generation status"""
    success: bool = Field(..., description="Request success status")
    request_id: str = Field(..., description="Request identifier")
    status: str = Field(..., description="Current processing status")
    message: str = Field(..., description="Human-readable status message")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class ChartResultResponse(BaseModel):
    """Response model for chart generation result"""
    success: bool = Field(..., description="Request success status")
    status: str = Field(..., description="Current processing status")
    message: str = Field(..., description="Human-readable status message")
    chart_config: Optional[ChartConfig] = Field(None, description="Generated chart configuration")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

class ChartValidationResponse(BaseModel):
    """Response model for chart validation"""
    success: bool = Field(..., description="Validation success status")
    is_valid: bool = Field(..., description="Whether the chart configuration is valid")
    is_r7_office_compatible: bool = Field(..., description="Whether configuration is R7-Office compatible")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    compatibility_warnings: List[str] = Field(default_factory=list, description="R7-Office compatibility warnings")
    message: str = Field(..., description="Validation summary message")

# Chart Intelligence Models
class DataPattern(BaseModel):
    """Detected data pattern for chart type recommendation"""
    pattern_type: str = Field(..., description="Type of detected pattern")
    confidence: float = Field(..., description="Confidence score (0-1)")
    recommended_chart_type: ChartType = Field(..., description="Recommended chart type")
    reasoning: str = Field(..., description="Explanation for the recommendation")

class ChartRecommendation(BaseModel):
    """AI-generated chart recommendation"""
    primary_recommendation: DataPattern = Field(..., description="Primary chart type recommendation")
    alternative_recommendations: List[DataPattern] = Field(default_factory=list, description="Alternative options")
    data_analysis: Dict[str, Any] = Field(..., description="Analysis of the source data")
    generation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about generation process")