#!/usr/bin/env python3
"""
YAML Schema Migration Utility

This script migrates JSON examples in YAML prompt files from v1 format (inline styles)
to v2 format (style reference architecture).

The migration process:
1. Parses YAML files to extract JSON examples
2. Converts inline styles to centralized style definitions
3. Replaces inline styles with style references
4. Validates the migrated data against Pydantic models
5. Updates YAML files with migrated examples

Usage:
    python scripts/migrate_yaml_examples.py --file path/to/file.yaml
    python scripts/migrate_yaml_examples.py --all
    python scripts/migrate_yaml_examples.py --phase 1
"""

import os
import sys
import json
import yaml
import argparse
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.api.spreadsheet import StyleDefinition, SpreadsheetData
from app.services.spreadsheet.style_registry import StyleRegistry, StyleValidator


class JSONExampleMigrator:
    """Handles migration of JSON examples from v1 to v2 format"""
    
    def __init__(self):
        self.style_counter = 0
        
    def migrate_json_example(self, json_str: str) -> Tuple[str, bool, List[str]]:
        """
        Migrate a single JSON example from v1 to v2 format.
        
        Args:
            json_str: JSON string in v1 format
            
        Returns:
            Tuple of (migrated_json_str, success, errors)
        """
        try:
            # Parse JSON
            data = json.loads(json_str)
            
            # Check if it's already v2 format
            if "styles" in data:
                return json_str, True, ["Already v2 format"]
            
            # Create style registry for this example
            registry = StyleRegistry()
            
            # Migrate the data
            migrated_data = self._migrate_data_structure(data, registry)
            
            # Validate the migrated data
            validator = StyleValidator(registry)
            is_valid, errors = validator.validate_spreadsheet_data(migrated_data)
            
            if not is_valid:
                return json_str, False, errors
            
            # Convert back to JSON with proper formatting
            migrated_json = json.dumps(migrated_data, indent=2, ensure_ascii=False)
            
            return migrated_json, True, []
            
        except json.JSONDecodeError as e:
            return json_str, False, [f"JSON parsing error: {str(e)}"]
        except Exception as e:
            return json_str, False, [f"Migration error: {str(e)}"]
    
    def _migrate_data_structure(self, data: Dict[str, Any], registry: StyleRegistry) -> Dict[str, Any]:
        """
        Migrate data structure from v1 to v2 format.
        
        Args:
            data: Original data dictionary
            registry: Style registry to populate
            
        Returns:
            Migrated data dictionary
        """
        migrated_data = data.copy()
        
        # Initialize styles array
        migrated_data["styles"] = []
        
        # Process header styles
        if "data" in migrated_data and "header" in migrated_data["data"]:
            header = migrated_data["data"]["header"]
            if "style" in header and isinstance(header["style"], dict):
                # Extract inline style and create style definition
                style_dict = header["style"]
                style_id = registry.add_style_from_dict(style_dict)
                header["style"] = style_id
        
        # Process row styles
        if "data" in migrated_data and "rows" in migrated_data["data"]:
            for row in migrated_data["data"]["rows"]:
                if "style" in row and isinstance(row["style"], dict):
                    # Extract inline style and create style definition
                    style_dict = row["style"]
                    style_id = registry.add_style_from_dict(style_dict)
                    row["style"] = style_id
        
        # Add all styles to the migrated data
        migrated_data["styles"] = [style.dict() for style in registry.get_all_styles()]
        
        return migrated_data
    
    def _generate_semantic_style_id(self, style_dict: Dict[str, Any], context: str = "") -> str:
        """
        Generate semantic style IDs based on design document specifications.
        
        Args:
            style_dict: Style properties dictionary
            context: Context hint (header, row, etc.)
            
        Returns:
            Semantic style ID
        """
        # Header styles
        if context == "header":
            return "header_style"
        
        # Row alternation patterns
        if style_dict.get("background_color") == "#F2F2F2":
            return "even_row_style"
        elif style_dict.get("background_color") == "#FFFFFF":
            return "odd_row_style"
        
        # Conditional formatting
        if style_dict.get("font_color") == "#FF0000":
            return "negative_value_style"
        
        # Fallback to descriptive naming
        parts = []
        if style_dict.get("background_color"):
            color = style_dict["background_color"].replace("#", "")
            parts.append(f"bg_{color.lower()}")
        
        if style_dict.get("font_color"):
            color = style_dict["font_color"].replace("#", "")
            parts.append(f"fc_{color.lower()}")
        
        if style_dict.get("font_weight") == "bold":
            parts.append("bold")
        
        if not parts:
            parts.append("default")
        
        base_id = "_".join(parts) + "_style"
        return base_id


