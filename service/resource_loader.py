"""
Resource Loader Utility
Утилита для загрузки строковых ресурсов из файлов
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

class ResourceLoader:
    """Загрузчик ресурсов из файлов"""
    
    def __init__(self, resources_dir: str = "resources"):
        self.resources_dir = Path(resources_dir)
        self._cache = {}
        self._ensure_resources_dir()
    
    def _ensure_resources_dir(self):
        """Создает папку с ресурсами если её нет"""
        self.resources_dir.mkdir(parents=True, exist_ok=True)
    
    def load_text(self, resource_path: str, encoding: str = "utf-8") -> str:
        """
        Загружает текстовый ресурс из файла
        
        Args:
            resource_path: Путь к файлу относительно resources_dir
            encoding: Кодировка файла
            
        Returns:
            Содержимое файла как строка
        """
        cache_key = f"text:{resource_path}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            file_path = self.resources_dir / resource_path
            
            if not file_path.exists():
                logger.warning(f"Resource file not found: {file_path}")
                return ""
            
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                
            self._cache[cache_key] = content
            return content
            
        except Exception as e:
            logger.error(f"Error loading text resource {resource_path}: {e}")
            return ""
    
    def load_json(self, resource_path: str) -> Dict[str, Any]:
        """
        Загружает JSON ресурс из файла
        
        Args:
            resource_path: Путь к JSON файлу
            
        Returns:
            Parsed JSON как словарь
        """
        cache_key = f"json:{resource_path}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            file_path = self.resources_dir / resource_path
            
            if not file_path.exists():
                logger.warning(f"JSON resource file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self._cache[cache_key] = data
            return data
            
        except Exception as e:
            logger.error(f"Error loading JSON resource {resource_path}: {e}")
            return {}
    
    def load_sql(self, resource_path: str) -> str:
        """
        Загружает SQL запрос из файла
        
        Args:
            resource_path: Путь к SQL файлу
            
        Returns:
            SQL запрос как строка
        """
        return self.load_text(resource_path).strip()
    
    def get_message(self, message_key: str, category: str = "error_messages", **kwargs) -> str:
        """
        Получает сообщение по ключу с форматированием
        
        Args:
            message_key: Ключ сообщения
            category: Категория сообщений (error_messages, success_messages)
            **kwargs: Параметры для форматирования строки
            
        Returns:
            Отформатированное сообщение
        """
        try:
            messages = self.load_json(f"messages/{category}.json")
            template = messages.get(message_key, message_key)
            
            if kwargs:
                return template.format(**kwargs)
            return template
            
        except Exception as e:
            logger.error(f"Error getting message {message_key}: {e}")
            return message_key
    
    def get_config(self, config_name: str) -> Dict[str, Any]:
        """
        Получает конфигурацию из файла
        
        Args:
            config_name: Имя конфигурационного файла (без расширения)
            
        Returns:
            Конфигурация как словарь
        """
        return self.load_json(f"config/{config_name}.json")
    
    def get_prompt_template(self, prompt_name: str) -> str:
        """
        Получает шаблон промпта
        
        Args:
            prompt_name: Имя файла промпта
            
        Returns:
            Шаблон промпта
        """
        return self.load_text(f"prompts/{prompt_name}")
    
    def clear_cache(self):
        """Очищает кэш загруженных ресурсов"""
        self._cache.clear()
    
    def reload_resource(self, resource_path: str, resource_type: str = "text"):
        """
        Перезагружает ресурс из файла
        
        Args:
            resource_path: Путь к ресурсу
            resource_type: Тип ресурса (text, json)
        """
        cache_key = f"{resource_type}:{resource_path}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        if resource_type == "text":
            return self.load_text(resource_path)
        elif resource_type == "json":
            return self.load_json(resource_path)

# Глобальный экземпляр загрузчика
resource_loader = ResourceLoader()
