#!/usr/bin/env python3
"""
Test script to verify data-visualization category implementation
"""

import json
import os
import sys

# Add the project root to the Python path
sys.path.append('/data/workspace/gigaoffice-server')

def test_category_file():
    """Test that the category file contains the new data-visualization category"""
    try:
        with open('/data/workspace/gigaoffice-server/resources/prompts/prompt_categories.json', 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        # Check if data-visualization category exists
        data_viz_category = None
        for category in categories:
            if category['name'] == 'data-visualization':
                data_viz_category = category
                break
        
        if data_viz_category is None:
            print("❌ FAILED: data-visualization category not found in prompt_categories.json")
            return False
        
        # Validate category structure
        expected_fields = ['name', 'display_name', 'description', 'is_active', 'sort_order']
        for field in expected_fields:
            if field not in data_viz_category:
                print(f"❌ FAILED: Missing field '{field}' in data-visualization category")
                return False
        
        # Validate values
        if data_viz_category['name'] != 'data-visualization':
            print("❌ FAILED: Incorrect category name")
            return False
            
        if data_viz_category['display_name'] != 'Визуализировать данные':
            print("❌ FAILED: Incorrect display name")
            return False
            
        if not data_viz_category['is_active']:
            print("❌ FAILED: Category should be active")
            return False
            
        if data_viz_category['sort_order'] != 6:
            print("❌ FAILED: Incorrect sort order")
            return False
        
        print("✅ PASSED: Category file validation")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error reading category file: {e}")
        return False

def test_directory_structure():
    """Test that all required directories and files exist"""
    base_path = '/data/workspace/gigaoffice-server/resources/prompts/data-visualization'
    
    # Check directory exists
    if not os.path.exists(base_path):
        print("❌ FAILED: data-visualization directory does not exist")
        return False
    
    # Check required files exist
    required_files = [
        'system_prompt.txt',
        'example_01.yaml',
        'example_02.yaml',
        'example_03.yaml',
        'example_04.yaml'
    ]
    
    for filename in required_files:
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            print(f"❌ FAILED: Required file '{filename}' does not exist")
            return False
    
    print("✅ PASSED: Directory structure validation")
    return True

def test_classifier_examples():
    """Test that classifier examples for data-visualization were created"""
    classifier_path = '/data/workspace/gigaoffice-server/resources/prompts/classifier'
    
    # Check that new example files exist
    new_examples = [
        'example_08.yaml',
        'example_09.yaml', 
        'example_10.yaml',
        'example_11.yaml',
        'example_12.yaml',
        'example_13.yaml'
    ]
    
    for filename in new_examples:
        filepath = os.path.join(classifier_path, filename)
        if not os.path.exists(filepath):
            print(f"❌ FAILED: Classifier example '{filename}' does not exist")
            return False
    
    # Check content of one example
    try:
        with open(os.path.join(classifier_path, 'example_08.yaml'), 'r', encoding='utf-8') as f:
            content = f.read()
            if 'data-visualization' not in content:
                print("❌ FAILED: Classifier example does not contain 'data-visualization'")
                return False
    except Exception as e:
        print(f"❌ FAILED: Error reading classifier example: {e}")
        return False
    
    print("✅ PASSED: Classifier examples validation")
    return True

def test_system_prompt():
    """Test that the system prompt for data-visualization exists and contains required content"""
    try:
        with open('/data/workspace/gigaoffice-server/resources/prompts/data-visualization/system_prompt.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key terms
        required_terms = ['графики', 'диаграммы', 'визуализации', 'charts', 'Р7-Офис']
        for term in required_terms:
            if term not in content:
                print(f"❌ FAILED: System prompt missing required term: '{term}'")
                return False
        
        print("✅ PASSED: System prompt validation")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error reading system prompt: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing data-visualization category implementation...\n")
    
    tests = [
        test_category_file,
        test_directory_structure,
        test_classifier_examples,
        test_system_prompt
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Data-visualization category implementation is complete.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)