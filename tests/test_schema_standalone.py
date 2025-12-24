"""
Standalone test for MCP tool schema validation
Tests schemas without importing executor or client modules
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_schemas_standalone():
    """Test schema loading and validation standalone"""
    print("=" * 70)
    print("MCP Tool Schema Standalone Test")
    print("=" * 70)
    print()
    
    # Import only the schema modules
    from app.services.mcp.tool_schemas import (
        MCP_TOOL_SCHEMAS,
        get_tool_schema,
        create_pydantic_schema,
        generate_enhanced_docstring,
        list_available_tools,
        validate_schema_completeness
    )
    
    # Test 1: Schema count
    print("Test 1: Schema Registry")
    print("-" * 70)
    tools = list_available_tools()
    print(f"✓ Loaded {len(tools)} tool schemas")
    print(f"  Sample tools: {', '.join(tools[:5])}")
    print()
    
    # Test 2: Specific schema retrieval
    print("Test 2: Get Workbook Metadata Schema")
    print("-" * 70)
    schema = get_tool_schema("get_workbook_metadata")
    if schema:
        print("✓ Schema retrieved successfully")
        print(f"  Description: {schema['description']}")
        print(f"  Parameters: {list(schema['parameters'].keys())}")
        
        # Check filepath parameter
        if 'filepath' in schema['parameters']:
            fp = schema['parameters']['filepath']
            print(f"  Filepath required: {fp['required']}")
            print(f"  Filepath description: {fp['description'][:60]}...")
    else:
        print("✗ Failed to retrieve schema")
        return False
    print()
    
    # Test 3: Pydantic model generation
    print("Test 3: Pydantic Model Generation")
    print("-" * 70)
    try:
        pydantic_model = create_pydantic_schema("get_workbook_metadata", schema)
        print(f"✓ Generated Pydantic model: {pydantic_model.__name__}")
        print(f"  Fields: {list(pydantic_model.model_fields.keys())}")
        
        # Test validation
        valid_data = {"filepath": "/test.xlsx", "include_ranges": False}
        instance = pydantic_model(**valid_data)
        print("✓ Validation works for valid data")
        
        # Test with missing required field (should fail)
        try:
            invalid_data = {"include_ranges": True}  # Missing filepath
            instance = pydantic_model(**invalid_data)
            print("✗ Should have failed validation")
            return False
        except Exception:
            print("✓ Correctly rejects invalid data")
            
    except Exception as e:
        print(f"✗ Pydantic generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test 4: Docstring generation
    print("Test 4: Enhanced Docstring Generation")
    print("-" * 70)
    docstring = generate_enhanced_docstring("get_workbook_metadata", schema)
    print("✓ Generated enhanced docstring")
    print("\nDocstring Preview:")
    print("-" * 70)
    for line in docstring.split('\n')[:10]:
        print(f"  {line}")
    print("  ...")
    print("-" * 70)
    
    # Check key elements
    has_description = schema['description'] in docstring
    has_params = "Parameters:" in docstring
    has_filepath = "filepath" in docstring
    has_note = "auto" in docstring.lower() or "inject" in docstring.lower()
    
    print(f"  {'✓' if has_description else '✗'} Contains description")
    print(f"  {'✓' if has_params else '✗'} Has Parameters section")
    print(f"  {'✓' if has_filepath else '✗'} Documents filepath parameter")
    print(f"  {'✓' if has_note else '✗'} Has auto-injection note")
    
    if not (has_description and has_params and has_filepath and has_note):
        print("✗ Docstring missing required elements")
        return False
    print()
    
    # Test 5: Schema completeness
    print("Test 5: Schema Completeness Validation")
    print("-" * 70)
    completeness = validate_schema_completeness()
    print(f"  Valid: {completeness['valid']}")
    print(f"  Total tools: {completeness['total_tools']}")
    print(f"  Issues: {len(completeness['issues'])}")
    
    if completeness['issues']:
        print("\n  Issues found:")
        for issue in completeness['issues'][:5]:
            print(f"    - {issue}")
        if len(completeness['issues']) > 5:
            print(f"    ... and {len(completeness['issues']) - 5} more")
    
    if not completeness['valid']:
        print("✗ Schema completeness check failed")
        return False
    
    print("✓ All schemas are complete")
    print()
    
    # Test 6: Check all tools have schemas
    print("Test 6: Verify All Tool Schemas")
    print("-" * 70)
    expected_tools = [
        "get_workbook_metadata",
        "write_data_to_excel",
        "create_worksheet",
        "format_range",
        "create_chart"
    ]
    
    missing = []
    for tool in expected_tools:
        if tool not in MCP_TOOL_SCHEMAS:
            missing.append(tool)
    
    if missing:
        print(f"✗ Missing schemas: {missing}")
        return False
    
    print(f"✓ All {len(expected_tools)} expected tools have schemas")
    print()
    
    # Test 7: Filepath parameter check
    print("Test 7: Filepath Parameter Verification")
    print("-" * 70)
    tools_without_filepath = []
    tools_without_auto_note = []
    
    for tool_name in tools:
        schema = MCP_TOOL_SCHEMAS.get(tool_name)
        if not schema or 'parameters' not in schema:
            continue
        
        if 'filepath' not in schema['parameters']:
            tools_without_filepath.append(tool_name)
        else:
            desc = schema['parameters']['filepath'].get('description', '').lower()
            if 'auto' not in desc and 'do not provide' not in desc:
                tools_without_auto_note.append(tool_name)
    
    print(f"  Tools total: {len(tools)}")
    print(f"  With filepath parameter: {len(tools) - len(tools_without_filepath)}")
    print(f"  With auto-injection note: {len(tools) - len(tools_without_auto_note)}")
    
    if tools_without_filepath:
        print(f"\n  ⚠ Tools without filepath: {', '.join(tools_without_filepath[:3])}")
    
    if tools_without_auto_note:
        print(f"  ⚠ Tools missing auto-inject note: {', '.join(tools_without_auto_note[:3])}")
    
    print()
    
    return True


def main():
    """Run standalone test"""
    print("\n" + "=" * 70)
    print("MCP Tool Schema System - Standalone Validation")
    print("=" * 70)
    print()
    
    try:
        success = test_schemas_standalone()
        
        print("=" * 70)
        if success:
            print("✓ All Tests Passed!")
            print("=" * 70)
            print("\nSchema system is ready for use:")
            print("  - All tool schemas are properly defined")
            print("  - Pydantic models generate correctly")
            print("  - Enhanced docstrings are created")
            print("  - Filepath auto-injection is documented")
            print("\nThe MCP tool contract validation system is operational.")
            return 0
        else:
            print("✗ Some Tests Failed")
            print("=" * 70)
            return 1
            
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
"""
Standalone test for MCP tool schema validation
Tests schemas without importing executor or client modules
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_schemas_standalone():
    """Test schema loading and validation standalone"""
    print("=" * 70)
    print("MCP Tool Schema Standalone Test")
    print("=" * 70)
    print()
    
    # Import only the schema modules
    from app.services.mcp.tool_schemas import (
        MCP_TOOL_SCHEMAS,
        get_tool_schema,
        create_pydantic_schema,
        generate_enhanced_docstring,
        list_available_tools,
        validate_schema_completeness
    )
    
    # Test 1: Schema count
    print("Test 1: Schema Registry")
    print("-" * 70)
    tools = list_available_tools()
    print(f"✓ Loaded {len(tools)} tool schemas")
    print(f"  Sample tools: {', '.join(tools[:5])}")
    print()
    
    # Test 2: Specific schema retrieval
    print("Test 2: Get Workbook Metadata Schema")
    print("-" * 70)
    schema = get_tool_schema("get_workbook_metadata")
    if schema:
        print("✓ Schema retrieved successfully")
        print(f"  Description: {schema['description']}")
        print(f"  Parameters: {list(schema['parameters'].keys())}")
        
        # Check filepath parameter
        if 'filepath' in schema['parameters']:
            fp = schema['parameters']['filepath']
            print(f"  Filepath required: {fp['required']}")
            print(f"  Filepath description: {fp['description'][:60]}...")
    else:
        print("✗ Failed to retrieve schema")
        return False
    print()
    
    # Test 3: Pydantic model generation
    print("Test 3: Pydantic Model Generation")
    print("-" * 70)
    try:
        pydantic_model = create_pydantic_schema("get_workbook_metadata", schema)
        print(f"✓ Generated Pydantic model: {pydantic_model.__name__}")
        print(f"  Fields: {list(pydantic_model.model_fields.keys())}")
        
        # Test validation
        valid_data = {"filepath": "/test.xlsx", "include_ranges": False}
        instance = pydantic_model(**valid_data)
        print("✓ Validation works for valid data")
        
        # Test with missing required field (should fail)
        try:
            invalid_data = {"include_ranges": True}  # Missing filepath
            instance = pydantic_model(**invalid_data)
            print("✗ Should have failed validation")
            return False
        except Exception:
            print("✓ Correctly rejects invalid data")
            
    except Exception as e:
        print(f"✗ Pydantic generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test 4: Docstring generation
    print("Test 4: Enhanced Docstring Generation")
    print("-" * 70)
    docstring = generate_enhanced_docstring("get_workbook_metadata", schema)
    print("✓ Generated enhanced docstring")
    print("\nDocstring Preview:")
    print("-" * 70)
    for line in docstring.split('\n')[:10]:
        print(f"  {line}")
    print("  ...")
    print("-" * 70)
    
    # Check key elements
    has_description = schema['description'] in docstring
    has_params = "Parameters:" in docstring
    has_filepath = "filepath" in docstring
    has_note = "auto" in docstring.lower() or "inject" in docstring.lower()
    
    print(f"  {'✓' if has_description else '✗'} Contains description")
    print(f"  {'✓' if has_params else '✗'} Has Parameters section")
    print(f"  {'✓' if has_filepath else '✗'} Documents filepath parameter")
    print(f"  {'✓' if has_note else '✗'} Has auto-injection note")
    
    if not (has_description and has_params and has_filepath and has_note):
        print("✗ Docstring missing required elements")
        return False
    print()
    
    # Test 5: Schema completeness
    print("Test 5: Schema Completeness Validation")
    print("-" * 70)
    completeness = validate_schema_completeness()
    print(f"  Valid: {completeness['valid']}")
    print(f"  Total tools: {completeness['total_tools']}")
    print(f"  Issues: {len(completeness['issues'])}")
    
    if completeness['issues']:
        print("\n  Issues found:")
        for issue in completeness['issues'][:5]:
            print(f"    - {issue}")
        if len(completeness['issues']) > 5:
            print(f"    ... and {len(completeness['issues']) - 5} more")
    
    if not completeness['valid']:
        print("✗ Schema completeness check failed")
        return False
    
    print("✓ All schemas are complete")
    print()
    
    # Test 6: Check all tools have schemas
    print("Test 6: Verify All Tool Schemas")
    print("-" * 70)
    expected_tools = [
        "get_workbook_metadata",
        "write_data_to_excel",
        "create_worksheet",
        "format_range",
        "create_chart"
    ]
    
    missing = []
    for tool in expected_tools:
        if tool not in MCP_TOOL_SCHEMAS:
            missing.append(tool)
    
    if missing:
        print(f"✗ Missing schemas: {missing}")
        return False
    
    print(f"✓ All {len(expected_tools)} expected tools have schemas")
    print()
    
    # Test 7: Filepath parameter check
    print("Test 7: Filepath Parameter Verification")
    print("-" * 70)
    tools_without_filepath = []
    tools_without_auto_note = []
    
    for tool_name in tools:
        schema = MCP_TOOL_SCHEMAS.get(tool_name)
        if not schema or 'parameters' not in schema:
            continue
        
        if 'filepath' not in schema['parameters']:
            tools_without_filepath.append(tool_name)
        else:
            desc = schema['parameters']['filepath'].get('description', '').lower()
            if 'auto' not in desc and 'do not provide' not in desc:
                tools_without_auto_note.append(tool_name)
    
    print(f"  Tools total: {len(tools)}")
    print(f"  With filepath parameter: {len(tools) - len(tools_without_filepath)}")
    print(f"  With auto-injection note: {len(tools) - len(tools_without_auto_note)}")
    
    if tools_without_filepath:
        print(f"\n  ⚠ Tools without filepath: {', '.join(tools_without_filepath[:3])}")
    
    if tools_without_auto_note:
        print(f"  ⚠ Tools missing auto-inject note: {', '.join(tools_without_auto_note[:3])}")
    
    print()
    
    return True


def main():
    """Run standalone test"""
    print("\n" + "=" * 70)
    print("MCP Tool Schema System - Standalone Validation")
    print("=" * 70)
    print()
    
    try:
        success = test_schemas_standalone()
        
        print("=" * 70)
        if success:
            print("✓ All Tests Passed!")
            print("=" * 70)
            print("\nSchema system is ready for use:")
            print("  - All tool schemas are properly defined")
            print("  - Pydantic models generate correctly")
            print("  - Enhanced docstrings are created")
            print("  - Filepath auto-injection is documented")
            print("\nThe MCP tool contract validation system is operational.")
            return 0
        else:
            print("✗ Some Tests Failed")
            print("=" * 70)
            return 1
            
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
