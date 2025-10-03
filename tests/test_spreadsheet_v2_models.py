"""
Comprehensive unit tests for the new Pydantic models and style reference architecture.
"""

import pytest
from typing import Dict, Any
from app.models.api.spreadsheet_v2 import (
    StyleDefinition, 
    SpreadsheetDataV2, 
    HeaderData, 
    DataRow, 
    WorksheetData,
    SpreadsheetMetadata,
    WorksheetInfo
)
from app.services.spreadsheet.style_registry import StyleRegistry, StyleValidator
from app.services.spreadsheet.data_transformer import DataTransformationService


class TestStyleDefinition:
    """Test cases for StyleDefinition model"""
    
    def test_valid_style_definition(self):
        """Test creating a valid style definition"""
        style = StyleDefinition(
            id="test_style_1",
            background_color="#FF0000",
            font_color="#FFFFFF",
            font_weight="bold",
            font_style="italic",
            font_size=12
        )
        
        assert style.id == "test_style_1"
        assert style.background_color == "#FF0000"
        assert style.font_color == "#FFFFFF"
        assert style.font_weight == "bold"
        assert style.font_style == "italic"
        assert style.font_size == 12
    
    def test_minimal_style_definition(self):
        """Test creating a style definition with only required fields"""
        style = StyleDefinition(id="minimal_style")
        
        assert style.id == "minimal_style"
        assert style.background_color is None
        assert style.font_color is None
        assert style.font_weight is None
        assert style.font_style is None
        assert style.font_size is None
    
    def test_invalid_color_format(self):
        """Test validation of color format"""
        with pytest.raises(ValueError, match="Color must start with #"):
            StyleDefinition(id="invalid_color", background_color="FF0000")
    
    def test_invalid_font_weight(self):
        """Test validation of font weight"""
        with pytest.raises(ValueError, match="Font weight must be"):
            StyleDefinition(id="invalid_weight", font_weight="extra-bold")
    
    def test_invalid_font_style(self):
        """Test validation of font style"""
        with pytest.raises(ValueError, match="Font style must be"):
            StyleDefinition(id="invalid_style", font_style="underline")
    
    def test_invalid_alignment(self):
        """Test validation of alignment values"""
        with pytest.raises(ValueError, match="Horizontal alignment must be"):
            StyleDefinition(id="invalid_align", horizontal_alignment="justify")
        
        with pytest.raises(ValueError, match="Vertical alignment must be"):
            StyleDefinition(id="invalid_valign", vertical_alignment="baseline")


class TestSpreadsheetDataV2:
    """Test cases for SpreadsheetDataV2 model"""
    
    def test_empty_spreadsheet_data(self):
        """Test creating empty spreadsheet data"""
        data = SpreadsheetDataV2()
        
        assert data.metadata.version == "2.0"
        assert data.worksheet.name == "Sheet1"
        assert data.worksheet.range == "A1"
        assert len(data.data.rows) == 0
        assert len(data.styles) == 0
        assert len(data.columns) == 0
        assert len(data.charts) == 0
    
    def test_spreadsheet_with_styles(self):
        """Test creating spreadsheet data with styles"""
        styles = [
            StyleDefinition(id="header_style", background_color="#4472C4", font_color="#FFFFFF", font_weight="bold"),
            StyleDefinition(id="row_style", background_color="#F2F2F2")
        ]
        
        header = HeaderData(values=["Name", "Age", "Email"], style="header_style")
        rows = [
            DataRow(values=["John", 30, "john@example.com"], style="row_style"),
            DataRow(values=["Jane", 25, "jane@example.com"])
        ]
        
        data = SpreadsheetDataV2(
            data=WorksheetData(header=header, rows=rows),
            styles=styles
        )
        
        assert len(data.styles) == 2
        assert data.data.header.style == "header_style"
        assert data.data.rows[0].style == "row_style"
        assert data.data.rows[1].style is None


