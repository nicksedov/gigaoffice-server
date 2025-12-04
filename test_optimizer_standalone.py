"""
Standalone test for data optimizer logic
Tests the filter_spreadsheet_data_by_requirements method directly
"""

import json
from typing import Dict, Any, Optional


class RequiredTableInfo:
    """Simple test version of RequiredTableInfo"""
    def __init__(self, needs_column_headers=False, needs_header_styles=False,
                 needs_cell_values=False, needs_cell_styles=False, needs_column_metadata=False):
        self.needs_column_headers = needs_column_headers
        self.needs_header_styles = needs_header_styles
        self.needs_cell_values = needs_cell_values
        self.needs_cell_styles = needs_cell_styles
        self.needs_column_metadata = needs_column_metadata


def filter_spreadsheet_data_by_requirements(
    spreadsheet_data: Dict[str, Any],
    required_table_info: Optional[RequiredTableInfo]
) -> Dict[str, Any]:
    """
    Extracted filter logic from SpreadsheetDataOptimizer
    """
    if required_table_info is None:
        return spreadsheet_data
    
    filtered_data = {
        "metadata": spreadsheet_data.get("metadata", {}),
        "worksheet": spreadsheet_data.get("worksheet", {}),
        "data": {}
    }
    
    original_data = spreadsheet_data.get("data", {})
    filtered_data_section: Dict[str, Any] = {}
    
    # Process header - always process if header exists to preserve range metadata
    original_header = original_data.get("header")
    if original_header:
        filtered_header: Dict[str, Any] = {}
        
        # Include header values if requested
        if required_table_info.needs_column_headers:
            filtered_header["values"] = original_header.get("values", [])
        
        # Include header style if requested
        if required_table_info.needs_header_styles:
            if "style" in original_header:
                filtered_header["style"] = original_header["style"]
        
        # Always include range if present (structural metadata)
        if "range" in original_header:
            filtered_header["range"] = original_header["range"]
        
        # Include header if it has any content (including range-only)
        if filtered_header:
            filtered_data_section["header"] = filtered_header
    
    # Process rows - always process if rows exist to preserve range metadata
    original_rows = original_data.get("rows", [])
    filtered_rows = []
    
    for row in original_rows:
        # Only process rows that have a range field
        if "range" not in row:
            continue
        
        filtered_row: Dict[str, Any] = {}
        
        # Include row values if requested
        if required_table_info.needs_cell_values and "values" in row:
            filtered_row["values"] = row["values"]
        
        # Include row style if requested
        if required_table_info.needs_cell_styles and "style" in row:
            filtered_row["style"] = row["style"]
        
        # Always include range (structural metadata)
        filtered_row["range"] = row["range"]
        
        # Add row (it will always have at least range)
        filtered_rows.append(filtered_row)
    
    # Always include rows array (even if empty)
    filtered_data_section["rows"] = filtered_rows
    
    # Add data section
    filtered_data["data"] = filtered_data_section
    
    # Include column metadata if requested
    if required_table_info.needs_column_metadata:
        if "columns" in spreadsheet_data:
            filtered_data["columns"] = spreadsheet_data["columns"]
    
    return filtered_data


def test_header_range_only_all_flags_false():
    """Test Issue 2: Header should contain only range when both flags are false"""
    print("\n=== Test 1: Header with range only when all flags false ===")
    
    data = {
        "metadata": {"version": "1.0"},
        "worksheet": {"name": "Sheet1"},
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
        needs_cell_styles=False
    )
    
    result = filter_spreadsheet_data_by_requirements(data, requirements)
    
    assert "header" in result["data"], "Header should exist"
    assert "range" in result["data"]["header"], "Header should have range"
    assert result["data"]["header"]["range"] == "A1:C1", "Range value should match"
    assert "values" not in result["data"]["header"], "Header should NOT have values"
    assert "style" not in result["data"]["header"], "Header should NOT have style"
    
    print("✓ Header contains only range field")
    print(f"  Result: {json.dumps(result['data']['header'], indent=2)}")


