"""
Import Analyzer for detecting unused imports.

Implements multi-phase detection algorithm to accurately identify unused imports
by tracking symbol usage across the entire codebase.
"""

import ast
import re
from typing import Dict, List, Set, Optional, Tuple
from code_analysis.services.ast_analysis import ASTAnalysisService, ImportInfo, SymbolUsage
from code_analysis.services.import_resolver import ImportResolverService
from code_analysis.services.fastapi_patterns import FastAPIPatternAnalyzer
from code_analysis.utils.config_manager import ConfigurationManager
from code_analysis.models.results import UnusedImport, ImportType


class ImportAnalyzer:
    """Analyzer for detecting unused imports in Python files."""
    
    def __init__(
        self,
        ast_service: ASTAnalysisService,
        resolver_service: ImportResolverService,
        config: ConfigurationManager
    ):
        """
        Initialize import analyzer.
        
        Args:
            ast_service: AST analysis service
            resolver_service: Import resolver service
            config: Configuration manager
        """
        self.ast_service = ast_service
        self.resolver_service = resolver_service
        self.config = config
        self.symbol_usage_map: Dict[str, Set[str]] = {}  # file -> used symbols
        self.fastapi_analyzer = FastAPIPatternAnalyzer(ast_service)
    
    def analyze_file(self, file_path: str) -> List[UnusedImport]:
        """
        Analyze a file for unused imports.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of unused imports found in the file
        """
        # Parse the file
        tree = self.ast_service.parse_file(file_path)
        if not tree:
            return []
        
        # Extract imports
        imports = self.ast_service.extract_imports(tree)
        if not imports:
            return []
        
        # Extract symbol usages
        usages = self.ast_service.extract_symbol_usages(tree)
        
        # Track used symbols
        used_symbols = self._extract_used_symbols(tree, usages)
        self.symbol_usage_map[file_path] = used_symbols
        
        # Check for special usage patterns
        type_annotation_symbols = self._extract_type_annotation_symbols(tree)
        string_reference_symbols = self._extract_string_reference_symbols(tree)
        docstring_symbols = self._extract_docstring_symbols(tree, file_path)
        
        # Combine all used symbols
        all_used_symbols = used_symbols | type_annotation_symbols | string_reference_symbols | docstring_symbols
        
        # Check __all__ declaration
        exported_symbols = self._extract_exported_symbols(tree)
        if exported_symbols:
            all_used_symbols.update(exported_symbols)
        
        # Check FastAPI-specific patterns if enabled
        if self.config.should_check_fastapi_patterns():
            fastapi_symbols = self.fastapi_analyzer.get_all_fastapi_used_symbols(tree)
            all_used_symbols.update(fastapi_symbols)
        
        # Analyze each import
        unused_imports = []
        for import_info in imports:
            unused_symbols = self._check_import_usage(
                import_info,
                all_used_symbols,
                file_path
            )
            
            if unused_symbols:
                # Categorize the import
                import_type = self.resolver_service.categorize_import(
                    import_info.module,
                    file_path,
                    import_info.level
                )
                
                # Generate import statement string
                import_stmt = self._generate_import_statement(import_info)
                
                # Generate suggestions
                suggestions = self._generate_suggestions(import_info, unused_symbols)
                
                unused_import = UnusedImport(
                    file_path=file_path,
                    line_number=import_info.line_number,
                    import_statement=import_stmt,
                    import_type=import_type,
                    unused_symbols=unused_symbols,
                    suggestions=suggestions,
                    column_offset=import_info.column_offset
                )
                
                unused_imports.append(unused_import)
        
        return unused_imports
    
    def _extract_used_symbols(self, tree: ast.Module, usages: List[SymbolUsage]) -> Set[str]:
        """
        Extract all symbols that are actually used in the code.
        
        Args:
            tree: AST module
            usages: List of symbol usages
            
        Returns:
            Set of used symbol names
        """
        used_symbols = set()
        
        # Add symbols from usage list (only loads, not stores)
        for usage in usages:
            if usage.context == 'load':
                used_symbols.add(usage.name)
        
        # Add function and class names that are actually called/instantiated
        calls = self.ast_service.extract_function_calls(tree)
        for call in calls:
            # Extract base name from dotted names
            base_name = call['name'].split('.')[0]
            used_symbols.add(base_name)
        
        # Add base classes
        classes = self.ast_service.extract_class_definitions(tree)
        for cls in classes:
            for base in cls['bases']:
                base_name = base.split('.')[0]
                used_symbols.add(base_name)
        
        return used_symbols
    
    def _extract_type_annotation_symbols(self, tree: ast.Module) -> Set[str]:
        """
        Extract symbols used in type annotations.
        
        Args:
            tree: AST module
            
        Returns:
            Set of symbols used in type annotations
        """
        symbols = set()
        
        annotations = self.ast_service.extract_type_annotations(tree)
        for annotation_info in annotations:
            node = annotation_info.get('node')
            if node:
                # Extract names from annotation AST
                annotation_symbols = self._extract_names_from_node(node)
                symbols.update(annotation_symbols)
        
        return symbols
    
    def _extract_names_from_node(self, node: ast.AST) -> Set[str]:
        """
        Recursively extract all Name nodes from an AST node.
        
        Args:
            node: AST node
            
        Returns:
            Set of name identifiers
        """
        names = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.add(child.id)
            elif isinstance(child, ast.Attribute):
                # For attributes like List[str], we want 'List'
                if isinstance(child.value, ast.Name):
                    names.add(child.value.id)
        
        return names
    
    def _extract_string_reference_symbols(self, tree: ast.Module) -> Set[str]:
        """
        Extract symbols that might be referenced in string literals.
        
        Args:
            tree: AST module
            
        Returns:
            Set of potential symbol names from strings
        """
        if not self.config.get('analysis_rules.check_string_imports', True):
            return set()
        
        symbols = set()
        strings = self.ast_service.extract_string_literals(tree)
        
        # Pattern for potential module/class names in strings
        # This is a heuristic - looks for capitalized words or dotted names
        pattern = r'\b([A-Z][a-zA-Z0-9_]*(?:\.[A-Z][a-zA-Z0-9_]*)*)\b'
        
        for string_info in strings:
            matches = re.findall(pattern, string_info['value'])
            for match in matches:
                # Get the base name
                base_name = match.split('.')[0]
                symbols.add(base_name)
        
        return symbols
    
    def _extract_docstring_symbols(self, tree: ast.Module, file_path: str) -> Set[str]:
        """
        Extract symbols referenced in docstrings.
        
        Args:
            tree: AST module
            file_path: Path to the file
            
        Returns:
            Set of symbols referenced in docstrings
        """
        if not self.config.get('analysis_rules.check_docstrings', True):
            return set()
        
        symbols = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Extract docstrings
            for node in ast.walk(tree):
                docstring = ast.get_docstring(node)
                if docstring:
                    # Look for :param, :type, :return, :rtype references
                    # Also look for class/function references in backticks
                    
                    # Extract from Sphinx/Google style annotations
                    type_pattern = r':(?:param|type|return|rtype|raises)\s+([A-Z][a-zA-Z0-9_\.]*)'
                    matches = re.findall(type_pattern, docstring)
                    for match in matches:
                        base_name = match.split('.')[0]
                        symbols.add(base_name)
                    
                    # Extract from backtick references
                    backtick_pattern = r'`([A-Z][a-zA-Z0-9_\.]*)`'
                    matches = re.findall(backtick_pattern, docstring)
                    for match in matches:
                        base_name = match.split('.')[0]
                        symbols.add(base_name)
        
        except Exception:
            pass
        
        return symbols
    
    def _extract_exported_symbols(self, tree: ast.Module) -> Set[str]:
        """
        Extract symbols declared in __all__.
        
        Args:
            tree: AST module
            
        Returns:
            Set of exported symbol names
        """
        exported = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        # Extract list items
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exported.add(elt.value)
                                elif isinstance(elt, ast.Str):  # Python < 3.8
                                    exported.add(elt.s)
        
        return exported
    
    def _check_import_usage(
        self,
        import_info: ImportInfo,
        used_symbols: Set[str],
        file_path: str
    ) -> List[str]:
        """
        Check if an import is used.
        
        Args:
            import_info: Import information
            used_symbols: Set of symbols used in the file
            file_path: Path to the file
            
        Returns:
            List of unused symbol names (empty if all are used)
        """
        unused = []
        
        if import_info.is_from_import:
            # For "from X import Y, Z" - check each imported name
            for name in import_info.names:
                # Check if it's a star import
                if name == '*':
                    if self.config.get('analysis_rules.ignore_star_imports', False):
                        continue
                    # Star imports are harder to track - conservative approach
                    # We'll flag them only if we're very confident
                    continue
                
                # Check the actual name used (could be aliased)
                actual_name = import_info.aliases.get(name, name)
                
                if actual_name not in used_symbols:
                    unused.append(name)
        else:
            # For "import X" or "import X as Y"
            module_name = import_info.module
            
            # Check if the module or its alias is used
            alias = import_info.aliases.get(module_name)
            check_name = alias if alias else module_name.split('.')[0]
            
            if check_name not in used_symbols:
                unused.append(module_name)
        
        return unused
    
    def _generate_import_statement(self, import_info: ImportInfo) -> str:
        """
        Generate the import statement string.
        
        Args:
            import_info: Import information
            
        Returns:
            Import statement as string
        """
        if import_info.is_from_import:
            module = import_info.module
            if import_info.level > 0:
                module = '.' * import_info.level + (module if module else '')
            
            names = []
            for name in import_info.names:
                if name in import_info.aliases:
                    names.append(f"{name} as {import_info.aliases[name]}")
                else:
                    names.append(name)
            
            return f"from {module} import {', '.join(names)}"
        else:
            module = import_info.module
            if module in import_info.aliases:
                return f"import {module} as {import_info.aliases[module]}"
            else:
                return f"import {module}"
    
    def _generate_suggestions(self, import_info: ImportInfo, unused_symbols: List[str]) -> List[str]:
        """
        Generate suggestions for fixing unused imports.
        
        Args:
            import_info: Import information
            unused_symbols: List of unused symbols
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        if import_info.is_from_import and len(unused_symbols) < len(import_info.names):
            # Some symbols are used, some are not
            used_names = [n for n in import_info.names if n not in unused_symbols]
            if used_names:
                suggestions.append(f"Remove unused imports: {', '.join(unused_symbols)}")
                suggestions.append(f"Keep only: {', '.join(used_names)}")
        else:
            # All symbols are unused
            suggestions.append("Remove this import statement entirely")
        
        return suggestions
    
    def get_usage_statistics(self) -> Dict[str, any]:
        """
        Get statistics about symbol usage.
        
        Returns:
            Dictionary containing usage statistics
        """
        total_symbols = sum(len(symbols) for symbols in self.symbol_usage_map.values())
        files_analyzed = len(self.symbol_usage_map)
        
        return {
            'files_analyzed': files_analyzed,
            'total_symbols_used': total_symbols,
            'average_symbols_per_file': total_symbols / files_analyzed if files_analyzed > 0 else 0
        }
