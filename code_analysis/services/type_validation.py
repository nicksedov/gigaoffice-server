"""
Type Validation Service for analyzing type annotations.

Validates type annotations and identifies non-existent type references,
missing imports, and other type-related issues.
"""

import ast
import sys
from typing import Dict, List, Set, Optional, Any
from code_analysis.services.ast_analysis import ASTAnalysisService
from code_analysis.services.import_resolver import ImportResolverService
from code_analysis.utils.config_manager import ConfigurationManager
from code_analysis.models.results import TypeError, TypeErrorType


class TypeValidationService:
    """Service for validating type annotations in Python code."""
    
    # Built-in types that don't need imports
    BUILTIN_TYPES = {
        'int', 'str', 'float', 'bool', 'bytes', 'bytearray',
        'list', 'tuple', 'dict', 'set', 'frozenset',
        'object', 'type', 'None', 'Any', 'callable',
        'complex', 'memoryview', 'range', 'slice',
        'property', 'classmethod', 'staticmethod'
    }
    
    # typing module types
    TYPING_TYPES = {
        'List', 'Dict', 'Set', 'Tuple', 'FrozenSet',
        'Optional', 'Union', 'Any', 'Callable', 'Type',
        'TypeVar', 'Generic', 'Protocol', 'Literal',
        'Final', 'ClassVar', 'Annotated', 'Awaitable',
        'Coroutine', 'AsyncIterable', 'AsyncIterator',
        'AsyncGenerator', 'Iterable', 'Iterator', 'Generator',
        'Sequence', 'MutableSequence', 'Mapping', 'MutableMapping',
        'ByteString', 'Deque', 'DefaultDict', 'OrderedDict',
        'Counter', 'ChainMap', 'NamedTuple', 'TypedDict',
        'cast', 'overload', 'get_type_hints', 'ForwardRef',
        'NewType', 'NoReturn', 'Text', 'AnyStr', 'IO',
        'TextIO', 'BinaryIO', 'Pattern', 'Match',
        'AbstractSet', 'MutableSet', 'ContextManager',
        'AsyncContextManager', 'SupportsInt', 'SupportsFloat',
        'SupportsComplex', 'SupportsBytes', 'SupportsAbs',
        'SupportsRound', 'Reversible', 'Sized', 'Hashable',
        'Container', 'Collection', 'Never'
    }
    
    def __init__(
        self,
        ast_service: ASTAnalysisService,
        resolver_service: ImportResolverService,
        config: ConfigurationManager
    ):
        """
        Initialize type validation service.
        
        Args:
            ast_service: AST analysis service
            resolver_service: Import resolver service
            config: Configuration manager
        """
        self.ast_service = ast_service
        self.resolver_service = resolver_service
        self.config = config
        self.available_types_cache: Dict[str, Set[str]] = {}
    
    def validate_file(self, file_path: str) -> List[TypeError]:
        """
        Validate type annotations in a file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of type errors found
        """
        if not self.config.should_check_type_annotations():
            return []
        
        # Parse the file
        tree = self.ast_service.parse_file(file_path)
        if not tree:
            return []
        
        # Get available types in this file
        available_types = self._get_available_types(file_path, tree)
        
        # Extract type annotations
        annotations = self.ast_service.extract_type_annotations(tree)
        
        # Validate each annotation
        type_errors = []
        for annotation_info in annotations:
            errors = self._validate_annotation(
                annotation_info,
                available_types,
                file_path,
                tree
            )
            type_errors.extend(errors)
        
        return type_errors
    
    def _get_available_types(self, file_path: str, tree: ast.Module) -> Set[str]:
        """
        Get all types available in a file (from imports and definitions).
        
        Args:
            file_path: Path to the file
            tree: AST module
            
        Returns:
            Set of available type names
        """
        if file_path in self.available_types_cache:
            return self.available_types_cache[file_path]
        
        available = set()
        
        # Add builtin types
        available.update(self.BUILTIN_TYPES)
        
        # Add types from imports
        imports = self.ast_service.extract_imports(tree)
        for import_info in imports:
            if import_info.is_from_import:
                # From imports - add imported names
                for name in import_info.names:
                    if name == '*':
                        # Star imports - we can't easily determine what's available
                        continue
                    # Use alias if present
                    actual_name = import_info.aliases.get(name, name)
                    available.add(actual_name)
            else:
                # Direct imports - add module name
                module = import_info.module
                actual_name = import_info.aliases.get(module, module.split('.')[0])
                available.add(actual_name)
        
        # Add locally defined classes
        classes = self.ast_service.extract_class_definitions(tree)
        for cls in classes:
            available.add(cls['name'])
        
        # Add typing types if typing is imported
        for import_info in imports:
            if import_info.module == 'typing' or import_info.module.startswith('typing.'):
                if import_info.is_from_import:
                    # Specific typing imports
                    for name in import_info.names:
                        if name == '*':
                            available.update(self.TYPING_TYPES)
                        else:
                            actual_name = import_info.aliases.get(name, name)
                            available.add(actual_name)
                else:
                    # import typing - all typing types available as typing.X
                    available.add('typing')
        
        self.available_types_cache[file_path] = available
        return available
    
    def _validate_annotation(
        self,
        annotation_info: Dict[str, Any],
        available_types: Set[str],
        file_path: str,
        tree: ast.Module
    ) -> List[TypeError]:
        """
        Validate a single type annotation.
        
        Args:
            annotation_info: Annotation information dictionary
            available_types: Set of available type names
            file_path: Path to the file
            tree: AST module
            
        Returns:
            List of type errors found
        """
        errors = []
        node = annotation_info.get('node')
        
        if not node:
            return errors
        
        # Extract type references from the annotation
        type_refs = self._extract_type_references(node)
        
        # Check each type reference
        for type_ref in type_refs:
            if not self._is_type_available(type_ref, available_types):
                # Type is not available
                error_type = self._classify_type_error(type_ref, available_types, tree)
                suggested_fix = self._suggest_fix(type_ref, error_type)
                
                # Get context string
                context = annotation_info.get('annotation', '')
                if annotation_info.get('type') == 'parameter':
                    context = f"Parameter '{annotation_info.get('parameter_name')}' in function '{annotation_info.get('function_name')}'"
                elif annotation_info.get('type') == 'return':
                    context = f"Return type of function '{annotation_info.get('function_name')}'"
                elif annotation_info.get('type') == 'variable':
                    context = f"Variable annotation"
                
                error = TypeError(
                    file_path=file_path,
                    line_number=annotation_info.get('line_number', 0),
                    error_type=error_type,
                    symbol_name=type_ref,
                    context=context,
                    suggested_fix=suggested_fix,
                    severity='error'
                )
                
                errors.append(error)
        
        return errors
    
    def _extract_type_references(self, node: ast.AST) -> Set[str]:
        """
        Extract all type references from an annotation node.
        
        Args:
            node: Annotation AST node
            
        Returns:
            Set of type reference names
        """
        type_refs = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                type_refs.add(child.id)
            elif isinstance(child, ast.Attribute):
                # Handle dotted names like typing.List
                if isinstance(child.value, ast.Name):
                    # Don't add the attribute part, just the module
                    type_refs.add(child.value.id)
            elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                # Forward reference (string annotation)
                # Parse the string to extract type names
                forward_refs = self._parse_forward_reference(child.value)
                type_refs.update(forward_refs)
            elif isinstance(child, ast.Str):  # Python < 3.8
                forward_refs = self._parse_forward_reference(child.s)
                type_refs.update(forward_refs)
        
        return type_refs
    
    def _parse_forward_reference(self, ref_string: str) -> Set[str]:
        """
        Parse a forward reference string to extract type names.
        
        Args:
            ref_string: Forward reference string
            
        Returns:
            Set of type names
        """
        types = set()
        
        try:
            # Try to parse as an expression
            expr = ast.parse(ref_string, mode='eval')
            for node in ast.walk(expr):
                if isinstance(node, ast.Name):
                    types.add(node.id)
        except SyntaxError:
            # If parsing fails, try simple pattern matching
            import re
            # Match capitalized words (likely type names)
            pattern = r'\b([A-Z][a-zA-Z0-9_]*)\b'
            matches = re.findall(pattern, ref_string)
            types.update(matches)
        
        return types
    
    def _is_type_available(self, type_name: str, available_types: Set[str]) -> bool:
        """
        Check if a type is available in the current scope.
        
        Args:
            type_name: Name of the type to check
            available_types: Set of available type names
            
        Returns:
            True if the type is available
        """
        # Check if it's in available types
        if type_name in available_types:
            return True
        
        # Check if it's a builtin
        if type_name in self.BUILTIN_TYPES:
            return True
        
        # Check if it's a typing type (in case typing import was missed)
        if type_name in self.TYPING_TYPES:
            # Still return False if typing wasn't imported
            # This will trigger a missing import error
            return 'typing' in available_types or type_name in available_types
        
        return False
    
    def _classify_type_error(
        self,
        type_name: str,
        available_types: Set[str],
        tree: ast.Module
    ) -> TypeErrorType:
        """
        Classify the type of error.
        
        Args:
            type_name: The type name causing the error
            available_types: Set of available types
            tree: AST module
            
        Returns:
            Type error classification
        """
        # Check if it's a typing type that needs import
        if type_name in self.TYPING_TYPES:
            return TypeErrorType.MISSING_IMPORT
        
        # Check if it looks like a valid class name but isn't imported
        if type_name[0].isupper():
            return TypeErrorType.MISSING_IMPORT
        
        # Check if it might be a forward reference issue
        # (defined later in the same file)
        classes = self.ast_service.extract_class_definitions(tree)
        class_names = {cls['name'] for cls in classes}
        if type_name in class_names:
            return TypeErrorType.FORWARD_REFERENCE
        
        # Otherwise, it's likely an invalid reference
        return TypeErrorType.INVALID_REFERENCE
    
    def _suggest_fix(self, type_name: str, error_type: TypeErrorType) -> str:
        """
        Suggest a fix for the type error.
        
        Args:
            type_name: The type name causing the error
            error_type: Classification of the error
            
        Returns:
            Suggestion string
        """
        if error_type == TypeErrorType.MISSING_IMPORT:
            if type_name in self.TYPING_TYPES:
                return f"Add import: from typing import {type_name}"
            else:
                return f"Import the type: {type_name}"
        
        elif error_type == TypeErrorType.FORWARD_REFERENCE:
            return f"Use forward reference: '{type_name}' (as a string)"
        
        elif error_type == TypeErrorType.INVALID_REFERENCE:
            return f"Check if '{type_name}' is the correct type name"
        
        return "Review type annotation"
    
    def get_validation_statistics(self) -> Dict[str, any]:
        """
        Get statistics about type validation.
        
        Returns:
            Dictionary containing validation statistics
        """
        return {
            'files_checked': len(self.available_types_cache),
            'builtin_types_count': len(self.BUILTIN_TYPES),
            'typing_types_count': len(self.TYPING_TYPES)
        }
