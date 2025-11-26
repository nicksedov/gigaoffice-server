"""
Histogram Data Validation
Validation logic for histogram statistical metadata
"""

from typing import Dict, Any
from fastapi import HTTPException


def validate_histogram_metadata(spreadsheet_data: Dict[str, Any]) -> None:
    """
    Validate spreadsheet data structure and statistical metadata for histogram requests
    
    Validates that spreadsheet_data contains columns with statistical metadata
    and ensures logical consistency of statistical values (min, max, median, count).
    
    Args:
        spreadsheet_data: Dictionary containing spreadsheet data with columns and metadata
        
    Raises:
        HTTPException: 400 if validation fails with detailed error message
    """
    # Validate that spreadsheet_data is a dictionary
    if not isinstance(spreadsheet_data, dict):
        raise HTTPException(
            status_code=400,
            detail="spreadsheet_data must be a valid dictionary"
        )
    
    # Check if columns exist
    columns = spreadsheet_data.get("columns", [])
    if not columns:
        raise HTTPException(
            status_code=400,
            detail="spreadsheet_data must contain at least one column definition"
        )
    
    # Validate statistical metadata consistency for numerical columns
    for col in columns:
        if not isinstance(col, dict):
            continue
        
        # Validate range field is present
        if "range" not in col:
            raise HTTPException(
                status_code=400,
                detail=f"Column {col.get('index', 'unknown')} must have a 'range' field"
            )
        
        # Validate statistical field consistency if present
        min_val = col.get("min")
        max_val = col.get("max")
        median_val = col.get("median")
        count_val = col.get("count")
        
        if min_val is not None and max_val is not None:
            if min_val > max_val:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column {col.get('index')}: min must be <= max"
                )
        
        if median_val is not None:
            if min_val is not None and median_val < min_val:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column {col.get('index')}: median must be >= min"
                )
            if max_val is not None and median_val > max_val:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column {col.get('index')}: median must be <= max"
                )
        
        if count_val is not None and count_val <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Column {col.get('index')}: count must be > 0"
            )
