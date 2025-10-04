"""
Unit tests for Spreadsheet Data Models and Style Registry
"""

import pytest
from pydantic import ValidationError
from app.models.api.spreadsheet import (
    SpreadsheetData, SpreadsheetRequest, StyleDefinition, HeaderData, 
    DataRow, SpreadsheetMetadata, WorksheetInfo, WorksheetData,
    SpreadsheetProcessResponse, SpreadsheetResultResponse
)
from app.services.spreadsheet.style_registry import (
    StyleRegistry, StyleValidator, create_style_registry_from_data
)


class TestSpreadsheetModels:
    """Test cases for spreadsheet data models"""
    
    def test_style_definition_validation(self):
        """Test StyleDefinition field validation"""
        # Valid style
        style = StyleDefinition(
            id="test_style",
            background_color="#FF0000",
            font_color="#FFFFFF",
            font_weight="bold",
            font_style="italic",
            horizontal_alignment="center",
            vertical_alignment="middle"
        )
        
        assert style.background_color == "#FF0000"
        assert style.font_weight == "bold"
        
        # Invalid color format
        with pytest.raises(ValidationError):
            StyleDefinition(id="test", background_color="red")
        
        # Invalid font weight
        with pytest.raises(ValidationError):
            StyleDefinition(id="test", font_weight="heavy")
    
    def test_spreadsheet_data_creation(self):
        """Test SpreadsheetData model creation"""
        data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "data": {
                "header": {"values": ["Col1", "Col2"], "style": "header_style"},
                "rows": [{"values": ["Val1", "Val2"], "style": "row_style"}]
            },
            "styles": [
                {"id": "header_style", "font_weight": "bold"},
                {"id": "row_style", "background_color": "#F0F0F0"}
            ]
        }
        
        spreadsheet = SpreadsheetData(**data)
        assert spreadsheet.metadata.version == "1.0"
        assert len(spreadsheet.styles) == 2
        assert spreadsheet.data.header.style == "header_style"
    
    def test_spreadsheet_request_validation(self):
        """Test SpreadsheetRequest validation"""
        data = {
            "spreadsheet_data": {
                "data": {"rows": [{"values": ["test"]}]},
                "styles": []
            },
            "query_text": "Process this data"
        }
        
        request = SpreadsheetRequest(**data)
        assert request.query_text == "Process this data"
        assert request.category is None


class TestStyleRegistry:
    """Test cases for StyleRegistry functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.registry = StyleRegistry()
    
    def test_add_style_from_dict(self):
        """Test adding styles from dictionary"""
        style_dict = {
            "background_color": "#FF0000",
            "font_color": "#FFFFFF",
            "font_weight": "bold"
        }
        
        style_id = self.registry.add_style_from_dict(style_dict)
        assert style_id is not None
        
        # Adding the same style should return the same ID
        same_id = self.registry.add_style_from_dict(style_dict)
        assert style_id == same_id
    
    def test_get_style_by_id(self):
        """Test retrieving styles by ID"""
        style_dict = {"background_color": "#00FF00"}
        style_id = self.registry.add_style_from_dict(style_dict)
        
        retrieved_style = self.registry.get_style_by_id(style_id)
        assert retrieved_style is not None
        assert retrieved_style.background_color == "#00FF00"
        
        # Non-existent ID should return None
        assert self.registry.get_style_by_id("non_existent") is None
    
    def test_style_consolidation(self):
        """Test that duplicate styles are consolidated"""
        style1 = {"background_color": "#FF0000", "font_weight": "bold"}
        style2 = {"background_color": "#FF0000", "font_weight": "bold"}
        style3 = {"background_color": "#00FF00", "font_weight": "bold"}
        
        id1 = self.registry.add_style_from_dict(style1)
        id2 = self.registry.add_style_from_dict(style2)
        id3 = self.registry.add_style_from_dict(style3)
        
        assert id1 == id2  # Same style should have same ID
        assert id1 != id3  # Different style should have different ID
        assert len(self.registry.get_all_styles()) == 2


class TestStyleValidator:
    """Test cases for StyleValidator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sample_data = {
            "data": {
                "header": {"values": ["Name", "Age"], "style": "header_style"},
                "rows": [
                    {"values": ["John", 30], "style": "row_style"},
                    {"values": ["Jane", 25], "style": "row_style"}
                ]
            },
            "styles": [
                {"id": "header_style", "font_weight": "bold"},
                {"id": "row_style", "background_color": "#F0F0F0"}
            ]
        }
    
    def test_validate_valid_data(self):
        """Test validation of valid spreadsheet data"""
        registry = create_style_registry_from_data(self.sample_data)
        validator = StyleValidator(registry)
        
        is_valid, errors = validator.validate_spreadsheet_data(self.sample_data)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_style_reference(self):
        """Test validation with missing style reference"""
        invalid_data = self.sample_data.copy()
        invalid_data["data"]["header"]["style"] = "missing_style"
        
        registry = create_style_registry_from_data(invalid_data)
        validator = StyleValidator(registry)
        
        is_valid, errors = validator.validate_spreadsheet_data(invalid_data)
        assert is_valid is False
        assert len(errors) > 0
        assert "missing_style" in str(errors)
    
    def test_validate_style_consistency(self):
        """Test style consistency validation"""
        registry = create_style_registry_from_data(self.sample_data)
        validator = StyleValidator(registry)
        
        is_consistent, warnings = validator.validate_style_consistency(self.sample_data)
        assert is_consistent is True
        assert len(warnings) == 0
    
    def test_create_registry_from_data(self):
        """Test creating style registry from spreadsheet data"""
        registry = create_style_registry_from_data(self.sample_data)
        
        assert len(registry.get_all_styles()) == 2
        assert registry.get_style_by_id("header_style") is not None
        assert registry.get_style_by_id("row_style") is not None


class TestDataValidation:
    """Test data validation scenarios"""
    
    def test_header_without_style(self):
        """Test header data without style reference"""
        header = HeaderData(values=["Col1", "Col2"])
        assert header.style is None
        assert header.values == ["Col1", "Col2"]
    
    def test_row_with_mixed_types(self):
        """Test data row with mixed value types"""
        row = DataRow(values=["Text", 123, 45.67, True])
        assert len(row.values) == 4
        assert isinstance(row.values[0], str)
        assert isinstance(row.values[1], int)
        assert isinstance(row.values[2], float)
        assert isinstance(row.values[3], bool)
    
    def test_metadata_defaults(self):
        """Test metadata with default values"""
        metadata = SpreadsheetMetadata()
        assert metadata.version == "1.0"
        assert metadata.plugin_id is None
        assert metadata.created_at is not None
    
    def test_worksheet_info_defaults(self):
        """Test worksheet info with default values"""
        worksheet = WorksheetInfo()
        assert worksheet.name == "Sheet1"
        assert worksheet.range == "A1"