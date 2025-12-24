"""
Test script for MCP tool schema validation
Tests the complete schema system without requiring MCP server connection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.mcp.tool_schemas import (
    get_tool_schema,
    create_pydantic_schema,
    generate_enhanced_docstring,
    list_available_tools,
    validate_schema_completeness
)
from app.services.mcp.schema_validator import schema_validator


def test_schema_registry():
    """Test that schemas are properly loaded"""
    print("=" * 70)
    print("Test 1: Schema Registry Loading")
    print("=" * 70)
    
    tools = list_available_tools()
    print(f"✓ Loaded {len(tools)} tool schemas")
    print(f"  Tools: {', '.join(tools[:5])}...")
    print()
    
    return True


def test_schema_retrieval():
    """Test retrieving individual schemas"""
    print("=" * 70)
    print("Test 2: Schema Retrieval")
    print("=" * 70)
    
    # Test get_workbook_metadata schema
    schema = get_tool_schema("get_workbook_metadata")
    
    if not schema:
        print("✗ Failed to retrieve schema for get_workbook_metadata")
        return False
    
    print("✓ Retrieved schema for 'get_workbook_metadata'")
    print(f"  Description: {schema['description']}")
    print(f"  Parameters: {', '.join(schema['parameters'].keys())}")
    
    # Check filepath parameter
    filepath_param = schema['parameters'].get('filepath')
    if filepath_param:
        print(f"  Filepath parameter: {filepath_param['description']}")
    
    print()
    return True


def test_pydantic_schema_generation():
    """Test Pydantic model generation"""
    print("=" * 70)
    print("Test 3: Pydantic Schema Generation")
    print("=" * 70)
    
    schema = get_tool_schema("write_data_to_excel")
    if not schema:
        print("✗ Failed to retrieve schema")
        return False
    
    try:
        pydantic_model = create_pydantic_schema("write_data_to_excel", schema)
        print("✓ Generated Pydantic model successfully")
        print(f"  Model name: {pydantic_model.__name__}")
        print(f"  Fields: {', '.join(pydantic_model.model_fields.keys())}")
        
        # Test validation with valid data
        test_data = {
            "filepath": "/path/to/file.xlsx",
            "sheet_name": "Sheet1",
            "data": [["Header1", "Header2"], ["Value1", "Value2"]],
            "start_cell": "A1"
        }
        
        instance = pydantic_model(**test_data)
        print("✓ Validation passed for valid data")
        
        # Test validation with missing required field
        try:
            invalid_data = {"filepath": "/path/to/file.xlsx"}
            instance = pydantic_model(**invalid_data)
            print("✗ Validation should have failed for missing required fields")
            return False
        except Exception as e:
            print(f"✓ Validation correctly rejected invalid data: {type(e).__name__}")
        
    except Exception as e:
        print(f"✗ Failed to generate Pydantic model: {e}")
        return False
    
    print()
    return True


def test_docstring_generation():
    """Test enhanced docstring generation"""
    print("=" * 70)
    print("Test 4: Enhanced Docstring Generation")
    print("=" * 70)
    
    schema = get_tool_schema("create_chart")
    if not schema:
        print("✗ Failed to retrieve schema")
        return False
    
    try:
        docstring = generate_enhanced_docstring("create_chart", schema)
        print("✓ Generated enhanced docstring")
        print("\nDocstring preview:")
        print("-" * 70)
        lines = docstring.split('\n')
        for line in lines[:15]:  # Show first 15 lines
            print(f"  {line}")
        if len(lines) > 15:
            print(f"  ... ({len(lines) - 15} more lines)")
        print("-" * 70)
        
        # Check for key components
        checks = {
            "Has description": schema['description'] in docstring,
            "Has Parameters section": "Parameters:" in docstring,
            "Has filepath parameter": "filepath" in docstring,
            "Has auto-inject note": "auto-inject" in docstring.lower() or "do not provide" in docstring.lower(),
            "Has Returns section": "Returns:" in docstring
        }
        
        for check_name, check_result in checks.items():
            status = "✓" if check_result else "✗"
            print(f"{status} {check_name}")
        
        if not all(checks.values()):
            return False
        
    except Exception as e:
        print(f"✗ Failed to generate docstring: {e}")
        return False
    
    print()
    return True


def test_schema_validation():
    """Test schema validation system"""
    print("=" * 70)
    print("Test 5: Schema Validation System")
    print("=" * 70)
    
    # Run validation
    validation_result = schema_validator.validate_all_schemas()
    
    print(f"Validation Status: {'PASSED' if validation_result['valid'] else 'FAILED'}")
    print(f"Total Tools: {validation_result['total_tools']}")
    print(f"Errors: {validation_result['error_count']}")
    print(f"Warnings: {validation_result['warning_count']}")
    
    if validation_result['errors']:
        print("\nErrors found:")
        for error in validation_result['errors'][:5]:
            print(f"  - {error}")
        if len(validation_result['errors']) > 5:
            print(f"  ... and {len(validation_result['errors']) - 5} more")
    
    if validation_result['warnings']:
        print("\nWarnings found:")
        for warning in validation_result['warnings'][:5]:
            print(f"  - {warning}")
        if len(validation_result['warnings']) > 5:
            print(f"  ... and {len(validation_result['warnings']) - 5} more")
    
    print()
    
    # Check filepath auto-injection
    filepath_check = schema_validator.check_filepath_auto_injection()
    print("Filepath Auto-Injection Check:")
    print(f"  Tools with filepath: {filepath_check['with_filepath']}/{filepath_check['total_tools']}")
    print(f"  With proper note: {filepath_check['proper_auto_inject_note']}")
    print(f"  Missing note: {filepath_check['missing_auto_inject_note']}")
    
    print()
    return validation_result['valid']


def test_completeness_check():
    """Test schema completeness validation"""
    print("=" * 70)
    print("Test 6: Schema Completeness Check")
    print("=" * 70)
    
    result = validate_schema_completeness()
    
    print(f"Completeness: {'VALID' if result['valid'] else 'INVALID'}")
    print(f"Total Tools: {result['total_tools']}")
    print(f"Issues: {len(result['issues'])}")
    
    if result['issues']:
        print("\nIssues found:")
        for issue in result['issues'][:10]:
            print(f"  - {issue}")
        if len(result['issues']) > 10:
            print(f"  ... and {len(result['issues']) - 10} more")
    
    print()
    return result['valid']


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("MCP Tool Schema System Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        ("Schema Registry Loading", test_schema_registry),
        ("Schema Retrieval", test_schema_retrieval),
        ("Pydantic Schema Generation", test_pydantic_schema_generation),
        ("Enhanced Docstring Generation", test_docstring_generation),
        ("Schema Validation System", test_schema_validation),
        ("Schema Completeness Check", test_completeness_check)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed successfully!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
"""
Test script for MCP tool schema validation
Tests the complete schema system without requiring MCP server connection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.mcp.tool_schemas import (
    get_tool_schema,
    create_pydantic_schema,
    generate_enhanced_docstring,
    list_available_tools,
    validate_schema_completeness
)
from app.services.mcp.schema_validator import schema_validator


