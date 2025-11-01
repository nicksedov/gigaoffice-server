"""
Test script for generate_prompt_examples.py

This script tests the YAML parsing and data extraction logic
without requiring database connectivity.
"""
import sys
from pathlib import Path

# Add parent directory to path to import the main script
sys.path.insert(0, str(Path(__file__).parent))

from generate_prompt_examples import (
    discover_yaml_files,
    parse_yaml_example,
    parse_all_examples,
    PromptExample
)

def test_yaml_discovery():
    """Test YAML file discovery"""
    print("Testing YAML file discovery...")
    yaml_files = discover_yaml_files("resources/prompts")
    
    print(f"Found {len(yaml_files)} YAML files")
    
    # Group by category
    by_category = {}
    for category, file_path in yaml_files:
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(file_path.name)
    
    print("\nFiles by category:")
    for category, files in sorted(by_category.items()):
        print(f"  {category}: {len(files)} files")
        for file in sorted(files)[:3]:  # Show first 3
            print(f"    - {file}")
        if len(files) > 3:
            print(f"    ... and {len(files) - 3} more")
    
    return len(yaml_files) > 0


def test_yaml_parsing():
    """Test parsing of individual YAML files"""
    print("\n" + "="*60)
    print("Testing YAML parsing...")
    
    yaml_files = discover_yaml_files("resources/prompts")
    if not yaml_files:
        print("No YAML files found to test")
        return False
    
    # Test first file from each category
    tested_categories = set()
    success_count = 0
    
    for category, file_path in yaml_files:
        if category in tested_categories:
            continue
        
        tested_categories.add(category)
        print(f"\nParsing: {category}/{file_path.name}")
        
        example = parse_yaml_example(category, file_path)
        if example:
            print(f"  ✓ Category: {example.category}")
            print(f"  ✓ Language: {example.language}")
            print(f"  ✓ Prompt: {example.prompt_text[:60]}...")
            print(f"  ✓ Has request: {example.request_json is not None}")
            print(f"  ✓ Has response: {example.response_json is not None}")
            print(f"  ✓ Lemmatized: {example.lemmatized_prompt[:60]}...")
            success_count += 1
        else:
            print(f"  ✗ Failed to parse")
    
    print(f"\nSuccessfully parsed {success_count}/{len(tested_categories)} test files")
    return success_count > 0


def test_full_parsing():
    """Test parsing all examples"""
    print("\n" + "="*60)
    print("Testing full example parsing...")
    
    examples = parse_all_examples("resources/prompts")
    
    if not examples:
        print("No examples parsed")
        return False
    
    print(f"\nTotal examples parsed: {len(examples)}")
    
    # Statistics
    by_category = {}
    by_language = {'ru': 0, 'en': 0}
    with_request = 0
    
    for ex in examples:
        by_category[ex.category] = by_category.get(ex.category, 0) + 1
        by_language[ex.language] += 1
        if ex.request_json:
            with_request += 1
    
    print("\nStatistics:")
    print(f"  Examples by category:")
    for category, count in sorted(by_category.items()):
        print(f"    {category}: {count}")
    
    print(f"\n  Examples by language:")
    print(f"    Russian: {by_language['ru']}")
    print(f"    English: {by_language['en']}")
    
    print(f"\n  Examples with request data: {with_request}/{len(examples)}")
    
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("Prompt Examples Parser Test Suite")
    print("="*60)
    
    tests = [
        ("YAML Discovery", test_yaml_discovery),
        ("YAML Parsing", test_yaml_parsing),
        ("Full Parsing", test_full_parsing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
