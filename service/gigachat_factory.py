import os
import json
from typing import Optional, List, Dict, Any
from resource_loader import resource_loader

"""
GigaChat Prompt Builder
Класс для формирования промптов для GigaChat API
"""
class GigachatPromptBuilder:
    """Класс для формирования промптов для GigaChat"""
    
    def __init__(self):
        pass
    
    def prepare_system_prompt(self) -> str:
        """Подготовка системного промпта для табличных данных"""
        return resource_loader.get_prompt_template("gigachat_system_prompt.txt")
    
    def prepare_user_prompt(self, query: str, input_data: Optional[List[Dict]] = None) -> str:
        """Подготовка пользовательского промпта"""
        prompt_parts = []
        
        if input_data:
            prompt_parts.append("ИСХОДНЫЕ ДАННЫЕ:")
            prompt_parts.append(json.dumps(input_data, ensure_ascii=False, indent=2))
            prompt_parts.append("")
        
        prompt_parts.append("ЗАДАЧА:")
        prompt_parts.append(query)
        prompt_parts.append("")
        prompt_parts.append("Предоставь ответ в виде JSON массива массивов, готового для вставки в таблицу.")
        
        return "\n".join(prompt_parts)

prompt_builder = GigachatPromptBuilder()

# Create global instance
if os.getenv("GIGACHAT_DRYRUN", "false").lower() == "true":
    from gigachat_dryrun import DryRunGigaChatService
    gigachat_service = DryRunGigaChatService(prompt_builder)
else:
    from gigachat_service import GigaChatService
    gigachat_service = GigaChatService(prompt_builder)
