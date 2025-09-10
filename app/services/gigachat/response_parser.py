import re
import json
from typing import Any, List, Optional
from loguru import logger

class GigachatResponseParser:

    def parse_object(self, text: str) -> Optional[Any]:
        decoder = json.JSONDecoder()
        pos = 0
        
        # Ищем начало JSON (массив или объект)
        while pos < len(text):
            # Найти первую открывающую скобку
            start_pos = text.find('{', pos)
            
            # Определить какая скобка ближе
            if start_pos == -1:
                break
            try:
                # Попытаться декодировать JSON начиная с найденной позиции
                result, _ = decoder.raw_decode(text[start_pos:])
                return result
            except (json.JSONDecodeError, ValueError):
                return None
        
        return None

    def parse_spreadsheet_data(self, response_content: str) -> Optional[dict]:
        """
        Parse enhanced spreadsheet data from response
        
        Args:
            response_content: Raw response content from GigaChat
            
        Returns:
            Parsed spreadsheet data as dictionary or None if parsing failed
        """
        try:
            # Try to extract JSON object from response
            result_object = self.parse_object(response_content)
            
            if result_object is None:
                logger.warning("Could not extract valid JSON from spreadsheet response")
                return None
            
            # Check if this is enhanced spreadsheet data
            if isinstance(result_object, dict):
                # Check for required spreadsheet data fields
                if "worksheet" in result_object and "data" in result_object:
                    logger.info("Successfully extracted enhanced spreadsheet data")
                    return result_object
                else:
                    raise Exception("Could not extract valid JSON from spreadsheet response")
                
        except Exception as e:
            logger.warning(f"Error processing spreadsheet response: {e}")
            return None

# Create global instance
response_parser = GigachatResponseParser()