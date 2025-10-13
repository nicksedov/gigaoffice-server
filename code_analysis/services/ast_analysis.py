"""
AST Analysis Service for code parsing and manipulation.

Provides functionality for parsing Python code into Abstract Syntax Trees (AST)
and extracting various code elements including imports, type annotations, and usage patterns.
"""

import ast
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImportInfo:
    """Information about an import statement."""
    module: str
    names: List[str]
    aliases: Dict[str, str]
    line_number: int
    column_offset: int
    is_from_import: bool
    level: int = 0  # For relative imports


@dataclass
class SymbolUsage:
    """Information about symbol usage in code."""
    name: str
    line_number: int
    column_offset: int
    context: str  # 'load', 'store', 'del', 'param', 'annotation'


class ASTAnalysisService:
    """Service for parsing and analyzing Python AST."""
    
    def __init__(self):
        """Initialize AST analysis service."""
        self.ast_cache: Dict[str, ast.Module] = {}
    
    def parse_file(self, file_path: str, use_cache: bool = True) -> Optional[ast.Module]:
        """
        Parse a Python file into an AST.
        
        Args:
            file_path: Path to the Python file
            use_cache: Whether to use cached AST if available
            
        Returns:
            Parsed AST module or None if parsing fails
        """
        if use_cache and file_path in self.ast_cache:
            return self.ast_cache[file_path]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=file_path)
            
            if use_cache:
                self.ast_cache[file_path] = tree
            
            return tree
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def extract_imports(self, tree: ast.Module) -> List[ImportInfo]:
        """
        Extract all import statements from an AST.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            List of ImportInfo objects
        """
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module=alias.name,
                        names=[alias.name],
                        aliases={alias.name: alias.asname} if alias.asname else {},
                        line_number=node.lineno,
                        column_offset=node.col_offset,
                        is_from_import=False
                    ))
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names = [alias.name for alias in node.names]
                    aliases = {alias.name: alias.asname for alias in node.names if alias.asname}
                    
                    imports.append(ImportInfo(
                        module=node.module,
                        names=names,
                        aliases=aliases,
                        line_number=node.lineno,
                        column_offset=node.col_offset,
                        is_from_import=True,
                        level=node.level or 0
                    ))
        
        return imports
    
    def extract_symbol_usages(self, tree: ast.Module) -> List[SymbolUsage]:
        """
        Extract all symbol usages from an AST.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            List of SymbolUsage objects
        """
        usages = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                context = self._get_context_type(node.ctx)
                usages.append(SymbolUsage(
                    name=node.id,
                    line_number=node.lineno,
                    column_offset=node.col_offset,
                    context=context
                ))
            
            elif isinstance(node, ast.Attribute):
                # Handle attribute access like module.function
                if isinstance(node.value, ast.Name):
                    usages.append(SymbolUsage(
                        name=node.value.id,
                        line_number=node.lineno,
                        column_offset=node.col_offset,
                        context='load'
                    ))
        
        return usages
    
    def _get_context_type(self, ctx: ast.expr_context) -> str:
        """Get string representation of AST context."""
        if isinstance(ctx, ast.Load):
            return 'load'
        elif isinstance(ctx, ast.Store):
            return 'store'
        elif isinstance(ctx, ast.Del):
            return 'del'
        elif isinstance(ctx, ast.Param):
            return 'param'
        else:
            return 'unknown'
    
    def extract_type_annotations(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """
        Extract type annotations from an AST.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            List of dictionaries containing annotation information
        """
        annotations = []
        
        for node in ast.walk(tree):
            # Function annotations
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Return type annotation
                if node.returns:
                    annotations.append({
                        'type': 'return',
                        'annotation': ast.unparse(node.returns) if hasattr(ast, 'unparse') else ast.get_source_segment(node.returns),
                        'line_number': node.lineno,
                        'function_name': node.name,
                        'node': node.returns
                    })
                
                # Parameter annotations
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    if arg.annotation:
                        annotations.append({
                            'type': 'parameter',
                            'annotation': ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation),
                            'line_number': arg.lineno,
                            'parameter_name': arg.arg,
                            'function_name': node.name,
                            'node': arg.annotation
                        })
            
            # Variable annotations
            elif isinstance(node, ast.AnnAssign):
                annotations.append({
                    'type': 'variable',
                    'annotation': ast.unparse(node.annotation) if hasattr(ast, 'unparse') else str(node.annotation),
                    'line_number': node.lineno,
                    'node': node.annotation
                })
        
        return annotations
    
    def extract_class_definitions(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """
        Extract class definitions from an AST.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            List of class definition information
        """
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_classes.append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))
                
                classes.append({
                    'name': node.name,
                    'line_number': node.lineno,
                    'bases': base_classes,
                    'decorators': [ast.unparse(dec) if hasattr(ast, 'unparse') else str(dec) for dec in node.decorator_list],
                    'node': node
                })
        
        return classes
    
    def extract_function_calls(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """
        Extract function calls from an AST.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            List of function call information
        """
        calls = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"
                    else:
                        func_name = node.func.attr
                
                if func_name:
                    calls.append({
                        'name': func_name,
                        'line_number': node.lineno,
                        'column_offset': node.col_offset,
                        'node': node
                    })
        
        return calls
    
    def extract_string_literals(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """
        Extract string literals that might contain dynamic imports.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            List of string literal information
        """
        strings = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append({
                    'value': node.value,
                    'line_number': node.lineno,
                    'column_offset': node.col_offset
                })
            elif isinstance(node, ast.Str):  # For Python < 3.8
                strings.append({
                    'value': node.s,
                    'line_number': node.lineno,
                    'column_offset': node.col_offset
                })
        
        return strings
    
    def get_node_source(self, node: ast.AST, source_code: str) -> str:
        """
        Get the source code for a specific AST node.
        
        Args:
            node: AST node
            source_code: Complete source code of the file
            
        Returns:
            Source code snippet for the node
        """
        if hasattr(ast, 'unparse'):
            return ast.unparse(node)
        elif hasattr(ast, 'get_source_segment'):
            return ast.get_source_segment(source_code, node) or ""
        else:
            return ""
    
    def find_all_names(self, tree: ast.Module) -> Set[str]:
        """
        Find all names (identifiers) used in the AST.
        
        Args:
            tree: AST module to analyze
            
        Returns:
            Set of all identifier names
        """
        names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                names.add(node.name)
        
        return names
    
    def clear_cache(self) -> None:
        """Clear the AST cache."""
        self.ast_cache.clear()
    
    def get_cache_size(self) -> int:
        """Get the number of cached AST modules."""
        return len(self.ast_cache)
