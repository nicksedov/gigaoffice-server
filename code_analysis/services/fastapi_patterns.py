"""
FastAPI-Specific Pattern Analyzer.

Handles detection of FastAPI framework-specific patterns including dependency
injection, router registration, and Pydantic model relationships.
"""

import ast
from typing import Set, List, Dict, Any
from code_analysis.services.ast_analysis import ASTAnalysisService


class FastAPIPatternAnalyzer:
    """Analyzer for FastAPI-specific code patterns."""
    
    # FastAPI-specific imports that should be tracked carefully
    FASTAPI_IMPORTS = {
        'FastAPI', 'APIRouter', 'Depends', 'HTTPException',
        'Request', 'Response', 'status', 'BackgroundTasks',
        'File', 'Form', 'Body', 'Query', 'Path', 'Header',
        'Cookie', 'Security', 'WebSocket', 'WebSocketDisconnect'
    }
    
    # Pydantic imports
    PYDANTIC_IMPORTS = {
        'BaseModel', 'Field', 'validator', 'root_validator',
        'ValidationError', 'constr', 'conint', 'confloat'
    }
    
    def __init__(self, ast_service: ASTAnalysisService):
        """
        Initialize FastAPI pattern analyzer.
        
        Args:
            ast_service: AST analysis service
        """
        self.ast_service = ast_service
    
    def find_dependency_injection_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find symbols used in FastAPI dependency injection.
        
        Args:
            tree: AST module
            
        Returns:
            Set of symbol names used in Depends()
        """
        symbols = set()
        
        for node in ast.walk(tree):
            # Look for Depends() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'Depends':
                    # Extract the dependency function name
                    if node.args:
                        arg = node.args[0]
                        if isinstance(arg, ast.Name):
                            symbols.add(arg.id)
                        elif isinstance(arg, ast.Attribute):
                            if isinstance(arg.value, ast.Name):
                                symbols.add(arg.value.id)
        
        return symbols
    
    def find_router_registration_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find routers registered in the application.
        
        Args:
            tree: AST module
            
        Returns:
            Set of router names
        """
        symbols = set()
        
        for node in ast.walk(tree):
            # Look for app.include_router() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'include_router':
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Name):
                                symbols.add(arg.id)
                            elif isinstance(arg, ast.Attribute):
                                if isinstance(arg.value, ast.Name):
                                    symbols.add(arg.value.id)
        
        return symbols
    
    def find_pydantic_model_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find Pydantic models used in the code.
        
        Args:
            tree: AST module
            
        Returns:
            Set of Pydantic model base classes and validators
        """
        symbols = set()
        
        # Find classes inheriting from BaseModel
        classes = self.ast_service.extract_class_definitions(tree)
        for cls in classes:
            for base in cls['bases']:
                if 'BaseModel' in base:
                    # This is a Pydantic model
                    # Check for Field usage
                    for node in ast.walk(cls['node']):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name):
                                if node.func.id in ('Field', 'validator', 'root_validator'):
                                    symbols.add(node.func.id)
        
        return symbols
    
    def find_route_decorator_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find symbols used in route decorators.
        
        Args:
            tree: AST module
            
        Returns:
            Set of symbols used in route decorators
        """
        symbols = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    # Extract symbols from decorators
                    if isinstance(decorator, ast.Call):
                        # @router.get("/path")
                        if isinstance(decorator.func, ast.Attribute):
                            if isinstance(decorator.func.value, ast.Name):
                                symbols.add(decorator.func.value.id)
                    elif isinstance(decorator, ast.Attribute):
                        # @router.middleware
                        if isinstance(decorator.value, ast.Name):
                            symbols.add(decorator.value.id)
        
        return symbols
    
    def find_response_model_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find response models specified in route decorators.
        
        Args:
            tree: AST module
            
        Returns:
            Set of response model names
        """
        symbols = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        # Check for response_model keyword argument
                        for keyword in decorator.keywords:
                            if keyword.arg == 'response_model':
                                value = keyword.value
                                if isinstance(value, ast.Name):
                                    symbols.add(value.id)
                                elif isinstance(value, ast.Attribute):
                                    if isinstance(value.value, ast.Name):
                                        symbols.add(value.value.id)
        
        return symbols
    
    def find_exception_handler_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find exception types used in exception handlers.
        
        Args:
            tree: AST module
            
        Returns:
            Set of exception class names
        """
        symbols = set()
        
        for node in ast.walk(tree):
            # Look for @app.exception_handler(ExceptionType)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == 'exception_handler':
                                if decorator.args:
                                    arg = decorator.args[0]
                                    if isinstance(arg, ast.Name):
                                        symbols.add(arg.id)
        
        return symbols
    
    def find_background_task_usage(self, tree: ast.Module) -> Set[str]:
        """
        Find functions used as background tasks.
        
        Args:
            tree: AST module
            
        Returns:
            Set of background task function names
        """
        symbols = set()
        
        for node in ast.walk(tree):
            # Look for background_tasks.add_task(func)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'add_task':
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Name):
                                symbols.add(arg.id)
        
        return symbols
    
    def get_all_fastapi_used_symbols(self, tree: ast.Module) -> Set[str]:
        """
        Get all symbols used in FastAPI-specific patterns.
        
        Args:
            tree: AST module
            
        Returns:
            Set of all FastAPI-related symbols that are actually used
        """
        all_symbols = set()
        
        all_symbols.update(self.find_dependency_injection_usage(tree))
        all_symbols.update(self.find_router_registration_usage(tree))
        all_symbols.update(self.find_pydantic_model_usage(tree))
        all_symbols.update(self.find_route_decorator_usage(tree))
        all_symbols.update(self.find_response_model_usage(tree))
        all_symbols.update(self.find_exception_handler_usage(tree))
        all_symbols.update(self.find_background_task_usage(tree))
        
        return all_symbols
    
    def analyze_file_for_fastapi_patterns(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive FastAPI pattern analysis for a file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary containing pattern analysis results
        """
        tree = self.ast_service.parse_file(file_path)
        if not tree:
            return {}
        
        return {
            'dependency_injection': self.find_dependency_injection_usage(tree),
            'router_registration': self.find_router_registration_usage(tree),
            'pydantic_models': self.find_pydantic_model_usage(tree),
            'route_decorators': self.find_route_decorator_usage(tree),
            'response_models': self.find_response_model_usage(tree),
            'exception_handlers': self.find_exception_handler_usage(tree),
            'background_tasks': self.find_background_task_usage(tree),
            'all_used_symbols': self.get_all_fastapi_used_symbols(tree)
        }
