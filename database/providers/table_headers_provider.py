"""
Table Headers Provider.

Extracts unique table header terms from CSV file and returns them
as a single-column CSV with semicolon delimiter.
"""

import csv
import os
from typing import List, Dict, Any
from pathlib import Path
from loguru import logger

from .base import DataProvider


class TableHeadersProvider(DataProvider):
    """
    Provider for table header terms.
    
    Reads table_headers.csv containing Russian and English terms,
    extracts unique terms, and returns them as single-column CSV.
    """
    
    def __init__(self, csv_file_path: str = None):
        """
        Initialize the provider.
        
        Args:
            csv_file_path: Path to table_headers.csv. If None, uses default path.
        """
        if csv_file_path is None:
            csv_file_path = os.getenv(
                "HEADERS_CSV_FILE",
                "database/embeddings/table_headers/table_headers.csv"
            )
        
        self.csv_file_path = Path(csv_file_path)
        self.delimiter = os.getenv("CSV_DELIMITER", ";")
        self.encoding = os.getenv("CSV_ENCODING", "utf-8")
        self._headers = None
        
        logger.info(f"TableHeadersProvider initialized with source: {self.csv_file_path}")
    
    def _extract_headers(self) -> List[str]:
        """
        Extract unique headers from the CSV file.
        
        Returns:
            List[str]: Sorted list of unique header terms
        """
        if not self.csv_file_path.exists():
            logger.error(f"Source file not found: {self.csv_file_path}")
            return []
        
        headers = set()
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                # Skip header row
                next(reader, None)
                
                for row in reader:
                    if len(row) >= 2:
                        # Extract Russian term (column 0)
                        russian_term = row[0].strip()
                        if russian_term:
                            headers.add(russian_term)
                        
                        # Extract English term (column 1)
                        english_term = row[1].strip()
                        if english_term:
                            headers.add(english_term)
            
            logger.info(f"Extracted {len(headers)} unique terms from CSV")
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []
        
        # Sort alphabetically
        return sorted(list(headers))
    
    def get_data(self) -> str:
        """
        Returns complete CSV output as string (including header row).
        
        Returns:
            str: CSV-formatted data with semicolon delimiter
        """
        if self._headers is None:
            self._headers = self._extract_headers()
        
        # Build CSV output
        output_lines = ["text"]  # Header row
        
        for header in self._headers:
            # Escape field if needed
            if self.delimiter in header or '"' in header or '\n' in header:
                # Escape quotes and wrap in quotes
                escaped = header.replace('"', '""')
                output_lines.append(f'"{escaped}"')
            else:
                output_lines.append(header)
        
        logger.info(f"Generated CSV with {len(self._headers)} records")
        
        return "\n".join(output_lines)
    
    def get_column_names(self) -> List[str]:
        """
        Returns list of column names for this provider.
        
        Returns:
            List[str]: Column names ["text"]
        """
        return ["text"]
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Returns metadata about data source.
        
        Returns:
            Dict[str, Any]: Metadata including path, file count, etc.
        """
        if self._headers is None:
            self._headers = self._extract_headers()
        
        return {
            "source_type": "csv",
            "source_path": str(self.csv_file_path),
            "file_exists": self.csv_file_path.exists(),
            "total_records": len(self._headers),
            "encoding": self.encoding,
            "delimiter": self.delimiter
        }
