"""Enhanced Spreadsheet Data Models for R7-Office API"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

class SpreadsheetMetadata(BaseModel):
    """Metadata for the enhanced spreadsheet data format"""
    version: str = Field(default="1.0", description="Format version for compatibility")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of creation")
    plugin_id: Optional[str] = Field(None, description="Identifier for the plugin generating the data")

class WorksheetInfo(BaseModel):
    """Worksheet information"""
    name: str = Field(default="Sheet1", description="Name of the worksheet where source data is located")
    range: str = Field(default="A1", description="Сell range reference for source data")

class CellStyle(BaseModel):
    """Unified styling for all spreadsheet cells"""
    background_color: Optional[str] = Field(None, description="Background color in hex format")
    font_color: Optional[str] = Field(None, description="Font color in hex format")
    font_weight: Optional[str] = Field(None, description="Font weight (normal, bold)")
    font_size: Optional[int] = Field(None, description="Font size in points")
    font_style: Optional[str] = Field(None, description="Font style (normal, italic)")
    horizontal_alignment: Optional[str] = Field(None, description="Horizontal alignment (left, center, right)")
    vertical_alignment: Optional[str] = Field(None, description="Vertical alignment (top, middle, bottom)")
    border: Optional[str|List[str]] = Field(None, description="Border settings (top, right, bottom, left)")

class HeaderData(BaseModel):
    """Header row definition"""
    values: List[str] = Field(..., description="Header values")
    style: Optional[CellStyle] = Field(None, description="Styling for the header row")

class DataRow(BaseModel):
    """Data row definition"""
    values: List[Union[str, int, float, bool]] = Field(..., description="Row values")
    style: Optional[CellStyle] = Field(None, description="Styling for this row")

class WorksheetData(BaseModel):
    """Worksheet data structure"""
    header: Optional[HeaderData] = Field(None, description="Header row data")
    rows: List[DataRow] = Field(..., description="Data rows")

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
    format: Optional[str] = Field(None, description="Display format for the data")
    width: Optional[int] = Field(None, description="Preferred column width in pixels")
    validation: Optional[ColumnValidation] = Field(None, description="Optional data validation rules")

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
    metadata: SpreadsheetMetadata = Field(default_factory=SpreadsheetMetadata, description="Metadata section")
    worksheet: WorksheetInfo = Field(default_factory=WorksheetInfo, description="Worksheet section")
    data: WorksheetData = Field(default_factory=WorksheetData, description="Data section containing header and rows")
    columns: Optional[List[ColumnDefinition]] = Field(default_factory=list, description="Column definitions")
    charts: Optional[List[ChartDefinition]] = Field(default_factory=list, description="Chart definitions")

class SpreadsheetRequest(BaseModel):
    """Request model for enhanced spreadsheet processing"""
    spreadsheet_data: SpreadsheetData = Field(..., description="Enhanced spreadsheet data to process")
    query_text: str = Field(..., description="Processing instruction for the AI")
    category: Optional[str] = Field(None, description="Category of the request")

class SpreadsheetProcessResponse(BaseModel):
    """Response model for initiating spreadsheet processing (without result data)"""
    success: bool = Field(..., description="Whether the request was successful")
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Human-readable message")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")

class SpreadsheetResultResponse(BaseModel):
    """Response model for spreadsheet processing result"""
    success: bool = Field(..., description="Whether the request was successful")
    status: str = Field(..., description="Current status of the request")
    message: str = Field(..., description="Human-readable message about the request status")
    result: Optional[SpreadsheetData] = Field(None, description="Processed result data when available")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used in processing")
    processing_time: Optional[float] = Field(None, description="Time taken to process the request in seconds")

class SpreadsheetSearchRequest(BaseModel):
    """Request model for spreadsheet data search"""
    data: Union[str, List[str]] = Field(..., description="Search string or list of search strings")

class SearchResultItem(BaseModel):
    """Search result item with text, language and similarity score"""
    text: str = Field(..., description="Matched text from the database")
    language: str = Field(..., description="Language of the matched text")
    score: float = Field(..., description="Similarity score (0-1, where 1 is most similar)")

class SearchResult(BaseModel):
    search_text: str = Field(..., description="Search prompt text")
    search_results: List[SearchResultItem] = Field(default_factory=list, description="Search result items")
