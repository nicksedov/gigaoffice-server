"""
Formatting Processor
Handles spreadsheet-formatting category requests
"""

import copy
from typing import Dict, Any
from loguru import logger

from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor


class FormattingProcessor(BaseSpreadsheetProcessor):
    """
    Processor for spreadsheet-formatting category.
    
    Preprocessing strategy:
    - Keep header values (column names needed for styling)
    - Remove cell values from data rows (replace with empty strings)
    - Preserve all style definitions and references
    - Keep worksheet metadata
    - Remove statistical metadata from columns
    """
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess data for formatting requests.
        
        Formatting decisions depend on table structure and styles, not actual values.
        This removes cell values to reduce token usage while preserving structure.
        
        Args:
            spreadsheet_data: Full spreadsheet data
            
        Returns:
            Preprocessed data with values removed from rows
        """
        if not spreadsheet_data:
            return spreadsheet_data
        
        # Deep copy to avoid modifying original data
        data = copy.deepcopy(spreadsheet_data)
        
        # Process data rows - replace values with empty strings
        if 'data' in data and 'rows' in data['data']:
            for row in data['data']['rows']:
                if 'values' in row and isinstance(row['values'], list):
                    # Replace each value with appropriate empty value based on type
                    row['values'] = ["" for _ in row['values']]
        
        # Remove statistical metadata from columns (min, max, median, count)
        if 'columns' in data:
            for column in data['columns']:
                column.pop('min', None)
                column.pop('max', None)
                column.pop('median', None)
                column.pop('count', None)
        
        logger.debug("Formatted data preprocessed: removed cell values, kept styles and structure")
        return data
