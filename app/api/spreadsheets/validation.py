"""
Spreadsheet Data Validation
Validation logic for spreadsheet data and style references
"""

from typing import Dict, Any, Tuple, List
from loguru import logger

from app.services.spreadsheet.style_registry import StyleValidator, create_style_registry_from_data


def validate_spreadsheet_structure(spreadsheet_data_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate spreadsheet data structure and style references
    
    Args:
        spreadsheet_data_dict: Spreadsheet data dictionary to validate
        
    Returns:
        Tuple of (is_valid, validation_errors)
        
    Raises:
        Exception: If validation process fails unexpectedly
    """
    try:
        # Create style registry and validate
        registry = create_style_registry_from_data(spreadsheet_data_dict)
        validator = StyleValidator(registry)
        is_valid, validation_errors = validator.validate_spreadsheet_data(spreadsheet_data_dict)
        
        return is_valid, validation_errors
        
    except Exception as e:
        logger.error(f"Error during spreadsheet validation: {e}")
        raise


def validate_with_consistency_check(data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform comprehensive validation including style consistency checks
    
    Args:
        data_dict: Spreadsheet data dictionary to validate
        
    Returns:
        Dictionary with validation results including:
        - is_valid: Whether data structure is valid
        - is_consistent: Whether style references are consistent
        - validation_errors: List of validation errors
        - consistency_warnings: List of consistency warnings
        - style_count: Number of styles defined
        
    Raises:
        Exception: If validation process fails unexpectedly
    """
    try:
        # Create style registry and validator
        registry = create_style_registry_from_data(data_dict)
        validator = StyleValidator(registry)
        
        # Perform comprehensive validation
        is_valid, validation_errors = validator.validate_spreadsheet_data(data_dict)
        is_consistent, consistency_warnings = validator.validate_style_consistency(data_dict)
        
        return {
            "success": True,
            "is_valid": is_valid,
            "is_consistent": is_consistent,
            "validation_errors": validation_errors,
            "consistency_warnings": consistency_warnings,
            "style_count": len(data_dict.get("styles", [])),
            "message": "Validation completed"
        }
        
    except Exception as e:
        logger.error(f"Error during comprehensive validation: {e}")
        raise
