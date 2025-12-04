"""
Test suite for SpreadsheetDataOptimizer JSON data optimization fixes
Tests the correct handling of header and rows sections when optimization flags are disabled
"""

import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from unittest.mock import Mock, MagicMock, patch

# Mock heavy dependencies before importing
with patch('app.services.database.vector_search.model.SentenceTransformer'):
    with patch('app.prompts.prompt_manager'):
        from app.services.spreadsheet.data_optimizer import SpreadsheetDataOptimizer
        from app.models.api.prompt import RequiredTableInfo


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def optimizer(mock_db_session):
    """Create optimizer instance with mock session"""
    return SpreadsheetDataOptimizer(mock_db_session)


class TestHeaderRangePreservation:
    """Test header range preservation when flags are false"""
    
    def test_header_with_range_only_when_all_flags_false(self, optimizer):
        """When both header flags are false, header should contain only range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "range": "A1:C1",
                    "style": "header_style"
                },
                "rows": []
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header should exist
        assert "header" in result["data"]
        # Header should have only range
        assert "range" in result["data"]["header"]
        assert result["data"]["header"]["range"] == "A1:C1"
        # Header should not have values or style
        assert "values" not in result["data"]["header"]
        assert "style" not in result["data"]["header"]
    
    def test_header_with_values_and_range_when_column_headers_true(self, optimizer):
        """When needs_column_headers is true, header should have values and range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "range": "A1:C1",
                    "style": "header_style"
                },
                "rows": []
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=True,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header should have values and range
        assert "header" in result["data"]
        assert "values" in result["data"]["header"]
        assert "range" in result["data"]["header"]
        assert result["data"]["header"]["values"] == ["Name", "Age", "City"]
        assert result["data"]["header"]["range"] == "A1:C1"
        # Header should not have style
        assert "style" not in result["data"]["header"]
    
    def test_header_with_style_and_range_when_header_styles_true(self, optimizer):
        """When needs_header_styles is true, header should have style and range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "range": "A1:C1",
                    "style": "header_style"
                },
                "rows": []
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=True,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header should have style and range
        assert "header" in result["data"]
        assert "style" in result["data"]["header"]
        assert "range" in result["data"]["header"]
        assert result["data"]["header"]["style"] == "header_style"
        assert result["data"]["header"]["range"] == "A1:C1"
        # Header should not have values
        assert "values" not in result["data"]["header"]
    
    def test_header_without_range_field(self, optimizer):
        """When header has no range field, header should still be included"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "style": "header_style"
                },
                "rows": []
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header should not be present (no range, no requested fields)
        assert "header" not in result["data"]


