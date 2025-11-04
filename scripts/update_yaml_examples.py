#!/usr/bin/env python
"""
YAML Example Update Script
Batch updates YAML example files to align with preprocessed data structures
"""

import json
import copy
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from loguru import logger
import yaml


# Configure logger
logger.remove()
logger.add(lambda msg: print(msg, end=''), colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def preprocess_formatting_data(data: dict) -> dict:
    """
    Preprocess data for formatting category.
    Remove values from rows, keep styles and structure.
    """
    result = copy.deepcopy(data)
    
    # Remove values from data rows
    if 'data' in result and 'rows' in result['data']:
        for row in result['data']['rows']:
            if 'values' in row and isinstance(row['values'], list):
                row['values'] = ["" for _ in row['values']]
    
    # Remove statistical metadata from columns
    if 'columns' in result:
        for column in result['columns']:
            column.pop('min', None)
            column.pop('max', None)
            column.pop('median', None)
            column.pop('count', None)
    
    return result


def preprocess_analysis_data(data: dict) -> dict:
    """
    Preprocess data for analysis category.
    Remove styles, keep values and statistical metadata.
    """
    result = copy.deepcopy(data)
    
    # Remove entire styles array
    result.pop('styles', None)
    
    # Remove style references from header
    if 'data' in result and 'header' in result['data']:
        result['data']['header'].pop('style', None)
    
    # Remove style references from rows
    if 'data' in result and 'rows' in result['data']:
        for row in result['data']['rows']:
            row.pop('style', None)
    
    return result


def preprocess_search_data(data: dict) -> dict:
    """
    Preprocess data for search category.
    Remove styles and statistics, keep values and formats.
    """
    result = copy.deepcopy(data)
    
    # Remove entire styles array
    result.pop('styles', None)
    
    # Remove style references from header
    if 'data' in result and 'header' in result['data']:
        result['data']['header'].pop('style', None)
    
    # Remove style references from rows
    if 'data' in result and 'rows' in result['data']:
        for row in result['data']['rows']:
            row.pop('style', None)
    
    # Remove statistical metadata from columns
    if 'columns' in result:
        for column in result['columns']:
            column.pop('min', None)
            column.pop('max', None)
            column.pop('median', None)
            column.pop('count', None)
    
    return result


def preprocess_generation_data(data: dict) -> dict:
    """
    Preprocess data for generation category.
    Minimal changes - generation typically doesn't use request_table.
    """
    # Generation examples usually don't have request_table
    return data


def preprocess_transformation_data(data: dict) -> dict:
    """
    Preprocess data for transformation category.
    Keep values and styles, remove statistics.
    """
    result = copy.deepcopy(data)
    
    # Remove statistical metadata from columns
    if 'columns' in result:
        for column in result['columns']:
            column.pop('min', None)
            column.pop('max', None)
            column.pop('median', None)
            column.pop('count', None)
    
    return result


# Mapping of category to preprocessing function
PREPROCESSING_FUNCTIONS = {
    'spreadsheet-formatting': preprocess_formatting_data,
    'spreadsheet-analysis': preprocess_analysis_data,
    'spreadsheet-search': preprocess_search_data,
    'spreadsheet-generation': preprocess_generation_data,
    'spreadsheet-transformation': preprocess_transformation_data,
}


def discover_yaml_files(prompts_dir: Path) -> List[Tuple[str, Path]]:
    """
    Discover all YAML example files in the prompts directory.
    
    Returns:
        List of (category_name, file_path) tuples
    """
    yaml_files = []
    
    if not prompts_dir.exists():
        logger.error(f"Prompts directory not found: {prompts_dir}")
        return yaml_files
    
    # Valid spreadsheet categories to process
    valid_categories = [
        'spreadsheet-formatting',
        'spreadsheet-analysis',
        'spreadsheet-search',
        'spreadsheet-generation',
        'spreadsheet-transformation'
    ]
    
    for category_dir in prompts_dir.iterdir():
        if not category_dir.is_dir():
            continue
        
        category_name = category_dir.name
        
        if category_name not in valid_categories:
            continue
        
        # Find all YAML example files
        for yaml_file in category_dir.glob("example_*.yaml"):
            yaml_files.append((category_name, yaml_file))
        for yaml_file in category_dir.glob("example_*.yml"):
            yaml_files.append((category_name, yaml_file))
    
    return yaml_files


def validate_json_structure(data: dict) -> bool:
    """
    Validate that required fields exist in the data structure.
    """
    if not isinstance(data, dict):
        return False
    
    # Check if data is wrapped in spreadsheet_data
    if 'spreadsheet_data' in data:
        data = data['spreadsheet_data']
    
    # Basic structure validation
    if 'metadata' not in data or 'worksheet' not in data or 'data' not in data:
        return False
    
    return True


def process_yaml_file(
    file_path: Path,
    category: str,
    dry_run: bool,
    backup: bool
) -> Dict[str, Any]:
    """
    Process a single YAML file.
    
    Returns:
        Dictionary with processing results
    """
    result = {
        'file': file_path.name,
        'category': category,
        'status': 'skipped',
        'message': '',
        'changes': []
    }
    
    try:
        # Load YAML file
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        # Check if request_table exists
        if 'request_table' not in yaml_data or not yaml_data['request_table']:
            result['message'] = 'No request_table field'
            return result
        
        # Parse request_table JSON
        try:
            request_table_str = yaml_data['request_table']
            request_table_data = json.loads(request_table_str)
        except json.JSONDecodeError as e:
            result['status'] = 'error'
            result['message'] = f'JSON parse error: {e}'
            return result
        
        # Validate structure
        if not validate_json_structure(request_table_data):
            result['status'] = 'error'
            result['message'] = 'Invalid data structure'
            return result
        
        # Apply preprocessing
        preprocess_func = PREPROCESSING_FUNCTIONS.get(category)
        if not preprocess_func:
            result['message'] = f'No preprocessing function for category {category}'
            return result
        
        # Handle wrapped spreadsheet_data structure
        is_wrapped = 'spreadsheet_data' in request_table_data
        if is_wrapped:
            inner_data = request_table_data['spreadsheet_data']
            preprocessed_inner = preprocess_func(inner_data)
            preprocessed_data = copy.deepcopy(request_table_data)
            preprocessed_data['spreadsheet_data'] = preprocessed_inner
        else:
            preprocessed_data = preprocess_func(request_table_data)
        
        # Convert back to JSON string (formatted)
        new_request_table_str = json.dumps(preprocessed_data, ensure_ascii=False, indent=2)
        
        # Detect changes
        if request_table_str.strip() != new_request_table_str.strip():
            original_size = len(request_table_str)
            new_size = len(new_request_table_str)
            size_diff = original_size - new_size
            
            result['changes'].append(f'Size reduced by {size_diff} chars ({size_diff/original_size*100:.1f}%)')
            
            if not dry_run:
                # Create backup if requested
                if backup:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_path = file_path.with_suffix(f'.yaml.backup.{timestamp}')
                    backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
                    result['changes'].append(f'Backup created: {backup_path.name}')
                
                # Update YAML data
                yaml_data['request_table'] = new_request_table_str
                
                # Write updated file
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                
                result['status'] = 'updated'
                result['message'] = 'Successfully updated'
            else:
                result['status'] = 'would_update'
                result['message'] = 'Would be updated (dry run)'
        else:
            result['status'] = 'unchanged'
            result['message'] = 'No changes needed'
        
    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
        logger.exception(f"Error processing {file_path}")
    
    return result


def generate_summary_report(results: List[Dict[str, Any]]) -> str:
    """
    Generate a summary report of processing results.
    """
    lines = ["\n" + "="*80, "YAML UPDATE SUMMARY", "="*80 + "\n"]
    
    # Group by category
    by_category = {}
    for result in results:
        category = result['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(result)
    
    # Report by category
    for category, cat_results in sorted(by_category.items()):
        lines.append(f"\nCategory: {category}")
        for res in cat_results:
            status_symbol = {
                'updated': '✓',
                'would_update': '→',
                'unchanged': '○',
                'skipped': '⊘',
                'error': '✗'
            }.get(res['status'], '?')
            
            lines.append(f"  {status_symbol} {res['file']}: {res['message']}")
            for change in res['changes']:
                lines.append(f"     - {change}")
    
    # Overall statistics
    lines.append("\n" + "-"*80)
    total = len(results)
    updated = sum(1 for r in results if r['status'] == 'updated')
    would_update = sum(1 for r in results if r['status'] == 'would_update')
    unchanged = sum(1 for r in results if r['status'] == 'unchanged')
    errors = sum(1 for r in results if r['status'] == 'error')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    
    lines.append(f"Total files processed: {total}")
    lines.append(f"Updated: {updated}")
    lines.append(f"Would update (dry run): {would_update}")
    lines.append(f"Unchanged: {unchanged}")
    lines.append(f"Skipped: {skipped}")
    lines.append(f"Errors: {errors}")
    lines.append("="*80 + "\n")
    
    return "\n".join(lines)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Update YAML example files with preprocessed data structures'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create backup files before modification (default: true)'
    )
    parser.add_argument(
        '--category',
        type=str,
        help='Process only specific category'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Detailed logging output'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate JSON structure without transforming'
    )
    parser.add_argument(
        '--prompts-dir',
        type=str,
        default='resources/prompts',
        help='Path to prompts directory (default: resources/prompts)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.info("Verbose mode enabled")
    
    prompts_dir = Path(args.prompts_dir)
    if not prompts_dir.exists():
        logger.error(f"Prompts directory not found: {prompts_dir}")
        return 1
    
    logger.info(f"Discovering YAML files in {prompts_dir}")
    yaml_files = discover_yaml_files(prompts_dir)
    
    # Filter by category if specified
    if args.category:
        yaml_files = [(cat, path) for cat, path in yaml_files if cat == args.category]
        logger.info(f"Filtering for category: {args.category}")
    
    if not yaml_files:
        logger.warning("No YAML files found to process")
        return 0
    
    logger.info(f"Found {len(yaml_files)} YAML files to process")
    
    if args.dry_run:
        logger.warning("DRY RUN MODE - No files will be modified")
    
    # Process files
    results = []
    for category, file_path in yaml_files:
        logger.info(f"Processing {file_path.name} ({category})")
        result = process_yaml_file(file_path, category, args.dry_run, args.backup)
        results.append(result)
        
        if args.verbose:
            logger.info(f"  Status: {result['status']} - {result['message']}")
    
    # Generate and display summary report
    summary = generate_summary_report(results)
    print(summary)
    
    # Return error code if there were errors
    errors = sum(1 for r in results if r['status'] == 'error')
    return 1 if errors > 0 else 0


if __name__ == '__main__':
    exit(main())
