#!/usr/bin/env python3
"""
YAML Migration Validation Script

This script validates the migrated YAML prompt files to ensure they comply with the v2 format
and can be successfully parsed by the Pydantic models and style registry.

Usage:
    python scripts/validate_migrations.py --all
    python scripts/validate_migrations.py --file system_prompt_spreadsheet_formatting.yaml
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.models.api.spreadsheet import StyleDefinition, SpreadsheetData
    from app.services.spreadsheet.style_registry import StyleRegistry, StyleValidator, create_style_registry_from_data
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")
    print("Running in validation-only mode without Pydantic model validation")
    SpreadsheetData = None
    StyleValidator = None


class MigrationValidator:
    """Validates migrated YAML files for v2 format compliance"""
    
    def __init__(self):
        self.resources_dir = project_root / "resources" / "prompts"
        self.has_pydantic = SpreadsheetData is not None
        
        # Files that should have been migrated
        self.migrated_files = [
            "system_prompt_spreadsheet_formatting.yaml",
            "system_prompt_spreadsheet_generation.yaml", 
            "system_prompt_spreadsheet_search.yaml"
        ]
        
        # Files that should not have styles (no migration needed)
        self.no_style_files = [
            "system_prompt_spreadsheet_analysis.yaml",
            "system_prompt_spreadsheet_transformation.yaml"
        ]
    
    def validate_json_structure(self, json_str: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate JSON structure without Pydantic models.
        
        Args:
            json_str: JSON string to validate
            
        Returns:
            Tuple of (is_valid, errors, parsed_data)
        """
        errors = []
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return False, [f"JSON parsing error: {str(e)}"], {}
        
        # Check required top-level fields
        required_fields = ["metadata", "worksheet", "data"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check if it has styling information
        has_styles = False
        style_references = set()
        
        # Check for styles array (v2 format)
        if "styles" in data:
            has_styles = True
            if not isinstance(data["styles"], list):
                errors.append("'styles' field must be an array")
            else:
                for i, style in enumerate(data["styles"]):
                    if not isinstance(style, dict):
                        errors.append(f"Style at index {i} must be an object")
                        continue
                    if "id" not in style:
                        errors.append(f"Style at index {i} missing 'id' field")
        
        # Check for inline styles (v1 format - should not exist after migration)
        if "data" in data:
            # Check header
            header = data["data"].get("header", {})
            if "style" in header:
                if isinstance(header["style"], dict):
                    errors.append("Found inline style in header - should be migrated to v2 format")
                elif isinstance(header["style"], str):
                    style_references.add(header["style"])
            
            # Check rows
            rows = data["data"].get("rows", [])
            for i, row in enumerate(rows):
                if "style" in row:
                    if isinstance(row["style"], dict):
                        errors.append(f"Found inline style in row {i} - should be migrated to v2 format")
                    elif isinstance(row["style"], str):
                        style_references.add(row["style"])
        
        # Validate style references
        if has_styles and style_references:
            defined_styles = {style["id"] for style in data.get("styles", []) if isinstance(style, dict) and "id" in style}
            for style_ref in style_references:
                if style_ref not in defined_styles:
                    errors.append(f"Style reference '{style_ref}' not found in styles array")
        
        return len(errors) == 0, errors, data
    
    def validate_pydantic_model(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate data against Pydantic SpreadsheetData model.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            Tuple of (is_valid, errors)
        """
        if not self.has_pydantic:
            return True, ["Pydantic validation skipped - models not available"]
        
        try:
            spreadsheet_data = SpreadsheetData(**data)
            return True, []
        except Exception as e:
            return False, [f"Pydantic validation error: {str(e)}"]
    
    def validate_style_registry(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate data using style registry validator.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            Tuple of (is_valid, errors)
        """
        if not self.has_pydantic or not StyleValidator:
            return True, ["Style registry validation skipped - modules not available"]
        
        try:
            registry = create_style_registry_from_data(data)
            validator = StyleValidator(registry)
            is_valid, errors = validator.validate_spreadsheet_data(data)
            return is_valid, errors
        except Exception as e:
            return False, [f"Style registry validation error: {str(e)}"]
    
    def validate_file(self, file_path: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate a single YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Tuple of (success, messages, statistics)
        """
        messages = []
        stats = {
            "total_examples": 0,
            "valid_examples": 0,
            "v2_format_examples": 0,
            "errors": 0,
            "warnings": 0
        }
        
        if not file_path.exists():
            return False, [f"File not found: {file_path}"], stats
        
        try:
            # Read YAML file
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if "examples" not in yaml_data:
                messages.append("No examples found in YAML file")
                return True, messages, stats
            
            # Validate each example response
            for i, example in enumerate(yaml_data["examples"]):
                if "response" not in example:
                    continue
                
                stats["total_examples"] += 1
                response_content = example["response"].strip()
                
                # Validate JSON structure
                is_valid_json, json_errors, parsed_data = self.validate_json_structure(response_content)
                
                if not is_valid_json:
                    stats["errors"] += 1
                    messages.append(f"Example {i+1}: JSON validation failed")
                    for error in json_errors:
                        messages.append(f"  - {error}")
                    continue
                
                # Check if it's v2 format
                if "styles" in parsed_data:
                    stats["v2_format_examples"] += 1
                    messages.append(f"Example {i+1}: v2 format ✓")
                else:
                    messages.append(f"Example {i+1}: v1 format (no migration needed)")
                
                # Validate with Pydantic model
                if self.has_pydantic:
                    is_valid_pydantic, pydantic_errors = self.validate_pydantic_model(parsed_data)
                    if not is_valid_pydantic:
                        stats["errors"] += 1
                        messages.append(f"Example {i+1}: Pydantic validation failed")
                        for error in pydantic_errors:
                            messages.append(f"  - {error}")
                        continue
                
                # Validate with style registry
                if self.has_pydantic and "styles" in parsed_data:
                    is_valid_registry, registry_errors = self.validate_style_registry(parsed_data)  
                    if not is_valid_registry:
                        stats["errors"] += 1
                        messages.append(f"Example {i+1}: Style registry validation failed")
                        for error in registry_errors:
                            messages.append(f"  - {error}")
                        continue
                
                stats["valid_examples"] += 1
                
            # Summary
            if stats["total_examples"] > 0:
                success_rate = (stats["valid_examples"] / stats["total_examples"]) * 100
                messages.append(f"\nValidation Summary:")
                messages.append(f"  Total examples: {stats['total_examples']}")
                messages.append(f"  Valid examples: {stats['valid_examples']}")
                messages.append(f"  v2 format examples: {stats['v2_format_examples']}")
                messages.append(f"  Success rate: {success_rate:.1f}%")
                
                return stats["errors"] == 0, messages, stats
            else:
                return True, ["No examples to validate"], stats
                
        except Exception as e:
            return False, [f"Error processing file: {str(e)}"], stats
    
    def validate_all_files(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate all YAML files.
        
        Returns:
            Tuple of (success, messages, aggregated_statistics)
        """
        messages = ["Starting validation of all migrated YAML files..."]
        total_stats = {
            "files_processed": 0,
            "files_successful": 0,
            "total_examples": 0,
            "valid_examples": 0,
            "v2_format_examples": 0,
            "errors": 0
        }
        
        overall_success = True
        
        # Validate migrated files
        messages.append(f"\n{'='*60}")
        messages.append("MIGRATED FILES (Should have v2 format)")
        messages.append(f"{'='*60}")
        
        for filename in self.migrated_files:
            file_path = self.resources_dir / filename
            messages.append(f"\nValidating {filename}...")
            
            success, file_messages, file_stats = self.validate_file(file_path)
            
            total_stats["files_processed"] += 1
            if success:
                total_stats["files_successful"] += 1
            else:
                overall_success = False
            
            # Aggregate statistics
            for key in ["total_examples", "valid_examples", "v2_format_examples", "errors"]:
                total_stats[key] += file_stats.get(key, 0)
            
            messages.extend([f"  {msg}" for msg in file_messages])
        
        # Validate no-style files
        messages.append(f"\n{'='*60}")
        messages.append("NO-STYLE FILES (Should have no styles)")
        messages.append(f"{'='*60}")
        
        for filename in self.no_style_files:
            file_path = self.resources_dir / filename
            messages.append(f"\nValidating {filename}...")
            
            success, file_messages, file_stats = self.validate_file(file_path)
            
            total_stats["files_processed"] += 1
            if success:
                total_stats["files_successful"] += 1
            else:
                overall_success = False
            
            # Aggregate statistics
            for key in ["total_examples", "valid_examples", "errors"]:
                total_stats[key] += file_stats.get(key, 0)
            
            messages.extend([f"  {msg}" for msg in file_messages])
        
        # Overall summary
        messages.append(f"\n{'='*60}")
        messages.append("OVERALL VALIDATION SUMMARY")
        messages.append(f"{'='*60}")
        messages.append(f"Files processed: {total_stats['files_processed']}")
        messages.append(f"Files successful: {total_stats['files_successful']}")
        messages.append(f"Total examples: {total_stats['total_examples']}")
        messages.append(f"Valid examples: {total_stats['valid_examples']}")
        messages.append(f"v2 format examples: {total_stats['v2_format_examples']}")
        messages.append(f"Errors encountered: {total_stats['errors']}")
        
        if total_stats["total_examples"] > 0:
            success_rate = (total_stats["valid_examples"] / total_stats["total_examples"]) * 100
            v2_rate = (total_stats["v2_format_examples"] / total_stats["total_examples"]) * 100
            messages.append(f"Overall success rate: {success_rate:.1f}%")
            messages.append(f"v2 format adoption: {v2_rate:.1f}%")
        
        return overall_success, messages, total_stats


def main():
    """Main entry point for the validation script"""
    parser = argparse.ArgumentParser(
        description="Validate migrated YAML prompt files for v2 format compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_migrations.py --all
  python scripts/validate_migrations.py --file system_prompt_spreadsheet_formatting.yaml
  python scripts/validate_migrations.py --verbose --all
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Validate a specific YAML file")
    group.add_argument("--all", action="store_true", help="Validate all YAML files")
    
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = MigrationValidator()
    
    try:
        if args.file:
            # Validate single file
            file_path = validator.resources_dir / args.file
            success, messages, stats = validator.validate_file(file_path)
            
            # Print results
            for message in messages:
                print(message)
            
            if args.verbose and stats:
                print(f"\nDetailed Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            return 0 if success else 1
            
        elif args.all:
            # Validate all files
            success, messages, stats = validator.validate_all_files()
            
            # Print results
            for message in messages:
                print(message)
            
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())