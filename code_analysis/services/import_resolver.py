"""
Import Resolver Service for categorizing and resolving imports.

Handles classification of imports into categories (standard library, third-party, local)
and tracks import dependencies across files.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from code_analysis.utils.config_manager import ConfigurationManager
from code_analysis.services.ast_analysis import ImportInfo
from code_analysis.models.results import ImportType


class ImportResolverService:
    """Service for resolving and categorizing imports."""
    
    def __init__(self, config: ConfigurationManager, project_root: str):
        """
        Initialize import resolver service.
        
        Args:
            config: Configuration manager instance
            project_root: Root directory of the project
        """
        self.config = config
        self.project_root = os.path.abspath(project_root)
        self.import_map: Dict[str, Set[str]] = {}  # module -> files that import it
        self.file_imports: Dict[str, List[ImportInfo]] = {}  # file -> imports in that file
    
    def categorize_import(self, module_name: str, file_path: str, level: int = 0) -> ImportType:
        """
        Categorize an import statement.
        
        Args:
            module_name: Name of the imported module
            file_path: Path to the file containing the import
            level: Import level (for relative imports)
            
        Returns:
            ImportType classification
        """
        # Handle relative imports
        if level > 0:
            return ImportType.LOCAL_RELATIVE
        
        # Check if it's a standard library module
        if self.config.is_standard_library(module_name):
            return ImportType.STANDARD_LIBRARY
        
        # Check if it's a third-party module
        if self.config.is_third_party(module_name):
            return ImportType.THIRD_PARTY
        
        # Check if it's a local module
        if self._is_local_module(module_name, file_path):
            return ImportType.LOCAL_ABSOLUTE
        
        # Try to determine if it's importable from sys.path
        if self._is_importable(module_name):
            # If importable but not in our lists, assume third-party
            return ImportType.THIRD_PARTY
        
        return ImportType.UNKNOWN
    
    def _is_local_module(self, module_name: str, file_path: str) -> bool:
        """
        Check if a module is a local project module.
        
        Args:
            module_name: Module name to check
            file_path: Path to the file importing the module
            
        Returns:
            True if the module is local to the project
        """
        # Get the base module name
        base_module = module_name.split('.')[0]
        
        # Check if the module exists in the project directory
        module_path = os.path.join(self.project_root, base_module)
        
        # Check for package directory
        if os.path.isdir(module_path) and os.path.exists(os.path.join(module_path, '__init__.py')):
            return True
        
        # Check for single module file
        if os.path.exists(module_path + '.py'):
            return True
        
        # Check if it's in the same directory as the importing file
        file_dir = os.path.dirname(file_path)
        local_module_path = os.path.join(file_dir, base_module)
        
        if os.path.isdir(local_module_path) or os.path.exists(local_module_path + '.py'):
            return True
        
        return False
    
    def _is_importable(self, module_name: str) -> bool:
        """
        Check if a module can be imported.
        
        Args:
            module_name: Module name to check
            
        Returns:
            True if the module is importable
        """
        try:
            __import__(module_name.split('.')[0])
            return True
        except (ImportError, ModuleNotFoundError):
            return False
    
    def resolve_relative_import(self, module_name: str, file_path: str, level: int) -> Optional[str]:
        """
        Resolve a relative import to its absolute module name.
        
        Args:
            module_name: Module name from the import statement
            file_path: Path to the file containing the import
            level: Number of parent directories to go up
            
        Returns:
            Resolved absolute module name or None if resolution fails
        """
        # Get the package path of the current file
        file_dir = os.path.dirname(os.path.abspath(file_path))
        
        # Go up 'level' directories
        target_dir = file_dir
        for _ in range(level):
            target_dir = os.path.dirname(target_dir)
        
        # Convert directory path to module path
        try:
            rel_path = os.path.relpath(target_dir, self.project_root)
            if rel_path == '.':
                package_path = ''
            else:
                package_path = rel_path.replace(os.sep, '.')
            
            if module_name:
                if package_path:
                    return f"{package_path}.{module_name}"
                else:
                    return module_name
            else:
                return package_path
        except ValueError:
            return None
    
    def track_import(self, import_info: ImportInfo, file_path: str) -> None:
        """
        Track an import statement for dependency analysis.
        
        Args:
            import_info: Import information
            file_path: Path to the file containing the import
        """
        # Track which files import which modules
        if import_info.module not in self.import_map:
            self.import_map[import_info.module] = set()
        self.import_map[import_info.module].add(file_path)
        
        # Track imports per file
        if file_path not in self.file_imports:
            self.file_imports[file_path] = []
        self.file_imports[file_path].append(import_info)
    
    def get_files_importing_module(self, module_name: str) -> Set[str]:
        """
        Get all files that import a specific module.
        
        Args:
            module_name: Module name to search for
            
        Returns:
            Set of file paths that import the module
        """
        return self.import_map.get(module_name, set())
    
    def get_imports_for_file(self, file_path: str) -> List[ImportInfo]:
        """
        Get all imports for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of import information for the file
        """
        return self.file_imports.get(file_path, [])
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """
        Find circular import dependencies in the project.
        
        Returns:
            List of circular dependency chains
        """
        # This is a simplified implementation
        # In production, you'd want a more sophisticated cycle detection algorithm
        circular_deps = []
        
        # Build a dependency graph
        dep_graph: Dict[str, Set[str]] = {}
        for file_path, imports in self.file_imports.items():
            if file_path not in dep_graph:
                dep_graph[file_path] = set()
            
            for import_info in imports:
                # Try to map module to file
                module_file = self._module_to_file(import_info.module)
                if module_file and module_file != file_path:
                    dep_graph[file_path].add(module_file)
        
        # Simple cycle detection (DFS-based)
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dep_graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, path[:]):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    circular_deps.append(path[cycle_start:] + [neighbor])
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in dep_graph:
            if node not in visited:
                has_cycle(node, [])
        
        return circular_deps
    
    def _module_to_file(self, module_name: str) -> Optional[str]:
        """
        Convert a module name to a file path.
        
        Args:
            module_name: Module name
            
        Returns:
            File path or None if not found
        """
        # Replace dots with path separators
        module_path = module_name.replace('.', os.sep)
        
        # Try as a package
        package_init = os.path.join(self.project_root, module_path, '__init__.py')
        if os.path.exists(package_init):
            return package_init
        
        # Try as a module file
        module_file = os.path.join(self.project_root, module_path + '.py')
        if os.path.exists(module_file):
            return module_file
        
        return None
    
    def get_import_statistics(self) -> Dict[str, any]:
        """
        Get statistics about imports in the project.
        
        Returns:
            Dictionary containing import statistics
        """
        total_imports = sum(len(imports) for imports in self.file_imports.values())
        
        import_types = {
            'standard_library': 0,
            'third_party': 0,
            'local': 0,
            'unknown': 0
        }
        
        for file_path, imports in self.file_imports.items():
            for import_info in imports:
                import_type = self.categorize_import(
                    import_info.module,
                    file_path,
                    import_info.level
                )
                
                if import_type == ImportType.STANDARD_LIBRARY:
                    import_types['standard_library'] += 1
                elif import_type == ImportType.THIRD_PARTY:
                    import_types['third_party'] += 1
                elif import_type in (ImportType.LOCAL_ABSOLUTE, ImportType.LOCAL_RELATIVE):
                    import_types['local'] += 1
                else:
                    import_types['unknown'] += 1
        
        return {
            'total_imports': total_imports,
            'files_with_imports': len(self.file_imports),
            'import_types': import_types,
            'most_imported_modules': self._get_most_imported_modules(10)
        }
    
    def _get_most_imported_modules(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get the most frequently imported modules.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of (module_name, import_count) tuples
        """
        module_counts = {}
        
        for imports in self.file_imports.values():
            for import_info in imports:
                module_counts[import_info.module] = module_counts.get(import_info.module, 0) + 1
        
        sorted_modules = sorted(module_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_modules[:limit]
