"""
Classification Prompts Provider.

Extracts prompt examples from classifier category YAML files and returns them
as a two-column CSV (text, response_json) with semicolon delimiter.
"""

import os
import json
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from .base import DataProvider


class ClassificationPromptsProvider(DataProvider):
    """
    Provider for classification prompt examples.
    
    Reads YAML files from resources/prompts/classifier/ directory,
    extracts task and response_table fields, and returns as two-column CSV.
    """
    
    def __init__(self, prompts_directory: str = None):
        """
        Initialize the provider.
        
        Args:
            prompts_directory: Base path to prompts directory. If None, uses default.
        """
        if prompts_directory is None:
            prompts_directory = os.getenv("PROMPTS_DIRECTORY", "resources/prompts")
        
        self.prompts_directory = Path(prompts_directory)
        self.classifier_directory = self.prompts_directory / "classifier"
        self.delimiter = os.getenv("CSV_DELIMITER", ";")
        self.encoding = os.getenv("CSV_ENCODING", "utf-8")
        self.skip_errors = os.getenv("SKIP_INVALID_RECORDS", "true").lower() == "true"
        self._examples = None
        
        logger.info(f"ClassificationPromptsProvider initialized with source: {self.classifier_directory}")
    
    def _discover_yaml_files(self) -> List[Path]:
        """
        Discover all YAML example files in the classifier directory.
        
        Returns:
            List[Path]: List of YAML file paths
        """
        if not self.classifier_directory.exists():
            logger.error(f"Classifier directory not found: {self.classifier_directory}")
            return []
        
        yaml_files = []
        
        # Find all example_*.yaml and example_*.yml files
        for pattern in ["example_*.yaml", "example_*.yml"]:
            yaml_files.extend(self.classifier_directory.glob(pattern))
        
        logger.info(f"Discovered {len(yaml_files)} YAML files in classifier directory")
        return sorted(yaml_files)
    
    def _parse_yaml_file(self, file_path: Path) -> Optional[Dict[str, str]]:
        """
        Parse a single YAML file and extract task and response_table.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Dict with 'text' and 'response_json' keys, or None if parsing fails
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
                # Convert back to compact JSON string (single-line, minimal whitespace)
                response_json_str = json.dumps(response_json, ensure_ascii=False, separators=(',', ':'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in 'response_table' of {file_path.name}: {e}")
                return None
            
            return {
                'text': task,
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
        Extract all examples from classifier YAML files.
        
        Returns:
            List[Dict]: List of examples with 'text' and 'response_json' keys
        """
        yaml_files = self._discover_yaml_files()
        examples = []
        errors = 0
        
        for file_path in yaml_files:
            example = self._parse_yaml_file(file_path)
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
        output_lines = [f"text{self.delimiter}response_json"]  # Header row
        
        for example in self._examples:
            text = self._escape_csv_field(example['text'])
            response_json = self._escape_csv_field(example['response_json'])
            output_lines.append(f"{text}{self.delimiter}{response_json}")
        
        logger.info(f"Generated CSV with {len(self._examples)} records")
        
        return "\n".join(output_lines)
    
    def get_column_names(self) -> List[str]:
        """
        Returns list of column names for this provider.
        
        Returns:
            List[str]: Column names ["text", "response_json"]
        """
        return ["text", "response_json"]
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Returns metadata about data source.
        
        Returns:
            Dict[str, Any]: Metadata including path, file count, etc.
        """
        if self._examples is None:
            self._examples = self._extract_examples()
        
        yaml_files = self._discover_yaml_files()
        
        return {
            "source_type": "yaml",
            "source_path": str(self.classifier_directory),
            "directory_exists": self.classifier_directory.exists(),
            "total_files": len(yaml_files),
            "total_records": len(self._examples),
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "skip_errors": self.skip_errors
        }
