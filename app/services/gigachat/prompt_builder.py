import os
import json
import re
import yaml
import glob
from datetime import datetime
from typing import Optional, List, Dict, Any
from string import Template
from loguru import logger
from app.resource_loader import resource_loader
from app.services.database.vector_search import prompt_example_search

"""
GigaChat Prompt Builder
Класс для формирования промптов для GigaChat API
"""

class GigachatPromptBuilder:
    """Класс для формирования промптов для GigaChat"""
    
    PROMPT_CATEGORY_DIRS = {
        'classifier':                 'classifier',
        'spreadsheet-analysis':       'spreadsheet-analysis',
        'spreadsheet-transformation': 'spreadsheet-transformation',
        'spreadsheet-search':         'spreadsheet-search', 
        'spreadsheet-generation':     'spreadsheet-generation',
        'spreadsheet-formatting':     'spreadsheet-formatting',
        'spreadsheet-assistance':     'spreadsheet-assistance',
        'data-chart':                 'data-chart',
        'data-histogram':             'data-histogram'
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
    
    def _load_examples_from_files(self, prompt_type: str) -> List[Dict[str, str]]:
        """
        Load examples from example_*.yaml files (fallback method).
        
        Args:
            prompt_type: Prompt category type
            
        Returns:
            List of example dictionaries
        """
        category_dir = self.PROMPT_CATEGORY_DIRS.get(prompt_type, self.PROMPT_CATEGORY_DIRS['spreadsheet-analysis'])
        examples_dir = os.path.join(self.resources_dir, category_dir)
        
        if not os.path.exists(examples_dir):
            logger.warning(f"Examples directory not found: {examples_dir}")
            return []
            
        example_files = glob.glob(os.path.join(examples_dir, 'example_*.yaml'))
        example_files.sort()  # Ensure consistent ordering
        
        examples = []
        for example_file in example_files:
            try:
                with open(example_file, 'r', encoding='utf-8') as f:
                    example_data = yaml.safe_load(f)
                    examples.append({
                        'task': example_data.get('task', ''),
                        'request_table': example_data.get('request_table', ''),
                        'response_table': example_data.get('response_table', '')
                    })
            except Exception as e:
                logger.error(f"Error loading example file {example_file}: {e}")
        
        return examples
    
    def _load_examples(self, prompt_type: str, user_query: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Load examples using database vector search with file-based fallback.
        
        Args:
            prompt_type: Prompt category type
            user_query: User's query text for relevance-based selection (optional)
            
        Returns:
            List of top 3 most relevant examples (or all available if less than 3)
        """
        # If no user query provided, fall back to file-based loading
        if not user_query:
            logger.info(f"No user query provided, loading all examples from files for {prompt_type}")
            return self._load_examples_from_files(prompt_type)
        
        try:
            # Attempt to load examples from database using vector search
            logger.info(f"Loading examples from database for category '{prompt_type}' with query: {user_query[:50]}...")
            examples = prompt_example_search.search_examples(
                query=user_query,
                category=prompt_type,
                search_mode="fulltext",
                limit=3
            )
            
            if examples:
                logger.info(f"Successfully loaded {len(examples)} examples from database")
                return examples
            else:
                logger.warning(f"No examples found in database for category '{prompt_type}', falling back to files")
                return self._load_examples_from_files(prompt_type)
                
        except Exception as e:
            # Fallback to file-based loading on any error
            logger.error(f"Error loading examples from database: {e}. Falling back to file-based loading.")
            return self._load_examples_from_files(prompt_type)
    
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
            prompt_parts.append(json.dumps(spreadsheet_data, ensure_ascii=False))
            prompt_parts.append("")
        
        return "\n".join(prompt_parts)

# Create global instance
prompt_builder = GigachatPromptBuilder()

