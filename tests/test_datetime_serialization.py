"""
Unit tests for datetime serialization fix
"""

import json
import pytest
from datetime import datetime
from app.utils.json_encoder import DateTimeEncoder
from app.models.api.spreadsheet import SpreadsheetData, SpreadsheetMetadata, WorksheetInfo

def test_datetime_encoder():
    """Test that DateTimeEncoder properly serializes datetime objects"""
    # Create a datetime object
    test_datetime = datetime(2023, 1, 1, 12, 0, 0)
    
    # Create a dictionary with datetime object
    test_data = {
        "name": "test",
        "timestamp": test_datetime
    }
    
    # Serialize with custom encoder
    json_str = json.dumps(test_data, cls=DateTimeEncoder)
    
    # Parse back to dict
    parsed_data = json.loads(json_str)
    
    # Verify datetime was converted to ISO format string
    assert parsed_data["name"] == "test"
    assert parsed_data["timestamp"] == "2023-01-01T12:00:00"
    assert isinstance(parsed_data["timestamp"], str)

def test_spreadsheet_data_serialization():
    """Test that SpreadsheetData with datetime fields serializes properly"""
    # Create a SpreadsheetData object with datetime in metadata
    spreadsheet_data = SpreadsheetData(
        metadata=SpreadsheetMetadata(
            version="1.0",
            format="test-format",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            plugin_id="test-plugin"
        ),
        worksheet=WorksheetInfo(
            name="Sheet1",
            range="A1"
        ),
        data={"test": "data"}
    )
    
    # Convert to dict and serialize with custom encoder
    spreadsheet_dict = spreadsheet_data.dict()
    json_str = json.dumps(spreadsheet_dict, cls=DateTimeEncoder)
    
    # Parse back to dict
    parsed_data = json.loads(json_str)
    
    # Verify datetime was converted to ISO format string
    assert parsed_data["metadata"]["created_at"] == "2023-01-01T12:00:00"
    assert isinstance(parsed_data["metadata"]["created_at"], str)