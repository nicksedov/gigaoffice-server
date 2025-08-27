"""
DryRunGigaChatService с интеграцией GigachatPromptBuilder
"""

import os
import json
import base64
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from app.services.gigachat.base import BaseGigaChatService

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

    def _generate_debug_table(self, query: str, input_range: Optional[str] = None, 
        category: Optional[str] = None,
        input_data: Optional[List[Dict]] = None) -> List[List[Any]]:
        """Генерация таблицы с отладочной информацией"""
        
        # Получаем переменные окружения
        env_vars = self._get_gigachat_env_vars()
        
        # Генерируем промпты используя GigachatPromptBuilder
        system_prompt = self.prompt_builder.prepare_system_prompt(category)
        user_prompt = self.prompt_builder.prepare_user_prompt(query, input_range, input_data)
        
        # Формируем таблицу
        result = [['Параметр', 'Значение']]
        
        # Добавляем переменные окружения
        result.append(['# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ GIGACHAT', ''])
        for env_var in env_vars:
            result.append(env_var)
        
        # Добавляем пользовательские данные
        result.append(['# ПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ', ''])
        result.append(['Промпт (запрос)', query])
        result.append(['Диапазон исходных данных', input_range or 'Не указан'])
        result.append(['Категория запроса', category or 'Не указана'])
        
        # Добавляем входные данные если есть
        if input_data:
            result.append(['Входные данные', json.dumps(input_data, ensure_ascii=False, indent=2)])
        
        # Добавляем сгенерированные промпты
        result.append(['# СГЕНЕРИРОВАННЫЕ ПРОМПТЫ', ''])
        result.append(['Системный промпт', system_prompt])
        result.append(['Пользовательский промпт', user_prompt])
        
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
            "category": {"name": "generation"},
            "confidence": 0.9
        }
        return fake_metadata

    async def process_query(
        self,
        query: str,
        input_range: Optional[str],
        category: Optional[str],
        input_data: Optional[List[Dict]] = None,
        temperature: float = 0.1
    ) -> Tuple[List[List[Any]], Dict[str, Any]]:
        """Обработка запроса с отображением отладочной информации"""
        
        self._add_request_time()
        time.sleep(0.2)  # Имитация обработки
        
        # Генерируем отладочную таблицу
        debug_result = self._generate_debug_table(query, input_range, category, input_data)
        
        fake_metadata = {
            "processing_time": 0.2,
            "input_tokens": 10,
            "output_tokens": 8,
            "total_tokens": 18,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "request_id": "dryrun-debug-123",
            "success": True
        }
        
        self.total_tokens_used += fake_metadata["total_tokens"]
        return debug_result, fake_metadata

    def _should_retry_error(self, error: Exception) -> bool:
        """
        Определяет, стоит ли повторять запрос при данной ошибке для dry-run режима
        
        Args:
            error: Исключение, которое произошло
        
        Returns:
            True, если ошибку можно повторить, False - если критичная
        """
        # In dry-run mode, we don't actually make requests, so no retries needed
        return False

    def _init_client(self):
        """Инициализация клиента (заглушка для dryrun)"""
        # In dry run mode, we don't initialize an actual client
        self.client = None