class TestStyleRegistry:
    """Test cases for StyleRegistry"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.registry = StyleRegistry()
    
    def test_add_style(self):
        """Test adding a style to the registry"""
        style = StyleDefinition(id="test_style", background_color="#FF0000")
        style_id = self.registry.add_style(style)
        
        assert style_id == "test_style"
        assert self.registry.get_style("test_style") is not None
        assert len(self.registry.get_all_styles()) == 1
    
    def test_add_duplicate_style(self):
        """Test adding duplicate styles - should return existing ID"""
        style1 = StyleDefinition(id="style1", background_color="#FF0000")
        style2 = StyleDefinition(id="style2", background_color="#FF0000")
        
        id1 = self.registry.add_style(style1)
        id2 = self.registry.add_style(style2)
        
        # Should return the same ID for identical styles
        assert id1 == id2
        assert len(self.registry.get_all_styles()) == 1
    
    def test_add_style_from_dict(self):
        """Test adding style from dictionary"""
        style_dict = {
            "background_color": "#FF0000",
            "font_color": "#FFFFFF",
            "font_weight": "bold"
        }
        
        style_id = self.registry.add_style_from_dict(style_dict)
        
        assert style_id is not None
        retrieved_style = self.registry.get_style(style_id)
        assert retrieved_style is not None
        assert retrieved_style.background_color == "#FF0000"
        assert retrieved_style.font_color == "#FFFFFF"
        assert retrieved_style.font_weight == "bold"
    
    def test_validate_style_reference(self):
        """Test style reference validation"""
        style = StyleDefinition(id="valid_style", background_color="#FF0000")
        self.registry.add_style(style)
        
        assert self.registry.validate_style_reference("valid_style") is True
        assert self.registry.validate_style_reference("invalid_style") is False
    
    def test_validate_all_references(self):
        """Test multiple style references validation"""
        style1 = StyleDefinition(id="style1", background_color="#FF0000")
        style2 = StyleDefinition(id="style2", background_color="#00FF00")
        
        self.registry.add_style(style1)
        self.registry.add_style(style2)
        
        # Test valid references
        is_valid, missing = self.registry.validate_all_references({"style1", "style2"})
        assert is_valid is True
        assert len(missing) == 0
        
        # Test with invalid reference
        is_valid, missing = self.registry.validate_all_references({"style1", "invalid_style"})
        assert is_valid is False
        assert "invalid_style" in missing
    
    def test_style_id_generation(self):
        """Test automatic style ID generation"""
        style_dict = {
            "background_color": "#4472C4",
            "font_color": "#FFFFFF",
            "font_weight": "bold"
        }
        
        style_id = self.registry.add_style_from_dict(style_dict)
        
        # Should generate meaningful ID
        assert "bg4472C4" in style_id
        assert "fcFFFFFF" in style_id
        assert "bold" in style_id


class TestStyleValidator:
    """Test cases for StyleValidator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.registry = StyleRegistry()
        self.validator = StyleValidator(self.registry)
    
    def test_validate_valid_spreadsheet_data(self):
        """Test validation of valid spreadsheet data"""
        data = {
            "styles": [
                {"id": "header_style", "background_color": "#4472C4", "font_color": "#FFFFFF"},
                {"id": "row_style", "background_color": "#F2F2F2"}
            ],
            "data": {
                "header": {"values": ["Name", "Age"], "style": "header_style"},
                "rows": [
                    {"values": ["John", 30], "style": "row_style"},
                    {"values": ["Jane", 25]}
                ]
            }
        }
        
        is_valid, errors = self.validator.validate_spreadsheet_data(data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_styles_array(self):
        """Test validation with missing styles array"""
        data = {
            "data": {
                "header": {"values": ["Name", "Age"], "style": "header_style"}
            }
        }
        
        is_valid, errors = self.validator.validate_spreadsheet_data(data)
        
        assert is_valid is False
        assert "Missing or invalid 'styles' array" in errors
    
    def test_validate_invalid_style_reference(self):
        """Test validation with invalid style references"""
        data = {
            "styles": [
                {"id": "valid_style", "background_color": "#FF0000"}
            ],
            "data": {
                "header": {"values": ["Name", "Age"], "style": "invalid_style"}
            }
        }
        
        is_valid, errors = self.validator.validate_spreadsheet_data(data)
        
        assert is_valid is False
        assert any("Style reference 'invalid_style' not found" in error for error in errors)
    
    def test_validate_duplicate_style_ids(self):
        """Test validation with duplicate style IDs"""
        data = {
            "styles": [
                {"id": "duplicate_style", "background_color": "#FF0000"},
                {"id": "duplicate_style", "background_color": "#00FF00"}
            ],
            "data": {"rows": []}
        }
        
        is_valid, errors = self.validator.validate_spreadsheet_data(data)
        
        assert is_valid is False
        assert any("Duplicate style ID" in error for error in errors)
    
    def test_validate_style_consistency(self):
        """Test style consistency validation"""
        data = {
            "styles": [
                {"id": "used_style", "background_color": "#FF0000"},
                {"id": "unused_style", "background_color": "#00FF00"}
            ],
            "data": {
                "header": {"values": ["Name"], "style": "used_style"},
                "rows": []
            }
        }
        
        is_consistent, warnings = self.validator.validate_style_consistency(data)
        
        assert is_consistent is True
        assert any("unused_style" in warning for warning in warnings)


class TestDataTransformationService:
    """Test cases for DataTransformationService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = DataTransformationService()
    
    def test_detect_format_version(self):
        """Test format version detection"""
        # Test V1.0 format (inline styles)
        v1_data = {
            "metadata": {"version": "1.0"},
            "data": {
                "header": {
                    "values": ["Name", "Age"],
                    "style": {"background_color": "#FF0000"}
                }
            }
        }
        
        assert self.service.detect_format_version(v1_data) == "1.0"
        
        # Test V2.0 format (style references)
        v2_data = {
            "metadata": {"version": "2.0"},
            "styles": [{"id": "style1", "background_color": "#FF0000"}],
            "data": {
                "header": {"values": ["Name", "Age"], "style": "style1"}
            }
        }
        
        assert self.service.detect_format_version(v2_data) == "2.0"
    
    def test_transform_to_new_format(self):
        """Test transformation from legacy to new format"""
        legacy_data = {
            "metadata": {"version": "1.0"},
            "data": {
                "header": {
                    "values": ["Name", "Age"],
                    "style": {"background_color": "#4472C4", "font_color": "#FFFFFF", "font_weight": "bold"}
                },
                "rows": [
                    {
                        "values": ["John", 30],
                        "style": {"background_color": "#F2F2F2"}
                    },
                    {
                        "values": ["Jane", 25],
                        "style": {"background_color": "#F2F2F2"}
                    }
                ]
            }
        }
        
        new_data, errors = self.service.transform_to_new_format(legacy_data)
        
        assert len(errors) == 0
        assert new_data["metadata"]["version"] == "2.0"
        assert "styles" in new_data
        assert len(new_data["styles"]) == 2  # Should consolidate duplicate row styles
        
        # Check that header style is now a reference
        assert isinstance(new_data["data"]["header"]["style"], str)
        
        # Check that row styles are now references
        for row in new_data["data"]["rows"]:
            assert isinstance(row["style"], str)
    
    def test_transform_to_legacy_format(self):
        """Test transformation from new to legacy format"""
        new_data = {
            "metadata": {"version": "2.0"},
            "styles": [
                {"id": "header_style", "background_color": "#4472C4", "font_color": "#FFFFFF", "font_weight": "bold"},
                {"id": "row_style", "background_color": "#F2F2F2"}
            ],
            "data": {
                "header": {"values": ["Name", "Age"], "style": "header_style"},
                "rows": [
                    {"values": ["John", 30], "style": "row_style"},
                    {"values": ["Jane", 25], "style": "row_style"}
                ]
            }
        }
        
        legacy_data, errors = self.service.transform_to_legacy_format(new_data)
        
        assert len(errors) == 0
        assert legacy_data["metadata"]["version"] == "1.0"
        assert "styles" not in legacy_data
        
        # Check that header style is now inline
        header_style = legacy_data["data"]["header"]["style"]
        assert isinstance(header_style, dict)
        assert header_style["background_color"] == "#4472C4"
        
        # Check that row styles are now inline
        for row in legacy_data["data"]["rows"]:
            row_style = row["style"]
            assert isinstance(row_style, dict)
            assert row_style["background_color"] == "#F2F2F2"
    
    def test_auto_transform_v1_to_v2(self):
        """Test automatic transformation from V1 to V2"""
        v1_data = {
            "metadata": {"version": "1.0"},
            "data": {
                "header": {
                    "values": ["Name"],
                    "style": {"background_color": "#FF0000"}
                }
            }
        }
        
        transformed_data, messages = self.service.auto_transform(v1_data, "2.0")
        
        assert "Detected format version: 1.0" in messages
        assert "Successfully transformed to new format" in messages
        assert transformed_data["metadata"]["version"] == "2.0"
    
    def test_auto_transform_same_version(self):
        """Test automatic transformation when already at target version"""
        v2_data = {
            "metadata": {"version": "2.0"},
            "styles": []
        }
        
        transformed_data, messages = self.service.auto_transform(v2_data, "2.0")
        
        assert "Data already in target format 2.0" in messages
        assert transformed_data == v2_data


if __name__ == "__main__":
    pytest.main([__file__])