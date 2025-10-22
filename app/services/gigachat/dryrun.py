"""
DryRunGigaChatService с интеграцией GigachatPromptBuilder
"""

import os
import json
import base64
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from app.services.gigachat.base import BaseGigaChatService
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

class MockGigaChatClient:
    """Mock client for dryrun mode that simulates GigaChat responses"""
    
    def __init__(self, service):
        self.service = service
    
    def _extract_data_from_user_prompt(self, content: str) -> Tuple[str, Optional[List[Dict]]]:
        """Extract query and input_data from user prompt"""
        user_query = ""
        input_data = None
        
        # Extract query from ЗАДАЧА line
        task_match = re.search(r'ЗАДАЧА:\s*(.+)', content)
        if task_match:
            user_query = task_match.group(1).strip()
        
        # Extract input data (JSON part)
        try:
            # Look for JSON data after "РАСШИРЕННЫЕ ДАННЫЕ ТАБЛИЦЫ:"
            data_section_match = re.search(r'РАСШИРЕННЫЕ ДАННЫЕ ТАБЛИЦЫ:\s*\n(.+?)(?=\n\n|\Z)', content, re.DOTALL)
            if data_section_match:
                json_content = data_section_match.group(1).strip()
                # Try to parse the JSON
                input_data = json.loads(json_content)
        except:
            pass
        
        return user_query, input_data
    
    def invoke(self, messages):
        """Generate and return debug table instead of mock response"""
        # Simulate processing delay
        time.sleep(0.2)
        
        # Extract information from messages
        user_query = ""
        category = None
        input_data = None
        
        # Parse messages to extract user query and other data
        for message in messages:
            if isinstance(message, HumanMessage) and hasattr(message, 'content'):
                content = message.content
                if isinstance(content, str):
                    # Try to extract query from user prompt
                    if "ЗАДАЧА:" in content:
                        # This is likely a user prompt, extract the data
                        user_query, input_data = self._extract_data_from_user_prompt(content)
                    else:
                        # Assume it's a simple query
                        user_query = content
                elif isinstance(content, list):
                    # Handle list content
                    user_query = " ".join(str(item) for item in content)
        
        # Generate debug table using the service's method
        debug_table = self.service._generate_debug_table(user_query, category, input_data)
        
        # Create a response with debug table
        response_content = json.dumps({
            'metadata': {
                'version': "1.0",
                'created_at': datetime.now().isoformat(),
            },
            'worksheet': {
                'name': "debug-table",
                'range': "A1"
            },
            'data': debug_table
        }, ensure_ascii=False)
        
        return AIMessage(content=response_content, id="dryrun-debug-response-id")

class DryRunGigaChatService(BaseGigaChatService):
    """Заглушка для GigaChat с отображением переменных окружения и промптов"""

    def __init__(self, prompt_builder, model=None):
        # Call parent constructor with prompt_builder and model
        super().__init__(prompt_builder, model)
        # Override model if needed
        self.model = model or "GigaChat-DryRun"
        logger.info("GigaChat client initialized successfully (DRY RUN mode)")

    def _get_gigachat_env_vars(self) -> List[List[str]]:
        """Получение всех переменных окружения с префиксом GIGACHAT"""
        env_vars = []
        
        for key, value in os.environ.items():
            if key.startswith("GIGACHAT_"):
                if key == "GIGACHAT_CREDENTIALS":
                    # Декодируем из BASE64 и маскируем после двоеточия
                    try:
                        decoded = base64.b64decode(value).decode('utf-8')
                        if ':' in decoded:
                            parts = decoded.split(':', 1)
                            masked_value = f"{parts[0]}:{'*' * len(parts[1])}"
                        else:
                            masked_value = decoded[:10] + '*' * max(0, len(decoded) - 10)
                        env_vars.append([key, masked_value])
                    except Exception:
                        env_vars.append([key, "***INVALID_BASE64***"])
                else:
                    env_vars.append([key, value])
        
        return env_vars

    def _generate_debug_table(self, query: str,  
        category: Optional[str] = None,
        input_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Генерация таблицы с отладочной информацией"""
        
        # Получаем переменные окружения
        env_vars = self._get_gigachat_env_vars()
        
        # Генерируем промпты используя GigachatPromptBuilder
        system_prompt = self.prompt_builder.prepare_system_prompt(category)
        user_prompt = self.prompt_builder.prepare_user_prompt(query, input_data)
        
        # Формируем таблицу
        result_rows = []
        result = {
            'header': {        
                'values': ['Параметр', 'Значение'],
                'style': 'header_style'
            },
            'styles': [{
                'id': 'header_style',
                'background_color': '#4472C4',
                'font_color': '#FFFFFF',
                'font_weight': 'bold'
            },
            {
                'id': 'chapter_style',
                'background_color': '#E0E0E0',
                'font_color': '#FFFFFF',
                'font_weight': 'bold'
            }],
            'rows': result_rows
        }
        
        # Добавляем переменные окружения
        result_rows.append({
            'values': ['# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ GIGACHAT', ''],
            'style': 'chapter_style'
        })
        for env_var in env_vars:
            result_rows.append({ 'values': env_var })
        
        # Добавляем пользовательские данные
        result_rows.append({
            'values': ['# ПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ', ''],
            'style': 'chapter_style'
        })
        result_rows.append({ 'values': ['Промпт (запрос)', query] })
        result_rows.append({ 'values': ['Категория запроса', category or 'Не указана'] })
        
        # Добавляем входные данные если есть
        if input_data:
            result_rows.append({ 'values': ['Входные данные', json.dumps(input_data, ensure_ascii=False, indent=2)] })
        
        # Добавляем сгенерированные промпты
        result_rows.append({ 
            'values': ['# СГЕНЕРИРОВАННЫЕ ПРОМПТЫ', ''],
            'style': 'chapter_style'
        })
        result_rows.append({ 'values': ['Системный промпт', system_prompt] })
        result_rows.append({ 'values': ['Пользовательский промпт', user_prompt] })
        
        return result

    async def classify_query(
        self,
        query: str,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Обработка запроса с отображением отладочной информации"""
        
        time.sleep(0.2)  # Имитация обработки
        
        fake_metadata = {
            "success": True,
            "query_text": query,
            "category": {"name": "spreadsheet-generation"},
            "confidence": 0.9
        }
        return fake_metadata


    def _init_client(self):
        """Инициализация клиента (заглушка для dryrun)"""
        # In dry run mode, we initialize a mock client instead of None
        self.client = MockGigaChatClient(self)
