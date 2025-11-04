"""
Analysis Processor
Handles spreadsheet-analysis category requests
"""

import copy
from typing import Dict, Any
from loguru import logger

from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor


class AnalysisProcessor(BaseSpreadsheetProcessor):
    """
    Processor for spreadsheet-analysis category.
    
    Preprocessing strategy:
    - Keep all header and row values (needed for analysis)
    - Remove all style definitions
    - Remove style references from header and rows
    - Keep columns with statistical metadata
    - Preserve worksheet metadata
    """
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess data for analysis requests.
        
        Analysis focuses on data content, not visual presentation.
        This removes all styling information while preserving data values.
        
        Args:
            spreadsheet_data: Full spreadsheet data
            
        Returns:
            Preprocessed data without styles, focusing on values
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
        
        logger.debug("Analysis data preprocessed: removed all styles, kept values and statistics")
        return data
