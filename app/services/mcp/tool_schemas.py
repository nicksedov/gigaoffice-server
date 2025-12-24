"""
MCP Tool Schema Registry
Centralized repository of MCP Excel tool parameter schemas for LangChain integration.

Based on: https://raw.githubusercontent.com/haris-musa/excel-mcp-server/refs/heads/main/TOOLS.md
Version: 2024-12-24
"""

from typing import Dict, Any, Type, Optional, List
from pydantic import BaseModel, Field, create_model
from loguru import logger


# ============================================================================
# MCP Tool Schema Definitions
# ============================================================================

MCP_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # Workbook Operations
    "create_workbook": {
        "description": "Create a new Excel workbook at the specified filepath",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path where to create the workbook (auto-injected, do not provide)"
            }
        }
    },
    
    "create_worksheet": {
        "description": "Create a new worksheet in an existing workbook",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Name for the new worksheet"
            }
        }
    },
    
    "get_workbook_metadata": {
        "description": "Get metadata about workbook including sheets and ranges",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "include_ranges": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Whether to include range information"
            }
        }
    },
    
    # Data Operations
    "write_data_to_excel": {
        "description": "Write data to Excel worksheet",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "data": {
                "type": "List[List]",
                "required": True,
                "description": "List of lists containing data to write (rows of data)"
            },
            "start_cell": {
                "type": "str",
                "required": False,
                "default": "A1",
                "description": "Starting cell reference (default: A1)"
            }
        }
    },
    
    "read_data_from_excel": {
        "description": "Read data from Excel worksheet",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Source worksheet name"
            },
            "start_cell": {
                "type": "str",
                "required": False,
                "default": "A1",
                "description": "Starting cell reference (default: A1)"
            },
            "end_cell": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Optional ending cell reference"
            },
            "preview_only": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Whether to return only a preview"
            }
        }
    },
    
    # Formatting Operations
    "format_range": {
        "description": "Apply formatting to a range of cells",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_cell": {
                "type": "str",
                "required": True,
                "description": "Starting cell of range"
            },
            "end_cell": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Optional ending cell of range"
            },
            "bold": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Apply bold formatting"
            },
            "italic": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Apply italic formatting"
            },
            "underline": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Apply underline formatting"
            },
            "font_size": {
                "type": "int",
                "required": False,
                "default": None,
                "description": "Font size in points"
            },
            "font_color": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Font color in hex format"
            },
            "bg_color": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Background color in hex format"
            },
            "border_style": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Border style"
            },
            "border_color": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Border color in hex format"
            },
            "number_format": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Number format string"
            },
            "alignment": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Text alignment (left, center, right)"
            },
            "wrap_text": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Enable text wrapping"
            },
            "merge_cells": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Merge cells in range"
            }
        }
    },
    
    # Formula Operations
    "apply_formula": {
        "description": "Apply Excel formula to a cell",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "cell": {
                "type": "str",
                "required": True,
                "description": "Target cell reference (e.g., 'A1')"
            },
            "formula": {
                "type": "str",
                "required": True,
                "description": "Excel formula to apply (e.g., '=SUM(A1:A10)')"
            }
        }
    },
    
    "validate_formula_syntax": {
        "description": "Validate Excel formula syntax without applying it",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "cell": {
                "type": "str",
                "required": True,
                "description": "Target cell reference"
            },
            "formula": {
                "type": "str",
                "required": True,
                "description": "Excel formula to validate"
            }
        }
    },
    
    # Chart Operations
    "create_chart": {
        "description": "Create a chart in the worksheet",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "data_range": {
                "type": "str",
                "required": True,
                "description": "Range containing chart data (e.g., 'A1:B10')"
            },
            "chart_type": {
                "type": "str",
                "required": True,
                "description": "Type of chart: line, bar, pie, scatter, or area"
            },
            "target_cell": {
                "type": "str",
                "required": True,
                "description": "Cell where to place chart (e.g., 'D1')"
            },
            "title": {
                "type": "str",
                "required": False,
                "default": "",
                "description": "Optional chart title"
            },
            "x_axis": {
                "type": "str",
                "required": False,
                "default": "",
                "description": "Optional X-axis label"
            },
            "y_axis": {
                "type": "str",
                "required": False,
                "default": "",
                "description": "Optional Y-axis label"
            }
        }
    },
    
    # Pivot Table Operations
    "create_pivot_table": {
        "description": "Create pivot table in worksheet",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "data_range": {
                "type": "str",
                "required": True,
                "description": "Range containing source data"
            },
            "rows": {
                "type": "List[str]",
                "required": True,
                "description": "List of field names for row labels"
            },
            "values": {
                "type": "List[str]",
                "required": True,
                "description": "List of field names for values"
            },
            "columns": {
                "type": "List[str]",
                "required": False,
                "default": None,
                "description": "Optional list of field names for column labels"
            },
            "agg_func": {
                "type": "str",
                "required": False,
                "default": "mean",
                "description": "Aggregation function: sum, count, average, max, min, mean"
            }
        }
    },
    
    "create_table": {
        "description": "Create a native Excel table from a specified range of data",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "data_range": {
                "type": "str",
                "required": True,
                "description": "The cell range for the table (e.g., 'A1:D5')"
            },
            "table_name": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Optional unique name for the table"
            },
            "table_style": {
                "type": "str",
                "required": False,
                "default": "TableStyleMedium9",
                "description": "Optional visual style for the table"
            }
        }
    },
    
    # Cell Operations
    "merge_cells": {
        "description": "Merge a range of cells",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_cell": {
                "type": "str",
                "required": True,
                "description": "Starting cell of range"
            },
            "end_cell": {
                "type": "str",
                "required": True,
                "description": "Ending cell of range"
            }
        }
    },
    
    "unmerge_cells": {
        "description": "Unmerge a previously merged range of cells",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_cell": {
                "type": "str",
                "required": True,
                "description": "Starting cell of range"
            },
            "end_cell": {
                "type": "str",
                "required": True,
                "description": "Ending cell of range"
            }
        }
    },
    
    "get_merged_cells": {
        "description": "Get merged cells in a worksheet",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            }
        }
    },
    
    # Worksheet Operations
    "copy_worksheet": {
        "description": "Copy worksheet within workbook",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "source_sheet": {
                "type": "str",
                "required": True,
                "description": "Name of sheet to copy"
            },
            "target_sheet": {
                "type": "str",
                "required": True,
                "description": "Name for new sheet"
            }
        }
    },
    
    "delete_worksheet": {
        "description": "Delete worksheet from workbook",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Name of sheet to delete"
            }
        }
    },
    
    "rename_worksheet": {
        "description": "Rename worksheet in workbook",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "old_name": {
                "type": "str",
                "required": True,
                "description": "Current sheet name"
            },
            "new_name": {
                "type": "str",
                "required": True,
                "description": "New sheet name"
            }
        }
    },
    
    # Range Operations
    "copy_range": {
        "description": "Copy a range of cells to another location",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Source worksheet name"
            },
            "source_start": {
                "type": "str",
                "required": True,
                "description": "Starting cell of source range"
            },
            "source_end": {
                "type": "str",
                "required": True,
                "description": "Ending cell of source range"
            },
            "target_start": {
                "type": "str",
                "required": True,
                "description": "Starting cell for paste"
            },
            "target_sheet": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Optional target worksheet name (defaults to source sheet)"
            }
        }
    },
    
    "delete_range": {
        "description": "Delete a range of cells and shift remaining cells",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_cell": {
                "type": "str",
                "required": True,
                "description": "Starting cell of range"
            },
            "end_cell": {
                "type": "str",
                "required": True,
                "description": "Ending cell of range"
            },
            "shift_direction": {
                "type": "str",
                "required": False,
                "default": "up",
                "description": "Direction to shift cells: 'up' or 'left'"
            }
        }
    },
    
    "validate_excel_range": {
        "description": "Validate if a range exists and is properly formatted",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_cell": {
                "type": "str",
                "required": True,
                "description": "Starting cell of range"
            },
            "end_cell": {
                "type": "str",
                "required": False,
                "default": None,
                "description": "Optional ending cell of range"
            }
        }
    },
    
    # Row and Column Operations
    "insert_rows": {
        "description": "Insert one or more rows starting at the specified row",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_row": {
                "type": "int",
                "required": True,
                "description": "Row number where to start inserting (1-based)"
            },
            "count": {
                "type": "int",
                "required": False,
                "default": 1,
                "description": "Number of rows to insert (default: 1)"
            }
        }
    },
    
    "insert_columns": {
        "description": "Insert one or more columns starting at the specified column",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_col": {
                "type": "int",
                "required": True,
                "description": "Column number where to start inserting (1-based)"
            },
            "count": {
                "type": "int",
                "required": False,
                "default": 1,
                "description": "Number of columns to insert (default: 1)"
            }
        }
    },
    
    "delete_sheet_rows": {
        "description": "Delete one or more rows starting at the specified row",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_row": {
                "type": "int",
                "required": True,
                "description": "Row number where to start deleting (1-based)"
            },
            "count": {
                "type": "int",
                "required": False,
                "default": 1,
                "description": "Number of rows to delete (default: 1)"
            }
        }
    },
    
    "delete_sheet_columns": {
        "description": "Delete one or more columns starting at the specified column",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            },
            "start_col": {
                "type": "int",
                "required": True,
                "description": "Column number where to start deleting (1-based)"
            },
            "count": {
                "type": "int",
                "required": False,
                "default": 1,
                "description": "Number of columns to delete (default: 1)"
            }
        }
    },
    
    # Data Validation
    "get_data_validation_info": {
        "description": "Get data validation rules and metadata for a worksheet",
        "parameters": {
            "filepath": {
                "type": "str",
                "required": True,
                "description": "Path to Excel file (auto-injected, do not provide)"
            },
            "sheet_name": {
                "type": "str",
                "required": True,
                "description": "Target worksheet name"
            }
        }
    }
}


