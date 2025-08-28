"""
Tests for the spreadsheet data models
"""

import pytest
from app.models.api.spreadsheet import (
    SpreadsheetMetadata, WorksheetInfo, WorksheetOptions, HeaderData, 
    DataRow, ColumnDefinition, StyleDefinition, SpreadsheetData,
    SpreadsheetRequest, SpreadsheetResponse
)

def test_spreadsheet_metadata_defaults():
    """Test SpreadsheetMetadata default values"""
    metadata = SpreadsheetMetadata()
    assert metadata.version == "1.0"
    assert metadata.format == "enhanced-spreadsheet-data"
    assert metadata.plugin_id is None

def test_worksheet_info_defaults():
    """Test WorksheetInfo default values"""
    worksheet = WorksheetInfo()
    assert worksheet.name == "Sheet1"
    assert worksheet.range == "A1"
    assert isinstance(worksheet.options, WorksheetOptions)

def test_worksheet_options_defaults():
    """Test WorksheetOptions default values"""
    options = WorksheetOptions()
    assert options.auto_resize_columns is True
    assert options.freeze_headers is True
    assert options.auto_filter is True

def test_header_data():
    """Test HeaderData model"""
    header_data = HeaderData(values=["A", "B", "C"])
    assert header_data.values == ["A", "B", "C"]
    assert header_data.style is None

def test_data_row():
    """Test DataRow model"""
    row = DataRow(values=["Product A", 100, 200.5])
    assert row.values == ["Product A", 100, 200.5]
    assert row.style is None

def test_column_definition():
    """Test ColumnDefinition model"""
    column = ColumnDefinition(
        index=0,
        name="Product",
        type="string",
        format="text"
    )
    assert column.index == 0
    assert column.name == "Product"
    assert column.type == "string"
    assert column.format == "text"

def test_style_definition_defaults():
    """Test StyleDefinition default values"""
    styles = StyleDefinition()
    assert styles.default.font_family == "Arial"
    assert styles.header.font_weight == "bold"
    assert styles.alternating_rows.even["background_color"] == "#F2F2F2"

def test_spreadsheet_data():
    """Test SpreadsheetData model"""
    data = SpreadsheetData(
        data={
            "headers": {"values": ["A", "B"]},
            "rows": [{"values": [1, 2]}]
        }
    )
    assert data.metadata.version == "1.0"
    assert data.worksheet.name == "Sheet1"
    assert data.data["headers"]["values"] == ["A", "B"]

def test_spreadsheet_request():
    """Test SpreadsheetRequest model"""
    spreadsheet_data = SpreadsheetData(
        data={
            "headers": {"values": ["A", "B"]},
            "rows": [{"values": [1, 2]}]
        }
    )
    request = SpreadsheetRequest(
        spreadsheet_data=spreadsheet_data,
        query_text="Test query"
    )
    assert request.query_text == "Test query"
    assert request.category is None

def test_spreadsheet_response():
    """Test SpreadsheetResponse model"""
    response = SpreadsheetResponse(
        success=True,
        request_id="test-id",
        status="completed",
        message="Test message"
    )
    assert response.success is True
    assert response.request_id == "test-id"
    assert response.status == "completed"
    assert response.message == "Test message"
    assert response.result_data is None
    assert response.error_message is None