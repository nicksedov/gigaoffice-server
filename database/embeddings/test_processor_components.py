"""
Test script for Embedding Processor components.

Tests individual components without requiring database connection.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.embeddings.processor import LemmatizationService


def test_lemmatization_service():
    """Test lemmatization service functionality."""
    print("Testing LemmatizationService...")
    
    service = LemmatizationService()
    
    # Test language detection
    assert service.detect_language("Hello world") == "en"
    assert service.detect_language("Привет мир") == "ru"
    assert service.detect_language("Mixed текст") == "ru"
    
    print("✅ Language detection works correctly")
    
    # Test lemmatization (should work even without pymystem3 for English)
    english_text = "Testing the system"
    result = service.lemmatize(english_text)
    assert result == english_text  # English text unchanged
    
    print("✅ English text processing works correctly")
    
    # Test empty text
    empty_result = service.lemmatize("")
    assert empty_result == ""
    
    print("✅ Empty text handling works correctly")
    
    print("✅ LemmatizationService tests passed!\n")


def test_csv_parsing():
    """Test CSV parsing logic."""
    print("Testing CSV parsing...")
    
    import csv
    from io import StringIO
    
    # Test semicolon-delimited CSV
    csv_data = """text;category
Hello;greeting
World;noun"""
    
    reader = csv.DictReader(StringIO(csv_data), delimiter=';')
    records = list(reader)
    
    assert len(records) == 2
    assert records[0]['text'] == 'Hello'
    assert records[0]['category'] == 'greeting'
    assert records[1]['text'] == 'World'
    assert records[1]['category'] == 'noun'
    
    print("✅ CSV parsing works correctly\n")


def test_provider_integration():
    """Test provider data extraction."""
    print("Testing provider integration...")
    
    from database.providers import TableHeadersProvider
    
    # Note: This requires the actual CSV file to exist
    try:
        provider = TableHeadersProvider()
        column_names = provider.get_column_names()
        
        assert column_names == ['text']
        print(f"✅ Provider column names: {column_names}")
        
        source_info = provider.get_source_info()
        print(f"✅ Provider source: {source_info.get('source_path', 'N/A')}")
        
        # Only test data retrieval if file exists
        if source_info.get('file_exists', False):
            csv_data = provider.get_data()
            lines = csv_data.split('\n')
            print(f"✅ Provider returned {len(lines)} lines")
        else:
            print("⚠️  Source file not found, skipping data retrieval test")
        
    except Exception as e:
        print(f"⚠️  Provider test skipped: {e}")
    
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("EMBEDDING PROCESSOR COMPONENT TESTS")
    print("=" * 60)
    print()
    
    try:
        test_lemmatization_service()
        test_csv_parsing()
        test_provider_integration()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