# ============================================================================
# Type Mapping for Pydantic Schema Generation
# ============================================================================

TYPE_MAPPING = {
    "str": str,
    "int": int,
    "bool": bool,
    "float": float,
    "List[str]": List[str],
    "List[int]": List[int],
    "List[List]": List[List[Any]],
    "Dict": Dict[str, Any],
}


# ============================================================================
# Schema Utility Functions
# ============================================================================

def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve schema for a specific tool
    
    Args:
        tool_name: Name of the MCP tool
        
    Returns:
        Tool schema dictionary or None if not found
    """
    schema = MCP_TOOL_SCHEMAS.get(tool_name)
    if not schema:
        logger.warning(f"No schema found for tool: {tool_name}")
    return schema


def create_pydantic_schema(tool_name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Generate Pydantic BaseModel from tool schema
    
    Args:
        tool_name: Name of the tool
        schema: Schema dictionary containing parameters
        
    Returns:
        Pydantic BaseModel class for parameter validation
    """
    field_definitions = {}
    
    for param_name, param_spec in schema["parameters"].items():
        # Get Python type from string representation
        param_type_str = param_spec["type"]
        param_type = TYPE_MAPPING.get(param_type_str, str)
        
        # Build Field with description and default
        if param_spec["required"]:
            # Required field
            field_definitions[param_name] = (
                param_type,
                Field(..., description=param_spec["description"])
            )
        else:
            # Optional field with default
            default_value = param_spec.get("default")
            field_definitions[param_name] = (
                Optional[param_type],
                Field(default=default_value, description=param_spec["description"])
            )
    
    # Create dynamic Pydantic model
    model_name = f"{tool_name.title().replace('_', '')}Schema"
    pydantic_model = create_model(model_name, **field_definitions)
    
    logger.debug(f"Generated Pydantic schema for tool: {tool_name}")
    return pydantic_model


