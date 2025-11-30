"""
Categorized Prompts Provider.

Extracts prompt examples from all category YAML files and returns them
as a four-column CSV (category, text, request_json, response_json) with semicolon delimiter.
"""

import os
import json
import yaml
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from loguru import logger

from .base import DataProvider


class CategorizedPromptsProvider(DataProvider):
    """
    Provider for categorized prompt examples.
    
    Reads YAML files from all category directories under resources/prompts/,
    extracts category, task, request_table, and response_table fields,
    and returns as four-column CSV.
    """
    
    # Valid category directories
    VALID_CATEGORIES = [
        'data-chart',
        'data-histogram',
        'spreadsheet-analysis',
        'spreadsheet-formatting',
        'spreadsheet-generation',
        'spreadsheet-search',
        'spreadsheet-transformation',
        'spreadsheet-assistance'
    ]
    
    def __init__(self, prompts_directory: str = None):
        """
        Initialize the provider.
        
        Args:
            prompts_directory: Base path to prompts directory. If None, uses default.
        """
        if prompts_directory is None:
            prompts_directory = os.getenv("CATEGORIZED_PROMPTS_DIRECTORY", "resources/prompts/category")
        
        self.prompts_directory = Path(prompts_directory)
        self.delimiter = os.getenv("CSV_DELIMITER", ";")
        self.encoding = os.getenv("CSV_ENCODING", "utf-8")
        self.skip_errors = os.getenv("SKIP_INVALID_RECORDS", "true").lower() == "true"
        self._examples = None
        
        logger.info(f"CategorizedPromptsProvider initialized with source: {self.prompts_directory}")
    
    def _discover_yaml_files(self) -> List[Tuple[str, Path]]:
        """
        Discover all YAML example files across all category directories.
        
        Returns:
            List[Tuple[str, Path]]: List of (category_name, file_path) tuples
        """
        if not self.prompts_directory.exists():
            logger.error(f"Prompts directory not found: {self.prompts_directory}")
            return []
        
        yaml_files = []
        
        # Iterate through subdirectories
        for category_dir in self.prompts_directory.iterdir():
            if not category_dir.is_dir():
                continue
            
            category_name = category_dir.name
            
            # Skip if not a valid category
            if category_name not in self.VALID_CATEGORIES:
                logger.warning(f"Skipping unexpected directory: {category_name}")
                continue
            
            # Find all example_*.yaml and example_*.yml files
            for pattern in ["example_*.yaml", "example_*.yml"]:
                for yaml_file in category_dir.glob(pattern):
                    yaml_files.append((category_name, yaml_file))
        
        logger.info(f"Discovered {len(yaml_files)} YAML files across {len(self.VALID_CATEGORIES)} categories")
        return sorted(yaml_files)
    
    def _parse_yaml_file(self, category: str, file_path: Path) -> Optional[Dict[str, str]]:
        """
        Parse a single YAML file and extract all fields.
        
        Args:
            category: Category name
            file_path: Path to YAML file
            
        Returns:
            Dict with 'category', 'text', 'request_json', 'response_json' keys, or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty YAML file: {file_path.name}")
                return None
            
            # Extract required fields
            task = data.get('task')
            if not task:
                logger.warning(f"Missing 'task' field in {file_path.name}")
                return None
            
            response_table = data.get('response_table')
            if not response_table:
                logger.warning(f"Missing 'response_table' field in {file_path.name}")
                return None
            
            # Parse response_table as JSON to validate it
            try:
                response_json = json.loads(response_table)
                response_json_str = json.dumps(response_json, ensure_ascii=False, separators=(',', ':'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in 'response_table' of {file_path.name}: {e}")
                return None
            
            # Extract optional request_table field
            request_json_str = ""
            request_table = data.get('request_table')
            if request_table:
                try:
                    request_json = json.loads(request_table)
                    request_json_str = json.dumps(request_json, ensure_ascii=False, separators=(',', ':'))
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in 'request_table' of {file_path.name}: {e}")
                    # Continue with empty request_json
            
            return {
                'category': category,
                'text': task,
                'request_json': request_json_str,
                'response_json': response_json_str
            }
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {file_path.name}: {e}")
            return None
    
    def _extract_examples(self) -> List[Dict[str, str]]:
        """
        Extract all examples from all category YAML files.
        
        Returns:
            List[Dict]: List of examples with 'category', 'text', 'request_json', 'response_json' keys
        """
        yaml_files = self._discover_yaml_files()
        examples = []
        errors = 0
        
        for category, file_path in yaml_files:
            example = self._parse_yaml_file(category, file_path)
            if example:
                examples.append(example)
            else:
                errors += 1
                if not self.skip_errors:
                    logger.error(f"Stopping due to error in {file_path.name}")
                    break
        
        logger.info(f"Successfully parsed {len(examples)} examples")
        if errors > 0:
            logger.warning(f"Failed to parse {errors} files")
        
        return examples
    
    def _escape_csv_field(self, field: str) -> str:
        """
        Escape a field for CSV output.
        
        Args:
            field: Field value to escape
            
        Returns:
            str: Escaped field value
        """
        # Check if field needs quoting
        if self.delimiter in field or '"' in field or '\n' in field:
            # Escape double quotes and wrap in quotes
            escaped = field.replace('"', '""')
            return f'"{escaped}"'
        return field
    
    def get_data(self) -> str:
        """
        Returns complete CSV output as string (including header row).
        
        Returns:
            str: CSV-formatted data with semicolon delimiter
        """
        if self._examples is None:
            self._examples = self._extract_examples()
        
        # Build CSV output
        header = f"category{self.delimiter}text{self.delimiter}request_json{self.delimiter}response_json"
        output_lines = [header]
        
        for example in self._examples:
            category = self._escape_csv_field(example['category'])
            text = self._escape_csv_field(example['text'])
            request_json = self._escape_csv_field(example['request_json'])
            response_json = self._escape_csv_field(example['response_json'])
            
            output_lines.append(
                f"{category}{self.delimiter}{text}{self.delimiter}{request_json}{self.delimiter}{response_json}"
            )
        
        logger.info(f"Generated CSV with {len(self._examples)} records")
        
        return "\n".join(output_lines)
    
    def get_column_names(self) -> List[str]:
        """
        Returns list of column names for this provider.
        
        Returns:
            List[str]: Column names ["category", "text", "request_json", "response_json"]
        """
        return ["category", "text", "request_json", "response_json"]
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Returns metadata about data source.
        
        Returns:
            Dict[str, Any]: Metadata including path, file count, etc.
        """
        if self._examples is None:
            self._examples = self._extract_examples()
        
        yaml_files = self._discover_yaml_files()
        
        # Count files per category
        category_counts = {}
        for category, _ in yaml_files:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "source_type": "yaml",
            "source_path": str(self.prompts_directory),
            "directory_exists": self.prompts_directory.exists(),
            "total_categories": len(self.VALID_CATEGORIES),
            "total_files": len(yaml_files),
            "total_records": len(self._examples),
            "category_counts": category_counts,
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "skip_errors": self.skip_errors
        }
