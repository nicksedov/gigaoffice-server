"""Data Transformation Utilities for Legacy to New Structure Conversion"""

import json
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from app.models.api.spreadsheet import SpreadsheetData, CellStyle
from app.models.api.spreadsheet_v2 import SpreadsheetDataV2, StyleDefinition
from app.services.spreadsheet.style_registry import StyleRegistry


class LegacyToNewTransformer:
    """
    Transforms legacy spreadsheet data (with inline styles) to new format (with style references).
    
    This class implements the core transformation logic for migrating from
    the old inline style format to the new centralized style reference architecture.
    """
    
    def __init__(self):
        self.registry = StyleRegistry()
    
    def transform(self, legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform legacy format to new format with style references.
        
        Args:
            legacy_data: Dictionary containing legacy spreadsheet data
            
        Returns:
            Dictionary containing new format spreadsheet data
        """
        logger.info("Starting legacy to new format transformation")
        
        # Create a deep copy to avoid modifying the original
        new_data = json.loads(json.dumps(legacy_data))
        
        # Initialize styles registry
        self.registry.clear()
        
        # Transform header styles
        self._transform_header_styles(new_data)
        
        # Transform row styles
        self._transform_row_styles(new_data)
        
        # Add styles array to the data structure
        new_data["styles"] = [style.dict() for style in self.registry.get_all_styles()]
        
        # Update metadata version
        if "metadata" not in new_data:
            new_data["metadata"] = {}
        new_data["metadata"]["version"] = "2.0"
        
        logger.info(f"Transformation completed. Generated {len(new_data['styles'])} unique styles")
        return new_data
    
    def _transform_header_styles(self, data: Dict[str, Any]):
        """Transform header inline styles to style references."""
        if not data.get("data", {}).get("header"):
            return
        
        header = data["data"]["header"]
        if "style" in header and isinstance(header["style"], dict):
            # Convert inline style to style reference
            style_id = self.registry.add_style_from_dict(header["style"])
            header["style"] = style_id
            logger.debug(f"Transformed header style to reference: {style_id}")
    
    def _transform_row_styles(self, data: Dict[str, Any]):
        """Transform row inline styles to style references."""
        if not data.get("data", {}).get("rows"):
            return
        
        for i, row in enumerate(data["data"]["rows"]):
            if "style" in row and isinstance(row["style"], dict):
                # Convert inline style to style reference
                style_id = self.registry.add_style_from_dict(row["style"])
                row["style"] = style_id
                logger.debug(f"Transformed row {i} style to reference: {style_id}")


class NewToLegacyTransformer:
    """
    Transforms new spreadsheet data (with style references) to legacy format (with inline styles).
    
    This class provides backward compatibility by converting the new style reference
    format back to the legacy inline style format when needed.
    """
    
    def transform(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform new format to legacy format with inline styles.
        
        Args:
            new_data: Dictionary containing new format spreadsheet data
            
        Returns:
            Dictionary containing legacy format spreadsheet data
        """
        logger.info("Starting new to legacy format transformation")
        
        # Create a deep copy to avoid modifying the original
        legacy_data = json.loads(json.dumps(new_data))
        
        # Create style lookup dictionary
        style_lookup = {}
        if "styles" in legacy_data:
            style_lookup = {style["id"]: style for style in legacy_data["styles"]}
        
        # Transform header style references
        self._transform_header_references(legacy_data, style_lookup)
        
        # Transform row style references
        self._transform_row_references(legacy_data, style_lookup)
        
        # Remove styles array and update version
        legacy_data.pop("styles", None)
        if "metadata" in legacy_data:
            legacy_data["metadata"]["version"] = "1.0"
        
        logger.info("New to legacy transformation completed")
        return legacy_data
    
    def _transform_header_references(self, data: Dict[str, Any], style_lookup: Dict[str, Dict]):
        """Transform header style references to inline styles."""
        if not data.get("data", {}).get("header"):
            return
        
        header = data["data"]["header"]
        if "style" in header and isinstance(header["style"], str):
            style_id = header["style"]
            if style_id in style_lookup:
                # Convert style reference to inline style
                style_dict = {k: v for k, v in style_lookup[style_id].items() 
                             if k != "id" and v is not None}
                header["style"] = style_dict
                logger.debug(f"Transformed header style reference {style_id} to inline style")
            else:
                # Remove invalid reference
                header.pop("style", None)
                logger.warning(f"Removed invalid header style reference: {style_id}")
    
    def _transform_row_references(self, data: Dict[str, Any], style_lookup: Dict[str, Dict]):
        """Transform row style references to inline styles."""
        if not data.get("data", {}).get("rows"):
            return
        
        for i, row in enumerate(data["data"]["rows"]):
            if "style" in row and isinstance(row["style"], str):
                style_id = row["style"]
                if style_id in style_lookup:
                    # Convert style reference to inline style
                    style_dict = {k: v for k, v in style_lookup[style_id].items() 
                                 if k != "id" and v is not None}
                    row["style"] = style_dict
                    logger.debug(f"Transformed row {i} style reference {style_id} to inline style")
                else:
                    # Remove invalid reference
                    row.pop("style", None)
                    logger.warning(f"Removed invalid style reference in row {i}: {style_id}")


class DataTransformationService:
    """
    High-level service for managing data transformations between formats.
    
    This service provides a unified interface for all transformation operations
    and includes validation and error handling.
    """
    
    def __init__(self):
        self.legacy_to_new = LegacyToNewTransformer()
        self.new_to_legacy = NewToLegacyTransformer()
    
    def transform_to_new_format(self, legacy_data: Dict[str, Any], 
                               validate: bool = True) -> Tuple[Dict[str, Any], List[str]]:
        """
        Transform legacy data to new format with validation.
        
        Args:
            legacy_data: Legacy format data
            validate: Whether to validate the result
            
        Returns:
            Tuple of (transformed_data, validation_errors)
        """
        try:
            # Perform transformation
            new_data = self.legacy_to_new.transform(legacy_data)
            
            errors = []
            if validate:
                # Validate the result
                from app.services.spreadsheet.style_registry import StyleValidator, create_style_registry_from_data
                registry = create_style_registry_from_data(new_data)
                validator = StyleValidator(registry)
                is_valid, validation_errors = validator.validate_spreadsheet_data(new_data)
                
                if not is_valid:
                    errors.extend(validation_errors)
                    logger.warning(f"Transformation validation failed: {validation_errors}")
            
            return new_data, errors
            
        except Exception as e:
            logger.error(f"Failed to transform to new format: {e}")
            return {}, [f"Transformation failed: {str(e)}"]
    
    def transform_to_legacy_format(self, new_data: Dict[str, Any],
                                  validate: bool = True) -> Tuple[Dict[str, Any], List[str]]:
        """
        Transform new data to legacy format with validation.
        
        Args:
            new_data: New format data
            validate: Whether to validate the input
            
        Returns:
            Tuple of (transformed_data, validation_errors)
        """
        try:
            errors = []
            
            if validate:
                # Validate the input
                from app.services.spreadsheet.style_registry import StyleValidator, create_style_registry_from_data
                registry = create_style_registry_from_data(new_data)
                validator = StyleValidator(registry)
                is_valid, validation_errors = validator.validate_spreadsheet_data(new_data)
                
                if not is_valid:
                    errors.extend(validation_errors)
                    logger.warning(f"Input validation failed: {validation_errors}")
            
            # Perform transformation
            legacy_data = self.new_to_legacy.transform(new_data)
            
            return legacy_data, errors
            
        except Exception as e:
            logger.error(f"Failed to transform to legacy format: {e}")
            return {}, [f"Transformation failed: {str(e)}"]
    
    def detect_format_version(self, data: Dict[str, Any]) -> str:
        """
        Detect the format version of spreadsheet data.
        
        Args:
            data: Spreadsheet data dictionary
            
        Returns:
            str: Format version ("1.0", "2.0", or "unknown")
        """
        # Check metadata version first
        if data.get("metadata", {}).get("version"):
            return data["metadata"]["version"]
        
        # Check for styles array (indicates v2.0)
        if "styles" in data and isinstance(data["styles"], list):
            return "2.0"
        
        # Check for inline styles (indicates v1.0)
        if data.get("data", {}).get("header", {}).get("style") and \
           isinstance(data["data"]["header"]["style"], dict):
            return "1.0"
        
        if data.get("data", {}).get("rows"):
            for row in data["data"]["rows"]:
                if row.get("style") and isinstance(row["style"], dict):
                    return "1.0"
        
        return "unknown"
    
    def auto_transform(self, data: Dict[str, Any], target_version: str = "2.0") -> Tuple[Dict[str, Any], List[str]]:
        """
        Automatically transform data to the target version.
        
        Args:
            data: Input spreadsheet data
            target_version: Target format version ("1.0" or "2.0")
            
        Returns:
            Tuple of (transformed_data, messages)
        """
        current_version = self.detect_format_version(data)
        messages = [f"Detected format version: {current_version}"]
        
        if current_version == target_version:
            messages.append(f"Data already in target format {target_version}")
            return data, messages
        
        if target_version == "2.0" and current_version == "1.0":
            transformed_data, errors = self.transform_to_new_format(data)
            if errors:
                messages.extend([f"Transformation error: {err}" for err in errors])
            else:
                messages.append("Successfully transformed to new format")
            return transformed_data, messages
        
        elif target_version == "1.0" and current_version == "2.0":
            transformed_data, errors = self.transform_to_legacy_format(data)
            if errors:
                messages.extend([f"Transformation error: {err}" for err in errors])
            else:
                messages.append("Successfully transformed to legacy format")
            return transformed_data, messages
        
        else:
            messages.append(f"Cannot transform from {current_version} to {target_version}")
            return data, messages


# Global service instance
transformation_service = DataTransformationService()


def transform_legacy_to_new(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for transforming legacy data to new format.
    
    Args:
        data: Legacy format spreadsheet data
        
    Returns:
        New format spreadsheet data
    """
    transformed_data, _ = transformation_service.transform_to_new_format(data, validate=False)
    return transformed_data


def transform_new_to_legacy(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for transforming new data to legacy format.
    
    Args:
        data: New format spreadsheet data
        
    Returns:
        Legacy format spreadsheet data
    """
    transformed_data, _ = transformation_service.transform_to_legacy_format(data, validate=False)
    return transformed_data


def detect_and_transform(data: Dict[str, Any], target_version: str = "2.0") -> Dict[str, Any]:
    """
    Convenience function for auto-detecting and transforming data.
    
    Args:
        data: Input spreadsheet data
        target_version: Target format version
        
    Returns:
        Transformed spreadsheet data
    """
    transformed_data, _ = transformation_service.auto_transform(data, target_version)
    return transformed_data