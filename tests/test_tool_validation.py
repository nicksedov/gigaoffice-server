"""
Test Tool Validation and Fuzzy Matching
Validates the new tool name validation and correction features
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.mcp.tool_schemas import validate_tool_name, get_tools_list_for_prompt


def test_valid_tool_name():
    """Test validation of a correct tool name"""
    print("=" * 70)
    print("Test 1: Valid Tool Name")
    print("=" * 70)
    
    result = validate_tool_name("get_workbook_metadata")
    
    assert result["valid"] == True, "Should validate correct tool name"
    assert result["corrected_name"] is None, "Should not need correction"
    assert len(result["suggestions"]) == 0, "Should have no suggestions"
    
    print("✓ Valid tool name 'get_workbook_metadata' passed validation")
    print(f"  Result: {result}")
    print()


def test_tool_with_prefix():
    """Test auto-correction of tool name with invalid prefix"""
    print("=" * 70)
    print("Test 2: Tool Name with Invalid Prefix")
    print("=" * 70)
    
    result = validate_tool_name("excel.get_workbook_metadata")
    
    assert result["valid"] == True, "Should auto-correct and validate"
    assert result["corrected_name"] == "get_workbook_metadata", "Should strip 'excel.' prefix"
    assert result["original_name"] == "excel.get_workbook_metadata", "Should preserve original"
    
    print("✓ Tool name 'excel.get_workbook_metadata' auto-corrected")
    print(f"  Original: {result['original_name']}")
    print(f"  Corrected to: {result['corrected_name']}")
    print()


def test_invalid_tool_with_suggestions():
    """Test fuzzy matching for invalid tool name"""
    print("=" * 70)
    print("Test 3: Invalid Tool Name - Fuzzy Matching")
    print("=" * 70)
    
    result = validate_tool_name("get_sheet_names")
    
    assert result["valid"] == False, "Should reject invalid tool name"
    assert len(result["suggestions"]) > 0, "Should provide suggestions"
    assert "get_workbook_metadata" in result["suggestions"], "Should suggest closest match"
    
    print("✗ Invalid tool name 'get_sheet_names' rejected")
    print(f"  Suggestions: {result['suggestions']}")
    print(f"  Error message:")
    for line in result["error_message"].split("\n")[:5]:
        print(f"    {line}")
    print()


def test_completely_wrong_tool():
    """Test completely invalid tool name"""
    print("=" * 70)
    print("Test 4: Completely Invalid Tool Name")
    print("=" * 70)
    
    result = validate_tool_name("invalid_tool_xyz")
    
    assert result["valid"] == False, "Should reject invalid tool name"
    assert "Invalid tool name" in result["error_message"], "Should have error message"
    
    print("✗ Invalid tool name 'invalid_tool_xyz' rejected")
    print(f"  Has suggestions: {len(result['suggestions']) > 0}")
    print()


def test_tool_list_generation():
    """Test tool list generation for prompt"""
    print("=" * 70)
    print("Test 5: Tool List Generation for Prompt")
    print("=" * 70)
    
    tool_list = get_tools_list_for_prompt()
    
    assert len(tool_list) > 0, "Should generate tool list"
    assert "AVAILABLE TOOLS" in tool_list, "Should have header"
    assert "get_workbook_metadata" in tool_list, "Should include tool names"
    assert "CRITICAL" in tool_list, "Should have warning about prefixes"
    assert "excel." in tool_list, "Should mention invalid prefix example"
    
    print("✓ Tool list generated successfully")
    print(f"  Length: {len(tool_list)} characters")
    print(f"  Sample (first 500 chars):")
    print("-" * 70)
    print(tool_list[:500])
    print("-" * 70)
    print()


def test_multiple_prefix_types():
    """Test different prefix types"""
    print("=" * 70)
    print("Test 6: Multiple Prefix Types")
    print("=" * 70)
    
    prefixes = ["excel.", "mcp.", "spreadsheet."]
    base_tool = "create_worksheet"
    
    for prefix in prefixes:
        tool_name = f"{prefix}{base_tool}"
        result = validate_tool_name(tool_name)
        
        assert result["valid"] == True, f"Should auto-correct {prefix} prefix"
        assert result["corrected_name"] == base_tool, f"Should strip {prefix}"
        
        print(f"✓ Prefix '{prefix}' auto-corrected: {tool_name} -> {base_tool}")
    
    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "MCP Tool Validation Test Suite" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    tests = [
        test_valid_tool_name,
        test_tool_with_prefix,
        test_invalid_tool_with_suggestions,
        test_completely_wrong_tool,
        test_tool_list_generation,
        test_multiple_prefix_types
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test_func.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test_func.__name__}")
            print(f"  Exception: {e}")
            failed += 1
    
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print()
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("The tool validation system is working correctly:")
        print("  ✓ Valid tool names pass validation")
        print("  ✓ Invalid prefixes are auto-corrected")
        print("  ✓ Fuzzy matching suggests similar tools")
        print("  ✓ Comprehensive error messages provided")
        print("  ✓ Tool list generation for prompts working")
        print()
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
"""
Test Tool Validation and Fuzzy Matching
Validates the new tool name validation and correction features
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.mcp.tool_schemas import validate_tool_name, get_tools_list_for_prompt


