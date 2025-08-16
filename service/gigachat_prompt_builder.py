import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from resource_loader import resource_loader
from string import Template

"""
GigaChat Prompt Builder
Класс для формирования промптов для GigaChat API
"""

class GigachatPromptBuilder:
    """Класс для формирования промптов для GigaChat"""
    
    def __init__(self):
        pass
    
    def prepare_classifier_system_prompt(self, categories: List[Dict[str, Any]]) -> str:
        """Подготовка системного промпта для классификатора пользовательского запроса"""
        # Добавляем информацию о категориях
        category_list = "\n"
        for category in categories:
            category_list += f"- {category['name']}"
            if category['description']:
                category_list += f": {category['description']}"
            category_list += "\n"
        prompt = resource_loader.get_prompt_template("gigachat_classifier_system_prompt.txt")
        pt = Template(prompt)
        text = pt.substitute({"category_list": category_list})
        return text

    def prepare_system_prompt(self) -> str:
        """Подготовка системного промпта для табличных данных"""
        return resource_loader.get_prompt_template("gigachat_system_prompt.txt")
    
    def _parse_excel_range(self, range_str: str) -> Optional[Dict[str, Any]]:
        """
        Парсинг диапазона ячеек Excel для вычисления размерности
        
        Args:
            range_str: Строка диапазона в формате "A1:C5" или "A1"
            
        Returns:
            dict: {"width": int, "height": int, "is_single_cell": bool} или None
        """
        if not range_str:
            return None
        
        # Удаляем пробелы и приводим к верхнему регистру
        range_str = range_str.strip().upper()
        
        # Проверяем, содержит ли диапазон двоеточие
        if ':' not in range_str:
            # Одна ячейка
            return {"width": 1, "height": 1, "is_single_cell": True}
        
        # Разбиваем диапазон на начальную и конечную ячейки
        try:
            start_cell, end_cell = range_str.split(':')
        except ValueError:
            return None
        
        # Регулярное выражение для парсинга ячейки (например, A1, AB123)
        cell_pattern = r'^([A-Z]+)(\d+)$'
        
        start_match = re.match(cell_pattern, start_cell)
        end_match = re.match(cell_pattern, end_cell)
        
        if not start_match or not end_match:
            return None
        
        # Функция для конвертации буквенного обозначения колонки в число
        def column_to_number(column_str):
            result = 0
            for char in column_str:
                result = result * 26 + (ord(char) - ord('A') + 1)
            return result
        
        # Извлекаем колонки и строки
        start_col = column_to_number(start_match.group(1))
        start_row = int(start_match.group(2))
        end_col = column_to_number(end_match.group(1))
        end_row = int(end_match.group(2))
        
        # Вычисляем размерность
        width = abs(end_col - start_col) + 1
        height = abs(end_row - start_row) + 1
        
        return {
            "width": width,
            "height": height,
            "is_single_cell": False
        }
    
    def prepare_user_prompt(
        self, 
        query: str, 
        input_range: Optional[str] = None,
        output_range: Optional[str] = None,
        input_data: Optional[List[Dict]] = None
    ) -> str:
        """
        Подготовка пользовательского промпта
        
        Args:
            query: Текст запроса пользователя
            input_data: Входные данные (опционально)
            input_range: Диапазон ячеек с исходными данными (например, "A1:C10")
            output_range: Диапазон ячеек для результата (например, "E1:G5")
            
        Returns:
            str: Сформированный промпт для отправки в GigaChat
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt_parts = [f"ДАТА ЗАПРОСА: {timestamp_str}", ""]
        
        # 1. Исходные данные
        if input_data:
            prompt_parts.append("ИСХОДНЫЕ ДАННЫЕ:")
            prompt_parts.append(json.dumps(input_data, ensure_ascii=False, indent=2))
            prompt_parts.append("")
        
        # 2. Диапазон ячеек с исходными данными
        if input_range:
            prompt_parts.append(f"ДИАПАЗОН ЯЧЕЕК С ИСХОДНЫМИ ДАННЫМИ: {input_range}")
            prompt_parts.append("")
        
        # 3. Диапазон ячеек результата
        if output_range:
            prompt_parts.append(f"ДИАПАЗОН ЯЧЕЕК ДЛЯ ВСТАВКИ РЕЗУЛЬТАТА: {output_range}")
        
        # 4. Задача
        prompt_parts.append("ЗАДАЧА:")
        prompt_parts.append(query)
        prompt_parts.append("")
        
        # 5. Инструкция по формату ответа
        prompt_parts.append("Предоставь ответ в виде JSON массива массивов.")
        
        return "\n".join(prompt_parts)

prompt_builder = GigachatPromptBuilder()