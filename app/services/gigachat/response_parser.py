import re
import json
from typing import Any, List, Optional
from loguru import logger

class GigachatResponseParser:

    def parse_object(self, text: str, required_fields: List[str] = None) -> Optional[Any]:
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
                result, json_length = decoder.raw_decode(text[start_pos:])
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in result]
                    if missing_fields:
                        logger.warning(f"Skipped valid JSON entry from LLM response due to missing fields: {missing_fields}")
                        pos = start_pos + json_length
                        continue
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
            result_object = self.parse_object(response_content, ['metadata', 'worksheet', 'data'])
            
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
    
    def parse_chart_data(self, response_content: str) -> Optional[dict]:
        """
        Extract and validate ChartConfig structure from GigaChat response
        
        Args:
            response_content: Raw AI response string
            
        Returns:
            Parsed chart configuration dictionary or None if parsing failed
        """
        try:
            # Required fields for ChartConfig
            required_fields = ['chart_type', 'title', 'series_config', 'position', 'styling']
            
            # Try to extract JSON object from response
            result_object = self.parse_object(response_content, required_fields)
            
            if result_object is None:
                logger.warning("Could not extract valid JSON from chart response")
                return None
            
            # Validate chart configuration structure
            if isinstance(result_object, dict):
                # Verify all required fields are present
                missing_fields = [field for field in required_fields if field not in result_object]
                
                if missing_fields:
                    logger.warning(f"Chart response missing required fields: {missing_fields}")
                    return None
                
                logger.info("Successfully extracted chart configuration")
                return result_object
            else:
                logger.warning("Chart response is not a dictionary")
                return None
                
        except Exception as e:
            logger.warning(f"Error processing chart response: {e}")
            return None

# Create global instance
response_parser = GigachatResponseParser()