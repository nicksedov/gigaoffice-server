"""Style Registry and Validation Logic for Spreadsheet Data"""

import hashlib
import json
from typing import Dict, List, Optional, Set, Tuple, Any
from loguru import logger
from app.models.api.spreadsheet_v2 import StyleDefinition

class StyleRegistry:
    """
    Centralized style registry for managing spreadsheet styles.
    
    This class implements the style reference architecture by:
    - Consolidating duplicate styles into unique definitions
    - Generating consistent style identifiers
    - Providing validation for style references
    - Supporting style transformation between formats
    """
    
    def __init__(self):
        self._styles: Dict[str, StyleDefinition] = {}
        self._style_hashes: Dict[str, str] = {}  # hash -> style_id mapping
        
    def add_style(self, style: StyleDefinition) -> str:
        """
        Add a style definition to the registry.
        
        Args:
            style: StyleDefinition object
            
        Returns:
            str: The style ID (may be existing if duplicate found)
        """
        # Calculate hash for duplicate detection
        style_hash = self._calculate_style_hash(style.dict(exclude={"id"}))
        
        # Check if we already have this style
        if style_hash in self._style_hashes:
            return self._style_hashes[style_hash]
        
        # Generate ID if not provided or if it conflicts
        if not style.id or style.id in self._styles:
            style.id = self._generate_style_id(style)
        
        # Store the style
        self._styles[style.id] = style
        self._style_hashes[style_hash] = style.id
        
        logger.debug(f"Added style to registry: {style.id}")
        return style.id
    
    def add_style_from_dict(self, style_dict: Dict[str, Any]) -> str:
        """
        Add a style from a dictionary (e.g., legacy format).
        
        Args:
            style_dict: Dictionary containing style properties
            
        Returns:
            str: The generated style ID
        """
        # Calculate hash first for duplicate detection
        style_hash = self._calculate_style_hash(style_dict)
        
        # Check if we already have this style
        if style_hash in self._style_hashes:
            return self._style_hashes[style_hash]
        
        # Generate ID and create StyleDefinition
        style_id = self._generate_style_id_from_dict(style_dict)
        style_dict["id"] = style_id
        
        try:
            style = StyleDefinition(**style_dict)
            self._styles[style_id] = style
            self._style_hashes[style_hash] = style_id
            
            logger.debug(f"Added style from dict to registry: {style_id}")
            return style_id
        except Exception as e:
            logger.error(f"Failed to create style from dict: {e}")
            # Fallback to basic style
            fallback_style = StyleDefinition(id=style_id)
            self._styles[style_id] = fallback_style
            return style_id
    
    def get_style(self, style_id: str) -> Optional[StyleDefinition]:
        """
        Get a style definition by ID.
        
        Args:
            style_id: The style identifier
            
        Returns:
            StyleDefinition or None if not found
        """
        return self._styles.get(style_id)
    
    def get_all_styles(self) -> List[StyleDefinition]:
        """
        Get all style definitions in the registry.
        
        Returns:
            List of all StyleDefinition objects
        """
        return list(self._styles.values())
    
    def validate_style_reference(self, style_id: str) -> bool:
        """
        Validate that a style reference exists in the registry.
        
        Args:
            style_id: The style identifier to validate
            
        Returns:
            bool: True if style exists, False otherwise
        """
        return style_id in self._styles
    
    def validate_all_references(self, style_references: Set[str]) -> Tuple[bool, List[str]]:
        """
        Validate multiple style references.
        
        Args:
            style_references: Set of style IDs to validate
            
        Returns:
            Tuple of (all_valid: bool, missing_styles: List[str])
        """
        missing_styles = []
        for style_id in style_references:
            if not self.validate_style_reference(style_id):
                missing_styles.append(style_id)
        
        return len(missing_styles) == 0, missing_styles
    
    def consolidate_duplicate_styles(self) -> int:
        """
        Consolidate duplicate styles in the registry.
        
        Returns:
            int: Number of duplicate styles removed
        """
        # This method could be used to clean up the registry
        # For now, we prevent duplicates during addition
        return 0
    
    def clear(self):
        """Clear all styles from the registry."""
        self._styles.clear()
        self._style_hashes.clear()
        logger.debug("Style registry cleared")
    
    def _calculate_style_hash(self, style_dict: Dict[str, Any]) -> str:
        """
        Calculate a hash for a style dictionary to detect duplicates.
        
        Args:
            style_dict: Style properties (excluding id)
            
        Returns:
            str: Hash of the style properties
        """
        # Remove None values and sort for consistent hashing
        clean_dict = {k: v for k, v in style_dict.items() if v is not None and k != "id"}
        sorted_json = json.dumps(clean_dict, sort_keys=True)
        return hashlib.md5(sorted_json.encode()).hexdigest()
    
    def _generate_style_id(self, style: StyleDefinition) -> str:
        """
        Generate a meaningful style ID based on style properties.
        
        Args:
            style: StyleDefinition object
            
        Returns:
            str: Generated style ID
        """
        return self._generate_style_id_from_dict(style.dict(exclude={"id"}))
    
    def _generate_style_id_from_dict(self, style_dict: Dict[str, Any]) -> str:
        """
        Generate a meaningful style ID from a style dictionary.
        
        Args:
            style_dict: Dictionary containing style properties
            
        Returns:
            str: Generated style ID
        """
        # Generate meaningful ID based on properties
        parts = []
        
        if style_dict.get("background_color"):
            parts.append(f"bg{style_dict['background_color'][1:]}")  # Remove #
        
        if style_dict.get("font_color"):
            parts.append(f"fc{style_dict['font_color'][1:]}")  # Remove #
        
        if style_dict.get("font_weight") == "bold":
            parts.append("bold")
        
        if style_dict.get("font_style") == "italic":
            parts.append("italic")
        
        if style_dict.get("font_size"):
            parts.append(f"fs{style_dict['font_size']}")
        
        if not parts:
            parts.append("default")
        
        base_id = "_".join(parts)
        
        # Ensure uniqueness
        counter = 1
        final_id = base_id
        while final_id in self._styles:
            final_id = f"{base_id}_{counter}"
            counter += 1
        
        return final_id