def generate_enhanced_docstring(tool_name: str, schema: Dict[str, Any]) -> str:
    """
    Generate comprehensive docstring with parameter details
    
    Args:
        tool_name: Name of the tool
        schema: Schema dictionary
        
    Returns:
        Formatted docstring with full parameter documentation
    """
    lines = [schema["description"], ""]
    
    if schema["parameters"]:
        lines.append("Parameters:")
        for param_name, param_spec in schema["parameters"].items():
            param_type = param_spec["type"]
            required_status = "required" if param_spec["required"] else "optional"
            
            # Build parameter line
            param_line = f"  {param_name} ({param_type}, {required_status})"
            
            # Add default value if present
            if not param_spec["required"] and "default" in param_spec:
                default_val = param_spec["default"]
                if default_val is None:
                    param_line += ", default=None"
                elif isinstance(default_val, str):
                    param_line += f", default='{default_val}'"
                else:
                    param_line += f", default={default_val}"
            
            param_line += f": {param_spec['description']}"
            lines.append(param_line)
        
        lines.append("")
    
    lines.append("Returns: Result from MCP Excel server")
    lines.append("")
    lines.append("Note: The filepath parameter is automatically resolved and injected.")
    
    return "\n".join(lines)


def list_available_tools() -> List[str]:
    """
    Get list of all registered tool names
    
    Returns:
        List of tool names
    """
    return list(MCP_TOOL_SCHEMAS.keys())


def validate_schema_completeness() -> Dict[str, Any]:
    """
    Validate that all schemas are properly defined
    
    Returns:
        Validation report with any issues found
    """
    issues = []
    
    for tool_name, schema in MCP_TOOL_SCHEMAS.items():
        # Check required fields
        if "description" not in schema:
            issues.append(f"{tool_name}: Missing description")
        
        if "parameters" not in schema:
            issues.append(f"{tool_name}: Missing parameters")
            continue
        
        # Check each parameter
        for param_name, param_spec in schema["parameters"].items():
            if "type" not in param_spec:
                issues.append(f"{tool_name}.{param_name}: Missing type")
            
            if "required" not in param_spec:
                issues.append(f"{tool_name}.{param_name}: Missing required flag")
            
            if "description" not in param_spec:
                issues.append(f"{tool_name}.{param_name}: Missing description")
            
            # Check optional parameters have defaults
            if not param_spec.get("required", True) and "default" not in param_spec:
                issues.append(f"{tool_name}.{param_name}: Optional parameter missing default")
    
    return {
        "valid": len(issues) == 0,
        "total_tools": len(MCP_TOOL_SCHEMAS),
        "issues": issues
    }


# ============================================================================
# Module Initialization
# ============================================================================

def initialize_schemas():
    """
    Initialize and validate tool schemas at module load
    """
    validation_report = validate_schema_completeness()
    
    if validation_report["valid"]:
        logger.info(
            f"MCP tool schemas loaded successfully: {validation_report['total_tools']} tools registered"
        )
    else:
        logger.warning(
            f"MCP tool schemas loaded with issues: {len(validation_report['issues'])} problems found"
        )
        for issue in validation_report["issues"]:
            logger.warning(f"  - {issue}")


# Auto-initialize on import
initialize_schemas()
