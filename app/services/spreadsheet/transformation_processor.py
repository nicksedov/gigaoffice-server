"""
Transformation Processor
Handles spreadsheet-transformation category requests
"""

import copy
from typing import Dict, Any
from loguru import logger

from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor


class TransformationProcessor(BaseSpreadsheetProcessor):
    """
    Processor for spreadsheet-transformation category.
    
    Preprocessing strategy:
    - Keep all header and row values (needed for transformations)
    - Keep style definitions (transformations may preserve or update styles)
    - Keep style references in header and rows
    - Keep columns with format information
    - Remove statistical metadata from columns
    - Preserve worksheet metadata
    """
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess data for transformation requests.
        
        Transformations modify data structure and content, potentially preserving
        or updating styles, so both data and styles are relevant.
        
        Args:
            spreadsheet_data: Full spreadsheet data
            
        Returns:
            Preprocessed data with values and styles, without statistics
        """
        if not spreadsheet_data:
            return spreadsheet_data
        
        # Deep copy to avoid modifying original data
        data = copy.deepcopy(spreadsheet_data)
        
        # Remove statistical metadata from columns (keep format info)
        if 'columns' in data:
            for column in data['columns']:
                column.pop('min', None)
                column.pop('max', None)
                column.pop('median', None)
                column.pop('count', None)
        
        logger.debug("Transformation data preprocessed: kept values and styles, removed statistics")
        return data