def test_valid_tool_name():
    """Test validation of a correct tool name"""
    print("=" * 70)
    print("Test 1: Valid Tool Name")
    print("=" * 70)
    
    result = validate_tool_name("get_workbook_metadata")
    
    assert result["valid"] == True, "Should validate correct tool name"
    assert result["corrected_name"] is None, "Should not need correction"
    assert len(result["suggestions"]) == 0, "Should have no suggestions"
    
    print("✓ Valid tool name 'get_workbook_metadata' passed validation")
    print(f"  Result: {result}")
    print()


def test_tool_with_prefix():
    """Test auto-correction of tool name with invalid prefix"""
    print("=" * 70)
    print("Test 2: Tool Name with Invalid Prefix")
    print("=" * 70)
    
    result = validate_tool_name("excel.get_workbook_metadata")
    
    assert result["valid"] == True, "Should auto-correct and validate"
    assert result["corrected_name"] == "get_workbook_metadata", "Should strip 'excel.' prefix"
    assert result["original_name"] == "excel.get_workbook_metadata", "Should preserve original"
    
    print("✓ Tool name 'excel.get_workbook_metadata' auto-corrected")
    print(f"  Original: {result['original_name']}")
    print(f"  Corrected to: {result['corrected_name']}")
    print()


def test_invalid_tool_with_suggestions():
    """Test fuzzy matching for invalid tool name"""
    print("=" * 70)
    print("Test 3: Invalid Tool Name - Fuzzy Matching")
    print("=" * 70)
    
    result = validate_tool_name("get_sheet_names")
    
    assert result["valid"] == False, "Should reject invalid tool name"
    assert len(result["suggestions"]) > 0, "Should provide suggestions"
    assert "get_workbook_metadata" in result["suggestions"], "Should suggest closest match"
    
    print("✗ Invalid tool name 'get_sheet_names' rejected")
    print(f"  Suggestions: {result['suggestions']}")
    print(f"  Error message:")
    for line in result["error_message"].split("\n")[:5]:
        print(f"    {line}")
    print()


def test_completely_wrong_tool():
    """Test completely invalid tool name"""
    print("=" * 70)
    print("Test 4: Completely Invalid Tool Name")
    print("=" * 70)
    
    result = validate_tool_name("invalid_tool_xyz")
    
    assert result["valid"] == False, "Should reject invalid tool name"
    assert "Invalid tool name" in result["error_message"], "Should have error message"
    
    print("✗ Invalid tool name 'invalid_tool_xyz' rejected")
    print(f"  Has suggestions: {len(result['suggestions']) > 0}")
    print()


def test_tool_list_generation():
    """Test tool list generation for prompt"""
    print("=" * 70)
    print("Test 5: Tool List Generation for Prompt")
    print("=" * 70)
    
    tool_list = get_tools_list_for_prompt()
    
    assert len(tool_list) > 0, "Should generate tool list"
    assert "AVAILABLE TOOLS" in tool_list, "Should have header"
    assert "get_workbook_metadata" in tool_list, "Should include tool names"
    assert "CRITICAL" in tool_list, "Should have warning about prefixes"
    assert "excel." in tool_list, "Should mention invalid prefix example"
    
    print("✓ Tool list generated successfully")
    print(f"  Length: {len(tool_list)} characters")
    print(f"  Sample (first 500 chars):")
    print("-" * 70)
    print(tool_list[:500])
    print("-" * 70)
    print()


def test_multiple_prefix_types():
    """Test different prefix types"""
    print("=" * 70)
    print("Test 6: Multiple Prefix Types")
    print("=" * 70)
    
    prefixes = ["excel.", "mcp.", "spreadsheet."]
    base_tool = "create_worksheet"
    
    for prefix in prefixes:
        tool_name = f"{prefix}{base_tool}"
        result = validate_tool_name(tool_name)
        
        assert result["valid"] == True, f"Should auto-correct {prefix} prefix"
        assert result["corrected_name"] == base_tool, f"Should strip {prefix}"
        
        print(f"✓ Prefix '{prefix}' auto-corrected: {tool_name} -> {base_tool}")
    
    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "MCP Tool Validation Test Suite" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    tests = [
        test_valid_tool_name,
        test_tool_with_prefix,
        test_invalid_tool_with_suggestions,
        test_completely_wrong_tool,
        test_tool_list_generation,
        test_multiple_prefix_types
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test_func.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test_func.__name__}")
            print(f"  Exception: {e}")
            failed += 1
    
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print()
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("The tool validation system is working correctly:")
        print("  ✓ Valid tool names pass validation")
        print("  ✓ Invalid prefixes are auto-corrected")
        print("  ✓ Fuzzy matching suggests similar tools")
        print("  ✓ Comprehensive error messages provided")
        print("  ✓ Tool list generation for prompts working")
        print()
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
