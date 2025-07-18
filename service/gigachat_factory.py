"""
GigaChat Factory
Фабрика для создания экземпляров GigaChat сервисов в зависимости от режима работы
"""

import os
from loguru import logger
from gigachat_prompt_builder import prompt_builder

def create_gigachat_service():
    """
    Фабричная функция для создания экземпляра GigaChat сервиса
    на основе переменной окружения GIGACHAT_RUN_MODE
    """
    run_mode = os.getenv("GIGACHAT_RUN_MODE", "dryrun").lower()
    
    logger.info(f"Creating GigaChat service in {run_mode} mode")
    
    if run_mode == "dryrun":
        from gigachat_service_dryrun import DryRunGigaChatService
        return DryRunGigaChatService(prompt_builder)
    
    elif run_mode == "cloud":
        from gigachat_service_cloud import CloudGigaChatService
        return CloudGigaChatService(prompt_builder)
    
    elif run_mode == "mtls":
        from gigachat_service_mtls import MtlsGigaChatService
        return MtlsGigaChatService(prompt_builder)
    
    else:
        logger.error(f"Unknown GIGACHAT_RUN_MODE: {run_mode}")
        raise ValueError(f"Unknown GIGACHAT_RUN_MODE: {run_mode}. Valid values: dryrun, cloud, mtls")

# Создаем глобальный экземпляр сервиса
gigachat_service = create_gigachat_service()

