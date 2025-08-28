"""Enhanced Spreadsheet Data Models for R7-Office API"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class SpreadsheetMetadata(BaseModel):
    """Metadata for the enhanced spreadsheet data format"""
    version: str = Field(default="1.0", description="Format version for compatibility")
    format: str = Field(default="enhanced-spreadsheet-data", description="Identifier for the data format type")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of creation")
    plugin_id: Optional[str] = Field(None, description="Identifier for the plugin generating the data")

class WorksheetOptions(BaseModel):
    """Worksheet-level options"""
    auto_resize_columns: bool = Field(default=True, description="Auto-resize columns based on content")
    freeze_headers: bool = Field(default=True, description="Freeze header rows")
    auto_filter: bool = Field(default=True, description="Enable auto-filter for data")

class WorksheetInfo(BaseModel):
    """Worksheet information"""
    name: str = Field(default="Sheet1", description="Name of the worksheet to insert data into")
    range: str = Field(default="A1", description="Starting cell reference for data insertion")
    options: WorksheetOptions = Field(default_factory=WorksheetOptions, description="Worksheet-level options")

class HeaderStyle(BaseModel):
    """Styling for header rows"""
    background_color: Optional[str] = Field(None, description="Background color in hex format")
    font_color: Optional[str] = Field(None, description="Font color in hex format")
    font_weight: Optional[str] = Field(None, description="Font weight (normal, bold)")
    font_size: Optional[int] = Field(None, description="Font size in points")
    horizontal_alignment: Optional[str] = Field(None, description="Horizontal alignment (left, center, right)")
    vertical_alignment: Optional[str] = Field(None, description="Vertical alignment (top, middle, bottom)")
    border: Optional[Dict[str, str]] = Field(None, description="Border settings (top, right, bottom, left)")

class HeaderData(BaseModel):
    """Header row definition"""
    values: List[str] = Field(..., description="Header values")
    style: Optional[HeaderStyle] = Field(None, description="Styling for the header row")

class RowStyle(BaseModel):
    """Styling for data rows"""
    background_color: Optional[str] = Field(None, description="Background color in hex format")
    font_weight: Optional[str] = Field(None, description="Font weight (normal, bold)")

class DataRow(BaseModel):
    """Data row definition"""
    values: List[Union[str, int, float, bool]] = Field(..., description="Row values")
    style: Optional[RowStyle] = Field(None, description="Styling for this row")

class ColumnValidation(BaseModel):
    """Data validation rules for a column"""
    type: str = Field(..., description="Validation type (numeric, text, date, etc.)")
    min: Optional[Union[int, float]] = Field(None, description="Minimum value")
    max: Optional[Union[int, float]] = Field(None, description="Maximum value")

class ColumnDefinition(BaseModel):
    """Column definition with type and formatting"""
    index: int = Field(..., description="Zero-based column index")
    name: str = Field(..., description="Column name for reference")
    type: str = Field(..., description="Data type (string, number, date, boolean, etc.)")
    format: str = Field(..., description="Display format for the data")
    width: Optional[int] = Field(None, description="Preferred column width in pixels")
    validation: Optional[ColumnValidation] = Field(None, description="Optional data validation rules")

class DefaultStyle(BaseModel):
    """Default styling applied to all cells"""
    font_family: str = Field(default="Arial", description="Font family")
    font_size: int = Field(default=10, description="Font size in points")
    font_color: str = Field(default="#000000", description="Font color in hex format")
    background_color: str = Field(default="#FFFFFF", description="Background color in hex format")

class HeaderStylePreset(BaseModel):
    """Special styling for header rows"""
    font_weight: str = Field(default="bold", description="Font weight")
    font_size: int = Field(default=12, description="Font size in points")
    background_color: str = Field(default="#4472C4", description="Background color in hex format")
    font_color: str = Field(default="#FFFFFF", description="Font color in hex format")

class AlternatingRowStyle(BaseModel):
    """Styling for alternating row colors"""
    even: Dict[str, str] = Field(default_factory=lambda: {"background_color": "#F2F2F2"}, description="Style for even rows")
    odd: Dict[str, str] = Field(default_factory=lambda: {"background_color": "#FFFFFF"}, description="Style for odd rows")

class StyleDefinition(BaseModel):
    """Complete style definition"""
    default: DefaultStyle = Field(default_factory=DefaultStyle, description="Default styling")
    header: HeaderStylePreset = Field(default_factory=HeaderStylePreset, description="Header styling")
    alternating_rows: AlternatingRowStyle = Field(default_factory=AlternatingRowStyle, description="Alternating row styling")

class FormulaDefinition(BaseModel):
    """Formula definition for cells"""
    cell: str = Field(..., description="Target cell for the formula")
    formula: str = Field(..., description="Formula expression")
    description: Optional[str] = Field(None, description="Human-readable description of the formula")

class ChartPosition(BaseModel):
    """Position and size specifications for charts"""
    top: int = Field(..., description="Top position in pixels")
    left: int = Field(..., description="Left position in pixels")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")

class ChartStyle(BaseModel):
    """Chart styling options"""
    color_scheme: str = Field(default="office", description="Color scheme for the chart")

class ChartDefinition(BaseModel):
    """Chart definition"""
    type: str = Field(..., description="Chart type (column, line, pie, etc.)")
    title: str = Field(..., description="Chart title")
    range: str = Field(..., description="Data range for the chart")
    position: ChartPosition = Field(..., description="Position and size specifications")
    style: ChartStyle = Field(default_factory=ChartStyle, description="Chart styling options")

class SpreadsheetData(BaseModel):
    """Main data structure for enhanced spreadsheet manipulation"""
    metadata: SpreadsheetMetadata = Field(default_factory=SpreadsheetData, description="Metadata section")
    worksheet: WorksheetInfo = Field(default_factory=WorksheetInfo, description="Worksheet section")
    data: Dict[str, Any] = Field(..., description="Data section containing headers and rows")
    columns: List[ColumnDefinition] = Field(default_factory=list, description="Column definitions")
    styles: StyleDefinition = Field(default_factory=StyleDefinition, description="Style definitions")
    formulas: List[FormulaDefinition] = Field(default_factory=list, description="Formula definitions")
    charts: List[ChartDefinition] = Field(default_factory=list, description="Chart definitions")

class SpreadsheetRequest(BaseModel):
    """Request model for enhanced spreadsheet processing"""
    spreadsheet_data: SpreadsheetData = Field(..., description="Enhanced spreadsheet data to process")
    query_text: str = Field(..., description="Processing instruction for the AI")
    category: Optional[str] = Field(None, description="Category of the request")

class SpreadsheetResponse(BaseModel):
    """Response model for enhanced spreadsheet processing"""
    success: bool = Field(..., description="Whether the request was successful")
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Human-readable message")
    result_data: Optional[SpreadsheetData] = Field(None, description="Processed spreadsheet data")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")