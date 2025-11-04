"""
Search Processor
Handles spreadsheet-search category requests
"""

import copy
from typing import Dict, Any
from loguru import logger

from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor


class SearchProcessor(BaseSpreadsheetProcessor):
    """
    Processor for spreadsheet-search category.
    
    Preprocessing strategy:
    - Keep all header and row values (needed for searching)
    - Remove all style definitions
    - Remove style references from header and rows
    - Keep columns with format but without statistical metadata
    - Preserve worksheet metadata
    """
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess data for search requests.
        
        Search operations need to examine values and understand data types,
        but styling is irrelevant.
        
        Args:
            spreadsheet_data: Full spreadsheet data
            
        Returns:
            Preprocessed data with values but without styles
        """
        if not spreadsheet_data:
            return spreadsheet_data
        
        # Deep copy to avoid modifying original data
        data = copy.deepcopy(spreadsheet_data)
        
        # Remove entire styles array
        data.pop('styles', None)
        
        # Remove style references from header
        if 'data' in data and 'header' in data['data']:
            data['data']['header'].pop('style', None)
        
        # Remove style references from rows
        if 'data' in data and 'rows' in data['data']:
            for row in data['data']['rows']:
                row.pop('style', None)
        
        # Remove statistical metadata from columns (keep format info)
        if 'columns' in data:
            for column in data['columns']:
                column.pop('min', None)
                column.pop('max', None)
                column.pop('median', None)
                column.pop('count', None)
        
        logger.debug("Search data preprocessed: removed styles and statistics, kept values and formats")
        return data