class StyleValidator:
    """
    Validator for spreadsheet data with style references.
    
    This class provides comprehensive validation for:
    - Style reference integrity
    - Style definition consistency
    - Data structure validation
    """
    
    def __init__(self, registry: StyleRegistry):
        self.registry = registry
    
    def validate_spreadsheet_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an entire spreadsheet data structure.
        
        Args:
            data: Spreadsheet data dictionary
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        # Validate that styles array exists and is populated
        if "styles" not in data or not isinstance(data["styles"], list):
            errors.append("Missing or invalid 'styles' array")
            return False, errors
        
        # Validate individual style definitions
        style_ids = set()
        for i, style in enumerate(data["styles"]):
            if not isinstance(style, dict):
                errors.append(f"Style at index {i} is not a dictionary")
                continue
            
            if "id" not in style:
                errors.append(f"Style at index {i} missing 'id' field")
                continue
            
            style_id = style["id"]
            if style_id in style_ids:
                errors.append(f"Duplicate style ID: {style_id}")
            else:
                style_ids.add(style_id)
            
            # Validate style definition
            try:
                StyleDefinition(**style)
            except Exception as e:
                errors.append(f"Invalid style definition for ID {style_id}: {str(e)}")
        
        # Collect all style references from data
        referenced_styles = set()
        
        # Check header style reference
        if (data.get("data", {}).get("header", {}).get("style")):
            referenced_styles.add(data["data"]["header"]["style"])
        
        # Check row style references
        for i, row in enumerate(data.get("data", {}).get("rows", [])):
            if row.get("style"):
                referenced_styles.add(row["style"])
        
        # Validate that all referenced styles exist
        for style_ref in referenced_styles:
            if style_ref not in style_ids:
                errors.append(f"Style reference '{style_ref}' not found in styles array")
        
        return len(errors) == 0, errors
    
    def validate_style_consistency(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate style consistency across the spreadsheet.
        
        Args:
            data: Spreadsheet data dictionary
            
        Returns:
            Tuple of (is_consistent: bool, warnings: List[str])
        """
        warnings = []
        
        # Check for unused styles
        if "styles" not in data:
            return True, warnings
        
        defined_styles = {style["id"] for style in data["styles"] if isinstance(style, dict) and "id" in style}
        referenced_styles = set()
        
        # Collect references
        if data.get("data", {}).get("header", {}).get("style"):
            referenced_styles.add(data["data"]["header"]["style"])
        
        for row in data.get("data", {}).get("rows", []):
            if row.get("style"):
                referenced_styles.add(row["style"])
        
        # Find unused styles
        unused_styles = defined_styles - referenced_styles
        if unused_styles:
            warnings.append(f"Unused style definitions: {', '.join(unused_styles)}")
        
        return True, warnings
    
    def validate_and_fix_references(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and attempt to fix invalid style references.
        
        Args:
            data: Spreadsheet data dictionary
            
        Returns:
            Tuple of (fixed_data: Dict, fix_messages: List[str])
        """
        fixes = []
        fixed_data = data.copy()
        
        if "styles" not in fixed_data:
            fixed_data["styles"] = []
            fixes.append("Added missing styles array")
        
        style_ids = {style["id"] for style in fixed_data["styles"] if isinstance(style, dict) and "id" in style}
        
        # Fix header style reference
        header = fixed_data.get("data", {}).get("header", {})
        if header.get("style") and header["style"] not in style_ids:
            header["style"] = None
            fixes.append(f"Removed invalid header style reference: {header['style']}")
        
        # Fix row style references
        for i, row in enumerate(fixed_data.get("data", {}).get("rows", [])):
            if row.get("style") and row["style"] not in style_ids:
                original_style = row["style"]
                row["style"] = None
                fixes.append(f"Removed invalid style reference in row {i}: {original_style}")
        
        return fixed_data, fixes


def create_style_registry_from_data(data: Dict[str, Any]) -> StyleRegistry:
    """
    Create and populate a style registry from spreadsheet data.
    
    Args:
        data: Spreadsheet data dictionary
        
    Returns:
        StyleRegistry: Populated registry
    """
    registry = StyleRegistry()
    
    if "styles" in data and isinstance(data["styles"], list):
        for style_dict in data["styles"]:
            if isinstance(style_dict, dict) and "id" in style_dict:
                try:
                    style = StyleDefinition(**style_dict)
                    registry.add_style(style)
                except Exception as e:
                    logger.warning(f"Failed to add style to registry: {e}")
    
    return registry