def test_rows_range_only_all_flags_false():
    """Test Issue 1: Rows should contain only range when both flags are false"""
    print("\n=== Test 2: Rows with range only when all flags false ===")
    
    data = {
        "metadata": {"version": "1.0"},
        "worksheet": {"name": "Sheet1"},
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
        needs_cell_styles=False
    )
    
    result = filter_spreadsheet_data_by_requirements(data, requirements)
    
    assert "rows" in result["data"], "Rows should exist"
    assert len(result["data"]["rows"]) == 2, "Should have 2 rows"
    
    for i, row in enumerate(result["data"]["rows"]):
        assert "range" in row, f"Row {i} should have range"
        assert "values" not in row, f"Row {i} should NOT have values"
        assert "style" not in row, f"Row {i} should NOT have style"
    
    print("✓ Rows contain only range field")
    print(f"  Result: {json.dumps(result['data']['rows'], indent=2)}")


def test_rows_without_range_excluded():
    """Test that rows without range are excluded when flags are false"""
    print("\n=== Test 3: Rows without range should be excluded ===")
    
    data = {
        "metadata": {"version": "1.0"},
        "worksheet": {"name": "Sheet1"},
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
        needs_cell_styles=False
    )
    
    result = filter_spreadsheet_data_by_requirements(data, requirements)
    
    assert "rows" in result["data"], "Rows should exist"
    assert len(result["data"]["rows"]) == 2, "Should have only 2 rows (Jane excluded)"
    assert result["data"]["rows"][0]["range"] == "A2:C2"
    assert result["data"]["rows"][1]["range"] == "A4:C4"
    
    print("✓ Row without range was excluded")
    print(f"  Result: {len(result['data']['rows'])} rows (expected 2)")


def test_mixed_scenario():
    """Test mixed scenario: header range-only, rows with values"""
    print("\n=== Test 4: Mixed scenario - header range, rows with values ===")
    
    data = {
        "metadata": {"version": "1.0"},
        "worksheet": {"name": "Sheet1"},
        "data": {
            "header": {
                "values": ["Name", "Age"],
                "range": "A1:B1",
                "style": "header_style"
            },
            "rows": [
                {
                    "values": ["John", 30],
                    "range": "A2:B2",
                    "style": "row_style"
                }
            ]
        }
    }
    
    requirements = RequiredTableInfo(
        needs_column_headers=False,  # Header: range only
        needs_header_styles=False,
        needs_cell_values=True,      # Rows: values + range
        needs_cell_styles=False
    )
    
    result = filter_spreadsheet_data_by_requirements(data, requirements)
    
    # Check header
    assert "range" in result["data"]["header"]
    assert "values" not in result["data"]["header"]
    assert "style" not in result["data"]["header"]
    
    # Check rows
    assert len(result["data"]["rows"]) == 1
    assert "values" in result["data"]["rows"][0]
    assert "range" in result["data"]["rows"][0]
    assert "style" not in result["data"]["rows"][0]
    
    print("✓ Header has range only, rows have values + range")
    print(f"  Header: {json.dumps(result['data']['header'], indent=2)}")
    print(f"  Row: {json.dumps(result['data']['rows'][0], indent=2)}")


def test_all_flags_enabled():
    """Test that all fields are included when all flags are true"""
    print("\n=== Test 5: All flags enabled - all fields included ===")
    
    data = {
        "metadata": {"version": "1.0"},
        "worksheet": {"name": "Sheet1"},
        "data": {
            "header": {
                "values": ["Name"],
                "range": "A1",
                "style": "header_style"
            },
            "rows": [
                {
                    "values": ["John"],
                    "range": "A2",
                    "style": "row_style"
                }
            ]
        }
    }
    
    requirements = RequiredTableInfo(
        needs_column_headers=True,
        needs_header_styles=True,
        needs_cell_values=True,
        needs_cell_styles=True
    )
    
    result = filter_spreadsheet_data_by_requirements(data, requirements)
    
    # Check header has all fields
    assert "values" in result["data"]["header"]
    assert "range" in result["data"]["header"]
    assert "style" in result["data"]["header"]
    
    # Check row has all fields
    assert "values" in result["data"]["rows"][0]
    assert "range" in result["data"]["rows"][0]
    assert "style" in result["data"]["rows"][0]
    
    print("✓ All fields included in header and rows")


def run_all_tests():
    """Run all test cases"""
    print("="*70)
    print("TESTING JSON DATA OPTIMIZATION LOGIC FIX")
    print("="*70)
    
    try:
        test_header_range_only_all_flags_false()
        test_rows_range_only_all_flags_false()
        test_rows_without_range_excluded()
        test_mixed_scenario()
        test_all_flags_enabled()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        return True
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