def test_schema_registry():
    """Test that schemas are properly loaded"""
    print("=" * 70)
    print("Test 1: Schema Registry Loading")
    print("=" * 70)
    
    tools = list_available_tools()
    print(f"✓ Loaded {len(tools)} tool schemas")
    print(f"  Tools: {', '.join(tools[:5])}...")
    print()
    
    return True


def test_schema_retrieval():
    """Test retrieving individual schemas"""
    print("=" * 70)
    print("Test 2: Schema Retrieval")
    print("=" * 70)
    
    # Test get_workbook_metadata schema
    schema = get_tool_schema("get_workbook_metadata")
    
    if not schema:
        print("✗ Failed to retrieve schema for get_workbook_metadata")
        return False
    
    print("✓ Retrieved schema for 'get_workbook_metadata'")
    print(f"  Description: {schema['description']}")
    print(f"  Parameters: {', '.join(schema['parameters'].keys())}")
    
    # Check filepath parameter
    filepath_param = schema['parameters'].get('filepath')
    if filepath_param:
        print(f"  Filepath parameter: {filepath_param['description']}")
    
    print()
    return True


def test_pydantic_schema_generation():
    """Test Pydantic model generation"""
    print("=" * 70)
    print("Test 3: Pydantic Schema Generation")
    print("=" * 70)
    
    schema = get_tool_schema("write_data_to_excel")
    if not schema:
        print("✗ Failed to retrieve schema")
        return False
    
    try:
        pydantic_model = create_pydantic_schema("write_data_to_excel", schema)
        print("✓ Generated Pydantic model successfully")
        print(f"  Model name: {pydantic_model.__name__}")
        print(f"  Fields: {', '.join(pydantic_model.model_fields.keys())}")
        
        # Test validation with valid data
        test_data = {
            "filepath": "/path/to/file.xlsx",
            "sheet_name": "Sheet1",
            "data": [["Header1", "Header2"], ["Value1", "Value2"]],
            "start_cell": "A1"
        }
        
        instance = pydantic_model(**test_data)
        print("✓ Validation passed for valid data")
        
        # Test validation with missing required field
        try:
            invalid_data = {"filepath": "/path/to/file.xlsx"}
            instance = pydantic_model(**invalid_data)
            print("✗ Validation should have failed for missing required fields")
            return False
        except Exception as e:
            print(f"✓ Validation correctly rejected invalid data: {type(e).__name__}")
        
    except Exception as e:
        print(f"✗ Failed to generate Pydantic model: {e}")
        return False
    
    print()
    return True