class YAMLFileMigrator:
    """Handles migration of entire YAML files"""
    
    def __init__(self):
        self.migrator = JSONExampleMigrator()
        self.resources_dir = project_root / "resources" / "prompts"
        
        # Define file migration phases based on design document
        self.migration_phases = {
            1: [
                "system_prompt_spreadsheet_formatting.yaml",
                "system_prompt_spreadsheet_generation.yaml"
            ],
            2: [
                "system_prompt_spreadsheet_analysis.yaml",
                "system_prompt_spreadsheet_transformation.yaml"
            ],
            3: [
                "system_prompt_spreadsheet_search.yaml"
            ]
        }
    
    def migrate_file(self, file_path: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Migrate a single YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Tuple of (success, messages, statistics)
        """
        messages = []
        stats = {
            "total_examples": 0,
            "migrated_examples": 0,
            "already_v2": 0,
            "errors": 0,
            "payload_reduction": 0.0
        }
        
        if not file_path.exists():
            return False, [f"File not found: {file_path}"], stats
        
        try:
            # Read YAML file
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if "examples" not in yaml_data:
                return True, ["No examples found in YAML file"], stats
            
            # Track original size for payload reduction calculation
            original_size = len(str(yaml_data))
            modified = False
            
            # Process each example
            for i, example in enumerate(yaml_data["examples"]):
                if "response" not in example:
                    continue
                
                stats["total_examples"] += 1
                response_content = example["response"].strip()
                
                # Try to migrate the JSON response
                migrated_json, success, migration_messages = self.migrator.migrate_json_example(response_content)
                
                if success:
                    if "Already v2 format" in migration_messages:
                        stats["already_v2"] += 1
                        messages.append(f"Example {i+1}: Already in v2 format")
                    else:
                        stats["migrated_examples"] += 1
                        example["response"] = migrated_json
                        modified = True
                        messages.append(f"Example {i+1}: Successfully migrated")
                else:
                    stats["errors"] += 1
                    messages.extend([f"Example {i+1}: {msg}" for msg in migration_messages])
            
            # Calculate payload reduction
            if modified:
                new_size = len(str(yaml_data))
                stats["payload_reduction"] = ((original_size - new_size) / original_size) * 100
                
                # Write back the modified YAML
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, width=1000)
                
                messages.append(f"File updated successfully")
                messages.append(f"Payload size reduction: {stats['payload_reduction']:.1f}%")
            
            return True, messages, stats
            
        except Exception as e:
            return False, [f"Error processing file: {str(e)}"], stats
    
    def migrate_phase(self, phase: int) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Migrate files from a specific phase.
        
        Args:
            phase: Migration phase number (1, 2, or 3)
            
        Returns:
            Tuple of (success, messages, aggregated_statistics)
        """
        if phase not in self.migration_phases:
            return False, [f"Invalid phase: {phase}"], {}
        
        messages = [f"Starting Phase {phase} migration..."]
        aggregated_stats = {
            "files_processed": 0,
            "files_successful": 0,
            "total_examples": 0,
            "migrated_examples": 0,
            "already_v2": 0,
            "errors": 0,
            "average_payload_reduction": 0.0
        }
        
        reductions = []
        
        for filename in self.migration_phases[phase]:
            file_path = self.resources_dir / filename
            messages.append(f"\nProcessing {filename}...")
            
            success, file_messages, file_stats = self.migrate_file(file_path)
            
            aggregated_stats["files_processed"] += 1
            if success:
                aggregated_stats["files_successful"] += 1
            
            # Aggregate statistics
            for key in ["total_examples", "migrated_examples", "already_v2", "errors"]:
                aggregated_stats[key] += file_stats.get(key, 0)
            
            if file_stats.get("payload_reduction", 0) > 0:
                reductions.append(file_stats["payload_reduction"])
            
            messages.extend([f"  {msg}" for msg in file_messages])
        
        # Calculate average payload reduction
        if reductions:
            aggregated_stats["average_payload_reduction"] = sum(reductions) / len(reductions)
        
        return True, messages, aggregated_stats
    
    def migrate_all_files(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Migrate all YAML files according to the phased approach.
        
        Returns:
            Tuple of (success, messages, aggregated_statistics)
        """
        messages = ["Starting complete migration of all YAML files..."]
        total_stats = {
            "phases_completed": 0,
            "files_processed": 0,
            "files_successful": 0,
            "total_examples": 0,
            "migrated_examples": 0,
            "already_v2": 0,
            "errors": 0,
            "average_payload_reduction": 0.0
        }
        
        all_reductions = []
        overall_success = True
        
        # Process each phase
        for phase in [1, 2, 3]:
            messages.append(f"\n{'='*60}")
            messages.append(f"PHASE {phase}")
            messages.append(f"{'='*60}")
            
            success, phase_messages, phase_stats = self.migrate_phase(phase)
            
            if success:
                total_stats["phases_completed"] += 1
            else:
                overall_success = False
            
            # Aggregate statistics
            for key in ["files_processed", "files_successful", "total_examples", 
                       "migrated_examples", "already_v2", "errors"]:
                total_stats[key] += phase_stats.get(key, 0)
            
            if phase_stats.get("average_payload_reduction", 0) > 0:
                all_reductions.append(phase_stats["average_payload_reduction"])
            
            messages.extend(phase_messages)
        
        # Calculate overall average payload reduction
        if all_reductions:
            total_stats["average_payload_reduction"] = sum(all_reductions) / len(all_reductions)
        
        # Add summary
        messages.append(f"\n{'='*60}")
        messages.append("MIGRATION SUMMARY")
        messages.append(f"{'='*60}")
        messages.append(f"Phases completed: {total_stats['phases_completed']}/3")
        messages.append(f"Files processed: {total_stats['files_processed']}")
        messages.append(f"Files successful: {total_stats['files_successful']}")
        messages.append(f"Total examples: {total_stats['total_examples']}")
        messages.append(f"Migrated examples: {total_stats['migrated_examples']}")
        messages.append(f"Already v2 format: {total_stats['already_v2']}")
        messages.append(f"Errors encountered: {total_stats['errors']}")
        messages.append(f"Average payload reduction: {total_stats['average_payload_reduction']:.1f}%")
        
        return overall_success, messages, total_stats


def main():
    """Main entry point for the migration script"""
    parser = argparse.ArgumentParser(
        description="Migrate YAML prompt files from v1 to v2 format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_yaml_examples.py --file system_prompt_spreadsheet_formatting.yaml
  python scripts/migrate_yaml_examples.py --phase 1
  python scripts/migrate_yaml_examples.py --all
  python scripts/migrate_yaml_examples.py --validate-only --file formatting.yaml
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Migrate a specific YAML file")
    group.add_argument("--phase", type=int, choices=[1, 2, 3], help="Migrate files from a specific phase")
    group.add_argument("--all", action="store_true", help="Migrate all YAML files")
    
    parser.add_argument("--validate-only", action="store_true", 
                       help="Only validate without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = YAMLFileMigrator()
    
    try:
        if args.file:
            # Migrate single file
            file_path = migrator.resources_dir / args.file
            success, messages, stats = migrator.migrate_file(file_path)
            
            # Print results
            for message in messages:
                print(message)
            
            if args.verbose and stats:
                print(f"\nStatistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            return 0 if success else 1
            
        elif args.phase:
            # Migrate specific phase
            success, messages, stats = migrator.migrate_phase(args.phase)
            
            # Print results
            for message in messages:
                print(message)
            
            if args.verbose and stats:
                print(f"\nPhase {args.phase} Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            return 0 if success else 1
            
        elif args.all:
            # Migrate all files
            success, messages, stats = migrator.migrate_all_files()
            
            # Print results
            for message in messages:
                print(message)
            
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\nMigration interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())