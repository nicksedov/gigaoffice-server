"""Enhanced Spreadsheet Data Models with Style Reference Architecture for R7-Office API"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

class SpreadsheetMetadata(BaseModel):
    """Metadata for the enhanced spreadsheet data format"""
    version: str = Field(default="2.0", description="Format version for compatibility")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of creation")
    plugin_id: Optional[str] = Field(None, description="Identifier for the plugin generating the data")

class WorksheetInfo(BaseModel):
    """Worksheet information"""
    name: str = Field(default="Sheet1", description="Name of the worksheet where source data is located")
    range: str = Field(default="A1", description="Cell range reference for source data")

class StyleDefinition(BaseModel):
    """Centralized style definition with unique identifier"""
    id: str = Field(..., description="Unique identifier for style reference")
    background_color: Optional[str] = Field(None, description="Background color in hex format")
    font_color: Optional[str] = Field(None, description="Font color in hex format")
    font_weight: Optional[str] = Field(None, description="Font weight (normal, bold)")
    font_size: Optional[int] = Field(None, description="Font size in points")
    font_style: Optional[str] = Field(None, description="Font style (normal, italic)")
    horizontal_alignment: Optional[str] = Field(None, description="Horizontal alignment (left, center, right)")
    vertical_alignment: Optional[str] = Field(None, description="Vertical alignment (top, middle, bottom)")
    border: Optional[Union[str, List[str]]] = Field(None, description="Border settings (top, right, bottom, left)")

    @field_validator('background_color', 'font_color')
    def validate_color_format(cls, v):
        """Validate hex color format"""
        if v is not None and not v.startswith('#'):
            raise ValueError('Color must start with #')
        return v

    @field_validator('font_weight')
    def validate_font_weight(cls, v):
        """Validate font weight values"""
        if v is not None and v not in ['normal', 'bold']:
            raise ValueError('Font weight must be "normal" or "bold"')
        return v

    @field_validator('font_style')
    def validate_font_style(cls, v):
        """Validate font style values"""
        if v is not None and v not in ['normal', 'italic']:
            raise ValueError('Font style must be "normal" or "italic"')
        return v

    @field_validator('horizontal_alignment')
    def validate_horizontal_alignment(cls, v):
        """Validate horizontal alignment values"""
        if v is not None and v not in ['left', 'center', 'right']:
            raise ValueError('Horizontal alignment must be "left", "center", or "right"')
        return v

    @field_validator('vertical_alignment')
    def validate_vertical_alignment(cls, v):
        """Validate vertical alignment values"""
        if v is not None and v not in ['top', 'middle', 'bottom']:
            raise ValueError('Vertical alignment must be "top", "middle", or "bottom"')
        return v

class HeaderData(BaseModel):
    """Header row definition with style reference"""
    values: List[str] = Field(..., description="Header values")
    style: Optional[str] = Field(None, description="Style reference ID for the header row")

class DataRow(BaseModel):
    """Data row definition with style reference"""
    values: List[Union[str, int, float, bool]] = Field(..., description="Row values")
    style: Optional[str] = Field(None, description="Style reference ID for this row")

class WorksheetData(BaseModel):
    """Worksheet data structure"""
    header: Optional[HeaderData] = Field(None, description="Header row data")
    rows: List[DataRow] = Field(..., description="Data rows")

class ColumnDefinition(BaseModel):
    """Column definition with type and formatting"""
    index: int = Field(..., description="Zero-based column index")
    format: str = Field(None, description="Display format for the data")

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

class SpreadsheetDataV2(BaseModel):
    """Main data structure for enhanced spreadsheet manipulation with style references"""
    metadata: SpreadsheetMetadata = Field(default_factory=SpreadsheetMetadata, description="Metadata section")
    worksheet: WorksheetInfo = Field(default_factory=WorksheetInfo, description="Worksheet section")
    data: WorksheetData = Field(default_factory=WorksheetData, description="Data section containing header and rows")
    columns: Optional[List[ColumnDefinition]] = Field(default_factory=list, description="Column definitions")
    styles: List[StyleDefinition] = Field(default_factory=list, description="Centralized style definitions")
    charts: Optional[List[ChartDefinition]] = Field(default_factory=list, description="Chart definitions")

class SpreadsheetRequestV2(BaseModel):
    """Request model for enhanced spreadsheet processing with style references"""
    spreadsheet_data: SpreadsheetDataV2 = Field(..., description="Enhanced spreadsheet data to process")
    query_text: str = Field(..., description="Processing instruction for the AI")
    category: Optional[str] = Field(None, description="Category of the request")

class SpreadsheetProcessResponseV2(BaseModel):
    """Response model for initiating spreadsheet processing (without result data)"""
    success: bool = Field(..., description="Whether the request was successful")
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Human-readable message")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")

class SpreadsheetResultResponseV2(BaseModel):
    """Response model for spreadsheet processing result"""
    success: bool = Field(..., description="Whether the request was successful")
    status: str = Field(..., description="Current status of the request")
    message: str = Field(..., description="Human-readable message about the request status")
    result: Optional[SpreadsheetDataV2] = Field(None, description="Processed result data when available")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used in processing")
    processing_time: Optional[float] = Field(None, description="Time taken to process the request in seconds")

# Compatibility models for backward compatibility
from app.models.api.spreadsheet import CellStyle

class CompatibilityTransformationMixin:
    """Mixin providing transformation between legacy and new formats"""
    
    @classmethod
    def from_legacy_format(cls, legacy_data: Dict[str, Any]) -> "SpreadsheetDataV2":
        """Transform legacy format with inline styles to new format with style references"""
        from app.services.spreadsheet.style_registry import StyleRegistry
        
        registry = StyleRegistry()
        
        # Extract styles from header and rows
        if "data" in legacy_data and legacy_data["data"].get("header"):
            header_data = legacy_data["data"]["header"]
            if "style" in header_data and isinstance(header_data["style"], dict):
                style_id = registry.add_style_from_dict(header_data["style"])
                header_data["style"] = style_id
        
        if "data" in legacy_data and "rows" in legacy_data["data"]:
            for row in legacy_data["data"]["rows"]:
                if "style" in row and isinstance(row["style"], dict):
                    style_id = registry.add_style_from_dict(row["style"])
                    row["style"] = style_id
        
        # Add styles to the data structure
        legacy_data["styles"] = [style.dict() for style in registry.get_all_styles()]
        
        # Ensure version is updated
        if "metadata" not in legacy_data:
            legacy_data["metadata"] = {}
        legacy_data["metadata"]["version"] = "2.0"
        
        return cls(**legacy_data)
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Transform new format with style references back to legacy format with inline styles"""
        data = self.dict()
        
        # Create style lookup dictionary
        style_lookup = {style["id"]: style for style in data.get("styles", [])}
        
        # Replace style references with full style objects
        if "data" in data and data["data"].get("header") and data["data"]["header"].get("style"):
            style_id = data["data"]["header"]["style"]
            if style_id in style_lookup:
                style_dict = {k: v for k, v in style_lookup[style_id].items() if k != "id" and v is not None}
                data["data"]["header"]["style"] = style_dict
        
        if "data" in data and "rows" in data["data"]:
            for row in data["data"]["rows"]:
                if row.get("style") and row["style"] in style_lookup:
                    style_dict = {k: v for k, v in style_lookup[row["style"]].items() if k != "id" and v is not None}
                    row["style"] = style_dict
        
        # Remove styles array and update version
        data.pop("styles", None)
        if "metadata" in data:
            data["metadata"]["version"] = "1.0"
        
        return data

# Add the mixin to the SpreadsheetDataV2 class
SpreadsheetDataV2.__bases__ = (BaseModel, CompatibilityTransformationMixin)