"""
Generation Processor
Handles spreadsheet-generation category requests
"""

from typing import Dict, Any
from loguru import logger

from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor


class GenerationProcessor(BaseSpreadsheetProcessor):
    """
    Processor for spreadsheet-generation category.
    
    Preprocessing strategy:
    - Minimal preprocessing (generation creates data from scratch)
    - Input data is typically null or minimal
    - Focus on the user query rather than existing data
    """
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess data for generation requests.
        
        Generation creates new data from scratch based on the prompt.
        Input spreadsheet data is typically not relevant.
        
        Args:
            spreadsheet_data: Full spreadsheet data (typically null or minimal)
            
        Returns:
            Empty dict (generation doesn't use input data)
        """
        # For generation, we typically don't send input spreadsheet data
        # If data is provided, it might contain structural hints only
        logger.debug("Generation data preprocessed: minimal/no input data required")
        # Return empty dict since generation doesn't use input data
        return {}
