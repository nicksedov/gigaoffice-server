"""
Test script for data providers.

This script demonstrates and validates the functionality of all three providers.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.providers import (
    TableHeadersProvider,
    ClassificationPromptsProvider,
    CategorizedPromptsProvider
)
from loguru import logger


def test_table_headers_provider():
    """Test TableHeadersProvider."""
    logger.info("=" * 60)
    logger.info("Testing TableHeadersProvider")
    logger.info("=" * 60)
    
    provider = TableHeadersProvider()
    
    # Get source info
    source_info = provider.get_source_info()
    logger.info(f"Source info: {source_info}")
    
    # Get column names
    columns = provider.get_column_names()
    logger.info(f"Columns: {columns}")
    
    # Get data
    csv_data = provider.get_data()
    lines = csv_data.split('\n')
    logger.info(f"Generated {len(lines)} lines (including header)")
    logger.info(f"First 10 lines:")
    for i, line in enumerate(lines[:10], 1):
        logger.info(f"  {i}: {line}")
    
    # Save to file for inspection
    output_file = Path("database/providers/output_table_headers.csv")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    logger.info(f"Saved output to: {output_file}")
    
    return source_info['total_records']


def test_classification_prompts_provider():
    """Test ClassificationPromptsProvider."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Testing ClassificationPromptsProvider")
    logger.info("=" * 60)
    
    provider = ClassificationPromptsProvider()
    
    # Get source info
    source_info = provider.get_source_info()
    logger.info(f"Source info: {source_info}")
    
    # Get column names
    columns = provider.get_column_names()
    logger.info(f"Columns: {columns}")
    
    # Get data
    csv_data = provider.get_data()
    lines = csv_data.split('\n')
    logger.info(f"Generated {len(lines)} lines (including header)")
    logger.info(f"First 5 lines:")
    for i, line in enumerate(lines[:5], 1):
        logger.info(f"  {i}: {line[:100]}...")  # Show first 100 chars
    
    # Save to file for inspection
    output_file = Path("database/providers/output_classification_prompts.csv")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    logger.info(f"Saved output to: {output_file}")
    
    return source_info['total_records']


def test_categorized_prompts_provider():
    """Test CategorizedPromptsProvider."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Testing CategorizedPromptsProvider")
    logger.info("=" * 60)
    
    provider = CategorizedPromptsProvider()
    
    # Get source info
    source_info = provider.get_source_info()
    logger.info(f"Source info: {source_info}")
    
    # Get column names
    columns = provider.get_column_names()
    logger.info(f"Columns: {columns}")
    
    # Get data
    csv_data = provider.get_data()
    lines = csv_data.split('\n')
    logger.info(f"Generated {len(lines)} lines (including header)")
    logger.info(f"First 5 lines:")
    for i, line in enumerate(lines[:5], 1):
        logger.info(f"  {i}: {line[:100]}...")  # Show first 100 chars
    
    # Save to file for inspection
    output_file = Path("database/providers/output_categorized_prompts.csv")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    logger.info(f"Saved output to: {output_file}")
    
    return source_info['total_records']


def main():
    """Run all provider tests."""
    logger.info("Starting provider tests...")
    logger.info("")
    
    try:
        # Test all providers
        headers_count = test_table_headers_provider()
        classification_count = test_classification_prompts_provider()
        categorized_count = test_categorized_prompts_provider()
        
        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"TableHeadersProvider: {headers_count} records")
        logger.info(f"ClassificationPromptsProvider: {classification_count} records")
        logger.info(f"CategorizedPromptsProvider: {categorized_count} records")
        logger.info("")
        logger.info("All tests completed successfully!")
        logger.info("Check the output CSV files in database/providers/ directory")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
