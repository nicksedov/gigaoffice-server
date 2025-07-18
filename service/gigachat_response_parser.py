import re
import json
from typing import Any, List, Optional
from loguru import logger

class GigachatResponseParser:
    def _extract_json_objects_from_text(self, text: str) -> Optional[List[List[Any]]]:
        """
        Извлекает JSON объекты/массивы из произвольного текста
        используя метод сканирования с подсчетом скобок
        """
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
                result, index = decoder.raw_decode(text[start_pos:])
                
                # Проверить, что результат соответствует ожидаемому формату
                if isinstance(result, list) and len(result) > 0:
                    # Проверить, что это массив массивов
                    if all(isinstance(row, list) for row in result):
                        return result
                    # Или это может быть плоский массив, который нужно обернуть
                    elif all(isinstance(item, (str, int, float, bool, type(None))) for item in result):
                        return [result]
                
                pos = start_pos + index
            except (json.JSONDecodeError, ValueError):
                return None
        
        return None

    def parse(self, response_content: str) -> Optional[List[List[Any]]]:
        
        try:
            # Попытаться извлечь JSON из ответа
            result_data = self._extract_json_objects_from_text(response_content)
            
            if result_data is None:
                logger.warning("Could not extract valid JSON from response")
                # Fallback: return response as single cell
                return None
            else:
                # Дополнительная валидация формата
                if not isinstance(result_data, list):
                    raise ValueError("Result must be a list")
                
                for row in result_data:
                    if not isinstance(row, list):
                        raise ValueError("Each row must be a list")
                
                logger.info(f"Successfully extracted JSON with {len(result_data)} rows")
                return result_data

        except Exception as e:
            logger.warning(f"Error processing JSON response: {e}")
            # Fallback: return response as single cell
            result_data = [[response_content.strip()]]
            return result_data

response_parser = GigachatResponseParser()