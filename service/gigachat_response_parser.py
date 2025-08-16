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
            start_bracket = text.find('[', pos)
            start_brace = text.find('{', pos)
            
            # Определить какая скобка ближе
            if start_bracket == -1 and start_brace == -1:
                break
            elif start_bracket == -1:
                start_pos = start_brace
            elif start_brace == -1:
                start_pos = start_bracket
            else:
                start_pos = min(start_bracket, start_brace)
            try:
                # Попытаться декодировать JSON начиная с найденной позиции
                result, _ = decoder.raw_decode(text[start_pos:])
                return result
            except (json.JSONDecodeError, ValueError):
                return None
        
        return None

    def parse(self, response_content: str) -> Optional[List[List[Any]]]:
        
        try:
            # Попытаться извлечь JSON из ответа
            result_object = self.parse_object(response_content)
            
            if result_object is None:
                logger.warning("Could not extract valid JSON from response")
                # Fallback: return response as single cell
                return None
            else:
                result_data = None
                if isinstance(result_object, list) and len(result_object) > 0:
                # Проверить, что это массив массивов
                    if all(isinstance(row, list) for row in result_object):
                        result_data = result_object
                    # Или это может быть плоский массив, который нужно обернуть
                    elif all(isinstance(item, (str, int, float, bool, type(None))) for item in result_object):
                        result_data = [result_object]
                    if result_data:
                        logger.info(f"Successfully extracted JSON with {len(result_data)} rows")
                        return result_data
                    else:
                        logger.warning("Could not extract valid JSON from response")
                        result_data = [[response_content.strip()]]
                        return result_data
        except Exception as e:
            logger.warning(f"Error processing JSON response: {e}")
            # Fallback: return response as single cell
            result_data = [[response_content.strip()]]
            return result_data

response_parser = GigachatResponseParser()