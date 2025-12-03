import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from string import Template
from loguru import logger
from app.resource_loader import resource_loader
from app.services.database.vector_search import (
    classification_prompt_search,
    categorized_prompt_search
)
from app.utils.json_encoder import DateTimeEncoder

"""
GigaChat Prompt Builder
Класс для формирования промптов для GigaChat API
"""

class GigachatPromptBuilder:
    """Класс для формирования промптов для GigaChat"""
    
    PROMPT_CATEGORY_DIRS = {
        'classifier':                 'classifier',
        'spreadsheet-analysis':       'category/spreadsheet-analysis',
        'spreadsheet-transformation': 'category/spreadsheet-transformation',
        'spreadsheet-search':         'category/spreadsheet-search', 
        'spreadsheet-generation':     'category/spreadsheet-generation',
        'spreadsheet-formatting':     'category/spreadsheet-formatting',
        'spreadsheet-assistance':     'category/spreadsheet-assistance',
        'data-chart':                 'category/data-chart',
        'data-histogram':             'category/data-histogram'
    }

    def __init__(self, resources_dir: str = 'resources/prompts/'):
        self.resources_dir = resources_dir

    def _load_system_prompt(self, prompt_type: str) -> str:
        """Load system prompt from system_prompt.txt file"""
        category_dir = self.PROMPT_CATEGORY_DIRS.get(prompt_type, self.PROMPT_CATEGORY_DIRS['spreadsheet-analysis'])
        prompt_path = os.path.join(self.resources_dir, category_dir, 'system_prompt.txt')
        
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"System prompt file not found: {prompt_path}")
            
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def _load_examples(self, prompt_type: str, user_query: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Load examples using database vector search.
        
        Args:
            prompt_type: Prompt category type
            user_query: User's query text for relevance-based selection (optional)
            
        Returns:
            List of top 3 most relevant examples (or all available if less than 3)
        """
        # If no user query provided, use empty string for search
        query = user_query if user_query else ""
        
        try:
            # Route to appropriate search service based on category
            if prompt_type == 'classifier':
                logger.info(f"Loading classification examples from database with query: {query[:50]}...")
                examples = classification_prompt_search.search_examples(
                    query=query,
                    search_mode="fulltext",
                    limit=3
                )
            else:
                logger.info(f"Loading examples from database for category '{prompt_type}' with query: {query[:50]}...")
                examples = categorized_prompt_search.search_examples(
                    query=query,
                    category=prompt_type,
                    search_mode="fulltext",
                    limit=3
                )
            
            if examples:
                logger.info(f"Successfully loaded {len(examples)} examples from database")
            else:
                logger.warning(f"No examples found in database for category '{prompt_type}'")
            
            return examples
                
        except Exception as e:
            # Log error and return empty list (no fallback)
            logger.error(f"Error loading examples from database for category '{prompt_type}': {e}")
            return []
    
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
        prompt_type: str = 'spreadsheet-analysis',
        user_query: Optional[str] = None
    ) -> str:
        """
        Формирует системный промпт с общей частью и релевантными примерами.
        
        Args:
            prompt_type: тип промпта, например 'spreadsheet-analysis', 'spreadsheet-transformation', 'spreadsheet-search' или 'spreadsheet-generation'
            user_query: пользовательский запрос для отбора релевантных примеров (optional)
            
        Returns:
            Сформированный системный промпт
        """
        system_prompt = self._load_system_prompt(prompt_type)
        examples = self._load_examples(prompt_type, user_query)
        
        prompt_lines = [system_prompt, "", "## Примеры:"]
        
        example_id = 1
        for ex in examples:
            task = ex['task']
            request_table_json = json.loads(ex['request_table']) if ex['request_table'] else None
            request = self.prepare_user_prompt(task, request_table_json)
            prompt_lines.append(f"### Пример {example_id}:")
            prompt_lines.append(request)
            prompt_lines.append("Твой ответ:")
            prompt_lines.append(ex['response_table'])
            prompt_lines.append('')
            example_id += 1

        return "\n".join(prompt_lines)

    def prepare_user_prompt(
        self,
        query: str,
        spreadsheet_data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Подготовка специализированного промпта для обработки расширенных данных таблиц
        
        Supports both spreadsheet data and chart data with range-based series.
        For chart data, the spreadsheet_data parameter contains series with 'range' fields
        instead of inline 'values'.
        
        Args:
            query: Текст запроса пользователя
            spreadsheet_data: Расширенные данные таблицы в формате JSON
                For chart requests, this will be a list of series with:
                - name: Series name
                - range: Cell range reference (e.g., "A2:A18")
                - format: Value format (e.g., "hh:mm", "# ##0.00")
            
        Returns:
            str: Сформированный промпт для отправки в GigaChat
            
        Example for chart data:
            spreadsheet_data = [
                {"name": "Время", "range": "A2:A18", "format": "hh:mm"},
                {"name": "Цена", "range": "B2:B18", "format": "# ##0.00"}
            ]
        """
        prompt_parts: list[str] = []
        # 1. Задача
        prompt_parts.append(f"ЗАДАЧА: {query}")
        prompt_parts.append("")
        
        # 2. Расширенные данные таблицы (если есть)
        if spreadsheet_data:
            prompt_parts.append("РАСШИРЕННЫЕ ДАННЫЕ ТАБЛИЦЫ:")
            prompt_parts.append(json.dumps(spreadsheet_data, ensure_ascii=False, cls=DateTimeEncoder))
            prompt_parts.append("")
        
        return "\n".join(prompt_parts)

# Create global instance
prompt_builder = GigachatPromptBuilder()

