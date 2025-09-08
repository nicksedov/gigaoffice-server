import os
import json
import re
import yaml
from datetime import datetime
from typing import Optional, List, Dict, Any
from string import Template
from app.resource_loader import resource_loader

"""
GigaChat Prompt Builder
Класс для формирования промптов для GigaChat API
"""

class GigachatPromptBuilder:
    """Класс для формирования промптов для GigaChat"""
    
    PROMPT_CONFIG_FILE_MAP = {
        'classifier':     'user_prompt_classifier.yaml',
        'spreadsheet-analysis':       'system_prompt_spreadsheet_analysis.yaml',
        'spreadsheet-transformation': 'system_prompt_spreadsheet_transformation.yaml',
        'spreadsheet-search':         'system_prompt_spreadsheet_search.yaml', 
        'spreadsheet-generation':     'system_prompt_spreadsheet_generation.yaml',
        'spreadsheet-formatting':     'system_prompt_spreadsheet_formatting.yaml'
    }

    def __init__(self, resources_dir: str = 'resources/prompts/'):
        self.resources_dir = resources_dir

    def _load_system_prompt(self, prompt_type: str) -> list:
        filename = self.PROMPT_CONFIG_FILE_MAP.get(prompt_type, self.PROMPT_CONFIG_FILE_MAP['spreadsheet-analysis'])
        path = os.path.join(self.resources_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    
    def prepare_classifier_system_prompt(self, categories: List[Dict[str, Any]]) -> str:
        """Подготовка системного промпта для классификатора пользовательского запроса"""
        text = self.prepare_system_prompt('classifier')
        # Добавляем информацию о категориях
        category_list = "\n"
        for category in categories:
            category_list += f"- {category['name']}"
            if category['description']:
                category_list += f": {category['description']}"
            category_list += "\n"
        pt = Template(text)
        return pt.substitute({"category_list": category_list})

    def prepare_system_prompt(
        self, 
        prompt_type: str = 'spreadsheet-analysis'
    ) -> str:
        """
        Формирует системный промпт с общей частью и релевантными примерами.
        Аргумент:
            prompt_type: тип промпта, например 'spreadsheet-analysis', 'spreadsheet-transformation', 'spreadsheet-search' или 'spreadsheet-generation'
        """
        data = self._load_system_prompt(prompt_type)
        examples = data['examples']
        prompt_lines = [data['prompt'], "", "### Примеры:"]
        for ex in examples:
            prompt_lines.append("Запрос:")
            prompt_lines.append(ex['request'])
            prompt_lines.append("Твой ответ:")
            prompt_lines.append(ex['response'])
            prompt_lines.append('')

        return "\n".join(prompt_lines)

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
        input_data: Optional[List[Dict]] = None
    ) -> str:
        """
        Подготовка пользовательского промпта
        
        Args:
            query: Текст запроса пользователя
            input_data: Входные данные (опционально)
            input_range: Диапазон ячеек с исходными данными (например, "A1:C10")
            
        Returns:
            str: Сформированный промпт для отправки в GigaChat
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt_parts = [f"ДАТА ЗАПРОСА: {timestamp_str}", ""]
        
        # 1. Задача
        prompt_parts.append(f"ЗАДАЧА: {query}")
        prompt_parts.append("")

        # 2. Исходные данные
        if input_data:
            # Check if this is enhanced spreadsheet data
            if len(input_data) == 1 and "spreadsheet_data" in input_data[0]:
                prompt_parts.append("РАСШИРЕННЫЕ ДАННЫЕ ТАБЛИЦЫ:")
                prompt_parts.append(input_data[0]["spreadsheet_data"])
            else:
                prompt_parts.append("ИСХОДНЫЕ ДАННЫЕ:")
                prompt_parts.append(json.dumps(input_data, ensure_ascii=False, indent=2))
            prompt_parts.append("")
        
        # 3. Диапазон ячеек с исходными данными
        if input_range:
            prompt_parts.append(f"ДИАПАЗОН ЯЧЕЕК С ИСХОДНЫМИ ДАННЫМИ: {input_range}")
            prompt_parts.append("")
        
        # 4. Инструкция по формату ответа
        prompt_parts.append("Предоставь ответ в виде JSON-массива массивов.")
        
        return "\n".join(prompt_parts)

    def prepare_spreadsheet_prompt(
        self,
        query: str,
        spreadsheet_data: Dict[str, Any]
    ) -> str:
        """
        Подготовка специализированного промпта для обработки расширенных данных таблиц
        
        Args:
            query: Текст запроса пользователя
            spreadsheet_data: Расширенные данные таблицы в формате JSON
            
        Returns:
            str: Сформированный промпт для отправки в GigaChat
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt_parts = [f"ДАТА ЗАПРОСА: {timestamp_str}", ""]
        
        # 1. Задача
        prompt_parts.append(f"ЗАДАЧА: {query}")
        prompt_parts.append("")
        
        # 2. Расширенные данные таблицы
        prompt_parts.append("РАСШИРЕННЫЕ ДАННЫЕ ТАБЛИЦЫ:")
        prompt_parts.append(json.dumps(spreadsheet_data, ensure_ascii=False, indent=2))
        prompt_parts.append("")
        
        # 3. Инструкция по формату ответа
        prompt_parts.append("Предоставь ответ в формате расширенных данных таблицы, сохраняя структуру JSON.")
        
        return "\n".join(prompt_parts)

# Create global instance
prompt_builder = GigachatPromptBuilder()