"""
Spreadsheet Data Optimizer
Handles JSON optimization operations for LLM input data
"""

import json
import uuid
from typing import Dict, Any, Optional, Tuple, List
from loguru import logger
from sqlalchemy.orm import Session

from app.models.api.prompt import RequiredTableInfo
from app.models.orm.llm_input_optimization import LLMInputOptimization
from app.utils.json_encoder import DateTimeEncoder


class SpreadsheetDataOptimizer:
    """
    Optimizes spreadsheet data for LLM consumption by filtering unnecessary components.
    
    This class provides data filtering and optimization logic, enabling tracking
    of optimization operations.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the data optimizer.
        
        Args:
            db_session: SQLAlchemy database session for storing optimization records
        """
        self.db_session = db_session
    
    def _serialize_for_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert datetime objects in data to JSON-safe ISO format strings.
        
        This method performs a serialization round-trip using DateTimeEncoder
        to ensure all datetime objects are converted to ISO format strings,
        making the data safe for SQLAlchemy JSON column serialization.
        
        Args:
            data: Dictionary that may contain datetime objects
            
        Returns:
            Dictionary with all datetime objects converted to ISO format strings
        """
        # Serialize with custom encoder that handles datetime
        json_str = json.dumps(data, ensure_ascii=False, cls=DateTimeEncoder)
        # Deserialize back to dictionary - datetime objects are now strings
        return json.loads(json_str)
    
    def optimize_data(
        self,
        spreadsheet_data: Dict[str, Any],
        required_table_info: Optional[RequiredTableInfo] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Optimize spreadsheet data and store optimization record in database.
        
        This is the main entry point that:
        1. Filters data based on requirements
        2. Calculates size metrics
        3. Generates optimization metadata
        4. Stores the optimization record in database
        5. Returns optimized data and optimization ID
        
        Args:
            spreadsheet_data: Full spreadsheet data dictionary
            required_table_info: Optional specification of required table components
            
        Returns:
            Tuple of (optimized_data, optimization_id)
        """
        try:
            # Calculate original data size
            original_json = json.dumps(spreadsheet_data, ensure_ascii=False, cls=DateTimeEncoder)
            original_size = len(original_json.encode('utf-8'))
            
            # Apply filtering
            optimized_data = self.filter_spreadsheet_data_by_requirements(
                spreadsheet_data, required_table_info
            )
            
            # Calculate optimized data size
            optimized_json = json.dumps(optimized_data, ensure_ascii=False, cls=DateTimeEncoder)
            optimized_size = len(optimized_json.encode('utf-8'))
            
            # Generate optimization metadata
            optimizations_applied = self._generate_optimization_metadata(
                spreadsheet_data, optimized_data, required_table_info
            )
            
            # Sanitize data dictionaries to ensure JSON compatibility
            # Convert any datetime objects to ISO format strings
            sanitized_original_data = self._serialize_for_json(spreadsheet_data)
            sanitized_optimizations = self._serialize_for_json(optimizations_applied)
            sanitized_optimized_data = self._serialize_for_json(optimized_data)
            
            # Create optimization record
            optimization_id = str(uuid.uuid4())
            optimization_record = LLMInputOptimization(
                id=optimization_id,
                original_data=sanitized_original_data,
                optimizations_applied=sanitized_optimizations,
                optimized_data=sanitized_optimized_data,
                original_size_bytes=original_size,
                optimized_size_bytes=optimized_size
            )
            
            # Store in database
            self.db_session.add(optimization_record)
            self.db_session.commit()
            
            # Refresh to get database-generated reduction_percentage value
            self.db_session.refresh(optimization_record)
            
            logger.info(
                f"Data optimization completed: {optimization_id}, "
                f"size reduction: {optimization_record.reduction_percentage:.2f}% "
                f"({original_size} -> {optimized_size} bytes)"
            )
            
            return optimized_data, optimization_id
            
        except Exception as e:
            logger.error(f"Error optimizing spreadsheet data: {e}")
            self.db_session.rollback()
            raise
    
    def filter_spreadsheet_data_by_requirements(
        self,
        spreadsheet_data: Dict[str, Any],
        required_table_info: Optional[RequiredTableInfo]
    ) -> Dict[str, Any]:
        """
        Filter spreadsheet data based on RequiredTableInfo specification.
        
        This method optimizes the data sent to GigaChat by including only
        the components specified in required_table_info. If required_table_info
        is None, returns the full data unchanged (backward compatibility).
        
        Args:
            spreadsheet_data: Full spreadsheet data dictionary
            required_table_info: Specification of required table components (optional)
            
        Returns:
            Filtered spreadsheet data with only required components
        """
        # If no requirements specified, return full data (backward compatibility)
        if required_table_info is None:
            return spreadsheet_data
        
        # Start with base structure (always included)
        filtered_data = {
            "metadata": spreadsheet_data.get("metadata", {}),
            "worksheet": spreadsheet_data.get("worksheet", {})
        }
        
        # Get original data section
        original_data = spreadsheet_data.get("data", {})
        filtered_data_section: Dict[str, Any] = {}
        
        # Process header if requested
        if required_table_info.needs_column_headers or required_table_info.needs_header_styles:
            original_header = original_data.get("header")
            if original_header:
                filtered_header: Dict[str, Any] = {}
                
                # Include header values if requested
                if required_table_info.needs_column_headers:
                    filtered_header["values"] = original_header.get("values", [])
                    if "range" in original_header:
                        filtered_header["range"] = original_header["range"]
                
                # Include header style if requested
                if required_table_info.needs_header_styles:
                    if "style" in original_header:
                        filtered_header["style"] = original_header["style"]
                
                if filtered_header:
                    filtered_data_section["header"] = filtered_header
        
        # Process rows if requested
        if required_table_info.needs_cell_values or required_table_info.needs_cell_styles:
            original_rows = original_data.get("rows", [])
            filtered_rows = []
            
            for row in original_rows:
                filtered_row: Dict[str, Any] = {}
                
                # Include row values if requested
                if required_table_info.needs_cell_values and "values" in row:
                    filtered_row["values"] = row["values"]
                
                # Include row style if requested
                if required_table_info.needs_cell_styles and "style" in row:
                    filtered_row["style"] = row["style"]
                
                # Include range if present
                if "range" in row:
                    filtered_row["range"] = row["range"]
                
                # Only add row if it has content
                if filtered_row and ("values" in filtered_row or "style" in filtered_row):
                    filtered_rows.append(filtered_row)
            
            if filtered_rows:
                filtered_data_section["rows"] = filtered_rows
        
        # Add data section if it has content
        if filtered_data_section:
            filtered_data["data"] = filtered_data_section
        
        # Include column metadata if requested
        if required_table_info.needs_column_metadata:
            if "columns" in spreadsheet_data:
                filtered_data["columns"] = spreadsheet_data["columns"]
        
        # Include styles if any style-related data was requested
        if (required_table_info.needs_header_styles or required_table_info.needs_cell_styles):
            if "styles" in spreadsheet_data:
                # Collect referenced style IDs
                referenced_styles = set()
                
                # Check header style
                if "data" in filtered_data and "header" in filtered_data["data"]:
                    header_style = filtered_data["data"]["header"].get("style")
                    if header_style:
                        referenced_styles.add(header_style)
                
                # Check row styles
                if "data" in filtered_data and "rows" in filtered_data["data"]:
                    for row in filtered_data["data"]["rows"]:
                        row_style = row.get("style")
                        if row_style:
                            referenced_styles.add(row_style)
                
                # Filter styles to only include referenced ones
                original_styles = spreadsheet_data["styles"]
                filtered_styles = [
                    style for style in original_styles 
                    if style.get("id") in referenced_styles
                ]
                
                if filtered_styles:
                    filtered_data["styles"] = filtered_styles
        
        return filtered_data
    
    def _generate_optimization_metadata(
        self,
        original_data: Dict[str, Any],
        optimized_data: Dict[str, Any],
        required_table_info: Optional[RequiredTableInfo]
    ) -> List[Dict[str, Any]]:
        """
        Generate metadata describing what optimizations were applied.
        
        Args:
            original_data: Original spreadsheet data
            optimized_data: Data after optimization
            required_table_info: Requirements that were applied
            
        Returns:
            List of optimization operation descriptions
        """
        optimizations = []
        
        # If no requirements, no optimizations were applied
        if required_table_info is None:
            return optimizations
        
        # Record the filter_by_requirements optimization
        filter_optimization = {
            "type": "filter_by_requirements",
            "details": {
                "needs_column_headers": required_table_info.needs_column_headers,
                "needs_header_styles": required_table_info.needs_header_styles,
                "needs_cell_values": required_table_info.needs_cell_values,
                "needs_cell_styles": required_table_info.needs_cell_styles,
                "needs_column_metadata": required_table_info.needs_column_metadata
            }
        }
        optimizations.append(filter_optimization)
        
        # Check if styles were filtered
        if "styles" in original_data and "styles" in optimized_data:
            original_style_count = len(original_data["styles"])
            optimized_style_count = len(optimized_data["styles"])
            if original_style_count != optimized_style_count:
                style_optimization = {
                    "type": "remove_unused_styles",
                    "details": {
                        "total_styles": original_style_count,
                        "referenced_styles": optimized_style_count,
                        "removed_count": original_style_count - optimized_style_count
                    }
                }
                optimizations.append(style_optimization)
        elif "styles" in original_data and "styles" not in optimized_data:
            # All styles removed
            original_style_count = len(original_data["styles"])
            style_optimization = {
                "type": "remove_all_styles",
                "details": {
                    "removed_count": original_style_count
                }
            }
            optimizations.append(style_optimization)
        
        # Check if columns metadata was removed
        if "columns" in original_data and "columns" not in optimized_data:
            columns_optimization = {
                "type": "remove_column_metadata",
                "details": {
                    "column_count": len(original_data["columns"])
                }
            }
            optimizations.append(columns_optimization)
        
        # Check if data sections were removed
        original_has_header = "data" in original_data and "header" in original_data["data"]
        optimized_has_header = "data" in optimized_data and "header" in optimized_data["data"]
        if original_has_header and not optimized_has_header:
            optimizations.append({
                "type": "remove_header",
                "details": {}
            })
        
        original_has_rows = "data" in original_data and "rows" in original_data["data"]
        optimized_has_rows = "data" in optimized_data and "rows" in optimized_data["data"]
        if original_has_rows and not optimized_has_rows:
            row_count = len(original_data["data"]["rows"])
            optimizations.append({
                "type": "remove_all_rows",
                "details": {
                    "row_count": row_count
                }
            })
        elif original_has_rows and optimized_has_rows:
            original_row_count = len(original_data["data"]["rows"])
            optimized_row_count = len(optimized_data["data"]["rows"])
            if original_row_count != optimized_row_count:
                optimizations.append({
                    "type": "filter_rows",
                    "details": {
                        "original_row_count": original_row_count,
                        "optimized_row_count": optimized_row_count,
                        "removed_count": original_row_count - optimized_row_count
                    }
                })
        
        return optimizations