def test_docstring_generation():
    """Test enhanced docstring generation"""
    print("=" * 70)
    print("Test 4: Enhanced Docstring Generation")
    print("=" * 70)
    
    schema = get_tool_schema("create_chart")
    if not schema:
        print("✗ Failed to retrieve schema")
        return False
    
    try:
        docstring = generate_enhanced_docstring("create_chart", schema)
        print("✓ Generated enhanced docstring")
        print("\nDocstring preview:")
        print("-" * 70)
        lines = docstring.split('\n')
        for line in lines[:15]:  # Show first 15 lines
            print(f"  {line}")
        if len(lines) > 15:
            print(f"  ... ({len(lines) - 15} more lines)")
        print("-" * 70)
        
        # Check for key components
        checks = {
            "Has description": schema['description'] in docstring,
            "Has Parameters section": "Parameters:" in docstring,
            "Has filepath parameter": "filepath" in docstring,
            "Has auto-inject note": "auto-inject" in docstring.lower() or "do not provide" in docstring.lower(),
            "Has Returns section": "Returns:" in docstring
        }
        
        for check_name, check_result in checks.items():
            status = "✓" if check_result else "✗"
            print(f"{status} {check_name}")
        
        if not all(checks.values()):
            return False
        
    except Exception as e:
        print(f"✗ Failed to generate docstring: {e}")
        return False
    
    print()
    return True


def test_schema_validation():
    """Test schema validation system"""
    print("=" * 70)
    print("Test 5: Schema Validation System")
    print("=" * 70)
    
    # Run validation
    validation_result = schema_validator.validate_all_schemas()
    
    print(f"Validation Status: {'PASSED' if validation_result['valid'] else 'FAILED'}")
    print(f"Total Tools: {validation_result['total_tools']}")
    print(f"Errors: {validation_result['error_count']}")
    print(f"Warnings: {validation_result['warning_count']}")
    
    if validation_result['errors']:
        print("\nErrors found:")
        for error in validation_result['errors'][:5]:
            print(f"  - {error}")
        if len(validation_result['errors']) > 5:
            print(f"  ... and {len(validation_result['errors']) - 5} more")
    
    if validation_result['warnings']:
        print("\nWarnings found:")
        for warning in validation_result['warnings'][:5]:
            print(f"  - {warning}")
        if len(validation_result['warnings']) > 5:
            print(f"  ... and {len(validation_result['warnings']) - 5} more")
    
    print()
    
    # Check filepath auto-injection
    filepath_check = schema_validator.check_filepath_auto_injection()
    print("Filepath Auto-Injection Check:")
    print(f"  Tools with filepath: {filepath_check['with_filepath']}/{filepath_check['total_tools']}")
    print(f"  With proper note: {filepath_check['proper_auto_inject_note']}")
    print(f"  Missing note: {filepath_check['missing_auto_inject_note']}")
    
    print()
    return validation_result['valid']


def test_completeness_check():
    """Test schema completeness validation"""
    print("=" * 70)
    print("Test 6: Schema Completeness Check")
    print("=" * 70)
    
    result = validate_schema_completeness()
    
    print(f"Completeness: {'VALID' if result['valid'] else 'INVALID'}")
    print(f"Total Tools: {result['total_tools']}")
    print(f"Issues: {len(result['issues'])}")
    
    if result['issues']:
        print("\nIssues found:")
        for issue in result['issues'][:10]:
            print(f"  - {issue}")
        if len(result['issues']) > 10:
            print(f"  ... and {len(result['issues']) - 10} more")
    
    print()
    return result['valid']


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("MCP Tool Schema System Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        ("Schema Registry Loading", test_schema_registry),
        ("Schema Retrieval", test_schema_retrieval),
        ("Pydantic Schema Generation", test_pydantic_schema_generation),
        ("Enhanced Docstring Generation", test_docstring_generation),
        ("Schema Validation System", test_schema_validation),
        ("Schema Completeness Check", test_completeness_check)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed successfully!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
