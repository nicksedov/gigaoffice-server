"""
Assistance Processor
Handles spreadsheet-assistance category requests
"""

from typing import Dict, Any
from loguru import logger

from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor


class AssistanceProcessor(BaseSpreadsheetProcessor):
    """
    Processor for spreadsheet-assistance category.
    
    Preprocessing strategy:
    - Returns empty dict (no spreadsheet data needed for consultations)
    - Focus entirely on user query text
    - Response is text-based consultation rather than spreadsheet transformation
    """
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess data for assistance requests.
        
        Assistance requests provide consultation about spreadsheet functions
        and capabilities, not data manipulation. Therefore, no input spreadsheet
        data is needed.
        
        Args:
            spreadsheet_data: Full spreadsheet data (ignored for assistance)
            
        Returns:
            Empty dict (assistance doesn't use input data)
        """
        # For assistance, we don't need any spreadsheet data
        # The response is based purely on the user's question
        logger.debug("Assistance data preprocessed: no input data required for consultation")
        return {}
