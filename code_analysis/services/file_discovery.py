"""
File Discovery Service for code analysis.

Handles recursive scanning of project directories to identify Python files
for analysis, applying configurable exclusion patterns.
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Set, Optional
from code_analysis.utils.config_manager import ConfigurationManager


class FileDiscoveryService:
    """Service for discovering Python files in a project directory."""
    
    def __init__(self, config: ConfigurationManager):
        """
        Initialize file discovery service.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.exclusion_patterns = config.get_exclusion_patterns()
        self.excluded_directories = set(config.get_excluded_directories())
    
    def discover_python_files(self, root_path: str) -> List[str]:
        """
        Recursively discover all Python files in the given directory.
        
        Args:
            root_path: Root directory to start scanning from
            
        Returns:
            List of absolute paths to Python files
        """
        python_files = []
        root_path = os.path.abspath(root_path)
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Filter out excluded directories
            dirnames[:] = [d for d in dirnames if not self._should_exclude_directory(d, dirpath)]
            
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(dirpath, filename)
                    if not self._should_exclude_file(file_path):
                        python_files.append(file_path)
        
        return sorted(python_files)
    
    def _should_exclude_directory(self, dirname: str, dirpath: str) -> bool:
        """
        Check if a directory should be excluded from scanning.
        
        Args:
            dirname: Name of the directory
            dirpath: Full path to the parent directory
            
        Returns:
            True if directory should be excluded
        """
        # Check against excluded directory names
        if dirname in self.excluded_directories:
            return True
        
        # Check against exclusion patterns
        for pattern in self.exclusion_patterns:
            if fnmatch.fnmatch(dirname, pattern):
                return True
        
        # Check if directory starts with dot (hidden)
        if dirname.startswith('.'):
            return True
        
        return False
    
    def _should_exclude_file(self, file_path: str) -> bool:
        """
        Check if a file should be excluded from analysis.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            True if file should be excluded
        """
        filename = os.path.basename(file_path)
        
        # Check against exclusion patterns
        for pattern in self.exclusion_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
            if fnmatch.fnmatch(file_path, pattern):
                return True
        
        # Exclude empty files
        try:
            if os.path.getsize(file_path) == 0:
                return True
        except OSError:
            return True
        
        return False
    
    def filter_files_by_pattern(self, files: List[str], pattern: str) -> List[str]:
        """
        Filter files by a specific pattern.
        
        Args:
            files: List of file paths
            pattern: Glob pattern to match against
            
        Returns:
            Filtered list of file paths
        """
        return [f for f in files if fnmatch.fnmatch(f, pattern)]
    
    def get_relative_path(self, file_path: str, root_path: str) -> str:
        """
        Get relative path of a file from the root directory.
        
        Args:
            file_path: Absolute path to the file
            root_path: Root directory path
            
        Returns:
            Relative path from root
        """
        return os.path.relpath(file_path, root_path)
    
    def group_files_by_directory(self, files: List[str]) -> dict:
        """
        Group files by their parent directory.
        
        Args:
            files: List of file paths
            
        Returns:
            Dictionary mapping directory paths to lists of files
        """
        grouped = {}
        for file_path in files:
            directory = os.path.dirname(file_path)
            if directory not in grouped:
                grouped[directory] = []
            grouped[directory].append(file_path)
        
        return grouped
    
    def count_lines_of_code(self, file_path: str) -> int:
        """
        Count lines of code in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Number of lines in the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return 0
    
    def get_project_statistics(self, files: List[str]) -> dict:
        """
        Get statistics about the discovered files.
        
        Args:
            files: List of discovered file paths
            
        Returns:
            Dictionary containing project statistics
        """
        total_files = len(files)
        total_lines = sum(self.count_lines_of_code(f) for f in files)
        directories = len(self.group_files_by_directory(files))
        
        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "total_directories": directories,
            "average_lines_per_file": total_lines / total_files if total_files > 0 else 0
        }
