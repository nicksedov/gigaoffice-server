"""
Resource Loader Utility
Enhanced utility for loading resources from files with improved caching and error handling
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from loguru import logger

from ..core.config import get_settings, get_resource_path


class ResourceLoader:
    """Enhanced resource loader with improved caching and error handling"""
    
    def __init__(self, resources_dir: Optional[str] = "resources"):
        if resources_dir:
            self.resources_dir = Path(resources_dir)
        else:
            settings = get_settings()
            self.resources_dir = settings.resources_path
            
        self._cache = {}
        self._file_timestamps = {}
        self._ensure_resources_dir()
    
    def _ensure_resources_dir(self):
        """Create resources directory if it doesn't exist"""
        self.resources_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, resource_path: str) -> Path:
        """Get absolute file path for resource"""
        return self.resources_dir / resource_path
    
    def _is_file_modified(self, file_path: Path, cache_key: str) -> bool:
        """Check if file has been modified since last load"""
        if not file_path.exists():
            return False
            
        current_mtime = file_path.stat().st_mtime
        cached_mtime = self._file_timestamps.get(cache_key, 0)
        
        return current_mtime != cached_mtime
    
    def _update_file_timestamp(self, file_path: Path, cache_key: str):
        """Update file timestamp in cache"""
        if file_path.exists():
            self._file_timestamps[cache_key] = file_path.stat().st_mtime
    
    def load_text(self, resource_path: str, encoding: str = "utf-8", 
                  use_cache: bool = True, reload_if_modified: bool = True) -> str:
        """
        Load text resource from file with improved caching
        
        Args:
            resource_path: Path to file relative to resources_dir
            encoding: File encoding
            use_cache: Whether to use caching
            reload_if_modified: Whether to reload if file is modified
            
        Returns:
            File content as string
        """
        cache_key = f"text:{resource_path}"
        file_path = self._get_file_path(resource_path)
        
        # Check cache and file modification
        if (use_cache and cache_key in self._cache and 
            (not reload_if_modified or not self._is_file_modified(file_path, cache_key))):
            return self._cache[cache_key]
            
        try:
            if not file_path.exists():
                logger.warning(f"Resource file not found: {file_path}")
                return ""
            
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            if use_cache:
                self._cache[cache_key] = content
                self._update_file_timestamp(file_path, cache_key)
                
            return content
            
        except Exception as e:
            logger.error(f"Error loading text resource {resource_path}: {e}")
            return ""
    
    def load_json(self, resource_path: str, use_cache: bool = True, 
                  reload_if_modified: bool = True) -> Dict[str, Any]:
        """
        Load JSON resource from file
        
        Args:
            resource_path: Path to JSON file
            use_cache: Whether to use caching
            reload_if_modified: Whether to reload if file is modified
            
        Returns:
            Parsed JSON as dictionary
        """
        cache_key = f"json:{resource_path}"
        file_path = self._get_file_path(resource_path)
        
        # Check cache and file modification
        if (use_cache and cache_key in self._cache and 
            (not reload_if_modified or not self._is_file_modified(file_path, cache_key))):
            return self._cache[cache_key]
            
        try:
            if not file_path.exists():
                logger.warning(f"JSON resource file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if use_cache:
                self._cache[cache_key] = data
                self._update_file_timestamp(file_path, cache_key)
                
            return data
            
        except Exception as e:
            logger.error(f"Error loading JSON resource {resource_path}: {e}")
            return {}
    
    def load_yaml(self, resource_path: str, use_cache: bool = True, 
                  reload_if_modified: bool = True) -> Dict[str, Any]:
        """
        Load YAML resource from file
        
        Args:
            resource_path: Path to YAML file
            use_cache: Whether to use caching
            reload_if_modified: Whether to reload if file is modified
            
        Returns:
            Parsed YAML as dictionary
        """
        cache_key = f"yaml:{resource_path}"
        file_path = self._get_file_path(resource_path)
        
        # Check cache and file modification
        if (use_cache and cache_key in self._cache and 
            (not reload_if_modified or not self._is_file_modified(file_path, cache_key))):
            return self._cache[cache_key]
            
        try:
            if not file_path.exists():
                logger.warning(f"YAML resource file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if use_cache:
                self._cache[cache_key] = data or {}
                self._update_file_timestamp(file_path, cache_key)
                
            return data or {}
            
        except Exception as e:
            logger.error(f"Error loading YAML resource {resource_path}: {e}")
            return {}
    
    def load_sql(self, resource_path: str) -> str:
        """
        Load SQL query from file
        
        Args:
            resource_path: Path to SQL file
            
        Returns:
            SQL query as string
        """
        return self.load_text(resource_path).strip()
    
    def get_message(self, message_key: str, category: str = "error_messages", **kwargs) -> str:
        """
        Get message by key with formatting
        
        Args:
            message_key: Message key
            category: Message category (error_messages, success_messages)
            **kwargs: Parameters for string formatting
            
        Returns:
            Formatted message
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
        Get configuration from file (supports both JSON and YAML)
        
        Args:
            config_name: Configuration file name (without extension)
            
        Returns:
            Configuration as dictionary
        """
        # Try JSON first, then YAML
        json_config = self.load_json(f"config/{config_name}.json")
        if json_config:
            return json_config
            
        yaml_config = self.load_yaml(f"config/{config_name}.yaml")
        if yaml_config:
            return yaml_config
            
        # Try .yml extension as well
        return self.load_yaml(f"config/{config_name}.yml")
    
    def get_prompt_template(self, prompt_name: str) -> str:
        """
        Get prompt template (supports .yaml, .yml, .txt files)
        
        Args:
            prompt_name: Prompt file name
            
        Returns:
            Prompt template
        """
        # Try different extensions
        for ext in ['.yaml', '.yml', '.txt', '']:
            if ext or not '.' in prompt_name:  # If no extension, try as-is
                file_name = f"{prompt_name}{ext}" if ext else prompt_name
                
                if ext in ['.yaml', '.yml']:
                    data = self.load_yaml(f"prompts/{file_name}")
                    if data:
                        # Return main prompt or template field
                        return data.get('template', data.get('prompt', str(data)))
                else:
                    content = self.load_text(f"prompts/{file_name}")
                    if content:
                        return content
        
        logger.warning(f"Prompt template not found: {prompt_name}")
        return ""
    
    def clear_cache(self):
        """Clear all cached resources"""
        self._cache.clear()
        self._file_timestamps.clear()
    
    def clear_cache_for_file(self, resource_path: str):
        """Clear cache for specific file"""
        keys_to_remove = [key for key in self._cache.keys() if key.endswith(f":{resource_path}")]
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._file_timestamps:
                del self._file_timestamps[key]
    
    def reload_resource(self, resource_path: str, resource_type: str = "auto") -> Union[str, Dict[str, Any]]:
        """
        Force reload resource from file
        
        Args:
            resource_path: Path to resource
            resource_type: Type of resource (auto, text, json, yaml)
            
        Returns:
            Loaded resource data
        """
        # Clear cache for this file
        self.clear_cache_for_file(resource_path)
        
        # Auto-detect type from extension
        if resource_type == "auto":
            ext = Path(resource_path).suffix.lower()
            if ext in ['.json']:
                resource_type = "json"
            elif ext in ['.yaml', '.yml']:
                resource_type = "yaml"
            else:
                resource_type = "text"
        
        # Load based on type
        if resource_type == "text":
            return self.load_text(resource_path, use_cache=True)
        elif resource_type == "json":
            return self.load_json(resource_path, use_cache=True)
        elif resource_type == "yaml":
            return self.load_yaml(resource_path, use_cache=True)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def list_resources(self, pattern: str = "*") -> list:
        """
        List available resources matching pattern
        
        Args:
            pattern: Glob pattern to match files
            
        Returns:
            List of resource paths
        """
        try:
            return [str(p.relative_to(self.resources_dir)) 
                   for p in self.resources_dir.glob(pattern) 
                   if p.is_file()]
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            return []


# Global resource loader instance
resource_loader = ResourceLoader()