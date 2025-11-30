"""
Base interface for data providers.

All providers implement this interface to ensure consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DataProvider(ABC):
    """
    Abstract base class for data providers.
    
    Data providers extract data from various sources and return them
    in CSV format with semicolon delimiter.
    """
    
    @abstractmethod
    def get_data(self) -> str:
        """
        Returns complete CSV output as string (including header row).
        
        Returns:
            str: CSV-formatted data with semicolon delimiter
        """
        pass
    
    @abstractmethod
    def get_column_names(self) -> List[str]:
        """
        Returns list of column names for this provider.
        
        Returns:
            List[str]: Column names in order
        """
        pass
    
    @abstractmethod
    def get_source_info(self) -> Dict[str, Any]:
        """
        Returns metadata about data source.
        
        Returns:
            Dict[str, Any]: Metadata including path, file count, etc.
        """
        pass