class TestRowsRangePreservation:
    """Test rows range preservation when flags are false"""
    
    def test_rows_with_range_only_when_all_flags_false(self, optimizer):
        """When both cell flags are false, rows should contain only range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {},
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    },
                    {
                        "values": ["Bob", 35, "Chicago"],
                        "range": "A4:C4"
                    }
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Rows should exist
        assert "rows" in result["data"]
        assert len(result["data"]["rows"]) == 2
        
        # Each row should have only range
        for row in result["data"]["rows"]:
            assert "range" in row
            assert "values" not in row
            assert "style" not in row
        
        # Verify ranges
        assert result["data"]["rows"][0]["range"] == "A2:C2"
        assert result["data"]["rows"][1]["range"] == "A4:C4"
    
    def test_rows_without_range_excluded_when_all_flags_false(self, optimizer):
        """Rows without range field should be excluded when both flags are false"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {},
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    },
                    {
                        "values": ["Jane", 25, "LA"],
                        "style": "row_style"
                        # No range field
                    },
                    {
                        "values": ["Bob", 35, "Chicago"],
                        "range": "A4:C4"
                    }
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Only 2 rows should be present (Jane excluded)
        assert "rows" in result["data"]
        assert len(result["data"]["rows"]) == 2
        assert result["data"]["rows"][0]["range"] == "A2:C2"
        assert result["data"]["rows"][1]["range"] == "A4:C4"
    
    def test_rows_with_values_and_range_when_cell_values_true(self, optimizer):
        """When needs_cell_values is true, rows should have values and range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {},
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    }
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=True,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Row should have values and range
        assert len(result["data"]["rows"]) == 1
        row = result["data"]["rows"][0]
        assert "values" in row
        assert "range" in row
        assert row["values"] == ["John", 30, "NYC"]
        assert row["range"] == "A2:C2"
        assert "style" not in row
    
    def test_rows_with_style_and_range_when_cell_styles_true(self, optimizer):
        """When needs_cell_styles is true, rows should have style and range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {},
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    }
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=True,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Row should have style and range
        assert len(result["data"]["rows"]) == 1
        row = result["data"]["rows"][0]
        assert "style" in row
        assert "range" in row
        assert row["style"] == "row_style"
        assert row["range"] == "A2:C2"
        assert "values" not in row
    
    def test_empty_rows_when_all_lack_range(self, optimizer):
        """When all rows lack range field, rows array should be empty"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {},
                "rows": [
                    {"values": ["John", 30, "NYC"], "style": "row_style"},
                    {"values": ["Jane", 25, "LA"], "style": "row_style"}
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Rows should be empty array
        assert "rows" in result["data"]
        assert len(result["data"]["rows"]) == 0


class TestMixedScenarios:
    """Test mixed flag scenarios"""
    
    def test_header_range_only_with_cell_values(self, optimizer):
        """Header with range only, rows with values and range"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "range": "A1:C1",
                    "style": "header_style"
                },
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    },
                    {
                        "values": ["Bob", 35, "Chicago"],
                        "range": "A4:C4"
                    }
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=True,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header should have only range
        assert "header" in result["data"]
        assert "range" in result["data"]["header"]
        assert result["data"]["header"]["range"] == "A1:C1"
        assert "values" not in result["data"]["header"]
        assert "style" not in result["data"]["header"]
        
        # Rows should have values and range
        assert len(result["data"]["rows"]) == 2
        for row in result["data"]["rows"]:
            assert "values" in row
            assert "range" in row
            assert "style" not in row
    
    def test_all_fields_enabled(self, optimizer):
        """When all flags are true, all fields should be included"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "range": "A1:C1",
                    "style": "header_style"
                },
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    }
                ]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=True,
            needs_header_styles=True,
            needs_cell_values=True,
            needs_cell_styles=True,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header should have all fields
        header = result["data"]["header"]
        assert "values" in header
        assert "range" in header
        assert "style" in header
        
        # Row should have all fields
        row = result["data"]["rows"][0]
        assert "values" in row
        assert "range" in row
        assert "style" in row


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_range_string_treated_as_valid(self, optimizer):
        """Empty string range should be treated as valid"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {"values": ["Name"], "range": ""},
                "rows": [{"values": ["John"], "range": ""}]
            }
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Header and row should still be included with empty range
        assert "header" in result["data"]
        assert result["data"]["header"]["range"] == ""
        assert len(result["data"]["rows"]) == 1
        assert result["data"]["rows"][0]["range"] == ""
    
    def test_no_data_section(self, optimizer):
        """When no data section exists, should handle gracefully"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"}
        }
        
        requirements = RequiredTableInfo(
            needs_column_headers=False,
            needs_header_styles=False,
            needs_cell_values=False,
            needs_cell_styles=False,
            needs_column_metadata=False
        )
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, requirements
        )
        
        # Data section should exist with empty rows
        assert "data" in result
        assert "rows" in result["data"]
        assert len(result["data"]["rows"]) == 0
        assert "header" not in result["data"]
    
    def test_backward_compatibility_none_requirements(self, optimizer):
        """When requirements is None, should return full data"""
        spreadsheet_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Sheet1", "range": "A1:C10"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "City"],
                    "range": "A1:C1",
                    "style": "header_style"
                },
                "rows": [
                    {
                        "values": ["John", 30, "NYC"],
                        "range": "A2:C2",
                        "style": "row_style"
                    }
                ]
            }
        }
        
        result = optimizer.filter_spreadsheet_data_by_requirements(
            spreadsheet_data, None
        )
        
        # Should return unchanged data
        assert result == spreadsheet_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
