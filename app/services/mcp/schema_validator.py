"""
MCP Tool Schema Validator
Validates that local tool schemas remain synchronized with MCP server contracts
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from .tool_schemas import MCP_TOOL_SCHEMAS, list_available_tools


class SchemaValidator:
    """
    Validates MCP tool schema integrity and consistency
    
    Provides validation capabilities for:
    - Schema completeness
    - Required field presence
    - Type specification validity
    - Parameter consistency
    """
    
    def __init__(self):
        """Initialize schema validator"""
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
    
    def validate_all_schemas(self) -> Dict[str, Any]:
        """
        Validate all registered tool schemas
        
        Returns:
            Validation report with status and any issues
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        tool_names = list_available_tools()
        
        for tool_name in tool_names:
            self._validate_tool_schema(tool_name)
        
        report = {
            "valid": len(self.validation_errors) == 0,
            "total_tools": len(tool_names),
            "tools_validated": tool_names,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings
        }
        
        if report["valid"]:
            logger.info(
                f"Schema validation passed: {report['total_tools']} tools validated successfully"
            )
        else:
            logger.error(
                f"Schema validation failed: {report['error_count']} errors, "
                f"{report['warning_count']} warnings"
            )
        
        return report
    
    def _validate_tool_schema(self, tool_name: str):
        """
        Validate a single tool schema
        
        Args:
            tool_name: Name of the tool to validate
        """
        schema = MCP_TOOL_SCHEMAS.get(tool_name)
        
        if not schema:
            self.validation_errors.append(f"{tool_name}: Schema not found")
            return
        
        # Validate description
        if "description" not in schema or not schema["description"]:
            self.validation_errors.append(f"{tool_name}: Missing or empty description")
        
        # Validate parameters
        if "parameters" not in schema:
            self.validation_errors.append(f"{tool_name}: Missing parameters section")
            return
        
        parameters = schema["parameters"]
        
        # Check for filepath parameter (should be present in all tools)
        if "filepath" not in parameters:
            self.validation_warnings.append(
                f"{tool_name}: Missing 'filepath' parameter (expected in all tools)"
            )
        
        # Validate each parameter
        for param_name, param_spec in parameters.items():
            self._validate_parameter(tool_name, param_name, param_spec)
    
    def _validate_parameter(
        self,
        tool_name: str,
        param_name: str,
        param_spec: Dict[str, Any]
    ):
        """
        Validate a single parameter specification
        
        Args:
            tool_name: Name of the tool
            param_name: Name of the parameter
            param_spec: Parameter specification dictionary
        """
        param_path = f"{tool_name}.{param_name}"
        
        # Check required fields
        required_fields = ["type", "required", "description"]
        for field in required_fields:
            if field not in param_spec:
                self.validation_errors.append(f"{param_path}: Missing '{field}' field")
        
        # Validate type
        if "type" in param_spec:
            valid_types = ["str", "int", "bool", "float", "List[str]", "List[int]", "List[List]", "Dict"]
            if param_spec["type"] not in valid_types:
                self.validation_warnings.append(
                    f"{param_path}: Type '{param_spec['type']}' may not be supported"
                )
        
        # Validate required flag
        if "required" in param_spec:
            if not isinstance(param_spec["required"], bool):
                self.validation_errors.append(
                    f"{param_path}: 'required' must be boolean, got {type(param_spec['required'])}"
                )
            
            # Check optional parameters have defaults
            if not param_spec["required"] and "default" not in param_spec:
                self.validation_errors.append(
                    f"{param_path}: Optional parameter missing 'default' value"
                )
        
        # Validate description
        if "description" in param_spec:
            if not isinstance(param_spec["description"], str) or not param_spec["description"]:
                self.validation_errors.append(f"{param_path}: Description must be non-empty string")
    
    def check_filepath_auto_injection(self) -> Dict[str, Any]:
        """
        Verify all tools have filepath parameter with auto-injection note
        
        Returns:
            Report of filepath parameter status across all tools
        """
        tool_names = list_available_tools()
        tools_with_filepath = []
        tools_without_filepath = []
        tools_with_proper_description = []
        tools_with_improper_description = []
        
        for tool_name in tool_names:
            schema = MCP_TOOL_SCHEMAS.get(tool_name)
            if not schema or "parameters" not in schema:
                continue
            
            parameters = schema["parameters"]
            
            if "filepath" in parameters:
                tools_with_filepath.append(tool_name)
                
                filepath_desc = parameters["filepath"].get("description", "")
                if "auto-inject" in filepath_desc.lower() or "do not provide" in filepath_desc.lower():
                    tools_with_proper_description.append(tool_name)
                else:
                    tools_with_improper_description.append(tool_name)
            else:
                tools_without_filepath.append(tool_name)
        
        report = {
            "total_tools": len(tool_names),
            "with_filepath": len(tools_with_filepath),
            "without_filepath": len(tools_without_filepath),
            "proper_auto_inject_note": len(tools_with_proper_description),
            "missing_auto_inject_note": len(tools_with_improper_description),
            "tools_without_filepath": tools_without_filepath,
            "tools_missing_note": tools_with_improper_description
        }
        
        if tools_without_filepath:
            logger.warning(
                f"Tools without filepath parameter: {', '.join(tools_without_filepath)}"
            )
        
        if tools_with_improper_description:
            logger.warning(
                f"Tools missing auto-injection note in filepath description: "
                f"{', '.join(tools_with_improper_description)}"
            )
        
        return report
    
    def generate_validation_report(self) -> str:
        """
        Generate a formatted validation report
        
        Returns:
            Formatted string report
        """
        validation_result = self.validate_all_schemas()
        filepath_result = self.check_filepath_auto_injection()
        
        lines = [
            "=" * 70,
            "MCP Tool Schema Validation Report",
            "=" * 70,
            "",
            f"Total Tools Registered: {validation_result['total_tools']}",
            f"Validation Status: {'PASSED' if validation_result['valid'] else 'FAILED'}",
            "",
            "Schema Validation:",
            f"  Errors: {validation_result['error_count']}",
            f"  Warnings: {validation_result['warning_count']}",
            ""
        ]
        
        if validation_result['errors']:
            lines.append("Errors:")
            for error in validation_result['errors']:
                lines.append(f"  - {error}")
            lines.append("")
        
        if validation_result['warnings']:
            lines.append("Warnings:")
            for warning in validation_result['warnings']:
                lines.append(f"  - {warning}")
            lines.append("")
        
        lines.extend([
            "Filepath Auto-Injection Check:",
            f"  Tools with filepath parameter: {filepath_result['with_filepath']}/{filepath_result['total_tools']}",
            f"  Tools with proper auto-inject note: {filepath_result['proper_auto_inject_note']}",
            f"  Tools missing auto-inject note: {filepath_result['missing_auto_inject_note']}",
            ""
        ])
        
        if filepath_result['tools_without_filepath']:
            lines.append("Tools without filepath parameter:")
            for tool in filepath_result['tools_without_filepath']:
                lines.append(f"  - {tool}")
            lines.append("")
        
        if filepath_result['tools_missing_note']:
            lines.append("Tools missing auto-injection note:")
            for tool in filepath_result['tools_missing_note']:
                lines.append(f"  - {tool}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# Global validator instance
schema_validator = SchemaValidator()


def validate_schemas_on_startup():
    """
    Validate schemas at application startup
    
    Should be called during application initialization to ensure
    all schemas are properly configured before use.
    """
    logger.info("Running MCP tool schema validation...")
    
    report = schema_validator.generate_validation_report()
    print(report)
    
    validation_result = schema_validator.validate_all_schemas()
    
    if not validation_result["valid"]:
        logger.error(
            f"Schema validation failed with {validation_result['error_count']} errors. "
            "Please fix schema definitions before proceeding."
        )
        # Note: In production, you might want to raise an exception here
        # to prevent application startup with invalid schemas
    
    return validation_result["valid"]
"""
MCP Tool Schema Validator
Validates that local tool schemas remain synchronized with MCP server contracts
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from .tool_schemas import MCP_TOOL_SCHEMAS, list_available_tools


class SchemaValidator:
    """
    Validates MCP tool schema integrity and consistency
    
    Provides validation capabilities for:
    - Schema completeness
    - Required field presence
    - Type specification validity
    - Parameter consistency
    """
    
    def __init__(self):
        """Initialize schema validator"""
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
    
    def validate_all_schemas(self) -> Dict[str, Any]:
        """
        Validate all registered tool schemas
        
        Returns:
            Validation report with status and any issues
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        tool_names = list_available_tools()
        
        for tool_name in tool_names:
            self._validate_tool_schema(tool_name)
        
        report = {
            "valid": len(self.validation_errors) == 0,
            "total_tools": len(tool_names),
            "tools_validated": tool_names,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings
        }
        
        if report["valid"]:
            logger.info(
                f"Schema validation passed: {report['total_tools']} tools validated successfully"
            )
        else:
            logger.error(
                f"Schema validation failed: {report['error_count']} errors, "
                f"{report['warning_count']} warnings"
            )
        
        return report
    
    def _validate_tool_schema(self, tool_name: str):
        """
        Validate a single tool schema
        
        Args:
            tool_name: Name of the tool to validate
        """
        schema = MCP_TOOL_SCHEMAS.get(tool_name)
        
        if not schema:
            self.validation_errors.append(f"{tool_name}: Schema not found")
            return
        
        # Validate description
        if "description" not in schema or not schema["description"]:
            self.validation_errors.append(f"{tool_name}: Missing or empty description")
        
        # Validate parameters
        if "parameters" not in schema:
            self.validation_errors.append(f"{tool_name}: Missing parameters section")
            return
        
        parameters = schema["parameters"]
        
        # Check for filepath parameter (should be present in all tools)
        if "filepath" not in parameters:
            self.validation_warnings.append(
                f"{tool_name}: Missing 'filepath' parameter (expected in all tools)"
            )
        
        # Validate each parameter
        for param_name, param_spec in parameters.items():
            self._validate_parameter(tool_name, param_name, param_spec)
    
    def _validate_parameter(
        self,
        tool_name: str,
        param_name: str,
        param_spec: Dict[str, Any]
    ):
        """
        Validate a single parameter specification
        
        Args:
            tool_name: Name of the tool
            param_name: Name of the parameter
            param_spec: Parameter specification dictionary
        """
        param_path = f"{tool_name}.{param_name}"
        
        # Check required fields
        required_fields = ["type", "required", "description"]
        for field in required_fields:
            if field not in param_spec:
                self.validation_errors.append(f"{param_path}: Missing '{field}' field")
        
        # Validate type
        if "type" in param_spec:
            valid_types = ["str", "int", "bool", "float", "List[str]", "List[int]", "List[List]", "Dict"]
            if param_spec["type"] not in valid_types:
                self.validation_warnings.append(
                    f"{param_path}: Type '{param_spec['type']}' may not be supported"
                )
        
        # Validate required flag
        if "required" in param_spec:
            if not isinstance(param_spec["required"], bool):
                self.validation_errors.append(
                    f"{param_path}: 'required' must be boolean, got {type(param_spec['required'])}"
                )
            
            # Check optional parameters have defaults
            if not param_spec["required"] and "default" not in param_spec:
                self.validation_errors.append(
                    f"{param_path}: Optional parameter missing 'default' value"
                )
        
        # Validate description
        if "description" in param_spec:
            if not isinstance(param_spec["description"], str) or not param_spec["description"]:
                self.validation_errors.append(f"{param_path}: Description must be non-empty string")
    
    def check_filepath_auto_injection(self) -> Dict[str, Any]:
        """
        Verify all tools have filepath parameter with auto-injection note
        
        Returns:
            Report of filepath parameter status across all tools
        """
        tool_names = list_available_tools()
        tools_with_filepath = []
        tools_without_filepath = []
        tools_with_proper_description = []
        tools_with_improper_description = []
        
        for tool_name in tool_names:
            schema = MCP_TOOL_SCHEMAS.get(tool_name)
            if not schema or "parameters" not in schema:
                continue
            
            parameters = schema["parameters"]
            
            if "filepath" in parameters:
                tools_with_filepath.append(tool_name)
                
                filepath_desc = parameters["filepath"].get("description", "")
                if "auto-inject" in filepath_desc.lower() or "do not provide" in filepath_desc.lower():
                    tools_with_proper_description.append(tool_name)
                else:
                    tools_with_improper_description.append(tool_name)
            else:
                tools_without_filepath.append(tool_name)
        
        report = {
            "total_tools": len(tool_names),
            "with_filepath": len(tools_with_filepath),
            "without_filepath": len(tools_without_filepath),
            "proper_auto_inject_note": len(tools_with_proper_description),
            "missing_auto_inject_note": len(tools_with_improper_description),
            "tools_without_filepath": tools_without_filepath,
            "tools_missing_note": tools_with_improper_description
        }
        
        if tools_without_filepath:
            logger.warning(
                f"Tools without filepath parameter: {', '.join(tools_without_filepath)}"
            )
        
        if tools_with_improper_description:
            logger.warning(
                f"Tools missing auto-injection note in filepath description: "
                f"{', '.join(tools_with_improper_description)}"
            )
        
        return report
    
    def generate_validation_report(self) -> str:
        """
        Generate a formatted validation report
        
        Returns:
            Formatted string report
        """
        validation_result = self.validate_all_schemas()
        filepath_result = self.check_filepath_auto_injection()
        
        lines = [
            "=" * 70,
            "MCP Tool Schema Validation Report",
            "=" * 70,
            "",
            f"Total Tools Registered: {validation_result['total_tools']}",
            f"Validation Status: {'PASSED' if validation_result['valid'] else 'FAILED'}",
            "",
            "Schema Validation:",
            f"  Errors: {validation_result['error_count']}",
            f"  Warnings: {validation_result['warning_count']}",
            ""
        ]
        
        if validation_result['errors']:
            lines.append("Errors:")
            for error in validation_result['errors']:
                lines.append(f"  - {error}")
            lines.append("")
        
        if validation_result['warnings']:
            lines.append("Warnings:")
            for warning in validation_result['warnings']:
                lines.append(f"  - {warning}")
            lines.append("")
        
        lines.extend([
            "Filepath Auto-Injection Check:",
            f"  Tools with filepath parameter: {filepath_result['with_filepath']}/{filepath_result['total_tools']}",
            f"  Tools with proper auto-inject note: {filepath_result['proper_auto_inject_note']}",
            f"  Tools missing auto-inject note: {filepath_result['missing_auto_inject_note']}",
            ""
        ])
        
        if filepath_result['tools_without_filepath']:
            lines.append("Tools without filepath parameter:")
            for tool in filepath_result['tools_without_filepath']:
                lines.append(f"  - {tool}")
            lines.append("")
        
        if filepath_result['tools_missing_note']:
            lines.append("Tools missing auto-injection note:")
            for tool in filepath_result['tools_missing_note']:
                lines.append(f"  - {tool}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# Global validator instance
schema_validator = SchemaValidator()


def validate_schemas_on_startup():
    """
    Validate schemas at application startup
    
    Should be called during application initialization to ensure
    all schemas are properly configured before use.
    """
    logger.info("Running MCP tool schema validation...")
    
    report = schema_validator.generate_validation_report()
    print(report)
    
    validation_result = schema_validator.validate_all_schemas()
    
    if not validation_result["valid"]:
        logger.error(
            f"Schema validation failed with {validation_result['error_count']} errors. "
            "Please fix schema definitions before proceeding."
        )
        # Note: In production, you might want to raise an exception here
        # to prevent application startup with invalid schemas
    
    return validation_result["valid"]
