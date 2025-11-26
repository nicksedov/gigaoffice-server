import re
import json
from typing import Any, List, Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from app.services.chart.validator import ChartValidator, ChartValidationError

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
    
    def parse_text_content(self, response_content: str) -> Optional[dict]:
        """
        Extract and validate text content from GigaChat response
        
        Args:
            response_content: Raw AI response string
            
        Returns:
            Parsed text content dictionary or None if parsing failed
        """
        try:
            # Required field for text content response
            required_fields = ['text_content']
            
            # Try to extract JSON object from response
            result_object = self.parse_object(response_content, required_fields)
            
            if result_object is None:
                logger.warning("Could not extract valid JSON from text content response")
                return None
            
            # Validate text content structure
            if isinstance(result_object, dict):
                # Verify text_content field is present
                if 'text_content' not in result_object:
                    logger.warning("Text content response missing required field: text_content")
                    raise Exception("Could not extract valid JSON from text content response")
                
                # Validate field type
                text_content = result_object.get('text_content')
                
                if not isinstance(text_content, str):
                    logger.warning("Text content response field 'text_content' must be a string")
                    return None
                
                if not text_content.strip():
                    logger.warning("Text content response field 'text_content' must be a non-empty string")
                    return None
                
                logger.info("Successfully extracted text content response")
                return result_object
            else:
                logger.warning("Text content response is not a dictionary")
                return None
                
        except Exception as e:
            logger.warning(f"Error processing text content response: {e}")
            return None
    
    def parse_histogram_data(self, response_content: str) -> Optional[dict]:
        """
        Extract and validate histogram configuration from GigaChat response
        
        Args:
            response_content: Raw AI response string
            
        Returns:
            Parsed histogram configuration dictionary or None if parsing failed
        """
        try:
            # Required fields for HistogramResponse
            required_fields = ['source_columns', 'recommended_bins', 'range_column_name', 'count_column_name']
            
            # Try to extract JSON object from response
            result_object = self.parse_object(response_content, required_fields)
            
            if result_object is None:
                logger.warning("Could not extract valid JSON from histogram response")
                return None
            
            # Validate histogram configuration structure
            if isinstance(result_object, dict):
                # Verify all required fields are present
                missing_fields = [field for field in required_fields if field not in result_object]
                
                if missing_fields:
                    logger.warning(f"Histogram response missing required fields: {missing_fields}")
                    return None
                
                # Validate field types and constraints
                source_columns = result_object.get('source_columns')
                recommended_bins = result_object.get('recommended_bins')
                range_column_name = result_object.get('range_column_name')
                count_column_name = result_object.get('count_column_name')
                
                # Type and constraint validation
                if not isinstance(source_columns, list) or len(source_columns) == 0:
                    logger.warning("Histogram response field 'source_columns' must be a non-empty list")
                    return None
                
                if not isinstance(recommended_bins, int) or recommended_bins < 1 or recommended_bins > 100:
                    logger.warning(f"Histogram response field 'recommended_bins' must be an integer between 1-100, got: {recommended_bins}")
                    return None
                
                if not isinstance(range_column_name, str) or not range_column_name.strip():
                    logger.warning("Histogram response field 'range_column_name' must be a non-empty string")
                    return None
                
                if not isinstance(count_column_name, str) or not count_column_name.strip():
                    logger.warning("Histogram response field 'count_column_name' must be a non-empty string")
                    return None
                
                logger.info("Successfully extracted and validated histogram configuration")
                return result_object
            else:
                logger.warning("Histogram response is not a dictionary")
                return None
                
        except Exception as e:
            logger.warning(f"Error processing histogram response: {e}")
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
            # Lazy import to avoid circular dependency
            from app.services.chart.validator import chart_validator, ChartValidationError
            
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
                
                # Validate chart configuration against ONLYOFFICE specification
                try:
                    chart_validator.validate_chart_config(result_object)
                    logger.info("Successfully extracted and validated chart configuration")
                    return result_object
                except ChartValidationError as e:
                    logger.error(f"Chart validation failed: {e.message}")
                    logger.error(f"Validation details: {e.to_dict()}")
                    # Return None to indicate validation failure
                    return None
            else:
                logger.warning("Chart response is not a dictionary")
                return None
                
        except Exception as e:
            logger.warning(f"Error processing chart response: {e}")
            return None

# Create global instance
response_parser = GigachatResponseParser()