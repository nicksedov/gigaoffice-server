#!/usr/bin/env python3
"""
Legacy Example Migration Script

This script migrates prompt examples from legacy backup YAML files 
to the new organized category-based system.
"""

import os
import yaml
import json
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path
from difflib import SequenceMatcher

# Configuration
LEGACY_BACKUP_DIR = "/data/workspace/gigaoffice-server/resources/prompts/legacy_backup"
TARGET_BASE_DIR = "/data/workspace/gigaoffice-server/resources/prompts"

# Mapping from legacy files to target directories
CATEGORY_MAPPING = {
    "system_prompt_spreadsheet_analysis.yaml": "spreadsheet-analysis",
    "system_prompt_spreadsheet_formatting.yaml": "spreadsheet-formatting", 
    "system_prompt_spreadsheet_generation.yaml": "spreadsheet-generation",
    "system_prompt_spreadsheet_search.yaml": "spreadsheet-search",
    "system_prompt_spreadsheet_transformation.yaml": "spreadsheet-transformation"
}

class ExampleMigrator:
    def __init__(self):
        self.migration_stats = {
            "total_processed": 0,
            "migrated": 0,
            "skipped_duplicates": 0,
            "errors": 0
        }
        
    def load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Load and parse YAML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}
    
    def save_yaml_file(self, file_path: str, content: Dict[str, Any]) -> bool:
        """Save content to YAML file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(content, f, default_flow_style=False, allow_unicode=True, 
                         sort_keys=False, width=1000)
            return True
        except Exception as e:
            print(f"Error saving {file_path}: {e}")
            return False
    
    def get_next_example_number(self, target_dir: str) -> int:
        """Get the next available example number in target directory"""
        if not os.path.exists(target_dir):
            return 1
            
        existing_files = [f for f in os.listdir(target_dir) if f.startswith('example_') and f.endswith('.yaml')]
        if not existing_files:
            return 1
            
        numbers = []
        for filename in existing_files:
            match = re.match(r'example_(\d+)\.yaml', filename)
            if match:
                numbers.append(int(match.group(1)))
        
        return max(numbers) + 1 if numbers else 1
    
    def extract_task_from_request(self, request_text: str) -> str:
        """Extract task description from request text"""
        lines = request_text.strip().split('\n')
        for line in lines:
            if line.strip().startswith('ЗАДАЧА:'):
                return line.replace('ЗАДАЧА:', '').strip()
        return request_text.split('\n')[0].strip()
    
    def content_similarity(self, text1: str, text2: str) -> float:
        """Calculate content similarity between two texts"""
        # Clean and normalize text for comparison
        clean1 = re.sub(r'\s+', ' ', text1.lower().strip())
        clean2 = re.sub(r'\s+', ' ', text2.lower().strip())
        return SequenceMatcher(None, clean1, clean2).ratio()
    
    def check_for_duplicates(self, target_dir: str, new_request: str, new_response: str) -> bool:
        """Check if similar example already exists in target directory"""
        if not os.path.exists(target_dir):
            return False
            
        existing_files = [f for f in os.listdir(target_dir) if f.startswith('example_') and f.endswith('.yaml')]
        
        for filename in existing_files:
            filepath = os.path.join(target_dir, filename)
            existing_data = self.load_yaml_file(filepath)
            
            if 'request_table' in existing_data:
                existing_request = existing_data['request_table']
                existing_response = existing_data.get('response_table', '')
                
                # Check similarity - if above 80% similar, consider duplicate
                request_similarity = self.content_similarity(new_request, existing_request)
                response_similarity = self.content_similarity(new_response, existing_response)
                
                if request_similarity > 0.8 or response_similarity > 0.8:
                    print(f"  Found potential duplicate in {filename} (similarity: {request_similarity:.2f}/{response_similarity:.2f})")
                    return True
        
        return False
    
    def transform_example_structure(self, legacy_example: Dict[str, Any]) -> Dict[str, Any]:
        """Transform legacy example structure to new format"""
        request = legacy_example.get('request', '')
        response = legacy_example.get('response', '')
        
        # Extract task from request
        task = self.extract_task_from_request(request)
        
        return {
            'task': task,
            'request_table': request,
            'response_table': response
        }
    
    def migrate_file(self, legacy_file: str, target_category: str) -> Tuple[int, int]:
        """Migrate examples from a legacy file to target category"""
        legacy_path = os.path.join(LEGACY_BACKUP_DIR, legacy_file)
        target_dir = os.path.join(TARGET_BASE_DIR, target_category)
        
        print(f"\nMigrating {legacy_file} -> {target_category}/")
        
        # Load legacy file
        legacy_data = self.load_yaml_file(legacy_path)
        if not legacy_data or 'examples' not in legacy_data:
            print(f"  No examples found in {legacy_file}")
            return 0, 0
        
        examples = legacy_data['examples']
        print(f"  Found {len(examples)} examples to process")
        
        migrated_count = 0
        skipped_count = 0
        next_number = self.get_next_example_number(target_dir)
        
        for i, example in enumerate(examples):
            self.migration_stats["total_processed"] += 1
            
            try:
                # Transform to new structure
                new_example = self.transform_example_structure(example)
                
                # Check for duplicates
                if self.check_for_duplicates(target_dir, new_example['request_table'], new_example['response_table']):
                    print(f"  Skipping example {i+1} - duplicate detected")
                    skipped_count += 1
                    self.migration_stats["skipped_duplicates"] += 1
                    continue
                
                # Create new file
                new_filename = f"example_{next_number:02d}.yaml"
                new_filepath = os.path.join(target_dir, new_filename)
                
                if self.save_yaml_file(new_filepath, new_example):
                    print(f"  Created {new_filename}")
                    migrated_count += 1
                    next_number += 1
                    self.migration_stats["migrated"] += 1
                else:
                    print(f"  Error creating {new_filename}")
                    self.migration_stats["errors"] += 1
                    
            except Exception as e:
                print(f"  Error processing example {i+1}: {e}")
                self.migration_stats["errors"] += 1
        
        return migrated_count, skipped_count
    
    def migrate_all(self) -> Dict[str, Any]:
        """Migrate all legacy files"""
        print("Starting legacy example migration...")
        print("=" * 50)
        
        for legacy_file, target_category in CATEGORY_MAPPING.items():
            migrated, skipped = self.migrate_file(legacy_file, target_category)
            print(f"  Result: {migrated} migrated, {skipped} skipped")
        
        return self.migration_stats
    
    def validate_migrated_files(self) -> List[str]:
        """Validate all migrated YAML files"""
        print("\nValidating migrated files...")
        errors = []
        
        for target_category in CATEGORY_MAPPING.values():
            target_dir = os.path.join(TARGET_BASE_DIR, target_category)
            if not os.path.exists(target_dir):
                continue
                
            example_files = [f for f in os.listdir(target_dir) if f.startswith('example_') and f.endswith('.yaml')]
            
            for filename in example_files:
                filepath = os.path.join(target_dir, filename)
                try:
                    data = self.load_yaml_file(filepath)
                    
                    # Check required fields
                    required_fields = ['task', 'request_table', 'response_table']
                    for field in required_fields:
                        if field not in data:
                            errors.append(f"{filepath}: Missing field '{field}'")
                        elif not data[field] or not str(data[field]).strip():
                            errors.append(f"{filepath}: Empty field '{field}'")
                            
                except Exception as e:
                    errors.append(f"{filepath}: YAML parsing error - {e}")
        
        return errors

def main():
    """Main migration function"""
    migrator = ExampleMigrator()
    
    # Run migration
    stats = migrator.migrate_all()
    
    # Validate results
    validation_errors = migrator.validate_migrated_files()
    
    # Print final report
    print("\n" + "=" * 50)
    print("MIGRATION REPORT")
    print("=" * 50)
    print(f"Total examples processed: {stats['total_processed']}")
    print(f"Successfully migrated: {stats['migrated']}")
    print(f"Skipped (duplicates): {stats['skipped_duplicates']}")
    print(f"Errors: {stats['errors']}")
    
    if validation_errors:
        print(f"\nValidation errors found: {len(validation_errors)}")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("\nAll migrated files passed validation!")
    
    print("\nMigration completed!")
    return stats

if __name__ == "__main__":
    main()